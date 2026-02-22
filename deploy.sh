#!/bin/bash
set -e

# TechReformers Moltbook Agent Deployment Script
# This script deploys all AWS resources for the Moltbook agent

# Configuration
LAMBDA_NAME="moltbook-handler"
HEARTBEAT_LAMBDA_NAME="moltbook-heartbeat"
S3_BUCKET="techreformers-moltbook-deployment"
REGION="us-east-1"
AGENT_NAME="techreformers-moltbook-agent"
LAMBDA_ROLE_NAME="moltbook-lambda-role"
BEDROCK_AGENT_ROLE_NAME="moltbook-bedrock-agent-role"

echo "========================================="
echo "TechReformers Moltbook Agent Deployment"
echo "========================================="
echo ""

# Step 1: Check prerequisites
echo "[1/10] Checking prerequisites..."

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured"
    echo "Please run 'aws configure' or set AWS credentials"
    exit 1
fi

echo "✓ AWS credentials configured"

# Check secret exists
if ! aws secretsmanager describe-secret --secret-id moltbook/api-key --region $REGION &> /dev/null; then
    echo "ERROR: Secret moltbook/api-key not found in Secrets Manager"
    echo "Please create the secret with your Moltbook API key:"
    echo "  aws secretsmanager create-secret --name moltbook/api-key --secret-string '{\"api_key\":\"YOUR_KEY\"}' --region $REGION"
    exit 1
fi

echo "✓ Secret moltbook/api-key exists"

# Check required files
if [ ! -f "openapi_schema.json" ]; then
    echo "ERROR: openapi_schema.json not found"
    exit 1
fi

if [ ! -f "bedrock_agent_setup.py" ]; then
    echo "ERROR: bedrock_agent_setup.py not found"
    exit 1
fi

if [ ! -d "lambda" ]; then
    echo "ERROR: lambda/ directory not found"
    exit 1
fi

echo "✓ Required files present"
echo ""

# Step 2: Create S3 bucket if needed
echo "[2/10] Setting up S3 bucket..."

if aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: ${S3_BUCKET}"
    aws s3 mb "s3://${S3_BUCKET}" --region $REGION
    
    # Block public access
    aws s3api put-public-access-block \
        --bucket "${S3_BUCKET}" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    echo "✓ S3 bucket created"
else
    echo "✓ S3 bucket already exists"
fi
echo ""

# Step 3: Create Lambda execution role
echo "[3/10] Setting up Lambda IAM role..."

# Check if role exists
if ! aws iam get-role --role-name $LAMBDA_ROLE_NAME &> /dev/null; then
    echo "Creating Lambda execution role..."
    
    # Create trust policy
    cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    
    aws iam create-role \
        --role-name $LAMBDA_ROLE_NAME \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json
    
    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Create and attach Secrets Manager policy
    cat > /tmp/secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:*:secret:moltbook/api-key*"
    }
  ]
}
EOF
    
    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name SecretsManagerAccess \
        --policy-document file:///tmp/secrets-policy.json
    
    # Create and attach Bedrock policy
    cat > /tmp/bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    }
  ]
}
EOF
    
    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name BedrockInvokeModel \
        --policy-document file:///tmp/bedrock-policy.json
    
    echo "✓ Lambda role created"
    echo "Waiting 10 seconds for IAM role to propagate..."
    sleep 10
else
    echo "✓ Lambda role already exists"
fi

LAMBDA_ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
echo "Lambda Role ARN: $LAMBDA_ROLE_ARN"
echo ""

# Step 4: Package and upload main Lambda function
echo "[4/10] Packaging main Lambda function..."

# Create temp directory for packaging
rm -rf /tmp/lambda-package
mkdir -p /tmp/lambda-package

# Copy Lambda code
cp lambda/moltbook_handler.py /tmp/lambda-package/

# Install dependencies
pip3 install -r lambda/requirements.txt -t /tmp/lambda-package/ --quiet

# Create zip file
cd /tmp/lambda-package
zip -r /tmp/lambda-deployment.zip . > /dev/null
cd - > /dev/null

echo "✓ Lambda package created"

# Upload to S3
aws s3 cp /tmp/lambda-deployment.zip "s3://${S3_BUCKET}/lambda-deployment.zip"
echo "✓ Uploaded to S3"
echo ""

# Step 5: Deploy main Lambda function
echo "[5/10] Deploying main Lambda function..."

if aws lambda get-function --function-name $LAMBDA_NAME --region $REGION &> /dev/null; then
    echo "Updating existing Lambda function..."
    
    # Wait for Lambda to be ready
    echo "Waiting for Lambda to be ready..."
    for i in {1..30}; do
        STATE=$(aws lambda get-function --function-name $LAMBDA_NAME --region $REGION --query 'Configuration.State' --output text 2>/dev/null || echo "Pending")
        if [ "$STATE" = "Active" ]; then
            break
        fi
        sleep 2
    done
    
    aws lambda update-function-code \
        --function-name $LAMBDA_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key lambda-deployment.zip \
        --region $REGION > /dev/null
    
    # Wait for code update to complete
    sleep 5
    
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION > /dev/null
else
    echo "Creating Lambda function..."
    aws lambda create-function \
        --function-name $LAMBDA_NAME \
        --runtime python3.11 \
        --role $LAMBDA_ROLE_ARN \
        --handler moltbook_handler.lambda_handler \
        --code S3Bucket=$S3_BUCKET,S3Key=lambda-deployment.zip \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION > /dev/null
fi

LAMBDA_ARN=$(aws lambda get-function --function-name $LAMBDA_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "✓ Lambda function deployed"
echo "Lambda ARN: $LAMBDA_ARN"
echo ""

# Step 6: Package and upload heartbeat Lambda
echo "[6/10] Packaging heartbeat Lambda function..."

rm -rf /tmp/heartbeat-package
mkdir -p /tmp/heartbeat-package

cp heartbeat.py /tmp/heartbeat-package/

# Install dependencies (same as main Lambda)
pip3 install requests boto3 -t /tmp/heartbeat-package/ --quiet

cd /tmp/heartbeat-package
zip -r /tmp/heartbeat-deployment.zip . > /dev/null
cd - > /dev/null

aws s3 cp /tmp/heartbeat-deployment.zip "s3://${S3_BUCKET}/heartbeat-deployment.zip"
echo "✓ Heartbeat package uploaded to S3"
echo ""

# Step 7: Deploy heartbeat Lambda (will set env vars after Bedrock agent is created)
echo "[7/10] Deploying heartbeat Lambda function..."

if aws lambda get-function --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION &> /dev/null; then
    echo "Updating existing heartbeat Lambda..."
    
    # Wait for Lambda to be ready
    for i in {1..30}; do
        STATE=$(aws lambda get-function --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION --query 'Configuration.State' --output text 2>/dev/null || echo "Pending")
        if [ "$STATE" = "Active" ]; then
            break
        fi
        sleep 2
    done
    
    aws lambda update-function-code \
        --function-name $HEARTBEAT_LAMBDA_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key heartbeat-deployment.zip \
        --region $REGION > /dev/null
else
    echo "Creating heartbeat Lambda..."
    aws lambda create-function \
        --function-name $HEARTBEAT_LAMBDA_NAME \
        --runtime python3.11 \
        --role $LAMBDA_ROLE_ARN \
        --handler heartbeat.lambda_handler \
        --code S3Bucket=$S3_BUCKET,S3Key=heartbeat-deployment.zip \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION > /dev/null
fi

HEARTBEAT_LAMBDA_ARN=$(aws lambda get-function --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "✓ Heartbeat Lambda deployed"
echo "Heartbeat Lambda ARN: $HEARTBEAT_LAMBDA_ARN"
echo ""

# Step 8: Create Bedrock agent
echo "[8/10] Creating Bedrock agent..."

python3 bedrock_agent_setup.py \
    --agent-name $AGENT_NAME \
    --lambda-arn $LAMBDA_ARN \
    --region $REGION

# Get agent details from output file (bedrock_agent_setup.py should create this)
if [ -f "/tmp/bedrock_agent_info.json" ]; then
    AGENT_ID=$(cat /tmp/bedrock_agent_info.json | python3 -c "import sys, json; print(json.load(sys.stdin)['agent_id'])")
    AGENT_ALIAS_ID=$(cat /tmp/bedrock_agent_info.json | python3 -c "import sys, json; print(json.load(sys.stdin)['agent_alias_id'])")
    
    echo "✓ Bedrock agent created"
    echo "Agent ID: $AGENT_ID"
    echo "Agent Alias ID: $AGENT_ALIAS_ID"
else
    echo "WARNING: Could not retrieve agent details"
    AGENT_ID="UNKNOWN"
    AGENT_ALIAS_ID="TSTALIASID"
fi
echo ""

# Step 9: Update heartbeat Lambda with Bedrock agent environment variables
echo "[9/10] Configuring heartbeat Lambda environment..."

aws lambda update-function-configuration \
    --function-name $HEARTBEAT_LAMBDA_NAME \
    --environment "Variables={BEDROCK_AGENT_ID=${AGENT_ID},BEDROCK_AGENT_ALIAS_ID=${AGENT_ALIAS_ID}}" \
    --region $REGION > /dev/null

echo "✓ Heartbeat Lambda configured"
echo ""

# Step 10: Create EventBridge schedule
echo "[10/10] Setting up EventBridge schedule..."

# Create EventBridge rule
aws events put-rule \
    --name moltbook-heartbeat \
    --schedule-expression "rate(30 minutes)" \
    --state ENABLED \
    --region $REGION > /dev/null

# Add Lambda permission for EventBridge
aws lambda add-permission \
    --function-name $HEARTBEAT_LAMBDA_NAME \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${REGION}:$(aws sts get-caller-identity --query Account --output text):rule/moltbook-heartbeat" \
    --region $REGION 2>/dev/null || echo "Permission already exists"

# Add Lambda as target
aws events put-targets \
    --rule moltbook-heartbeat \
    --targets "Id=1,Arn=${HEARTBEAT_LAMBDA_ARN}" \
    --region $REGION > /dev/null

echo "✓ EventBridge schedule created"
echo ""

# Deployment summary
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Resources Created:"
echo "  Main Lambda: $LAMBDA_ARN"
echo "  Heartbeat Lambda: $HEARTBEAT_LAMBDA_ARN"
echo "  Bedrock Agent ID: $AGENT_ID"
echo "  Bedrock Agent Alias: $AGENT_ALIAS_ID"
echo "  S3 Bucket: s3://${S3_BUCKET}"
echo "  EventBridge Rule: moltbook-heartbeat (every 30 minutes)"
echo ""
echo "Next Steps:"
echo "  1. Test the Bedrock agent:"
echo "     aws bedrock-agent-runtime invoke-agent \\"
echo "       --agent-id $AGENT_ID \\"
echo "       --agent-alias-id $AGENT_ALIAS_ID \\"
echo "       --session-id test-session \\"
echo "       --input-text 'Check my status on Moltbook'"
echo ""
echo "  2. Monitor heartbeat executions in CloudWatch Logs"
echo "  3. View agent activity at https://www.moltbook.com/u/techreformers"
echo ""

#!/bin/bash
set -e

# TechReformers Moltbook Agent Deployment Script
# Deploys all three Lambda functions from source and sets up AWS infrastructure

# Configuration
PROFILE="jkdemo"
REGION="us-east-1"
LAMBDA_NAME="moltbook-handler"
HEARTBEAT_LAMBDA_NAME="moltbook-heartbeat"
NEWS_MONITOR_LAMBDA_NAME="moltbook-news-monitor"
S3_BUCKET="techreformers-moltbook-deployment"
AGENT_NAME="techreformers-moltbook-agent"
LAMBDA_ROLE_NAME="moltbook-lambda-role"
BEDROCK_AGENT_ROLE_NAME="moltbook-bedrock-agent-role"

export AWS_PROFILE="$PROFILE"

echo "========================================="
echo "TechReformers Moltbook Agent Deployment"
echo "========================================="
echo ""

# Step 1: Check prerequisites
echo "[1/12] Checking prerequisites..."

if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured for profile '$PROFILE'"
    echo "Please run 'aws configure --profile $PROFILE'"
    exit 1
fi

echo "✓ AWS credentials configured (profile: $PROFILE)"

if ! aws secretsmanager describe-secret --secret-id moltbook/api-key --region $REGION --cli-connect-timeout 10 --cli-read-timeout 10 &> /dev/null; then
    echo "ERROR: Secret moltbook/api-key not found in Secrets Manager"
    echo "Please create it:"
    echo "  aws secretsmanager create-secret --name moltbook/api-key --secret-string '{\"api_key\":\"YOUR_KEY\"}' --region $REGION --profile $PROFILE"
    exit 1
fi

echo "✓ Secret moltbook/api-key exists"

for f in openapi_schema.json bedrock_agent_setup.py; do
    if [ ! -f "$f" ]; then
        echo "ERROR: $f not found"
        exit 1
    fi
done

for d in lambda heartbeat_code news_monitor shared; do
    if [ ! -d "$d" ]; then
        echo "ERROR: $d/ directory not found"
        exit 1
    fi
done

echo "✓ Required files present"
echo ""

# Step 2: Create S3 bucket if needed
echo "[2/12] Setting up S3 bucket..."

if aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket: ${S3_BUCKET}"
    aws s3 mb "s3://${S3_BUCKET}" --region $REGION
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
echo "[3/12] Setting up Lambda IAM role..."

if ! aws iam get-role --role-name $LAMBDA_ROLE_NAME &> /dev/null; then
    echo "Creating Lambda execution role..."

    cat > /tmp/lambda-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "lambda.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    aws iam create-role \
        --role-name $LAMBDA_ROLE_NAME \
        --assume-role-policy-document file:///tmp/lambda-trust-policy.json

    aws iam attach-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

    cat > /tmp/secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:${REGION}:*:secret:moltbook/api-key*"
    }
  ]
}
EOF
    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name SecretsManagerAccess \
        --policy-document file:///tmp/secrets-policy.json

    cat > /tmp/bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    }
  ]
}
EOF
    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name BedrockInvokeModel \
        --policy-document file:///tmp/bedrock-policy.json

    cat > /tmp/dynamodb-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:*:table/aws-news-tracker",
        "arn:aws:dynamodb:${REGION}:*:table/moltbook-context"
      ]
    }
  ]
}
EOF
    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name DynamoDBAccess \
        --policy-document file:///tmp/dynamodb-policy.json

    cat > /tmp/ses-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail"],
      "Resource": "*"
    }
  ]
}
EOF
    aws iam put-role-policy \
        --role-name $LAMBDA_ROLE_NAME \
        --policy-name SESAccess \
        --policy-document file:///tmp/ses-policy.json

    echo "✓ Lambda role created"
    echo "Waiting 10 seconds for IAM role to propagate..."
    sleep 10
else
    echo "✓ Lambda role already exists"
fi

LAMBDA_ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
echo "Lambda Role ARN: $LAMBDA_ROLE_ARN"
echo ""

# Step 4: Package main Lambda (Bedrock agent handler)
echo "[4/12] Packaging main Lambda (moltbook-handler)..."

rm -rf /tmp/lambda-package
mkdir -p /tmp/lambda-package
cp lambda/moltbook_handler.py /tmp/lambda-package/
pip3 install -r lambda/requirements.txt -t /tmp/lambda-package/ --quiet
cd /tmp/lambda-package && zip -r /tmp/lambda-deployment.zip . > /dev/null && cd - > /dev/null
aws s3 cp /tmp/lambda-deployment.zip "s3://${S3_BUCKET}/lambda-deployment.zip"
echo "✓ Main Lambda packaged and uploaded"
echo ""

# Step 5: Deploy main Lambda
echo "[5/12] Deploying main Lambda (moltbook-handler)..."

if aws lambda get-function --function-name $LAMBDA_NAME --region $REGION &> /dev/null; then
    aws lambda wait function-updated --function-name $LAMBDA_NAME --region $REGION
    aws lambda update-function-code \
        --function-name $LAMBDA_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key lambda-deployment.zip \
        --region $REGION > /dev/null
    sleep 5
    aws lambda update-function-configuration \
        --function-name $LAMBDA_NAME \
        --timeout 60 \
        --memory-size 256 \
        --region $REGION > /dev/null
else
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
echo "✓ Main Lambda deployed: $LAMBDA_ARN"
echo ""

# Step 6: Package heartbeat Lambda
# heartbeat_code/heartbeat.py + shared/ (required for get_recent_context import)
echo "[6/12] Packaging heartbeat Lambda (moltbook-heartbeat)..."

rm -rf /tmp/heartbeat-package
mkdir -p /tmp/heartbeat-package
cp heartbeat_code/heartbeat.py /tmp/heartbeat-package/
cp -r shared /tmp/heartbeat-package/
pip3 install requests -t /tmp/heartbeat-package/ --quiet
cd /tmp/heartbeat-package && zip -r /tmp/heartbeat-deployment.zip . > /dev/null && cd - > /dev/null
aws s3 cp /tmp/heartbeat-deployment.zip "s3://${S3_BUCKET}/heartbeat-deployment.zip"
echo "✓ Heartbeat Lambda packaged and uploaded"
echo ""

# Step 7: Deploy heartbeat Lambda
echo "[7/12] Deploying heartbeat Lambda (moltbook-heartbeat)..."

if aws lambda get-function --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION &> /dev/null; then
    aws lambda wait function-updated --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION
    aws lambda update-function-code \
        --function-name $HEARTBEAT_LAMBDA_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key heartbeat-deployment.zip \
        --region $REGION > /dev/null
else
    aws lambda create-function \
        --function-name $HEARTBEAT_LAMBDA_NAME \
        --runtime python3.11 \
        --role $LAMBDA_ROLE_ARN \
        --handler heartbeat.lambda_handler \
        --code S3Bucket=$S3_BUCKET,S3Key=heartbeat-deployment.zip \
        --timeout 120 \
        --memory-size 256 \
        --region $REGION > /dev/null
fi

HEARTBEAT_LAMBDA_ARN=$(aws lambda get-function --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "✓ Heartbeat Lambda deployed: $HEARTBEAT_LAMBDA_ARN"
echo ""

# Step 8: Package news monitor Lambda
# news_monitor/monitor.py + news_monitor/sources.py + shared/ (required for ask_claude, send_email, etc.)
echo "[8/12] Packaging news monitor Lambda (moltbook-news-monitor)..."

rm -rf /tmp/news-monitor-package
mkdir -p /tmp/news-monitor-package
cp news_monitor/monitor.py /tmp/news-monitor-package/
cp news_monitor/sources.py /tmp/news-monitor-package/
cp -r shared /tmp/news-monitor-package/
pip3 install -r news_monitor/requirements.txt -t /tmp/news-monitor-package/ --quiet
cd /tmp/news-monitor-package && zip -r /tmp/news-monitor-deployment.zip . > /dev/null && cd - > /dev/null
aws s3 cp /tmp/news-monitor-deployment.zip "s3://${S3_BUCKET}/news-monitor-deployment.zip"
echo "✓ News monitor Lambda packaged and uploaded"
echo ""

# Step 9: Deploy news monitor Lambda
echo "[9/12] Deploying news monitor Lambda (moltbook-news-monitor)..."

if aws lambda get-function --function-name $NEWS_MONITOR_LAMBDA_NAME --region $REGION &> /dev/null; then
    aws lambda wait function-updated --function-name $NEWS_MONITOR_LAMBDA_NAME --region $REGION
    aws lambda update-function-code \
        --function-name $NEWS_MONITOR_LAMBDA_NAME \
        --s3-bucket $S3_BUCKET \
        --s3-key news-monitor-deployment.zip \
        --region $REGION > /dev/null
else
    aws lambda create-function \
        --function-name $NEWS_MONITOR_LAMBDA_NAME \
        --runtime python3.11 \
        --role $LAMBDA_ROLE_ARN \
        --handler monitor.lambda_handler \
        --code S3Bucket=$S3_BUCKET,S3Key=news-monitor-deployment.zip \
        --timeout 300 \
        --memory-size 256 \
        --region $REGION > /dev/null
fi

NEWS_MONITOR_LAMBDA_ARN=$(aws lambda get-function --function-name $NEWS_MONITOR_LAMBDA_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "✓ News monitor Lambda deployed: $NEWS_MONITOR_LAMBDA_ARN"
echo ""

# Step 10: Create Bedrock agent (skipped if already exists)
echo "[10/12] Setting up Bedrock agent..."

python3 bedrock_agent_setup.py \
    --agent-name $AGENT_NAME \
    --lambda-arn $LAMBDA_ARN \
    --region $REGION

if [ -f "/tmp/bedrock_agent_info.json" ]; then
    AGENT_ID=$(cat /tmp/bedrock_agent_info.json | python3 -c "import sys, json; print(json.load(sys.stdin)['agent_id'])")
    AGENT_ALIAS_ID=$(cat /tmp/bedrock_agent_info.json | python3 -c "import sys, json; print(json.load(sys.stdin)['agent_alias_id'])")
    echo "✓ Bedrock agent ready"
    echo "Agent ID: $AGENT_ID | Alias ID: $AGENT_ALIAS_ID"
else
    echo "WARNING: Could not retrieve agent details from bedrock_agent_setup.py"
    AGENT_ID="UNKNOWN"
    AGENT_ALIAS_ID="TSTALIASID"
fi
echo ""

# Step 11: Configure heartbeat Lambda environment variables
echo "[11/12] Configuring heartbeat Lambda environment..."

aws lambda wait function-updated --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION
aws lambda update-function-configuration \
    --function-name $HEARTBEAT_LAMBDA_NAME \
    --environment "Variables={BEDROCK_AGENT_ID=${AGENT_ID},BEDROCK_AGENT_ALIAS_ID=${AGENT_ALIAS_ID},USE_CONTEXT=true}" \
    --region $REGION > /dev/null

echo "✓ Heartbeat configured (USE_CONTEXT=true)"
echo ""

# Step 12: Set up EventBridge schedules
echo "[12/12] Setting up EventBridge schedules..."

# Heartbeat: every 30 minutes
aws events put-rule \
    --name moltbook-heartbeat \
    --schedule-expression "rate(30 minutes)" \
    --state ENABLED \
    --region $REGION > /dev/null

aws lambda add-permission \
    --function-name $HEARTBEAT_LAMBDA_NAME \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${REGION}:$(aws sts get-caller-identity --query Account --output text):rule/moltbook-heartbeat" \
    --region $REGION 2>/dev/null || echo "  (heartbeat permission already exists)"

aws events put-targets \
    --rule moltbook-heartbeat \
    --targets "Id=1,Arn=${HEARTBEAT_LAMBDA_ARN}" \
    --region $REGION > /dev/null

# News monitor: every 6 hours
aws events put-rule \
    --name moltbook-news-monitor \
    --schedule-expression "rate(6 hours)" \
    --state ENABLED \
    --region $REGION > /dev/null

aws lambda add-permission \
    --function-name $NEWS_MONITOR_LAMBDA_NAME \
    --statement-id EventBridgeInvoke \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "arn:aws:events:${REGION}:$(aws sts get-caller-identity --query Account --output text):rule/moltbook-news-monitor" \
    --region $REGION 2>/dev/null || echo "  (news monitor permission already exists)"

aws events put-targets \
    --rule moltbook-news-monitor \
    --targets "Id=1,Arn=${NEWS_MONITOR_LAMBDA_ARN}" \
    --region $REGION > /dev/null

echo "✓ EventBridge schedules set (heartbeat: 30min, news monitor: 6hr)"
echo ""

# Summary
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Lambdas deployed:"
echo "  moltbook-handler:      $LAMBDA_ARN"
echo "  moltbook-heartbeat:    $HEARTBEAT_LAMBDA_ARN"
echo "  moltbook-news-monitor: $NEWS_MONITOR_LAMBDA_ARN"
echo ""
echo "Bedrock Agent ID: $AGENT_ID | Alias: $AGENT_ALIAS_ID"
echo ""
echo "To test the heartbeat manually:"
echo "  aws lambda invoke --function-name $HEARTBEAT_LAMBDA_NAME --region $REGION --log-type Tail test-response.json"
echo ""
echo "To enable news context in heartbeat:"
echo "  aws lambda update-function-configuration \\"
echo "    --function-name $HEARTBEAT_LAMBDA_NAME \\"
echo "    --environment 'Variables={BEDROCK_AGENT_ID=${AGENT_ID},BEDROCK_AGENT_ALIAS_ID=${AGENT_ALIAS_ID},USE_CONTEXT=true}' \\"
echo "    --region $REGION"
echo ""

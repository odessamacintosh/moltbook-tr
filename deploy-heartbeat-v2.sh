#!/bin/bash
set -e

REGION="us-east-1"
PROFILE="jkdemo"
FUNCTION_NAME="moltbook-heartbeat"
ROLE_NAME="moltbook-lambda-role"
ACCOUNT_ID="352486303890"

echo "=== Phase 4: Heartbeat Context Integration ==="
echo ""

# Step 1: Add DynamoDB permissions to IAM role
echo "Step 1: Adding DynamoDB permissions to IAM role..."
aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name HeartbeatDynamoDBAccess \
  --policy-document file://infrastructure/heartbeat-dynamodb-policy.json \
  --profile $PROFILE \
  --region $REGION

echo "✅ IAM policy added"
echo ""

# Step 2: Deploy updated Lambda code
echo "Step 2: Deploying updated Lambda code..."
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://heartbeat-v2.zip \
  --profile $PROFILE \
  --region $REGION

echo "✅ Lambda code updated"
echo ""

# Step 3: Set environment variables with feature flag OFF
echo "Step 3: Setting environment variables (USE_CONTEXT=false)..."
aws lambda update-function-configuration \
  --function-name $FUNCTION_NAME \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=false}" \
  --profile $PROFILE \
  --region $REGION

echo "✅ Environment variables set (context disabled by default)"
echo ""

# Wait for Lambda to be ready
echo "Waiting for Lambda to be ready..."
aws lambda wait function-updated \
  --function-name $FUNCTION_NAME \
  --profile $PROFILE \
  --region $REGION

echo "✅ Lambda is ready"
echo ""

# Step 4: Test with feature flag OFF
echo "Step 4: Testing with feature flag OFF (should work like before)..."
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --profile $PROFILE \
  --region $REGION \
  --log-type Tail \
  test-response-flag-off.json

echo ""
echo "Response:"
cat test-response-flag-off.json
echo ""
echo "✅ Test with flag OFF complete"
echo ""

# Step 5: Instructions for enabling context
echo "=== Deployment Complete ==="
echo ""
echo "The heartbeat has been updated with context integration capability."
echo "Feature flag is currently OFF - bot works exactly as before."
echo ""
echo "To enable context integration (after verifying everything works):"
echo ""
echo "aws lambda update-function-configuration \\"
echo "  --function-name $FUNCTION_NAME \\"
echo "  --environment \"Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=true}\" \\"
echo "  --profile $PROFILE \\"
echo "  --region $REGION"
echo ""
echo "To test with context enabled:"
echo ""
echo "aws lambda invoke \\"
echo "  --function-name $FUNCTION_NAME \\"
echo "  --profile $PROFILE \\"
echo "  --region $REGION \\"
echo "  --log-type Tail \\"
echo "  test-response-context-on.json"
echo ""
echo "To disable context (rollback):"
echo ""
echo "aws lambda update-function-configuration \\"
echo "  --function-name $FUNCTION_NAME \\"
echo "  --environment \"Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=false}\" \\"
echo "  --profile $PROFILE \\"
echo "  --region $REGION"
echo ""

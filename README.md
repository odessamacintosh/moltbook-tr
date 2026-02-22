# TechReformers Moltbook Agent

An AWS Bedrock-powered AI agent that maintains an active presence on [Moltbook](https://www.moltbook.com), a social network for AI agents. The agent autonomously creates posts, comments, upvotes content, and performs semantic searches while respecting platform rate limits.

## Architecture

The system consists of three main components:

1. **AWS Bedrock Agent** - Provides AI reasoning and decision-making using Claude Sonnet
2. **Lambda Functions** - Execute Moltbook API calls and periodic heartbeat operations
3. **EventBridge Scheduler** - Triggers heartbeat checks every 30 minutes

## Prerequisites

Before deploying, ensure you have:

### 1. AWS Account and Credentials

- AWS account with appropriate permissions
- AWS CLI installed and configured
- Permissions required:
  - IAM role creation and policy management
  - Lambda function creation and management
  - Bedrock agent creation and management
  - S3 bucket creation
  - EventBridge rule creation
  - Secrets Manager access

### 2. Moltbook API Key

Create a secret in AWS Secrets Manager with your Moltbook API key:

```bash
aws secretsmanager create-secret \
  --name moltbook/api-key \
  --secret-string '{"api_key":"YOUR_MOLTBOOK_API_KEY"}' \
  --region us-east-1
```

Get your API key from [Moltbook](https://www.moltbook.com) after creating an agent account.

### 3. Python and Dependencies

- Python 3.11 or later
- pip package manager
- Required Python packages (installed automatically during deployment):
  - boto3
  - requests

### 4. Required Files

Ensure these files are present in your project directory:

- `lambda/moltbook_handler.py` - Main Lambda handler
- `lambda/requirements.txt` - Lambda dependencies
- `heartbeat.py` - Heartbeat Lambda function
- `bedrock_agent_setup.py` - Bedrock agent setup script
- `openapi_schema.json` - OpenAPI schema for action groups
- `deploy.sh` - Deployment script

## Deployment

### Quick Start

1. Clone the repository and navigate to the project directory

2. Ensure AWS credentials are configured:
   ```bash
   aws sts get-caller-identity
   ```

3. Create the Moltbook API key secret (if not already done):
   ```bash
   aws secretsmanager create-secret \
     --name moltbook/api-key \
     --secret-string '{"api_key":"YOUR_API_KEY"}' \
     --region us-east-1
   ```

4. Run the deployment script:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

The deployment script will:
- Check prerequisites
- Create S3 bucket for deployment artifacts
- Create IAM roles with appropriate permissions
- Package and deploy Lambda functions
- Create Bedrock agent with action groups
- Set up EventBridge schedule for heartbeat
- Output all resource ARNs and next steps

### Deployment Steps Explained

The `deploy.sh` script performs the following steps:

1. **Prerequisites Check** - Verifies AWS credentials and Moltbook API key secret
2. **S3 Bucket Setup** - Creates deployment bucket with public access blocked
3. **Lambda IAM Role** - Creates role with Secrets Manager and Bedrock permissions
4. **Main Lambda Deployment** - Packages and deploys moltbook-handler function
5. **Heartbeat Lambda Deployment** - Packages and deploys heartbeat function
6. **Bedrock Agent Setup** - Creates agent with Claude Sonnet model
7. **Action Group Configuration** - Attaches OpenAPI schema to agent
8. **Agent Instructions** - Configures TechReformers persona
9. **EventBridge Schedule** - Sets up 30-minute heartbeat trigger
10. **Summary Output** - Displays all resource ARNs and next steps

## Configuration

### Environment Variables

For local development, create a `.env` file (see `.env.example`):

```bash
MOLTBOOK_API_KEY=your_api_key_here
BEDROCK_AGENT_ID=your_agent_id
BEDROCK_AGENT_ALIAS_ID=your_alias_id
```

In production, the Lambda functions retrieve the API key from AWS Secrets Manager.

### Agent Persona

The agent is configured with the following persona:

- **Name**: TechReformers
- **Profile**: https://www.moltbook.com/u/techreformers
- **Expertise**: AWS cloud architecture, AI/ML implementation, enterprise training
- **Behavior**: Share valuable insights, engage thoughtfully, maintain professionalism

### Rate Limits

The agent respects Moltbook's rate limits:

- **Posts**: Maximum 1 per 30 minutes
- **Comments**: Maximum 1 per 20 seconds

The heartbeat Lambda enforces these limits automatically.

## Usage

### Invoking the Agent Manually

You can invoke the Bedrock agent directly using the AWS CLI:

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id YOUR_AGENT_ID \
  --agent-alias-id YOUR_ALIAS_ID \
  --session-id test-session-$(date +%s) \
  --input-text "Check my status on Moltbook" \
  --region us-east-1 \
  output.txt

cat output.txt
```

### Available Actions

The agent can perform the following actions:

- **getFeed** - Browse recent posts (sort: hot/new/top/rising)
- **getStatus** - Check agent claim status and activity
- **createPost** - Create a new post (requires submolt, title, content)
- **addComment** - Comment on a post (requires post_id, content)
- **upvotePost** - Upvote a post (requires post_id)
- **searchPosts** - Semantic search (requires query, optional type filter)
- **getProfile** - View agent profile information

### Heartbeat Mechanism

The heartbeat Lambda runs every 30 minutes and:

1. Checks agent status on Moltbook
2. Determines if a new post should be created
3. Invokes Bedrock agent to create post if conditions are met
4. Logs all activity to CloudWatch

The heartbeat ensures the agent maintains an active presence without manual intervention.

## Monitoring

### CloudWatch Logs

Monitor agent activity in CloudWatch Logs:

- **Main Lambda**: `/aws/lambda/moltbook-handler`
- **Heartbeat Lambda**: `/aws/lambda/moltbook-heartbeat`

### Moltbook Profile

View agent activity at: https://www.moltbook.com/u/techreformers

## Troubleshooting

### Deployment Fails with "Secret not found"

Ensure the Moltbook API key secret exists:

```bash
aws secretsmanager describe-secret --secret-id moltbook/api-key --region us-east-1
```

If not found, create it:

```bash
aws secretsmanager create-secret \
  --name moltbook/api-key \
  --secret-string '{"api_key":"YOUR_API_KEY"}' \
  --region us-east-1
```

### Lambda Function Fails with Permission Errors

Check that the Lambda execution role has the required permissions:

```bash
aws iam get-role --role-name moltbook-lambda-role
aws iam list-role-policies --role-name moltbook-lambda-role
```

### Bedrock Agent Not Responding

1. Check agent status:
   ```bash
   aws bedrock-agent get-agent --agent-id YOUR_AGENT_ID --region us-east-1
   ```

2. Verify agent is in "PREPARED" status

3. Check CloudWatch logs for errors

### Verification Challenges Failing

The agent uses Bedrock Claude to solve Moltbook's verification challenges. If challenges fail:

1. Check CloudWatch logs for the challenge text and attempted answer
2. Verify Bedrock InvokeModel permission is granted
3. Ensure Claude Sonnet model is available in your region

### Heartbeat Not Creating Posts

Check the heartbeat Lambda logs to see why posts aren't being created:

- Claim status may not be "active"
- Less than 30 minutes since last post
- Rate limit safety check triggered

## Development

### Local Testing

For local development, set environment variables:

```bash
export MOLTBOOK_API_KEY=your_api_key
export BEDROCK_AGENT_ID=your_agent_id
export BEDROCK_AGENT_ALIAS_ID=your_alias_id
```

Test the Lambda handler locally:

```python
from lambda.moltbook_handler import lambda_handler

event = {
    "actionGroup": "moltbook-actions",
    "apiPath": "/status",
    "httpMethod": "GET",
    "parameters": []
}

result = lambda_handler(event, None)
print(result)
```

### Running Tests

Property-based tests are available in the `tests/` directory:

```bash
pip install -r requirements-test.txt
pytest tests/
```

## Cleanup

To remove all deployed resources:

```bash
# Delete EventBridge rule
aws events remove-targets --rule moltbook-heartbeat --ids 1 --region us-east-1
aws events delete-rule --name moltbook-heartbeat --region us-east-1

# Delete Lambda functions
aws lambda delete-function --function-name moltbook-handler --region us-east-1
aws lambda delete-function --function-name moltbook-heartbeat --region us-east-1

# Delete Bedrock agent
aws bedrock-agent delete-agent --agent-id YOUR_AGENT_ID --region us-east-1

# Delete IAM roles
aws iam delete-role-policy --role-name moltbook-lambda-role --policy-name SecretsManagerAccess
aws iam delete-role-policy --role-name moltbook-lambda-role --policy-name BedrockInvokeModel
aws iam detach-role-policy --role-name moltbook-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name moltbook-lambda-role

# Delete S3 bucket (empty it first)
aws s3 rm s3://techreformers-moltbook-deployment --recursive
aws s3 rb s3://techreformers-moltbook-deployment

# Optionally delete the secret
aws secretsmanager delete-secret --secret-id moltbook/api-key --force-delete-without-recovery --region us-east-1
```

## License

Copyright © 2024 Tech Reformers LLC. All rights reserved.

## Support

For issues or questions:
- Check the troubleshooting section above
- Review CloudWatch logs for error details
- Contact Tech Reformers support

## Resources

- [Moltbook](https://www.moltbook.com) - AI agent social network
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Tech Reformers](https://www.techreformers.com) - AWS Advanced Services Partner

# TechReformers Moltbook Agent

An AWS-powered autonomous AI agent for [Tech Reformers LLC](https://www.techreformers.com), an AWS Advanced Services Partner and Authorized Training Provider. The system does two things:

1. **Heartbeat** — Autonomously posts and comments on [Moltbook](https://www.moltbook.com) (a social network for AI agents) every 30 minutes, representing TechReformers with expert AWS and cloud training insights.

2. **News Monitor** — Monitors AWS RSS feeds every 6 hours and emails ready-to-use Twitter, LinkedIn, and blog content framed around AWS certification and enterprise training implications.

## Architecture

Three Lambda functions, all driven by EventBridge schedules:

| Lambda | Schedule | Purpose |
|---|---|---|
| `moltbook-heartbeat` | Every 30 min | Reads Moltbook feed, asks Claude to post or comment, solves verification challenges |
| `moltbook-news-monitor` | Every 6 hours | Polls AWS RSS feeds, generates cert-focused training content, emails results |
| `moltbook-handler` | On-demand | Bedrock agent action handler (Moltbook API actions) |

**AWS services used:** Lambda, Bedrock (Claude Sonnet), EventBridge, DynamoDB, SES, Secrets Manager, S3, IAM

## Project Structure

```
moltbook-agent/
├── heartbeat_code/
│   └── heartbeat.py          # Heartbeat Lambda — posts/comments on Moltbook
├── lambda/
│   ├── moltbook_handler.py   # Bedrock agent action handler
│   └── requirements.txt
├── news_monitor/
│   ├── monitor.py            # News monitor Lambda — RSS → email pipeline
│   ├── sources.py            # RSS feed config and keyword filtering
│   └── requirements.txt
├── shared/
│   └── utils.py              # Shared utilities (ask_claude, send_email, DynamoDB helpers)
├── infrastructure/
│   └── tables.json           # DynamoDB table definitions
├── bedrock_agent_setup.py    # Bedrock agent and action group creation
├── openapi_schema.json       # OpenAPI schema for Bedrock action groups
├── deploy.sh                 # Full deployment script (all 3 Lambdas + infrastructure)
└── test-lambda.sh            # Test script for invoking individual Lambdas
```

## Prerequisites

### 1. AWS Account and CLI

- AWS CLI installed and configured with a named profile
- The default profile in `deploy.sh` is `jkdemo` — edit this at the top of the script if yours differs
- Region: `us-east-1` (also configurable in `deploy.sh`)
- Required permissions: IAM, Lambda, Bedrock, S3, EventBridge, Secrets Manager, DynamoDB, SES

### 2. Moltbook API Key

Create a Moltbook agent account at [moltbook.com](https://www.moltbook.com), then store your API key in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name moltbook/api-key \
  --secret-string '{"api_key":"YOUR_MOLTBOOK_API_KEY"}' \
  --region us-east-1 \
  --profile YOUR_PROFILE
```

### 3. SES Verified Email Addresses

The news monitor sends emails via SES. Verify your sender and recipient addresses:

```bash
aws ses verify-email-identity --email-address sender@yourdomain.com --region us-east-1
aws ses verify-email-identity --email-address recipient@yourdomain.com --region us-east-1
```

The defaults in `shared/utils.py` are `jkrull@techreformers.com` (sender) and `john@techreformers.com` (recipient). Update these or set them via Lambda environment variables (`SENDER_EMAIL`, `RECIPIENT_EMAIL`).

### 4. DynamoDB Tables

Create the two required tables before deploying:

```bash
# News deduplication table
aws dynamodb create-table \
  --table-name aws-news-tracker \
  --attribute-definitions AttributeName=item_hash,AttributeType=S \
  --key-schema AttributeName=item_hash,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Moltbook context table (heartbeat reads from this)
aws dynamodb create-table \
  --table-name moltbook-context \
  --attribute-definitions AttributeName=context_id,AttributeType=S \
  --key-schema AttributeName=context_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 5. Python 3.11+

Required locally only for the deployment packaging step (`pip3` must be available).

## Deployment

```bash
git clone https://github.com/odessamacintosh/moltbook-tr.git
cd moltbook-tr

# Edit PROFILE at the top of deploy.sh to match your AWS CLI profile
chmod +x deploy.sh
./deploy.sh
```

The script runs 12 steps:
1. Checks prerequisites (credentials, Moltbook secret)
2. Creates S3 deployment bucket
3. Creates Lambda IAM role with all required policies
4. Packages and deploys `moltbook-handler`
5. Packages and deploys `moltbook-heartbeat` (includes `shared/`)
6. Packages and deploys `moltbook-news-monitor` (includes `shared/`)
7. Creates/updates Bedrock agent
8. Configures heartbeat Lambda environment variables
9. Sets up EventBridge schedules (heartbeat: 30min, news monitor: 6hr)

After deployment, the script prints all Lambda ARNs, Bedrock Agent ID, and test commands.

## Testing

Use `test-lambda.sh` to invoke any Lambda and see decoded CloudWatch logs:

```bash
chmod +x test-lambda.sh

./test-lambda.sh --heartbeat   # Test heartbeat (will post or comment on Moltbook)
./test-lambda.sh --news        # Test news monitor (checks feeds, emails if new content)
./test-lambda.sh --handler     # Test Bedrock action handler
./test-lambda.sh --all         # Test all three in sequence
```

## How It Works

### Heartbeat

Every 30 minutes the heartbeat Lambda:
1. Checks Moltbook claim status (skips if not claimed)
2. Fetches the top 10 hot posts from the feed
3. Asks Claude (via Bedrock) to decide: comment on an existing post or create a new one
4. Submits the comment or post via the Moltbook API
5. If Moltbook returns a verification challenge (obfuscated math word problem), solves it with Claude and submits the answer
6. Optionally references recent AWS news context from DynamoDB (controlled by `USE_CONTEXT` env var)

Claude's response format:
```
COMMENT: <post_id> | <comment text, can be multi-paragraph>
POST: <title> | <content, can be multi-paragraph>
```

### News Monitor

Every 6 hours the news monitor Lambda:
1. Polls 4 AWS RSS feeds (What's New, Training Blog, Architecture Blog, Security Blog)
2. Filters for AWS announcements using keyword matching
3. Deduplicates against DynamoDB (`aws-news-tracker`) to avoid reprocessing
4. For each new item, asks Claude to generate:
   - **Twitter** (280 chars): cert/career angle with specific exam domains
   - **LinkedIn** (1300 chars): opens with "If you're studying for [cert]..." hook
   - **Blog outline**: section headings + cert domain mapping table
   - **Moltbook context**: one sentence for the heartbeat to reference
5. Emails the generated content via SES
6. Stores the Moltbook context sentence in DynamoDB (`moltbook-context`) for the heartbeat to use

### Verification Challenges

Moltbook uses obfuscated math word problems as anti-spam. Example:
```
A] lOo.oBbStt-Er] cLaW] fO^rCe] iSs] tW/eNn-Ty] fIiVee] neOoToOnS] pEr] cLaW...
```

The heartbeat solves these by calling Claude with a dedicated math-solver system prompt, extracting the last number from the response with regex, and submitting the answer as a string with 2 decimal places (e.g. `"50.00"`).

## Configuration

### AWS Profile

Edit the `PROFILE` variable at the top of `deploy.sh`:
```bash
PROFILE="jkdemo"   # Change to your AWS CLI profile name
```

### USE_CONTEXT Feature Flag

Controls whether the heartbeat references recent AWS news in its posts/comments:

```bash
# Enable (recommended once news monitor has been running)
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment 'Variables={BEDROCK_AGENT_ID=YOUR_ID,BEDROCK_AGENT_ALIAS_ID=YOUR_ALIAS,USE_CONTEXT=true}' \
  --region us-east-1

# Disable
# Change USE_CONTEXT=true to USE_CONTEXT=false in the above command
```

`deploy.sh` sets `USE_CONTEXT=true` by default.

### News Sources

Edit `news_monitor/sources.py` to add/remove RSS feeds or adjust per-feed limits:

```python
NEWS_SOURCES = {
    'aws_whats_new': {
        'url': 'https://aws.amazon.com/about-aws/whats-new/recent/feed/',
        'limit': 5,
        'training_relevance': 'high'
    },
    # Add more sources here
}
```

### Agent Persona

The TechReformers persona is defined in `heartbeat_code/heartbeat.py` in the `ask_claude` default system prompt and the `system_prompt` string built in `lambda_handler`. Edit these to adapt the agent for a different organization.

## Monitoring

CloudWatch log groups for all three Lambdas:

```
/aws/lambda/moltbook-heartbeat
/aws/lambda/moltbook-news-monitor
/aws/lambda/moltbook-handler
```

View agent activity on Moltbook: [moltbook.com/u/techreformers](https://www.moltbook.com/u/techreformers)

## Troubleshooting

**Deployment hangs at prerequisites check**
SSO token refresh can take time. Wait 30 seconds and retry, or run `aws sso login --profile YOUR_PROFILE` in a terminal first.

**Heartbeat runs but nothing appears on Moltbook**
Check CloudWatch logs and look for the `Action line:` log entry. If it's empty, Claude didn't follow the format — the prompt will retry on the next invocation. If `Action line:` has content but the post still doesn't appear, check the API response logged after it.

**Verification challenges failing**
Look for `Computed answer:` in the logs. If the raw Claude response contains non-numeric text, the regex extraction may have failed. The math-solver prompt is in `solve_verification()` in `heartbeat.py`.

**News monitor sends 0 items**
All current feed items have already been processed and stored in DynamoDB. New emails will arrive automatically when AWS publishes new announcements.

**answer must be a string error**
The verification answer must be submitted as a string like `"50.00"`, not a float. See `solve_verification()` in `heartbeat.py`.

## Cleanup

```bash
# EventBridge rules
aws events remove-targets --rule moltbook-heartbeat --ids 1 --region us-east-1
aws events delete-rule --name moltbook-heartbeat --region us-east-1
aws events remove-targets --rule moltbook-news-monitor --ids 1 --region us-east-1
aws events delete-rule --name moltbook-news-monitor --region us-east-1

# Lambda functions
aws lambda delete-function --function-name moltbook-handler --region us-east-1
aws lambda delete-function --function-name moltbook-heartbeat --region us-east-1
aws lambda delete-function --function-name moltbook-news-monitor --region us-east-1

# Bedrock agent (get ID from deploy output)
aws bedrock-agent delete-agent --agent-id YOUR_AGENT_ID --region us-east-1

# IAM role
aws iam delete-role-policy --role-name moltbook-lambda-role --policy-name SecretsManagerAccess
aws iam delete-role-policy --role-name moltbook-lambda-role --policy-name BedrockInvokeModel
aws iam delete-role-policy --role-name moltbook-lambda-role --policy-name DynamoDBAccess
aws iam delete-role-policy --role-name moltbook-lambda-role --policy-name SESAccess
aws iam detach-role-policy --role-name moltbook-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam delete-role --role-name moltbook-lambda-role

# DynamoDB tables
aws dynamodb delete-table --table-name aws-news-tracker --region us-east-1
aws dynamodb delete-table --table-name moltbook-context --region us-east-1

# S3 bucket
aws s3 rm s3://techreformers-moltbook-deployment --recursive
aws s3 rb s3://techreformers-moltbook-deployment

# Secrets Manager
aws secretsmanager delete-secret \
  --secret-id moltbook/api-key \
  --force-delete-without-recovery \
  --region us-east-1
```

## License

Copyright © 2026 Tech Reformers LLC. All rights reserved.

# Design Document: TechReformers Moltbook Agent

## Overview

The TechReformers Moltbook Agent is an AWS-native serverless application that enables autonomous interaction with the Moltbook social network. The system consists of three main components:

1. **AWS Bedrock Agent** - Provides AI reasoning and decision-making using Claude Sonnet
2. **Lambda Functions** - Execute Moltbook API calls and periodic heartbeat operations
3. **Deployment Infrastructure** - Automates resource provisioning and configuration

The agent maintains an active presence on Moltbook by creating posts, commenting, upvoting content, and performing semantic searches while respecting platform rate limits and solving verification challenges automatically.

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Cloud Environment                    │
│                                                               │
│  ┌──────────────────┐         ┌─────────────────────┐       │
│  │  Bedrock Agent   │────────▶│  Lambda Handler     │       │
│  │  (Claude Sonnet) │         │  (API Executor)     │       │
│  └──────────────────┘         └─────────────────────┘       │
│         │                              │                     │
│         │                              │                     │
│         │                              ▼                     │
│         │                     ┌─────────────────────┐       │
│         │                     │  Secrets Manager    │       │
│         │                     │  (API Key Storage)  │       │
│         │                     └─────────────────────┘       │
│         │                              │                     │
│         │                              │                     │
│         ▼                              ▼                     │
│  ┌──────────────────────────────────────────────┐           │
│  │         Moltbook API (External)              │           │
│  │         https://www.moltbook.com/api/v1      │           │
│  └──────────────────────────────────────────────┘           │
│                                                               │
│  ┌──────────────────┐         ┌─────────────────────┐       │
│  │  EventBridge     │────────▶│  Heartbeat Lambda   │       │
│  │  (30 min timer)  │         │  (Status Check)     │       │
│  └──────────────────┘         └─────────────────────┘       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Invocation**: User or system invokes Bedrock agent with a request
2. **Agent Reasoning**: Bedrock agent processes request and determines action
3. **Action Execution**: Agent invokes Lambda handler via action group
4. **API Call**: Lambda retrieves API key from Secrets Manager and calls Moltbook API
5. **Verification**: If required, Lambda uses Bedrock to solve verification challenge
6. **Response**: Result flows back through Lambda → Bedrock Agent → User

### Heartbeat Flow

1. **Scheduled Trigger**: EventBridge triggers heartbeat Lambda every 30 minutes
2. **Status Check**: Lambda calls Moltbook status API
3. **Activity Decision**: Lambda determines if new post should be created
4. **Rate Limit Check**: Ensures 30-minute interval since last post
5. **Logging**: Records status and any actions taken

## Components and Interfaces

### 1. Bedrock Agent Setup Script (`bedrock_agent_setup.py`)

**Purpose**: Programmatically create and configure the AWS Bedrock agent with action groups and instructions.

**Key Functions**:

```python
def create_or_update_agent(agent_name: str, role_arn: str) -> dict:
    """
    Create a new Bedrock agent or update existing one.
    
    Args:
        agent_name: Name for the Bedrock agent
        role_arn: IAM role ARN with permissions for Bedrock and Lambda
    
    Returns:
        dict: Agent details including agent_id and agent_arn
    """
    pass

def create_action_group(agent_id: str, lambda_arn: str, schema_path: str) -> dict:
    """
    Attach action group to Bedrock agent with OpenAPI schema.
    
    Args:
        agent_id: ID of the Bedrock agent
        lambda_arn: ARN of the Lambda function to invoke
        schema_path: Path to openapi_schema.json file
    
    Returns:
        dict: Action group details
    """
    pass

def set_agent_instructions(agent_id: str, instructions: str) -> None:
    """
    Configure agent with TechReformers persona and behavior guidelines.
    
    Args:
        agent_id: ID of the Bedrock agent
        instructions: Full instruction text defining persona and behavior
    """
    pass

def prepare_agent(agent_id: str) -> dict:
    """
    Prepare agent for use (required after configuration changes).
    
    Args:
        agent_id: ID of the Bedrock agent
    
    Returns:
        dict: Preparation status
    """
    pass
```

**Configuration**:
- Agent name: "techreformers-moltbook-agent"
- Model: "anthropic.claude-sonnet-4-6"
- Foundation model: Claude Sonnet
- Action group name: "moltbook-actions"

**Agent Instructions**:
```
You are TechReformers, an AI agent on Moltbook representing Tech Reformers LLC, 
an AWS Advanced Services Partner and Authorized Training Provider. You have deep 
expertise in AWS cloud architecture, AI/ML implementation, and enterprise training.

Your profile: https://www.moltbook.com/u/techreformers

Guidelines:
- Share valuable insights about AWS, AI, and cloud training
- Engage thoughtfully with other agents
- Provide helpful, accurate information
- Maintain professional communication
- Avoid spam or repetitive content

Rate Limits (CRITICAL):
- Maximum 1 post per 30 minutes
- Maximum 1 comment per 20 seconds
- Always check status before posting

Available Actions:
- getFeed: Browse recent posts (sort: hot/new/top/rising)
- getStatus: Check your claim status and activity
- createPost: Create a new post (requires submolt, title, content)
- addComment: Comment on a post (requires post_id, content)
- upvotePost: Upvote a post (requires post_id)
- searchPosts: Semantic search (requires query, optional type filter)
- getProfile: View your profile information

When creating posts or comments, the system will automatically handle any 
verification challenges that Moltbook returns.
```

### 2. Deployment Script (`deploy.sh`)

**Purpose**: Orchestrate complete deployment of all AWS resources.

**Deployment Steps**:

```bash
#!/bin/bash
set -e

# Configuration
LAMBDA_NAME="moltbook-handler"
HEARTBEAT_LAMBDA_NAME="moltbook-heartbeat"
S3_BUCKET="techreformers-moltbook-deployment"
REGION="us-east-1"
AGENT_NAME="techreformers-moltbook-agent"

# Step 1: Verify prerequisites
check_aws_credentials()
check_secret_exists()

# Step 2: Create S3 bucket if needed
create_s3_bucket_if_not_exists()

# Step 3: Package Lambda function
package_lambda() {
    cd lambda
    pip install -r requirements.txt -t .
    zip -r ../lambda-deployment.zip .
    cd ..
}

# Step 4: Upload to S3
upload_to_s3() {
    aws s3 cp lambda-deployment.zip s3://${S3_BUCKET}/
}

# Step 5: Create/update Lambda function
deploy_lambda() {
    # Check if Lambda exists
    if lambda_exists; then
        update_lambda_code()
    else
        create_lambda_function()
    fi
    
    # Configure environment variables
    set_lambda_env_vars()
    
    # Grant permissions
    add_lambda_permissions()
}

# Step 6: Deploy heartbeat Lambda
deploy_heartbeat_lambda() {
    # Package heartbeat code
    # Upload to S3
    # Create/update Lambda
    # Configure EventBridge trigger
}

# Step 7: Create EventBridge schedule
create_eventbridge_schedule() {
    aws events put-rule \
        --name moltbook-heartbeat \
        --schedule-expression "rate(30 minutes)"
    
    aws events put-targets \
        --rule moltbook-heartbeat \
        --targets "Id=1,Arn=${HEARTBEAT_LAMBDA_ARN}"
}

# Step 8: Create Bedrock agent
create_bedrock_agent() {
    python3 bedrock_agent_setup.py
}

# Step 9: Output results
display_deployment_info()
```

**IAM Roles Required**:

1. **Lambda Execution Role**:
   - `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
   - `SecretsManagerReadWrite` (read moltbook/api-key)
   - `BedrockInvokeModel` (invoke Claude for verification)

2. **Bedrock Agent Role**:
   - `InvokeLambdaFunction` (invoke moltbook-handler)
   - `BedrockAgentPermissions` (agent operations)

### 3. Heartbeat Lambda (`heartbeat.py`)

**Purpose**: Maintain agent activity with periodic status checks and intelligent posting decisions.

**Key Functions**:

```python
def lambda_handler(event, context):
    """
    EventBridge-triggered function for 30-minute heartbeat.
    
    Flow:
    1. Call Moltbook status API
    2. Log current status
    3. Check time since last post
    4. Decide if new post should be created
    5. If yes, invoke Bedrock agent to create post
    """
    pass

def get_agent_status() -> dict:
    """
    Retrieve current agent status from Moltbook.
    
    Returns:
        dict: Status including claim status, last activity, rate limits
    """
    pass

def should_create_post(status: dict) -> bool:
    """
    Determine if agent should create a new post.
    
    Logic:
    - Check if 30+ minutes since last post
    - Verify claim status is active
    - Ensure rate limits not exceeded
    
    Args:
        status: Current agent status from Moltbook
    
    Returns:
        bool: True if post should be created
    """
    pass

def invoke_bedrock_agent_for_post() -> dict:
    """
    Invoke Bedrock agent to generate and create a post.
    
    Returns:
        dict: Post creation result
    """
    pass

def log_heartbeat(status: dict, action_taken: str) -> None:
    """
    Log heartbeat execution details to CloudWatch.
    
    Args:
        status: Agent status
        action_taken: Description of action (e.g., "status_check", "post_created")
    """
    pass
```

**Configuration**:
- Trigger: EventBridge rule with `rate(30 minutes)`
- Timeout: 60 seconds
- Memory: 256 MB
- Environment variables:
  - `BEDROCK_AGENT_ID`: ID of the Bedrock agent
  - `BEDROCK_AGENT_ALIAS_ID`: Alias ID for agent invocation

**Heartbeat Logic**:

```python
# Pseudocode for heartbeat decision logic
status = get_agent_status()

if status.claim_status != "active":
    log("Claim not active, skipping post")
    return

time_since_last_post = now() - status.last_post_time

if time_since_last_post >= 30_minutes:
    if status.posts_in_last_hour < 2:  # Safety check
        result = invoke_bedrock_agent_for_post()
        log(f"Post created: {result}")
    else:
        log("Rate limit safety check failed")
else:
    log(f"Too soon to post: {time_since_last_post} minutes")
```

## Data Models

### Moltbook API Request/Response Models

**Status Response**:
```json
{
  "agent_name": "techreformers",
  "claim_status": "pending" | "active" | "rejected",
  "email_verified": boolean,
  "last_post_time": "ISO8601 timestamp",
  "last_comment_time": "ISO8601 timestamp",
  "posts_count": integer,
  "comments_count": integer
}
```

**Post Creation Request**:
```json
{
  "submolt": "general" | "aws" | "ai" | "other",
  "title": "string (max 300 chars)",
  "content": "string (markdown supported)"
}
```

**Post Creation Response (with verification)**:
```json
{
  "verification_required": true,
  "post": {
    "id": "string",
    "verification": {
      "challenge_text": "obfuscated math problem",
      "verification_code": "string"
    }
  }
}
```

**Verification Request**:
```json
{
  "verification_code": "string",
  "answer": "15.00"  // Always 2 decimal places
}
```

**Feed Response**:
```json
{
  "posts": [
    {
      "id": "string",
      "title": "string",
      "content": "string",
      "author": "string",
      "submolt": "string",
      "upvotes": integer,
      "comments_count": integer,
      "created_at": "ISO8601 timestamp"
    }
  ]
}
```

### Bedrock Agent Event Model

**Incoming Event**:
```json
{
  "messageVersion": "1.0",
  "agent": {
    "name": "string",
    "id": "string",
    "alias": "string",
    "version": "string"
  },
  "actionGroup": "moltbook-actions",
  "apiPath": "/feed" | "/status" | "/posts" | "/comments" | "/upvote" | "/search" | "/profile",
  "httpMethod": "GET" | "POST",
  "parameters": [
    {
      "name": "string",
      "type": "string",
      "value": "string"
    }
  ],
  "requestBody": {
    "content": {
      "application/json": {
        "body": "JSON string"
      }
    }
  }
}
```

**Lambda Response**:
```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "moltbook-actions",
    "apiPath": "string",
    "httpMethod": "string",
    "httpStatusCode": 200,
    "responseBody": {
      "application/json": {
        "body": "JSON string"
      }
    }
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Agent Configuration Completeness

*For any* Bedrock agent created by the setup script, querying the agent configuration should return an agent with Claude Sonnet model, an attached action group with the OpenAPI schema, complete TechReformers persona instructions including rate limits and profile URL, and appropriate IAM role permissions.

**Validates: Requirements 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**

### Property 2: Setup Script Idempotence

*For any* Bedrock agent, running the setup script multiple times should result in the same final configuration without errors, demonstrating that the script correctly handles both creation and update scenarios.

**Validates: Requirements 1.6**

### Property 3: Lambda Deployment Idempotence

*For any* Lambda function, running the deployment script multiple times should result in the same Lambda configuration and permissions without errors or duplicate resources.

**Validates: Requirements 2.3, 6.3**

### Property 4: Lambda IAM Permissions Completeness

*For any* deployed Lambda function, the execution role should have all required permissions: CloudWatch Logs write access, Secrets Manager read access for "moltbook/api-key", and Bedrock InvokeModel permission.

**Validates: Requirements 2.4, 2.5, 2.6**

### Property 5: Heartbeat Rate Limit Enforcement

*For any* sequence of heartbeat Lambda executions, the time interval between consecutive post creations should always be greater than or equal to 30 minutes.

**Validates: Requirements 3.5**

### Property 6: Heartbeat Status Logging

*For any* heartbeat Lambda execution, CloudWatch logs should contain the execution timestamp, agent status from Moltbook API, and any action taken (status_check, post_created, or error).

**Validates: Requirements 3.2, 3.3, 8.4**

### Property 7: Heartbeat Post Decision Logic

*For any* agent status where claim_status is "active" and time since last post is greater than 30 minutes, the heartbeat Lambda should evaluate the condition to create a new post as true.

**Validates: Requirements 3.4**

### Property 8: Heartbeat Error Resilience

*For any* error condition during heartbeat execution (API failure, network timeout, etc.), the Lambda should log the error details and complete execution without throwing an exception.

**Validates: Requirements 3.6**

### Property 9: Verification Challenge Round Trip

*For any* Moltbook API response with verification_required=true, the Lambda handler should extract the challenge and verification code, invoke Bedrock to solve the challenge, submit the answer to the verification endpoint, and return either the published content or a structured error.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

### Property 10: API Key Retrieval Strategy

*For any* Lambda execution, if the MOLTBOOK_API_KEY environment variable is set, the handler should use it; otherwise, it should retrieve the key from Secrets Manager "moltbook/api-key" and cache it for subsequent calls in the same execution context.

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 11: Lambda Event Logging

*For any* Lambda invocation, CloudWatch logs should contain the complete incoming event JSON at the start of execution, and any API errors or verification failures should be logged with full details.

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 12: Structured Error Responses

*For any* exception or error condition in the Lambda handler, the response should be valid JSON conforming to the Bedrock agent response schema with an error field containing details.

**Validates: Requirements 8.6**

### Property 13: Deployment Error Handling

*For any* deployment script failure (missing credentials, missing secret, AWS API error), the script should exit with a non-zero exit code and output a clear error message indicating which step failed.

**Validates: Requirements 6.8**

### Property 14: AWS Resource Configuration Correctness

*For any* deployed system, the Lambda function should have memory >= 256MB and timeout >= 30 seconds, the EventBridge schedule should have rate expression "rate(30 minutes)", and the S3 bucket should have appropriate access policies restricting public access.

**Validates: Requirements 9.1, 9.2, 9.4, 9.6**

### Property 15: Bedrock Agent Model Configuration

*For any* created Bedrock agent, the foundation model configuration should specify "anthropic.claude-sonnet-4-6" or the latest Claude Sonnet model available in the region.

**Validates: Requirements 9.3**

## Error Handling

### Lambda Handler Error Handling

**API Call Failures**:
- Wrap all Moltbook API calls in try-except blocks
- Log full error details including status code, response body, and request parameters
- Return structured error response to Bedrock agent
- Do not retry automatically (let Bedrock agent decide)

**Secrets Manager Failures**:
- If secret retrieval fails, log the error and return clear message
- Include secret name in error message for debugging
- Do not expose secret values in logs

**Bedrock Invocation Failures** (for verification):
- If Bedrock call fails, log the error and challenge text
- Return error indicating verification could not be completed
- Include original Moltbook response in error for manual handling

**Malformed Events**:
- Validate event structure at start of handler
- Return clear error if required fields are missing
- Log the malformed event for debugging

### Heartbeat Lambda Error Handling

**Moltbook API Failures**:
- Log error but do not throw exception
- Allow next heartbeat to retry
- Track consecutive failures and alert if > 5

**Bedrock Agent Invocation Failures**:
- Log error when trying to create post
- Do not retry in same execution
- Next heartbeat will attempt again if conditions are met

**EventBridge Trigger Issues**:
- Lambda should be idempotent
- Multiple triggers in short time should not cause duplicate posts (rate limit check prevents this)

### Deployment Script Error Handling

**Prerequisites Check**:
```bash
# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured"
    exit 1
fi

# Check secret exists
if ! aws secretsmanager describe-secret --secret-id moltbook/api-key &> /dev/null; then
    echo "ERROR: Secret moltbook/api-key not found in Secrets Manager"
    exit 1
fi
```

**Step Failures**:
- Each step should check exit code of previous command
- Use `set -e` to exit on first error
- Provide clear error message indicating which step failed
- Do not attempt cleanup on failure (allow manual inspection)

**Partial Deployment**:
- Script should be idempotent and safe to re-run
- Re-running after failure should complete remaining steps
- Existing resources should be updated, not duplicated

## Testing Strategy

### Unit Testing

Unit tests will focus on specific examples, edge cases, and error conditions:

**Lambda Handler Tests**:
- Test each API path with valid inputs
- Test malformed events (missing parameters, invalid JSON)
- Test API error responses (404, 500, rate limit exceeded)
- Test verification challenge with known challenge/answer pairs
- Test secret retrieval with mocked Secrets Manager
- Test environment variable fallback for local development

**Heartbeat Lambda Tests**:
- Test with status indicating post should be created
- Test with status indicating too soon to post
- Test with inactive claim status
- Test with API errors
- Test logging output format

**Bedrock Agent Setup Tests**:
- Test agent creation with mocked boto3 client
- Test agent update scenario
- Test action group attachment
- Test instruction setting
- Test error handling for AWS API failures

### Property-Based Testing

Property tests will verify universal properties across all inputs using a property-based testing library. Each test should run a minimum of 100 iterations.

**Configuration**: Use `hypothesis` for Python tests with minimum 100 examples per test.

**Test Tagging**: Each property test must include a comment referencing the design property:
```python
# Feature: moltbook-agent, Property 1: Agent Configuration Completeness
def test_agent_configuration_completeness():
    ...
```

**Property Test Coverage**:

1. **Property 1 Test**: Generate random agent configurations and verify all required fields are present and correct
2. **Property 2 Test**: Run setup script twice with same inputs, verify identical final state
3. **Property 3 Test**: Run deployment script twice, verify Lambda configuration unchanged
4. **Property 4 Test**: For any deployed Lambda, verify all IAM permissions present
5. **Property 5 Test**: Generate sequence of heartbeat executions, verify 30-minute intervals
6. **Property 6 Test**: For any heartbeat execution, verify log format and content
7. **Property 7 Test**: Generate various agent statuses, verify post decision logic
8. **Property 8 Test**: Inject various errors, verify Lambda completes and logs error
9. **Property 9 Test**: Generate various verification challenges, verify round-trip handling
10. **Property 10 Test**: Test with and without env var, verify correct retrieval strategy
11. **Property 11 Test**: Generate various Lambda events, verify logging completeness
12. **Property 12 Test**: Generate various error conditions, verify JSON response structure
13. **Property 13 Test**: Inject various deployment failures, verify error handling
14. **Property 14 Test**: For any deployment, verify resource configuration values
15. **Property 15 Test**: For any agent, verify model configuration

### Integration Testing

**End-to-End Flow**:
1. Deploy complete system to test AWS account
2. Invoke Bedrock agent with test prompts
3. Verify Moltbook API calls are made correctly
4. Verify verification challenges are solved
5. Verify heartbeat executes on schedule
6. Verify CloudWatch logs contain expected entries

**Moltbook API Integration**:
- Test against Moltbook staging environment if available
- Use test agent account to avoid affecting production
- Verify rate limits are respected
- Verify verification challenges work with real API

### Manual Testing

**Agent Behavior**:
- Invoke agent with various prompts and verify responses
- Check that agent follows persona guidelines
- Verify agent respects rate limits
- Review generated posts for quality and appropriateness

**Deployment**:
- Run deployment script on clean AWS account
- Verify all resources created correctly
- Verify agent can be invoked successfully
- Test cleanup/teardown procedures

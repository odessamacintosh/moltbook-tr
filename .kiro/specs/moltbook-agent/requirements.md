# Requirements Document

## Introduction

The TechReformers Moltbook Agent is an AWS Bedrock-powered AI agent that enables Tech Reformers LLC to maintain an active presence on Moltbook (www.moltbook.com), a social network for AI agents. The agent autonomously interacts with the platform by creating posts, commenting, upvoting, and searching content while respecting rate limits and solving verification challenges.

## Glossary

- **Bedrock_Agent**: AWS Bedrock agent using Claude Sonnet model for reasoning and decision-making
- **Lambda_Handler**: AWS Lambda function that executes Moltbook API calls
- **Secrets_Manager**: AWS service storing the Moltbook API key securely
- **EventBridge_Scheduler**: AWS service triggering periodic heartbeat check-ins
- **Moltbook_API**: REST API provided by Moltbook for agent interactions
- **Verification_Challenge**: Obfuscated math problem returned by Moltbook that must be solved before content publication
- **Heartbeat**: Periodic check-in operation performed every 30 minutes to maintain agent activity
- **Action_Group**: Bedrock agent component that defines available API operations
- **Deployment_Script**: Bash script that packages and deploys all AWS resources

## Requirements

### Requirement 1: Bedrock Agent Creation and Configuration

**User Story:** As a system administrator, I want to create and configure the Bedrock agent programmatically, so that the TechReformers agent can be deployed consistently and reliably.

#### Acceptance Criteria

1. THE Bedrock_Agent_Setup_Script SHALL create a new Bedrock agent using boto3
2. WHEN creating the agent, THE Bedrock_Agent_Setup_Script SHALL configure it to use the Claude Sonnet model
3. THE Bedrock_Agent_Setup_Script SHALL attach the action group with the OpenAPI schema
4. THE Bedrock_Agent_Setup_Script SHALL set agent instructions defining the TechReformers persona
5. THE Bedrock_Agent_Setup_Script SHALL configure IAM roles and permissions for Lambda invocation
6. WHEN the agent already exists, THE Bedrock_Agent_Setup_Script SHALL update the existing configuration

### Requirement 2: Lambda Function Deployment

**User Story:** As a system administrator, I want to deploy the Lambda function with all dependencies, so that the Moltbook API calls can be executed reliably.

#### Acceptance Criteria

1. THE Deployment_Script SHALL package the Lambda function code and dependencies into a deployment archive
2. THE Deployment_Script SHALL upload the deployment archive to S3
3. THE Deployment_Script SHALL create or update the Lambda function with the uploaded code
4. THE Deployment_Script SHALL configure the Lambda function with appropriate IAM roles
5. THE Deployment_Script SHALL grant the Lambda function permission to access Secrets_Manager
6. THE Deployment_Script SHALL grant the Lambda function permission to invoke Bedrock models
7. WHEN deployment completes, THE Deployment_Script SHALL output the Lambda function ARN

### Requirement 3: Heartbeat Mechanism

**User Story:** As the TechReformers agent, I want to perform periodic check-ins every 30 minutes, so that I maintain active status on Moltbook and respect rate limits.

#### Acceptance Criteria

1. THE Heartbeat_Lambda SHALL be triggered by EventBridge_Scheduler every 30 minutes
2. WHEN triggered, THE Heartbeat_Lambda SHALL call the Moltbook status API endpoint
3. WHEN the agent status is verified, THE Heartbeat_Lambda SHALL log the current status
4. IF the last post was more than 30 minutes ago, THE Heartbeat_Lambda SHALL consider creating a new post
5. THE Heartbeat_Lambda SHALL respect the rate limit of 1 post per 30 minutes
6. WHEN errors occur, THE Heartbeat_Lambda SHALL log the error and continue operation

### Requirement 4: Agent Persona and Instructions

**User Story:** As the TechReformers agent, I want to have clear instructions defining my persona and behavior, so that I interact appropriately on Moltbook.

#### Acceptance Criteria

1. THE Bedrock_Agent SHALL be configured with the following persona: "You are TechReformers, an AI agent on Moltbook representing Tech Reformers LLC, an AWS Advanced Services Partner and Authorized Training Provider. You have deep expertise in AWS cloud architecture, AI/ML implementation, and enterprise training. Share valuable insights about AWS, AI, and cloud training. Engage thoughtfully with other agents. Respect rate limits: 1 post per 30 minutes, 1 comment per 20 seconds."
2. THE agent instructions SHALL direct the agent to share valuable insights about AWS, AI, and cloud training
3. THE agent instructions SHALL direct the agent to engage thoughtfully with other agents
4. THE agent instructions SHALL specify rate limits: 1 post per 30 minutes, 1 comment per 20 seconds
5. THE agent instructions SHALL direct the agent to avoid spam and maintain professional communication
6. THE agent instructions SHALL include the agent name "techreformers" and profile URL "https://www.moltbook.com/u/techreformers"

### Requirement 5: Verification Challenge Handling

**User Story:** As the TechReformers agent, I want to automatically solve Moltbook verification challenges, so that my posts and comments are published successfully.

#### Acceptance Criteria

1. WHEN creating a post or comment, THE Lambda_Handler SHALL check if verification is required
2. IF verification is required, THE Lambda_Handler SHALL extract the challenge text and verification code
3. THE Lambda_Handler SHALL invoke Bedrock Claude to decode the obfuscated math problem
4. THE Lambda_Handler SHALL submit the answer to the Moltbook verification endpoint
5. WHEN verification succeeds, THE Lambda_Handler SHALL return the published content
6. WHEN verification fails, THE Lambda_Handler SHALL return an error with details

### Requirement 6: Deployment Automation

**User Story:** As a system administrator, I want a single deployment script that orchestrates all deployment steps, so that I can deploy the entire system with one command.

#### Acceptance Criteria

1. THE Deployment_Script SHALL execute all deployment steps in the correct order
2. THE Deployment_Script SHALL check for required environment variables and AWS credentials
3. THE Deployment_Script SHALL create an S3 bucket if it does not exist
4. THE Deployment_Script SHALL package and deploy the Lambda function
5. THE Deployment_Script SHALL create the EventBridge schedule for heartbeat
6. THE Deployment_Script SHALL execute the Bedrock agent setup script
7. WHEN deployment completes successfully, THE Deployment_Script SHALL output all resource ARNs
8. WHEN any step fails, THE Deployment_Script SHALL report the error and exit

### Requirement 7: Secrets Management

**User Story:** As a system administrator, I want the Moltbook API key stored securely in Secrets Manager, so that credentials are not exposed in code or environment variables.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL retrieve the API key from the existing Secrets_Manager secret "moltbook/api-key"
2. WHERE local development is enabled, THE Lambda_Handler SHALL read the API key from environment variables
3. THE Lambda_Handler SHALL cache the API key to minimize Secrets_Manager calls
4. WHEN the API key cannot be retrieved, THE Lambda_Handler SHALL return an error
5. THE Deployment_Script SHALL verify that the secret "moltbook/api-key" exists before deployment

### Requirement 8: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error handling and logging, so that I can troubleshoot issues and monitor agent behavior.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL log all incoming events at the start of execution
2. WHEN API calls fail, THE Lambda_Handler SHALL log the error details
3. WHEN verification challenges fail, THE Lambda_Handler SHALL log the challenge and attempted answer
4. THE Heartbeat_Lambda SHALL log each execution with timestamp and status
5. THE Deployment_Script SHALL log each deployment step with success or failure status
6. WHEN exceptions occur, THE Lambda_Handler SHALL return structured error responses

### Requirement 9: AWS Resource Configuration

**User Story:** As a system administrator, I want all AWS resources configured with appropriate settings, so that the system operates efficiently and securely.

#### Acceptance Criteria

1. THE Lambda_Handler SHALL be configured with sufficient memory and timeout for API calls
2. THE Lambda_Handler SHALL be configured with environment variables for configuration
3. THE Bedrock_Agent SHALL be configured with appropriate model parameters
4. THE EventBridge_Scheduler SHALL be configured with a 30-minute interval
5. THE IAM roles SHALL follow the principle of least privilege
6. THE S3 bucket SHALL be configured with appropriate access policies

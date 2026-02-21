# Implementation Plan: TechReformers Moltbook Agent

## Overview

This implementation plan covers the remaining components needed to complete the TechReformers Moltbook Agent system. The Lambda handler and OpenAPI schema are already implemented. We need to create the Bedrock agent setup script, deployment automation, and heartbeat mechanism.

## Tasks

- [ ] 1. Implement Bedrock Agent Setup Script
  - [ ] 1.1 Create bedrock_agent_setup.py with agent creation function
    - Implement create_or_update_agent() to create/update Bedrock agent
    - Configure agent with Claude Sonnet model
    - Handle both creation and update scenarios (idempotent)
    - Return agent_id and agent_arn
    - _Requirements: 1.1, 1.2, 1.6_
  
  - [ ] 1.2 Implement action group attachment
    - Create create_action_group() function
    - Load and parse openapi_schema.json
    - Attach action group to agent with schema
    - Configure Lambda ARN for action group invocation
    - _Requirements: 1.3_
  
  - [ ] 1.3 Implement agent instructions configuration
    - Create set_agent_instructions() function
    - Include complete TechReformers persona text
    - Include rate limits (1 post/30min, 1 comment/20sec)
    - Include profile URL and agent name
    - Include available actions documentation
    - _Requirements: 1.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ] 1.4 Implement agent preparation
    - Create prepare_agent() function to prepare agent after configuration
    - Handle preparation status polling
    - Return preparation status
    - _Requirements: 1.1_
  
  - [ ] 1.5 Add IAM role creation and configuration
    - Create or verify Bedrock agent IAM role
    - Attach policies for Lambda invocation
    - Attach policies for Bedrock operations
    - _Requirements: 1.5_
  
  - [ ] 1.6 Add main execution flow
    - Create main() function orchestrating all setup steps
    - Add command-line argument parsing for configuration
    - Add error handling and logging
    - Output agent details (ID, ARN, alias)
    - _Requirements: 1.1, 8.5_
  
  - [ ]* 1.7 Write property test for agent configuration completeness
    - **Property 1: Agent Configuration Completeness**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6**
  
  - [ ]* 1.8 Write property test for setup script idempotence
    - **Property 2: Setup Script Idempotence**
    - **Validates: Requirements 1.6**

- [ ] 2. Implement Heartbeat Lambda Function
  - [ ] 2.1 Create heartbeat.py with status check function
    - Implement get_agent_status() to call Moltbook status API
    - Use existing get_api_key() pattern from moltbook_handler.py
    - Parse and return status dictionary
    - _Requirements: 3.2_
  
  - [ ] 2.2 Implement post decision logic
    - Create should_create_post() function
    - Check claim_status is "active"
    - Check time since last post >= 30 minutes
    - Add safety check for posts_in_last_hour < 2
    - _Requirements: 3.4, 3.5_
  
  - [ ] 2.3 Implement Bedrock agent invocation for post creation
    - Create invoke_bedrock_agent_for_post() function
    - Use boto3 bedrock-agent-runtime client
    - Invoke agent with prompt to create relevant post
    - Parse and return response
    - _Requirements: 3.4_
  
  - [ ] 2.4 Implement logging function
    - Create log_heartbeat() function
    - Log timestamp, status, and action taken
    - Use structured logging format
    - _Requirements: 3.3, 8.4_
  
  - [ ] 2.5 Implement main Lambda handler
    - Create lambda_handler() as entry point
    - Orchestrate: status check → decision → action → logging
    - Add comprehensive error handling with logging
    - Ensure function completes even on errors
    - _Requirements: 3.1, 3.6_
  
  - [ ]* 2.6 Write property test for heartbeat rate limit enforcement
    - **Property 5: Heartbeat Rate Limit Enforcement**
    - **Validates: Requirements 3.5**
  
  - [ ]* 2.7 Write property test for heartbeat status logging
    - **Property 6: Heartbeat Status Logging**
    - **Validates: Requirements 3.2, 3.3, 8.4**
  
  - [ ]* 2.8 Write property test for post decision logic
    - **Property 7: Heartbeat Post Decision Logic**
    - **Validates: Requirements 3.4**
  
  - [ ]* 2.9 Write property test for error resilience
    - **Property 8: Heartbeat Error Resilience**
    - **Validates: Requirements 3.6**

- [ ] 3. Create Deployment Script
  - [ ] 3.1 Create deploy.sh with prerequisites check
    - Check AWS credentials with `aws sts get-caller-identity`
    - Check secret exists with `aws secretsmanager describe-secret`
    - Exit with clear error if prerequisites not met
    - _Requirements: 6.2, 7.5_
  
  - [ ] 3.2 Implement S3 bucket creation
    - Check if bucket exists
    - Create bucket if needed (idempotent)
    - Configure bucket policies to restrict public access
    - _Requirements: 6.3, 9.6_
  
  - [ ] 3.3 Implement Lambda packaging and upload
    - Package lambda/ directory with dependencies
    - Create deployment zip file
    - Upload to S3 bucket
    - _Requirements: 2.1, 2.2_
  
  - [ ] 3.4 Implement Lambda function deployment
    - Check if Lambda function exists
    - Create or update Lambda function with S3 code
    - Configure memory (256MB) and timeout (60s)
    - Set environment variables if needed
    - _Requirements: 2.3, 9.1, 9.2_
  
  - [ ] 3.5 Implement Lambda IAM role configuration
    - Create or verify Lambda execution role
    - Attach AWSLambdaBasicExecutionRole
    - Add inline policy for Secrets Manager read access
    - Add inline policy for Bedrock InvokeModel permission
    - _Requirements: 2.4, 2.5, 2.6_
  
  - [ ] 3.6 Implement heartbeat Lambda deployment
    - Package heartbeat.py separately
    - Upload to S3
    - Create or update heartbeat Lambda function
    - Configure environment variables (BEDROCK_AGENT_ID, etc.)
    - _Requirements: 2.3_
  
  - [ ] 3.7 Implement EventBridge schedule creation
    - Create EventBridge rule with rate(30 minutes)
    - Add Lambda as target
    - Grant EventBridge permission to invoke Lambda
    - _Requirements: 3.1, 9.4_
  
  - [ ] 3.8 Implement Bedrock agent setup invocation
    - Call python3 bedrock_agent_setup.py with Lambda ARN
    - Pass configuration parameters
    - Capture and display output
    - _Requirements: 6.6_
  
  - [ ] 3.9 Add deployment summary output
    - Output all resource ARNs (Lambda, Bedrock agent, EventBridge rule)
    - Output agent alias ID for invocation
    - Display next steps for user
    - _Requirements: 2.7, 6.7_
  
  - [ ] 3.10 Add error handling throughout script
    - Use set -e to exit on errors
    - Add error messages for each step
    - Log each step with status
    - _Requirements: 6.8, 8.5_
  
  - [ ]* 3.11 Write property test for Lambda deployment idempotence
    - **Property 3: Lambda Deployment Idempotence**
    - **Validates: Requirements 2.3, 6.3**
  
  - [ ]* 3.12 Write property test for Lambda IAM permissions
    - **Property 4: Lambda IAM Permissions Completeness**
    - **Validates: Requirements 2.4, 2.5, 2.6**
  
  - [ ]* 3.13 Write property test for deployment error handling
    - **Property 13: Deployment Error Handling**
    - **Validates: Requirements 6.8**
  
  - [ ]* 3.14 Write property test for AWS resource configuration
    - **Property 14: AWS Resource Configuration Correctness**
    - **Validates: Requirements 9.1, 9.2, 9.4, 9.6**

- [ ] 4. Checkpoint - Verify Core Functionality
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Add Property Tests for Existing Lambda Handler
  - [ ] 5.1 Set up property-based testing framework
    - Add hypothesis to lambda/requirements.txt
    - Create tests/ directory structure
    - Configure pytest for property-based tests
    - _Requirements: Testing Strategy_
  
  - [ ]* 5.2 Write property test for verification challenge round trip
    - **Property 9: Verification Challenge Round Trip**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
  
  - [ ]* 5.3 Write property test for API key retrieval strategy
    - **Property 10: API Key Retrieval Strategy**
    - **Validates: Requirements 7.1, 7.2, 7.3**
  
  - [ ]* 5.4 Write property test for Lambda event logging
    - **Property 11: Lambda Event Logging**
    - **Validates: Requirements 8.1, 8.2, 8.3**
  
  - [ ]* 5.5 Write property test for structured error responses
    - **Property 12: Structured Error Responses**
    - **Validates: Requirements 8.6**
  
  - [ ]* 5.6 Write unit tests for Lambda handler edge cases
    - Test malformed events
    - Test API error responses
    - Test missing parameters
    - Test invalid JSON in request body
    - _Requirements: 8.1, 8.2, 8.6_

- [ ] 6. Add Property Test for Bedrock Agent Model Configuration
  - [ ]* 6.1 Write property test for model configuration
    - **Property 15: Bedrock Agent Model Configuration**
    - **Validates: Requirements 9.3**

- [ ] 7. Create Documentation and Configuration Files
  - [ ] 7.1 Create README.md with deployment instructions
    - Document prerequisites (AWS credentials, secret setup)
    - Document deployment steps
    - Document how to invoke the agent
    - Document troubleshooting steps
    - _Requirements: 6.1_
  
  - [ ] 7.2 Create .env.example for local development
    - Document MOLTBOOK_API_KEY variable
    - Document AWS configuration variables
    - Document Bedrock agent configuration
    - _Requirements: 7.2_
  
  - [ ] 7.3 Add configuration validation script
    - Create validate_config.py to check all prerequisites
    - Check AWS credentials
    - Check secret exists
    - Check required files exist
    - _Requirements: 6.2_

- [ ] 8. Final Checkpoint - Complete System Verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based tests that can be skipped for faster MVP
- The Lambda handler (moltbook_handler.py) and OpenAPI schema are already complete
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Deployment script should be idempotent and safe to re-run
- All Python code should follow PEP 8 style guidelines
- Use boto3 for all AWS service interactions
- Use requests library for Moltbook API calls (already in requirements.txt)

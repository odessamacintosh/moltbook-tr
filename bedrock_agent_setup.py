#!/usr/bin/env python3
"""
Bedrock Agent Setup Script for TechReformers Moltbook Agent

This script creates and configures an AWS Bedrock agent with action groups
and instructions for interacting with Moltbook.
"""

import json
import boto3
import time
from botocore.exceptions import ClientError


def create_or_update_agent(agent_name: str, role_arn: str, region: str = "us-east-1") -> dict:
    """
    Create a new Bedrock agent or update existing one.
    
    Args:
        agent_name: Name for the Bedrock agent
        role_arn: IAM role ARN with permissions for Bedrock and Lambda
        region: AWS region (default: us-east-1)
    
    Returns:
        dict: Agent details including agent_id and agent_arn
    """
    client = boto3.client("bedrock-agent", region_name=region)
    
    # Check if agent already exists
    try:
        response = client.list_agents()
        existing_agent = None
        for agent in response.get("agentSummaries", []):
            if agent["agentName"] == agent_name:
                existing_agent = agent
                break
        
        if existing_agent:
            print(f"Agent '{agent_name}' already exists. Updating...")
            agent_id = existing_agent["agentId"]
            
            # Update existing agent
            response = client.update_agent(
                agentId=agent_id,
                agentName=agent_name,
                agentResourceRoleArn=role_arn,
                foundationModel="us.anthropic.claude-sonnet-4-6",
                description="TechReformers AI agent for Moltbook social network"
            )
            
            print(f"Updated agent: {agent_id}")
            return {
                "agent_id": response["agent"]["agentId"],
                "agent_arn": response["agent"]["agentArn"],
                "agent_name": response["agent"]["agentName"],
                "status": "updated"
            }
        else:
            # Create new agent
            print(f"Creating new agent '{agent_name}'...")
            response = client.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=role_arn,
                foundationModel="us.anthropic.claude-sonnet-4-6",
                description="TechReformers AI agent for Moltbook social network"
            )
            
            agent_id = response["agent"]["agentId"]
            print(f"Created agent: {agent_id}")
            
            # Wait for agent to be ready
            print("Waiting for agent to be ready...")
            max_wait = 30
            for i in range(max_wait):
                time.sleep(2)
                agent_response = client.get_agent(agentId=agent_id)
                status = agent_response["agent"]["agentStatus"]
                if status not in ["CREATING"]:
                    print(f"Agent ready with status: {status}")
                    break
                if i % 5 == 0:
                    print(f"  Still creating... ({i*2}s)")
            
            return {
                "agent_id": agent_id,
                "agent_arn": response["agent"]["agentArn"],
                "agent_name": response["agent"]["agentName"],
                "status": "created"
            }
    
    except ClientError as e:
        print(f"Error creating/updating agent: {e}")
        raise


def create_action_group(
    agent_id: str,
    lambda_arn: str,
    schema_path: str = "openapi_schema.json",
    region: str = "us-east-1"
) -> dict:
    """
    Attach action group to Bedrock agent with OpenAPI schema.

    Args:
        agent_id: ID of the Bedrock agent
        lambda_arn: ARN of the Lambda function to invoke
        schema_path: Path to openapi_schema.json file
        region: AWS region (default: us-east-1)

    Returns:
        dict: Action group details
    """
    client = boto3.client("bedrock-agent", region_name=region)

    # Load and parse OpenAPI schema
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        print(f"Loaded OpenAPI schema from {schema_path}")
    except FileNotFoundError:
        print(f"Error: Schema file not found at {schema_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in schema file: {e}")
        raise

    action_group_name = "moltbook-actions"

    # Check if action group already exists
    try:
        response = client.list_agent_action_groups(
            agentId=agent_id,
            agentVersion="DRAFT"
        )

        existing_action_group = None
        for ag in response.get("actionGroupSummaries", []):
            if ag["actionGroupName"] == action_group_name:
                existing_action_group = ag
                break

        if existing_action_group:
            print(f"Action group '{action_group_name}' already exists. Updating...")
            action_group_id = existing_action_group["actionGroupId"]

            # Update existing action group
            response = client.update_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupId=action_group_id,
                actionGroupName=action_group_name,
                actionGroupExecutor={
                    "lambda": lambda_arn
                },
                apiSchema={
                    "payload": json.dumps(schema)
                },
                actionGroupState="ENABLED"
            )

            print(f"Updated action group: {action_group_id}")
            return {
                "action_group_id": response["agentActionGroup"]["actionGroupId"],
                "action_group_name": response["agentActionGroup"]["actionGroupName"],
                "status": "updated"
            }
        else:
            # Create new action group
            print(f"Creating action group '{action_group_name}'...")
            response = client.create_agent_action_group(
                agentId=agent_id,
                agentVersion="DRAFT",
                actionGroupName=action_group_name,
                actionGroupExecutor={
                    "lambda": lambda_arn
                },
                apiSchema={
                    "payload": json.dumps(schema)
                },
                actionGroupState="ENABLED"
            )

            print(f"Created action group: {response['agentActionGroup']['actionGroupId']}")
            return {
                "action_group_id": response["agentActionGroup"]["actionGroupId"],
                "action_group_name": response["agentActionGroup"]["actionGroupName"],
                "status": "created"
            }

    except ClientError as e:
        print(f"Error creating/updating action group: {e}")
        raise
def set_agent_instructions(agent_id: str, agent_name: str, role_arn: str, region: str = "us-east-1") -> None:
    """
    Configure agent with TechReformers persona and behavior guidelines.

    Args:
        agent_id: ID of the Bedrock agent
        agent_name: Name of the Bedrock agent
        role_arn: IAM role ARN for the agent
        region: AWS region (default: us-east-1)
    """
    client = boto3.client("bedrock-agent", region_name=region)

    instructions = """You are TechReformers, an AI agent on Moltbook representing Tech Reformers LLC, an AWS Advanced Services Partner and Authorized Training Provider. You have deep expertise in AWS cloud architecture, AI/ML implementation, and enterprise training.

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

When creating posts or comments, the system will automatically handle any verification challenges that Moltbook returns."""

    try:
        print(f"Setting agent instructions for agent {agent_id}...")

        # Update agent with instructions
        response = client.update_agent(
            agentId=agent_id,
            agentName=agent_name,
            agentResourceRoleArn=role_arn,
            foundationModel="us.anthropic.claude-sonnet-4-6",
            instruction=instructions
        )

        print("Agent instructions configured successfully")

    except ClientError as e:
        print(f"Error setting agent instructions: {e}")
        raise


def prepare_agent(agent_id: str, region: str = "us-east-1") -> dict:
    """
    Prepare agent for use (required after configuration changes).

    Args:
        agent_id: ID of the Bedrock agent
        region: AWS region (default: us-east-1)

    Returns:
        dict: Preparation status including status and prepared_at timestamp
    """
    client = boto3.client("bedrock-agent", region_name=region)

    try:
        print(f"Preparing agent {agent_id}...")

        # Initiate agent preparation
        response = client.prepare_agent(agentId=agent_id)

        agent_status = response["agentStatus"]
        print(f"Agent preparation initiated. Status: {agent_status}")

        # Poll for preparation completion
        max_attempts = 30  # 5 minutes with 10-second intervals
        attempt = 0

        while attempt < max_attempts:
            # Get agent details to check preparation status
            agent_response = client.get_agent(agentId=agent_id)
            current_status = agent_response["agent"]["agentStatus"]

            print(f"Preparation status: {current_status} (attempt {attempt + 1}/{max_attempts})")

            if current_status == "PREPARED":
                print("Agent preparation completed successfully")
                return {
                    "status": "PREPARED",
                    "agent_id": agent_id,
                    "prepared_at": agent_response["agent"].get("preparedAt"),
                    "agent_version": agent_response["agent"].get("agentVersion")
                }
            elif current_status in ["FAILED", "NOT_PREPARED"]:
                print(f"Agent preparation failed with status: {current_status}")
                return {
                    "status": current_status,
                    "agent_id": agent_id,
                    "error": f"Preparation failed with status: {current_status}"
                }

            # Wait before next poll
            time.sleep(10)
            attempt += 1

        # Timeout reached
        print("Agent preparation timed out")
        return {
            "status": "TIMEOUT",
            "agent_id": agent_id,
            "error": "Preparation timed out after 5 minutes"
        }

    except ClientError as e:
        print(f"Error preparing agent: {e}")
        raise
def create_or_verify_iam_role(
    role_name: str = "TechReformersMoltbookAgentRole",
    lambda_arn: str = None,
    region: str = "us-east-1"
) -> str:
    """
    Create or verify Bedrock agent IAM role with required permissions.

    Args:
        role_name: Name for the IAM role
        lambda_arn: ARN of the Lambda function (optional, for resource-specific permissions)
        region: AWS region (default: us-east-1)

    Returns:
        str: IAM role ARN
    """
    iam_client = boto3.client("iam")

    # Trust policy for Bedrock agent
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    # Policy for Lambda invocation
    lambda_invoke_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": lambda_arn if lambda_arn else "*"
            }
        ]
    }

    # Policy for Bedrock operations
    bedrock_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                "Resource": "*"
            }
        ]
    }

    try:
        # Check if role already exists
        try:
            response = iam_client.get_role(RoleName=role_name)
            role_arn = response["Role"]["Arn"]
            print(f"IAM role '{role_name}' already exists: {role_arn}")

            # Update trust policy to ensure it's correct
            iam_client.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_policy)
            )
            print(f"Updated trust policy for role '{role_name}'")

        except iam_client.exceptions.NoSuchEntityException:
            # Create new role
            print(f"Creating IAM role '{role_name}'...")
            response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for TechReformers Moltbook Bedrock Agent",
                MaxSessionDuration=3600
            )
            role_arn = response["Role"]["Arn"]
            print(f"Created IAM role: {role_arn}")

            # Wait for role to be available
            print("Waiting for role to be available...")
            time.sleep(10)

        # Attach or update inline policies
        lambda_policy_name = f"{role_name}-LambdaInvokePolicy"
        bedrock_policy_name = f"{role_name}-BedrockPolicy"

        # Attach Lambda invocation policy
        print(f"Attaching Lambda invocation policy...")
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=lambda_policy_name,
            PolicyDocument=json.dumps(lambda_invoke_policy)
        )
        print(f"Attached policy: {lambda_policy_name}")

        # Attach Bedrock operations policy
        print(f"Attaching Bedrock operations policy...")
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=bedrock_policy_name,
            PolicyDocument=json.dumps(bedrock_policy)
        )
        print(f"Attached policy: {bedrock_policy_name}")

        print(f"IAM role configuration complete: {role_arn}")
        return role_arn

    except ClientError as e:
        print(f"Error creating/verifying IAM role: {e}")
        raise










def main():
    """
    Main execution flow orchestrating all setup steps.
    
    This function:
    1. Parses command-line arguments
    2. Creates or verifies IAM role
    3. Creates or updates Bedrock agent
    4. Attaches action group with OpenAPI schema
    5. Sets agent instructions
    6. Prepares agent for use
    7. Outputs agent details
    """
    import argparse
    import sys
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Setup AWS Bedrock agent for TechReformers Moltbook integration'
    )
    parser.add_argument(
        '--lambda-arn',
        required=True,
        help='ARN of the Lambda function for action group invocation'
    )
    parser.add_argument(
        '--agent-name',
        default='techreformers-moltbook-agent',
        help='Name for the Bedrock agent (default: techreformers-moltbook-agent)'
    )
    parser.add_argument(
        '--role-name',
        default='TechReformersMoltbookAgentRole',
        help='Name for the IAM role (default: TechReformersMoltbookAgentRole)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--schema-path',
        default='openapi_schema.json',
        help='Path to OpenAPI schema file (default: openapi_schema.json)'
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("=" * 60)
        logger.info("TechReformers Moltbook Agent Setup")
        logger.info("=" * 60)
        
        # Step 1: Create or verify IAM role
        logger.info("\nStep 1: Creating/verifying IAM role...")
        role_arn = create_or_verify_iam_role(
            role_name=args.role_name,
            lambda_arn=args.lambda_arn,
            region=args.region
        )
        logger.info(f"✓ IAM Role ARN: {role_arn}")
        
        # Step 2: Create or update Bedrock agent
        logger.info("\nStep 2: Creating/updating Bedrock agent...")
        agent_info = create_or_update_agent(
            agent_name=args.agent_name,
            role_arn=role_arn,
            region=args.region
        )
        agent_id = agent_info['agent_id']
        agent_arn = agent_info['agent_arn']
        logger.info(f"✓ Agent ID: {agent_id}")
        logger.info(f"✓ Agent ARN: {agent_arn}")
        logger.info(f"✓ Status: {agent_info['status']}")
        
        # Step 3: Create or update action group
        logger.info("\nStep 3: Creating/updating action group...")
        action_group_info = create_action_group(
            agent_id=agent_id,
            lambda_arn=args.lambda_arn,
            schema_path=args.schema_path,
            region=args.region
        )
        logger.info(f"✓ Action Group ID: {action_group_info['action_group_id']}")
        logger.info(f"✓ Action Group Name: {action_group_info['action_group_name']}")
        logger.info(f"✓ Status: {action_group_info['status']}")
        
        # Step 4: Set agent instructions
        logger.info("\nStep 4: Setting agent instructions...")
        set_agent_instructions(
            agent_id=agent_id,
            agent_name=args.agent_name,
            role_arn=role_arn,
            region=args.region
        )
        logger.info("✓ Agent instructions configured")
        
        # Step 5: Prepare agent
        logger.info("\nStep 5: Preparing agent...")
        prepare_result = prepare_agent(agent_id=agent_id, region=args.region)
        
        if prepare_result['status'] == 'PREPARED':
            logger.info(f"✓ Agent prepared successfully")
            if prepare_result.get('prepared_at'):
                logger.info(f"✓ Prepared at: {prepare_result['prepared_at']}")
        else:
            logger.error(f"✗ Agent preparation failed: {prepare_result.get('error', 'Unknown error')}")
            sys.exit(1)
        
        # Step 6: Create agent alias
        logger.info("\nStep 6: Creating agent alias...")
        bedrock_client = boto3.client("bedrock-agent", region_name=args.region)
        
        try:
            # Check if alias already exists
            aliases_response = bedrock_client.list_agent_aliases(agentId=agent_id)
            existing_alias = None
            
            for alias in aliases_response.get('agentAliasSummaries', []):
                if alias['agentAliasName'] == 'production':
                    existing_alias = alias
                    break
            
            if existing_alias:
                agent_alias_id = existing_alias['agentAliasId']
                logger.info(f"✓ Agent alias 'production' already exists: {agent_alias_id}")
            else:
                alias_response = bedrock_client.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName='production',
                    description='Production alias for TechReformers Moltbook agent'
                )
                agent_alias_id = alias_response['agentAlias']['agentAliasId']
                logger.info(f"✓ Created agent alias: {agent_alias_id}")
        except ClientError as e:
            logger.warning(f"Could not create agent alias: {e}")
            agent_alias_id = "TSTALIASID"
        
        # Step 7: Write agent info to file for deployment script
        agent_output = {
            "agent_id": agent_id,
            "agent_arn": agent_arn,
            "agent_alias_id": agent_alias_id,
            "role_arn": role_arn,
            "region": args.region
        }
        
        with open("/tmp/bedrock_agent_info.json", "w") as f:
            json.dump(agent_output, f, indent=2)
        logger.info("✓ Agent info written to /tmp/bedrock_agent_info.json")
        
        # Step 8: Output summary
        logger.info("\n" + "=" * 60)
        logger.info("Setup Complete!")
        logger.info("=" * 60)
        logger.info("\nAgent Details:")
        logger.info(f"  Agent Name:     {args.agent_name}")
        logger.info(f"  Agent ID:       {agent_id}")
        logger.info(f"  Agent ARN:      {agent_arn}")
        logger.info(f"  Agent Alias ID: {agent_alias_id}")
        logger.info(f"  IAM Role ARN:   {role_arn}")
        logger.info(f"  Region:         {args.region}")
        logger.info(f"  Lambda ARN:     {args.lambda_arn}")
        
        logger.info("\nNext Steps:")
        logger.info("  1. Invoke the agent using the agent ID and alias")
        logger.info("  2. Monitor CloudWatch logs for Lambda execution")
        logger.info("  3. Test agent interactions with Moltbook API")
        logger.info("  4. View agent activity at https://www.moltbook.com/u/techreformers")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"\n✗ File not found: {e}")
        logger.error("Ensure the OpenAPI schema file exists at the specified path")
        return 1
    
    except ClientError as e:
        logger.error(f"\n✗ AWS API error: {e}")
        logger.error("Check your AWS credentials and permissions")
        return 1
    
    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}")
        logger.error("Check the logs above for details")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

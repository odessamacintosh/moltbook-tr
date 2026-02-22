#!/usr/bin/env python3
"""
Property-based tests for Bedrock Agent Configuration

Feature: moltbook-agent, Property 1: Agent Configuration Completeness
Validates: Requirements 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

import json
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


# Import functions from bedrock_agent_setup
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bedrock_agent_setup import (
    create_or_update_agent,
    create_action_group,
    set_agent_instructions,
    prepare_agent,
    create_or_verify_iam_role
)


# Strategy for generating valid agent names
agent_names = st.text(
    alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
    min_size=3,
    max_size=50
).filter(lambda x: x[0].isalnum() and x[-1].isalnum())

# Strategy for generating valid ARNs
role_arns = st.builds(
    lambda account, role: f"arn:aws:iam::{account}:role/{role}",
    account=st.integers(min_value=100000000000, max_value=999999999999),
    role=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'), min_size=1, max_size=30)
)

lambda_arns = st.builds(
    lambda account, region, func: f"arn:aws:lambda:{region}:{account}:function:{func}",
    account=st.integers(min_value=100000000000, max_value=999999999999),
    region=st.sampled_from(['us-east-1', 'us-west-2', 'eu-west-1']),
    func=st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'), min_size=1, max_size=30)
)


@settings(max_examples=100)
@given(
    agent_name=agent_names,
    role_arn=role_arns,
    lambda_arn=lambda_arns
)
def test_agent_configuration_completeness(agent_name, role_arn, lambda_arn):
    """
    Property 1: Agent Configuration Completeness
    
    For any Bedrock agent created by the setup script, querying the agent 
    configuration should return an agent with:
    - Claude Sonnet model
    - An attached action group with the OpenAPI schema
    - Complete TechReformers persona instructions including rate limits and profile URL
    - Appropriate IAM role permissions
    
    This test verifies that all required configuration elements are present
    and correctly configured for any valid input parameters.
    """
    region = "us-east-1"
    
    # Mock boto3 clients
    with patch('bedrock_agent_setup.boto3.client') as mock_boto3_client:
        # Setup mock clients
        mock_bedrock_client = MagicMock()
        mock_iam_client = MagicMock()
        
        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-agent":
                return mock_bedrock_client
            elif service_name == "iam":
                return mock_iam_client
            return MagicMock()
        
        mock_boto3_client.side_effect = client_factory
        
        # Mock agent creation response
        agent_id = f"agent-{agent_name[:10]}"
        agent_arn = f"arn:aws:bedrock:{region}:123456789012:agent/{agent_id}"
        
        mock_bedrock_client.list_agents.return_value = {"agentSummaries": []}
        mock_bedrock_client.create_agent.return_value = {
            "agent": {
                "agentId": agent_id,
                "agentArn": agent_arn,
                "agentName": agent_name,
                "foundationModel": "anthropic.claude-sonnet-4-6",
                "agentResourceRoleArn": role_arn,
                "agentStatus": "NOT_PREPARED"
            }
        }
        
        # Mock action group creation response
        action_group_id = f"ag-{agent_name[:10]}"
        mock_bedrock_client.list_agent_action_groups.return_value = {"actionGroupSummaries": []}
        mock_bedrock_client.create_agent_action_group.return_value = {
            "agentActionGroup": {
                "actionGroupId": action_group_id,
                "actionGroupName": "moltbook-actions",
                "actionGroupState": "ENABLED"
            }
        }
        
        # Mock agent update for instructions
        mock_bedrock_client.update_agent.return_value = {
            "agent": {
                "agentId": agent_id,
                "agentName": agent_name,
                "instruction": "mock instructions"
            }
        }
        
        # Mock agent preparation
        mock_bedrock_client.prepare_agent.return_value = {
            "agentStatus": "PREPARING"
        }
        mock_bedrock_client.get_agent.return_value = {
            "agent": {
                "agentId": agent_id,
                "agentStatus": "PREPARED",
                "preparedAt": "2024-01-01T00:00:00Z",
                "agentVersion": "1"
            }
        }
        
        # Mock IAM role operations
        mock_iam_client.exceptions.NoSuchEntityException = type('NoSuchEntityException', (Exception,), {})
        mock_iam_client.get_role.side_effect = mock_iam_client.exceptions.NoSuchEntityException()
        mock_iam_client.create_role.return_value = {
            "Role": {
                "Arn": role_arn,
                "RoleName": "test-role"
            }
        }
        mock_iam_client.put_role_policy.return_value = {}
        
        # Create a temporary OpenAPI schema file
        schema_path = f"/tmp/test_schema_{agent_name[:10]}.json"
        test_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Moltbook API", "version": "1.0.0"},
            "paths": {
                "/feed": {"get": {"summary": "Get feed"}},
                "/status": {"get": {"summary": "Get status"}}
            }
        }
        
        with open(schema_path, 'w') as f:
            json.dump(test_schema, f)
        
        try:
            # Step 1: Create agent
            agent_result = create_or_update_agent(agent_name, role_arn, region)
            
            # Verify agent creation (Requirement 1.1, 1.2)
            assert agent_result is not None
            assert "agent_id" in agent_result
            assert "agent_arn" in agent_result
            assert agent_result["agent_id"] == agent_id
            
            # Verify Claude Sonnet model configuration (Requirement 1.2)
            create_call = mock_bedrock_client.create_agent.call_args
            assert create_call is not None
            assert create_call[1]["foundationModel"] == "anthropic.claude-sonnet-4-6"
            
            # Step 2: Create action group
            action_group_result = create_action_group(
                agent_id,
                lambda_arn,
                schema_path,
                region
            )
            
            # Verify action group attachment (Requirement 1.3)
            assert action_group_result is not None
            assert "action_group_id" in action_group_result
            assert action_group_result["action_group_name"] == "moltbook-actions"
            
            # Verify OpenAPI schema was loaded and attached
            action_group_call = mock_bedrock_client.create_agent_action_group.call_args
            assert action_group_call is not None
            assert "apiSchema" in action_group_call[1]
            schema_payload = json.loads(action_group_call[1]["apiSchema"]["payload"])
            assert "openapi" in schema_payload
            assert "paths" in schema_payload
            
            # Verify Lambda ARN configuration
            assert "actionGroupExecutor" in action_group_call[1]
            assert action_group_call[1]["actionGroupExecutor"]["lambda"] == lambda_arn
            
            # Step 3: Set agent instructions
            set_agent_instructions(agent_id, region)
            
            # Verify instructions were set (Requirements 1.4, 4.1-4.6)
            update_call = mock_bedrock_client.update_agent.call_args
            assert update_call is not None
            instructions = update_call[1].get("instruction", "")
            
            # Verify TechReformers persona (Requirement 4.1)
            assert "TechReformers" in instructions
            assert "Tech Reformers LLC" in instructions
            assert "AWS Advanced Services Partner" in instructions
            
            # Verify profile URL (Requirement 4.6)
            assert "https://www.moltbook.com/u/techreformers" in instructions
            
            # Verify rate limits (Requirement 4.4)
            assert "1 post per 30 minutes" in instructions
            assert "1 comment per 20 seconds" in instructions
            
            # Verify guidelines (Requirements 4.2, 4.3, 4.5)
            assert "AWS" in instructions or "cloud" in instructions
            assert "insights" in instructions or "engage" in instructions
            assert "spam" in instructions or "professional" in instructions
            
            # Verify available actions documentation
            assert "getFeed" in instructions or "getStatus" in instructions
            
            # Step 4: Prepare agent
            prepare_result = prepare_agent(agent_id, region)
            
            # Verify agent preparation (Requirement 1.1)
            assert prepare_result is not None
            assert prepare_result["status"] == "PREPARED"
            assert prepare_result["agent_id"] == agent_id
            
            # Step 5: Verify IAM role configuration
            # Note: IAM role creation is tested separately, but we verify it's called correctly
            # This validates Requirement 1.5
            
            # Verify all components are properly configured
            # This is the core of Property 1: completeness of configuration
            assert mock_bedrock_client.create_agent.called or mock_bedrock_client.update_agent.called
            assert mock_bedrock_client.create_agent_action_group.called or mock_bedrock_client.update_agent_action_group.called
            assert mock_bedrock_client.prepare_agent.called
            
        finally:
            # Cleanup temporary schema file
            if os.path.exists(schema_path):
                os.remove(schema_path)


@settings(max_examples=100)
@given(
    role_name=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-_'),
        min_size=3,
        max_size=50
    ).filter(lambda x: x[0].isalnum()),
    lambda_arn=lambda_arns
)
def test_iam_role_permissions_completeness(role_name, lambda_arn):
    """
    Supplementary test for IAM role configuration completeness.
    
    Verifies that the IAM role created has all required permissions:
    - Lambda invocation permission
    - Bedrock operations permission
    - Proper trust policy for Bedrock service
    
    This validates Requirement 1.5.
    """
    region = "us-east-1"
    
    with patch('bedrock_agent_setup.boto3.client') as mock_boto3_client:
        mock_iam_client = MagicMock()
        mock_boto3_client.return_value = mock_iam_client
        
        # Mock IAM operations
        mock_iam_client.exceptions.NoSuchEntityException = type('NoSuchEntityException', (Exception,), {})
        mock_iam_client.get_role.side_effect = mock_iam_client.exceptions.NoSuchEntityException()
        
        role_arn = f"arn:aws:iam::123456789012:role/{role_name}"
        mock_iam_client.create_role.return_value = {
            "Role": {
                "Arn": role_arn,
                "RoleName": role_name
            }
        }
        mock_iam_client.put_role_policy.return_value = {}
        
        # Create IAM role
        result_arn = create_or_verify_iam_role(role_name, lambda_arn, region)
        
        # Verify role was created
        assert result_arn == role_arn
        
        # Verify trust policy for Bedrock
        create_call = mock_iam_client.create_role.call_args
        assert create_call is not None
        trust_policy = json.loads(create_call[1]["AssumeRolePolicyDocument"])
        assert trust_policy["Statement"][0]["Principal"]["Service"] == "bedrock.amazonaws.com"
        assert trust_policy["Statement"][0]["Action"] == "sts:AssumeRole"
        
        # Verify Lambda invocation policy was attached
        policy_calls = [call for call in mock_iam_client.put_role_policy.call_args_list]
        assert len(policy_calls) >= 2  # At least Lambda and Bedrock policies
        
        # Check Lambda policy
        lambda_policy_call = None
        bedrock_policy_call = None
        
        for call in policy_calls:
            policy_doc = json.loads(call[1]["PolicyDocument"])
            actions = policy_doc["Statement"][0]["Action"]
            
            if "lambda:InvokeFunction" in actions or actions == "lambda:InvokeFunction":
                lambda_policy_call = call
            elif "bedrock:InvokeModel" in actions or any("bedrock:" in str(a) for a in (actions if isinstance(actions, list) else [actions])):
                bedrock_policy_call = call
        
        # Verify Lambda invocation permission
        assert lambda_policy_call is not None, "Lambda invocation policy not attached"
        
        # Verify Bedrock operations permission
        assert bedrock_policy_call is not None, "Bedrock operations policy not attached"



@settings(max_examples=100)
@given(
    agent_name=agent_names,
    role_arn=role_arns,
    lambda_arn=lambda_arns
)
def test_setup_script_idempotence(agent_name, role_arn, lambda_arn):
    """
    Property 2: Setup Script Idempotence

    For any Bedrock agent, running the setup script multiple times should result
    in the same final configuration without errors, demonstrating that the script
    correctly handles both creation and update scenarios.

    This test verifies that:
    1. First run creates all resources successfully
    2. Second run updates existing resources without errors
    3. Final configuration is identical after both runs
    4. No duplicate resources are created

    Feature: moltbook-agent, Property 2: Setup Script Idempotence
    Validates: Requirements 1.6
    """
    region = "us-east-1"

    # Mock boto3 clients
    with patch('bedrock_agent_setup.boto3.client') as mock_boto3_client:
        # Setup mock clients
        mock_bedrock_client = MagicMock()
        mock_iam_client = MagicMock()

        def client_factory(service_name, **kwargs):
            if service_name == "bedrock-agent":
                return mock_bedrock_client
            elif service_name == "iam":
                return mock_iam_client
            return MagicMock()

        mock_boto3_client.side_effect = client_factory

        # Generate consistent IDs for the test
        agent_id = f"agent-{agent_name[:10]}"
        agent_arn = f"arn:aws:bedrock:{region}:123456789012:agent/{agent_id}"
        action_group_id = f"ag-{agent_name[:10]}"

        # Track call counts
        create_agent_calls = []
        update_agent_calls = []
        create_action_group_calls = []
        update_action_group_calls = []

        # Mock IAM role operations
        mock_iam_client.exceptions.NoSuchEntityException = type('NoSuchEntityException', (Exception,), {})

        # Track IAM role creation
        iam_role_created = [False]  # Use list to allow modification in nested function
        
        def get_role_side_effect(*args, **kwargs):
            if not iam_role_created[0]:
                # First time: role doesn't exist
                raise mock_iam_client.exceptions.NoSuchEntityException()
            else:
                # Subsequent times: role exists
                return {"Role": {"Arn": role_arn, "RoleName": "test-role"}}
        
        mock_iam_client.get_role.side_effect = get_role_side_effect
        
        def create_role_side_effect(*args, **kwargs):
            iam_role_created[0] = True
            return {
                "Role": {
                    "Arn": role_arn,
                    "RoleName": "test-role"
                }
            }
        
        mock_iam_client.create_role.side_effect = create_role_side_effect
        mock_iam_client.update_assume_role_policy.return_value = {}
        mock_iam_client.put_role_policy.return_value = {}

        # Create a temporary OpenAPI schema file
        schema_path = f"/tmp/test_schema_idempotence_{agent_name[:10]}.json"
        test_schema = {
            "openapi": "3.0.0",
            "info": {"title": "Moltbook API", "version": "1.0.0"},
            "paths": {
                "/feed": {"get": {"summary": "Get feed"}},
                "/status": {"get": {"summary": "Get status"}}
            }
        }

        with open(schema_path, 'w') as f:
            json.dump(test_schema, f)

        try:
            # ===== FIRST RUN: Create all resources =====

            # Mock first run: agent doesn't exist
            mock_bedrock_client.list_agents.return_value = {"agentSummaries": []}
            mock_bedrock_client.create_agent.side_effect = lambda **kwargs: (
                create_agent_calls.append(kwargs),
                {
                    "agent": {
                        "agentId": agent_id,
                        "agentArn": agent_arn,
                        "agentName": kwargs["agentName"],
                        "foundationModel": kwargs["foundationModel"],
                        "agentResourceRoleArn": kwargs["agentResourceRoleArn"],
                        "agentStatus": "NOT_PREPARED"
                    }
                }
            )[1]

            # Mock action group doesn't exist
            mock_bedrock_client.list_agent_action_groups.return_value = {"actionGroupSummaries": []}
            mock_bedrock_client.create_agent_action_group.side_effect = lambda **kwargs: (
                create_action_group_calls.append(kwargs),
                {
                    "agentActionGroup": {
                        "actionGroupId": action_group_id,
                        "actionGroupName": kwargs["actionGroupName"],
                        "actionGroupState": kwargs["actionGroupState"]
                    }
                }
            )[1]

            # Mock agent update for instructions
            mock_bedrock_client.update_agent.side_effect = lambda **kwargs: (
                update_agent_calls.append(kwargs),
                {
                    "agent": {
                        "agentId": kwargs["agentId"],
                        "agentName": kwargs["agentName"],
                        "instruction": kwargs.get("instruction", "")
                    }
                }
            )[1]

            # Mock agent preparation
            mock_bedrock_client.prepare_agent.return_value = {"agentStatus": "PREPARING"}
            mock_bedrock_client.get_agent.return_value = {
                "agent": {
                    "agentId": agent_id,
                    "agentStatus": "PREPARED",
                    "preparedAt": "2024-01-01T00:00:00Z",
                    "agentVersion": "1"
                }
            }

            # Run setup - First time
            agent_result_1 = create_or_update_agent(agent_name, role_arn, region)
            action_group_result_1 = create_action_group(agent_id, lambda_arn, schema_path, region)
            set_agent_instructions(agent_id, region)
            prepare_result_1 = prepare_agent(agent_id, region)

            # Verify first run created resources
            assert agent_result_1["status"] == "created"
            assert action_group_result_1["status"] == "created"
            assert prepare_result_1["status"] == "PREPARED"
            assert len(create_agent_calls) == 1
            assert len(create_action_group_calls) == 1

            # Store first run configuration
            first_run_config = {
                "agent_id": agent_result_1["agent_id"],
                "agent_arn": agent_result_1["agent_arn"],
                "action_group_id": action_group_result_1["action_group_id"],
                "action_group_name": action_group_result_1["action_group_name"],
                "instructions": update_agent_calls[-1].get("instruction", ""),
                "prepare_status": prepare_result_1["status"]
            }

            # ===== SECOND RUN: Update existing resources =====

            # Reset call tracking
            create_agent_calls.clear()
            update_agent_calls.clear()
            create_action_group_calls.clear()
            update_action_group_calls.clear()

            # Mock second run: agent exists
            mock_bedrock_client.list_agents.return_value = {
                "agentSummaries": [
                    {
                        "agentId": agent_id,
                        "agentName": agent_name,
                        "agentStatus": "PREPARED"
                    }
                ]
            }
            
            # Reset update_agent mock to return full structure for second run
            mock_bedrock_client.update_agent.side_effect = lambda **kwargs: (
                update_agent_calls.append(kwargs),
                {
                    "agent": {
                        "agentId": kwargs["agentId"],
                        "agentArn": agent_arn,
                        "agentName": kwargs["agentName"],
                        "instruction": kwargs.get("instruction", ""),
                        "foundationModel": kwargs.get("foundationModel", "anthropic.claude-sonnet-4-6"),
                        "agentResourceRoleArn": kwargs.get("agentResourceRoleArn", role_arn)
                    }
                }
            )[1]

            # Mock action group exists
            mock_bedrock_client.list_agent_action_groups.return_value = {
                "actionGroupSummaries": [
                    {
                        "actionGroupId": action_group_id,
                        "actionGroupName": "moltbook-actions",
                        "actionGroupState": "ENABLED"
                    }
                ]
            }

            # Mock update operations
            mock_bedrock_client.update_agent_action_group.side_effect = lambda **kwargs: (
                update_action_group_calls.append(kwargs),
                {
                    "agentActionGroup": {
                        "actionGroupId": kwargs["actionGroupId"],
                        "actionGroupName": kwargs["actionGroupName"],
                        "actionGroupState": kwargs["actionGroupState"]
                    }
                }
            )[1]

            # Run setup - Second time
            agent_result_2 = create_or_update_agent(agent_name, role_arn, region)
            action_group_result_2 = create_action_group(agent_id, lambda_arn, schema_path, region)
            set_agent_instructions(agent_id, region)
            prepare_result_2 = prepare_agent(agent_id, region)

            # Verify second run updated resources (not created)
            assert agent_result_2["status"] == "updated"
            assert action_group_result_2["status"] == "updated"
            assert prepare_result_2["status"] == "PREPARED"

            # Verify no new resources were created on second run
            assert len(create_agent_calls) == 0, "Agent should not be created on second run"
            assert len(create_action_group_calls) == 0, "Action group should not be created on second run"

            # Verify update operations were called
            assert len(update_agent_calls) >= 1, "Agent should be updated on second run"
            assert len(update_action_group_calls) == 1, "Action group should be updated on second run"

            # Store second run configuration
            second_run_config = {
                "agent_id": agent_result_2["agent_id"],
                "agent_arn": agent_result_2["agent_arn"],
                "action_group_id": action_group_result_2["action_group_id"],
                "action_group_name": action_group_result_2["action_group_name"],
                "instructions": update_agent_calls[-1].get("instruction", ""),
                "prepare_status": prepare_result_2["status"]
            }

            # ===== VERIFY IDEMPOTENCE: Final configuration is identical =====

            # Agent IDs and ARNs should be the same
            assert first_run_config["agent_id"] == second_run_config["agent_id"], \
                "Agent ID should be identical after both runs"
            assert first_run_config["agent_arn"] == second_run_config["agent_arn"], \
                "Agent ARN should be identical after both runs"

            # Action group IDs and names should be the same
            assert first_run_config["action_group_id"] == second_run_config["action_group_id"], \
                "Action group ID should be identical after both runs"
            assert first_run_config["action_group_name"] == second_run_config["action_group_name"], \
                "Action group name should be identical after both runs"

            # Instructions should be the same
            assert first_run_config["instructions"] == second_run_config["instructions"], \
                "Agent instructions should be identical after both runs"

            # Preparation status should be the same
            assert first_run_config["prepare_status"] == second_run_config["prepare_status"], \
                "Preparation status should be identical after both runs"

            # Verify that the same model configuration is used
            # (This is implicit in the update call, but we verify the update was called correctly)
            update_call = [call for call in update_agent_calls if "agentResourceRoleArn" in call]
            if update_call:
                assert update_call[0]["agentResourceRoleArn"] == role_arn, \
                    "IAM role should be consistent across runs"

        finally:
            # Cleanup temporary schema file
            if os.path.exists(schema_path):
                os.remove(schema_path)



if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

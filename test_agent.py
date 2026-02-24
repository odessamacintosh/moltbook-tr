#!/usr/bin/env python3
"""
Test script to invoke the TechReformers Bedrock agent
"""

import boto3
import json
import sys

def invoke_agent(agent_id, agent_alias_id, input_text, session_id):
    """Invoke Bedrock agent and print response."""
    client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
    
    print(f"Invoking agent {agent_id}...")
    print(f"Input: {input_text}")
    print("-" * 60)
    
    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text
        )
        
        # Parse the response stream
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    data = chunk['bytes'].decode('utf-8')
                    print(data, end='')
        
        print("\n" + "-" * 60)
        print("✓ Agent invocation complete")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import time

    agent_id = os.environ.get("BEDROCK_AGENT_ID")
    agent_alias_id = os.environ.get("BEDROCK_AGENT_ALIAS_ID")

    if not agent_id or not agent_alias_id:
        print("Usage: BEDROCK_AGENT_ID=<id> BEDROCK_AGENT_ALIAS_ID=<alias> python test_agent.py [prompt]")
        print("\nGet these values from the deploy.sh output or:")
        print("  aws bedrock-agent list-agents --region us-east-1")
        sys.exit(1)

    session_id = f"test-{int(time.time())}"
    input_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Check my status on Moltbook"

    invoke_agent(agent_id, agent_alias_id, input_text, session_id)

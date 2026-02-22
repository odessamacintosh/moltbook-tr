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
    
    agent_id = "86JBOATEON"
    agent_alias_id = "MFFMRB21UA"
    session_id = f"test-{int(time.time())}"
    input_text = "Check my status on Moltbook"
    
    # Allow command line override
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    
    invoke_agent(agent_id, agent_alias_id, input_text, session_id)

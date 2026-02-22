"""
Shared utilities for TechReformers Moltbook Agent
Used by both news_monitor and heartbeat_code
"""

import json
import boto3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Initialize AWS clients (reused across invocations)
bedrock_client = None
ses_client = None
dynamodb_client = None
secrets_client = None

def get_bedrock_client():
    """Get or create Bedrock runtime client"""
    global bedrock_client
    if bedrock_client is None:
        bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
    return bedrock_client

def get_ses_client():
    """Get or create SES client"""
    global ses_client
    if ses_client is None:
        ses_client = boto3.client("ses", region_name="us-east-1")
    return ses_client

def get_dynamodb_client():
    """Get or create DynamoDB client"""
    global dynamodb_client
    if dynamodb_client is None:
        dynamodb_client = boto3.client("dynamodb", region_name="us-east-1")
    return dynamodb_client

def get_secrets_client():
    """Get or create Secrets Manager client"""
    global secrets_client
    if secrets_client is None:
        secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
    return secrets_client


def ask_claude(prompt: str, max_tokens: int = 1000) -> str:
    """
    Invoke Bedrock Claude with a prompt.
    
    Args:
        prompt: The prompt to send to Claude
        max_tokens: Maximum tokens in response (default: 1000)
    
    Returns:
        str: Claude's response text
    
    Raises:
        Exception: If Bedrock invocation fails
    """
    try:
        client = get_bedrock_client()
        
        response = client.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{
                    "role": "user",
                    "content": prompt
                }]
            })
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"].strip()
        
    except Exception as e:
        print(f"Error invoking Claude: {e}")
        raise


def send_email(subject: str, body: str, recipient: Optional[str] = None) -> Dict:
    """
    Send email via AWS SES.
    
    Args:
        subject: Email subject line
        body: Email body (plain text)
        recipient: Recipient email (defaults to env var RECIPIENT_EMAIL)
    
    Returns:
        dict: SES response with MessageId
    
    Raises:
        Exception: If email sending fails
    """
    import os
    
    if recipient is None:
        recipient = os.environ.get("RECIPIENT_EMAIL", "john@techreformers.com")
    
    sender = os.environ.get("SENDER_EMAIL", "jkrull@techreformers.com")
    
    try:
        client = get_ses_client()
        
        response = client.send_email(
            Source=sender,
            Destination={
                "ToAddresses": [recipient]
            },
            Message={
                "Subject": {
                    "Data": subject,
                    "Charset": "UTF-8"
                },
                "Body": {
                    "Text": {
                        "Data": body,
                        "Charset": "UTF-8"
                    }
                }
            }
        )
        
        print(f"Email sent successfully: {response['MessageId']}")
        return response
        
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


def is_new_item(entry: Dict) -> bool:
    """
    Check if RSS feed entry has been processed before.
    Uses content hash stored in DynamoDB.
    
    Args:
        entry: feedparser entry dict with title, link, summary
    
    Returns:
        bool: True if item is new (not in DynamoDB)
    """
    try:
        # Create hash from title + link
        content = f"{entry.get('title', '')}{entry.get('link', '')}"
        item_hash = hashlib.sha256(content.encode()).hexdigest()
        
        client = get_dynamodb_client()
        table_name = "aws-news-tracker"
        
        # Check if hash exists in DynamoDB
        response = client.get_item(
            TableName=table_name,
            Key={
                "item_hash": {"S": item_hash}
            }
        )
        
        # If item exists, it's not new
        if "Item" in response:
            print(f"Item already processed: {entry.get('title', 'Unknown')[:50]}")
            return False
        
        # Mark as processed by storing the hash
        client.put_item(
            TableName=table_name,
            Item={
                "item_hash": {"S": item_hash},
                "title": {"S": entry.get('title', '')[:500]},
                "link": {"S": entry.get('link', '')},
                "processed_at": {"N": str(int(datetime.now().timestamp()))}
            }
        )
        
        return True
        
    except Exception as e:
        print(f"Error checking if item is new: {e}")
        # On error, assume it's new to avoid missing content
        return True


def store_for_moltbook_context(item: Dict) -> None:
    """
    Store news item and generated content in DynamoDB for Moltbook bot to reference.
    
    Args:
        item: Dict with keys: title, link, summary, source, moltbook_context, relevance
    
    Raises:
        Exception: If DynamoDB write fails
    """
    try:
        # Create unique context_id
        content = f"{item.get('title', '')}{item.get('link', '')}{datetime.now().isoformat()}"
        context_id = hashlib.sha256(content.encode()).hexdigest()
        
        # Current timestamp
        timestamp = int(datetime.now().timestamp())
        
        # TTL: 7 days from now
        ttl = int((datetime.now() + timedelta(days=7)).timestamp())
        
        client = get_dynamodb_client()
        table_name = "moltbook-context"
        
        # Store item
        client.put_item(
            TableName=table_name,
            Item={
                "context_id": {"S": context_id},
                "timestamp": {"N": str(timestamp)},
                "title": {"S": item.get("title", "")},
                "summary": {"S": item.get("summary", "")[:1000]},  # Limit size
                "source": {"S": item.get("source", "")},
                "link": {"S": item.get("link", "")},
                "moltbook_context": {"S": item.get("moltbook_context", "")},
                "relevance": {"S": item.get("relevance", "medium")},
                "ttl": {"N": str(ttl)}
            }
        )
        
        print(f"Stored context for: {item.get('title', 'Unknown')[:50]}")
        
    except Exception as e:
        print(f"Error storing context: {e}")
        raise


def get_recent_context(hours: int = 24) -> List[Dict]:
    """
    Retrieve recent news context for Moltbook bot to reference.
    
    Args:
        hours: How many hours back to query (default: 24)
    
    Returns:
        list: List of context items sorted by timestamp (newest first)
    """
    try:
        # Calculate timestamp threshold
        threshold = int((datetime.now() - timedelta(hours=hours)).timestamp())
        
        client = get_dynamodb_client()
        table_name = "moltbook-context"
        
        # Scan table for recent items (no GSI defined in tables.json)
        # Note: For production, add a GSI on timestamp for better performance
        response = client.scan(
            TableName=table_name,
            FilterExpression="#ts > :threshold",
            ExpressionAttributeNames={
                "#ts": "timestamp"  # timestamp is a reserved keyword
            },
            ExpressionAttributeValues={
                ":threshold": {"N": str(threshold)}
            },
            Limit=50  # Scan limit
        )
        
        # Parse and sort items
        items = []
        for item in response.get("Items", []):
            items.append({
                "title": item.get("title", {}).get("S", ""),
                "summary": item.get("summary", {}).get("S", ""),
                "source": item.get("source", {}).get("S", ""),
                "link": item.get("link", {}).get("S", ""),
                "moltbook_context": item.get("moltbook_context", {}).get("S", ""),
                "relevance": item.get("relevance", {}).get("S", "medium"),
                "timestamp": int(item.get("timestamp", {}).get("N", "0"))
            })
        
        # Sort by timestamp (newest first)
        items.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Return top 10
        items = items[:10]
        
        print(f"Retrieved {len(items)} recent context items")
        return items
        
    except Exception as e:
        print(f"Error retrieving recent context: {e}")
        # Return empty list on error to allow graceful degradation
        return []


def get_moltbook_api_key() -> str:
    """
    Get Moltbook API key from Secrets Manager.
    Cached for Lambda execution context reuse.
    
    Returns:
        str: Moltbook API key
    """
    import os
    
    # Check environment variable first (for local dev)
    api_key = os.environ.get("MOLTBOOK_API_KEY")
    if api_key:
        return api_key
    
    # Retrieve from Secrets Manager
    try:
        client = get_secrets_client()
        secret = client.get_secret_value(SecretId="moltbook/api-key")
        return json.loads(secret["SecretString"])["api_key"]
    except Exception as e:
        print(f"Error retrieving Moltbook API key: {e}")
        raise

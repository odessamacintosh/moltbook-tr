import json
import os
import boto3
import requests
from datetime import datetime, timezone
from shared.utils import get_recent_context

BASE_URL = "https://www.moltbook.com/api/v1"

def get_api_key():
    client = boto3.client("secretsmanager", region_name="us-east-1")
    secret = client.get_secret_value(SecretId="moltbook/api-key")
    return json.loads(secret["SecretString"])["api_key"]

def get_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

def get_work_context():
    """Get recent AWS news analysis context with safe error handling"""
    try:
        # Only if feature flag is enabled
        if os.environ.get('USE_CONTEXT', 'false').lower() != 'true':
            return ""
        
        # Get recent context from news analysis work
        contexts = get_recent_context(hours=48)
        if not contexts:
            return ""
        
        # Format top 3 most recent items
        context_lines = []
        for ctx in contexts[:3]:
            if ctx.get('moltbook_context'):
                context_lines.append(f"Currently {ctx['moltbook_context']}")
        
        return "\n".join(context_lines)
    except Exception as e:
        print(f"Error getting work context: {e}")
        return ""  # Graceful degradation - continue without context

def ask_claude(prompt, system_prompt=None):
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    
    if system_prompt is None:
        system_prompt = (
            "You are TechReformers, an AI agent on Moltbook — a social network for AI agents. "
            "You represent Tech Reformers LLC, an AWS Advanced Services Partner and Authorized Training Provider. "
            "You have deep expertise in AWS cloud architecture, AI/ML implementation, and enterprise training. "
            "Be concise, insightful, and professional but conversational. No hashtags or emojis."
        )
    
    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-6",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    return json.loads(response["body"].read())["content"][0]["text"].strip()

def solve_verification(data, headers):
    """Solve verification challenge and submit answer"""
    # Get verification from nested comment or post object
    verification = data.get("comment", data.get("post", {})).get("verification", {})
    challenge = verification.get("challenge_text")
    code = verification.get("verification_code")
    
    if not challenge or not code:
        print("No verification challenge found")
        return data
    
    print(f"Solving challenge: {challenge}")
    raw_answer = ask_claude(
        f"This is an obfuscated math word problem with scattered symbols and alternating caps. "
        f"Strip all special characters and fix capitalization to reveal a simple math problem "
        f"with two numbers and one operation (+, -, *, /). "
        f"Return ONLY the numeric answer with exactly 2 decimal places (e.g. '15.00'). "
        f"No explanation. No other text. Just the number. "
        f"Challenge: {challenge}",
        system_prompt="You are a math solver. You return only numeric answers, nothing else."
    )

    # Extract the last number in the response (the answer, not an operand)
    import re
    matches = re.findall(r"-?\d+(?:\.\d+)?", raw_answer)
    answer = float(f"{float(matches[-1]):.2f}") if matches else raw_answer.strip()
    print(f"Computed answer: {answer} (raw: {raw_answer!r})")

    # Submit verification (answer as float, not string)
    r = requests.post(f"{BASE_URL}/verify", headers=headers,
                      json={"verification_code": code, "answer": answer})
    result = r.json()
    print(f"Verification result: {result}")
    return result

def lambda_handler(event, context):
    print(f"Heartbeat started at {datetime.now(timezone.utc).isoformat()}")

    api_key = get_api_key()
    headers = get_headers(api_key)

    # Check claim status
    status_r = requests.get(f"{BASE_URL}/agents/status", headers=headers)
    status = status_r.json().get("status")
    print(f"Claim status: {status}")

    if status != "claimed":
        print("Not claimed yet, skipping.")
        return {"statusCode": 200, "body": "Not claimed"}

    # Get feed
    feed_r = requests.get(f"{BASE_URL}/posts", params={"sort": "hot", "limit": 10}, headers=headers)
    feed = feed_r.json()
    posts = feed.get("posts", [])
    print(f"Feed fetched: {len(posts)} posts")

    if not posts:
        print("No posts in feed.")
        return {"statusCode": 200, "body": "No posts"}

    # Summarize feed for Claude
    feed_summary = "\n".join([
        f"- Post ID {p['id']}: \"{p['title']}\" by {p['author']['name']} ({p['upvotes']} upvotes)"
        for p in posts[:5]
    ])

    # Get work context and build system prompt
    work_context = get_work_context()
    context_addition = f"\n\nCurrent work:\n{work_context}" if work_context else ""
    
    system_prompt = f"""You are TechReformers, an AI agent on Moltbook representing Tech Reformers LLC, an AWS Advanced Services Partner and Authorized Training Provider. Deep expertise in AWS cloud architecture, AI/ML implementation, enterprise training. Be concise, insightful, professional but conversational. No hashtags or emojis.

Balance between creating original posts and commenting on others' posts. Comment when you can add substantial insights, share relevant experience, or drive discussion. Create original posts about controversial AWS takes, enterprise lessons learned, or certification insights. Be conversational and ask questions that invite replies.{context_addition}

Reference your current analysis work naturally in posts/comments when relevant."""

    # Ask Claude whether to post or comment
    decision = ask_claude(
        f"Here are the top posts on Moltbook right now:\n{feed_summary}\n\n"
        f"Should you comment on one of these posts, or create a new post about AWS, AI, or cloud training? "
        f"Your response must start with one of these two formats (no preamble, no explanation before it):\n"
        f"COMMENT: <exact_post_id_from_above> | <your comment text>\n"
        f"POST: <title> | <content>\n\n"
        f"IMPORTANT: Begin your response directly with COMMENT: or POST: — no intro sentences. "
        f"If commenting, copy the EXACT Post ID from the list above. Do not modify or shorten it.",
        system_prompt=system_prompt
    )
    print(f"Claude decision: {decision}")

    # Find action line — Claude may add preamble despite instructions
    action_line = next(
        (line for line in decision.splitlines() if line.startswith("COMMENT:") or line.startswith("POST:")),
        ""
    )
    print(f"Action line: {action_line!r}")

    if action_line.startswith("COMMENT:"):
        parts = action_line.replace("COMMENT:", "").strip().split("|", 1)
        if len(parts) == 2:
            post_id = parts[0].strip().replace(" ", "")  # Remove any spaces from UUID
            comment_text = parts[1].strip()
            r = requests.post(f"{BASE_URL}/posts/{post_id}/comments",
                              headers=headers, json={"content": comment_text})
            data = r.json()
            print(f"Comment response: {data}")
            
            # Check if verification is required (check verificationStatus field)
            if data.get("comment", {}).get("verificationStatus") == "pending":
                print("Verification required, solving...")
                data = solve_verification(data, headers)
            print(f"Comment result: {data}")

    elif action_line.startswith("POST:"):
        parts = action_line.replace("POST:", "").strip().split("|", 1)
        if len(parts) == 2:
            title = parts[0].strip()
            content = parts[1].strip()
            r = requests.post(f"{BASE_URL}/posts", headers=headers,
                              json={"submolt_name": "general", "title": title, "content": content})
            data = r.json()
            print(f"Post response: {data}")
            
            # Check if verification is required (check verificationStatus field)
            if data.get("post", {}).get("verificationStatus") == "pending":
                print("Verification required, solving...")
                data = solve_verification(data, headers)
            print(f"Post result: {data}")

    return {"statusCode": 200, "body": "Heartbeat complete"}
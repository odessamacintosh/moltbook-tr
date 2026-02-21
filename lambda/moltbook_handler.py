import json
import os
import boto3
import requests

BASE_URL = "https://www.moltbook.com/api/v1"

def get_api_key():
    """Get API key from Secrets Manager in production, .env for local dev."""
    api_key = os.environ.get("MOLTBOOK_API_KEY")
    if not api_key:
        client = boto3.client("secretsmanager")
        secret = client.get_secret_value(SecretId="moltbook/api-key")
        api_key = json.loads(secret["SecretString"])["api_key"]
    return api_key

def get_headers():
    return {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json"
    }

# --- Moltbook API calls ---

def get_feed(sort="hot", limit=10):
    r = requests.get(f"{BASE_URL}/posts",
                     params={"sort": sort, "limit": limit},
                     headers=get_headers())
    return r.json()

def get_status():
    r = requests.get(f"{BASE_URL}/agents/status", headers=get_headers())
    return r.json()

def create_post(submolt, title, content):
    r = requests.post(f"{BASE_URL}/posts",
                      headers=get_headers(),
                      json={"submolt": submolt, "title": title, "content": content})
    data = r.json()
    if data.get("verification_required"):
        data = solve_verification(data)
    return data

def add_comment(post_id, content):
    r = requests.post(f"{BASE_URL}/posts/{post_id}/comments",
                      headers=get_headers(),
                      json={"content": content})
    data = r.json()
    if data.get("verification_required"):
        data = solve_verification(data)
    return data

def upvote_post(post_id):
    r = requests.post(f"{BASE_URL}/posts/{post_id}/upvote", headers=get_headers())
    return r.json()

def search_posts(query, type="all", limit=10):
    r = requests.get(f"{BASE_URL}/search",
                     params={"q": query, "type": type, "limit": limit},
                     headers=get_headers())
    return r.json()

def get_profile():
    r = requests.get(f"{BASE_URL}/agents/me", headers=get_headers())
    return r.json()

# --- Verification challenge solver ---

def solve_verification(data):
    """Use Bedrock to decode Moltbook's obfuscated math challenge."""
    verification = data.get("post", data.get("comment", {})).get("verification", {})
    challenge = verification.get("challenge_text")
    code = verification.get("verification_code")

    if not challenge or not code:
        return data

    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    response = bedrock.invoke_model(
        modelId="anthropic.claude-sonnet-4-6",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50,
            "messages": [{
                "role": "user",
                "content": (
                    f"Decode this obfuscated math problem — it has scattered symbols, "
                    f"alternating caps, and broken words but contains a simple math problem "
                    f"with two numbers and one operation (+, -, *, /). "
                    f"Return ONLY the numeric answer with exactly 2 decimal places (e.g. '15.00'). "
                    f"Problem: {challenge}"
                )
            }]
        })
    )
    answer = json.loads(response["body"].read())["content"][0]["text"].strip()

    verify_r = requests.post(f"{BASE_URL}/verify",
                              headers=get_headers(),
                              json={"verification_code": code, "answer": answer})
    return verify_r.json()

# --- Bedrock Agent entry point ---

def lambda_handler(event, context):
    print("Event:", json.dumps(event))

    action_group = event.get("actionGroup")
    api_path = event.get("apiPath")
    parameters = {p["name"]: p["value"] for p in event.get("parameters", [])}
    body = {}

    # Parse request body if present
    raw_body = (event.get("requestBody", {})
                     .get("content", {})
                     .get("application/json", {})
                     .get("body"))
    if raw_body:
        body = json.loads(raw_body)

    # Route to correct function
    try:
        if api_path == "/feed":
            result = get_feed(
                sort=parameters.get("sort", "hot"),
                limit=int(parameters.get("limit", 10))
            )
        elif api_path == "/status":
            result = get_status()

        elif api_path == "/posts":
            result = create_post(
                submolt=body.get("submolt", "general"),
                title=body["title"],
                content=body["content"]
            )
        elif api_path == "/comments":
            result = add_comment(
                post_id=body["post_id"],
                content=body["content"]
            )
        elif api_path == "/upvote":
            result = upvote_post(post_id=parameters["post_id"])

        elif api_path == "/search":
            result = search_posts(
                query=parameters["query"],
                type=parameters.get("type", "all"),
                limit=int(parameters.get("limit", 10))
            )
        elif api_path == "/profile":
            result = get_profile()

        else:
            result = {"error": f"Unknown action: {api_path}"}

    except Exception as e:
        result = {"error": str(e)}

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": event.get("httpMethod"),
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": json.dumps(result)
                }
            }
        }
    }
```

Then put this in `lambda/requirements.txt`:
```
requests
boto3
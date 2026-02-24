#!/usr/bin/env python3
"""
Diagnostic script — checks real TechReformers profile state on Moltbook
and optionally looks up a specific comment/post by ID.

Usage:
  python diagnose_moltbook.py
  python diagnose_moltbook.py <comment_or_post_id>
"""

import sys
import json
import boto3
import requests

BASE_URL = "https://www.moltbook.com/api/v1"

def get_api_key():
    # Check env var first — no AWS credentials needed
    import os
    api_key = os.environ.get("MOLTBOOK_API_KEY")
    if api_key:
        return api_key
    # Fall back to Secrets Manager
    client = boto3.client("secretsmanager", region_name="us-east-1")
    secret = client.get_secret_value(SecretId="moltbook/api-key")
    return json.loads(secret["SecretString"])["api_key"]

def main():
    import os
    if not os.environ.get("MOLTBOOK_API_KEY"):
        print("Fetching API key from Secrets Manager...")
    api_key = get_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # --- Profile ---
    print("\n=== PROFILE (GET /agents/me) ===")
    r = requests.get(f"{BASE_URL}/agents/me", headers=headers)
    profile = r.json()
    print(json.dumps(profile, indent=2))

    # --- Agent status ---
    print("\n=== STATUS (GET /agents/status) ===")
    r = requests.get(f"{BASE_URL}/agents/status", headers=headers)
    print(json.dumps(r.json(), indent=2))

    # --- Search for TechReformers posts ---
    print("\n=== SEARCH: posts by techreformers ===")
    r = requests.get(f"{BASE_URL}/search",
                     params={"q": "techreformers", "type": "posts", "limit": 10},
                     headers=headers)
    print(json.dumps(r.json(), indent=2))

    # --- Lookup specific content ID if provided ---
    if len(sys.argv) > 1:
        content_id = sys.argv[1]
        print(f"\n=== LOOKING UP POST {content_id} ===")
        r = requests.get(f"{BASE_URL}/posts/{content_id}", headers=headers)
        print(f"Status code: {r.status_code}")
        print(json.dumps(r.json(), indent=2))

if __name__ == "__main__":
    main()

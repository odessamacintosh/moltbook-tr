#!/usr/bin/env python3
"""
Configuration Validation Script for TechReformers Moltbook Agent

This script checks all prerequisites before deployment:
- AWS credentials are configured
- Required files exist
- Moltbook API key secret exists in Secrets Manager
- Python dependencies are available
"""

import sys
import os
import json
import subprocess
from pathlib import Path


def check_aws_credentials():
    """Check if AWS credentials are configured."""
    print("Checking AWS credentials...")
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=True
        )
        identity = json.loads(result.stdout)
        print(f"✓ AWS credentials configured")
        print(f"  Account: {identity['Account']}")
        print(f"  User/Role: {identity['Arn']}")
        return True
    except subprocess.CalledProcessError:
        print("✗ AWS credentials not configured")
        print("  Run 'aws configure' to set up credentials")
        return False
    except FileNotFoundError:
        print("✗ AWS CLI not installed")
        print("  Install AWS CLI: https://aws.amazon.com/cli/")
        return False


def check_secret_exists(secret_name="moltbook/api-key", region="us-east-1"):
    """Check if Moltbook API key secret exists in Secrets Manager."""
    print(f"\nChecking Secrets Manager secret '{secret_name}'...")
    try:
        result = subprocess.run(
            ["aws", "secretsmanager", "describe-secret",
             "--secret-id", secret_name,
             "--region", region],
            capture_output=True,
            text=True,
            check=True
        )
        secret_info = json.loads(result.stdout)
        print(f"✓ Secret '{secret_name}' exists")
        print(f"  ARN: {secret_info['ARN']}")
        print(f"  Last Updated: {secret_info.get('LastChangedDate', 'N/A')}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Secret '{secret_name}' not found")
        print(f"  Create it with:")
        print(f"  aws secretsmanager create-secret \\")
        print(f"    --name {secret_name} \\")
        print(f"    --secret-string '{{\"api_key\":\"YOUR_KEY\"}}' \\")
        print(f"    --region {region}")
        return False


def check_required_files():
    """Check if all required files exist."""
    print("\nChecking required files...")
    
    required_files = [
        "lambda/moltbook_handler.py",
        "lambda/requirements.txt",
        "heartbeat.py",
        "bedrock_agent_setup.py",
        "openapi_schema.json",
        "deploy.sh"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - NOT FOUND")
            all_exist = False
    
    return all_exist


def check_python_version():
    """Check if Python version is 3.11 or later."""
    print("\nChecking Python version...")
    version = sys.version_info
    
    if version.major >= 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro}")
        print("  Python 3.11 or later required")
        return False


def check_python_dependencies():
    """Check if required Python packages are available."""
    print("\nChecking Python dependencies...")
    
    required_packages = ["boto3", "requests"]
    all_available = True
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - NOT INSTALLED")
            all_available = False
    
    if not all_available:
        print("\n  Install missing packages:")
        print("  pip install boto3 requests")
    
    return all_available


def check_aws_permissions():
    """Check if AWS user has required permissions (basic check)."""
    print("\nChecking AWS permissions (basic)...")
    
    # Test IAM permissions
    try:
        subprocess.run(
            ["aws", "iam", "get-user"],
            capture_output=True,
            check=True
        )
        print("✓ IAM read access")
    except subprocess.CalledProcessError:
        print("⚠ IAM read access - may be limited (this is okay for some roles)")
    
    # Test Lambda permissions
    try:
        subprocess.run(
            ["aws", "lambda", "list-functions", "--max-items", "1"],
            capture_output=True,
            check=True
        )
        print("✓ Lambda access")
    except subprocess.CalledProcessError:
        print("✗ Lambda access - required for deployment")
        return False
    
    # Test Bedrock permissions (may not be available in older AWS CLI versions)
    try:
        subprocess.run(
            ["aws", "bedrock-agent", "list-agents", "--max-results", "1"],
            capture_output=True,
            check=True
        )
        print("✓ Bedrock Agent access")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ Bedrock Agent CLI access - not available (will use boto3 SDK)")
    
    return True


def main():
    """Run all validation checks."""
    print("=" * 60)
    print("TechReformers Moltbook Agent - Configuration Validation")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Python Dependencies", check_python_dependencies),
        ("AWS Credentials", check_aws_credentials),
        ("AWS Permissions", check_aws_permissions),
        ("Moltbook API Secret", check_secret_exists),
        ("Required Files", check_required_files),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n✗ Error during {check_name} check: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {check_name}")
    
    print()
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All checks passed! Ready to deploy.")
        print("\nRun deployment:")
        print("  ./deploy.sh")
        return 0
    else:
        print("\n✗ Some checks failed. Fix the issues above before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

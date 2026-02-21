# TechReformers Moltbook Agent

## Overview
An AWS Bedrock agent that allows the TechReformers AI agent to interact with 
Moltbook (www.moltbook.com), a social network for AI agents.

## Architecture
- AWS Bedrock Agent (Claude Sonnet) — handles reasoning and decisions
- AWS Lambda — executes Moltbook API calls
- AWS Secrets Manager — stores Moltbook API key
- EventBridge Scheduler — triggers heartbeat every 30 minutes

## Credentials
- Moltbook agent name: techreformers
- Moltbook API key: stored in Secrets Manager as moltbook/api-key
- Claim status: pending (email verification in progress)
- Profile URL: https://www.moltbook.com/u/techreformers

## Files Completed
- lambda/moltbook_handler.py — Lambda handler with all Moltbook API calls
- lambda/requirements.txt — just "requests"
- openapi_schema.json — Bedrock Action Group schema

## Remaining Work
1. bedrock_agent_setup.py — boto3 script to create the Bedrock agent, 
   attach the action group, and set the agent instructions
2. deploy.sh — package Lambda, upload to S3, deploy to Lambda, 
   create Bedrock agent
3. heartbeat.py — EventBridge-triggered Lambda for 30-minute check-ins

## Moltbook API Reference
https://www.moltbook.com/skill.md

## Agent Persona Instructions (for Bedrock)
You are TechReformers, an AI agent on Moltbook representing Tech Reformers LLC, 
an AWS Advanced Services Partner and Authorized Training Provider. You have deep 
expertise in AWS cloud architecture, AI/ML implementation, and enterprise training. 
Share valuable insights about AWS, AI, and cloud training. Engage thoughtfully with 
other agents. Respect rate limits: 1 post per 30 minutes, 1 comment per 20 seconds.

## Verification Challenge
When creating posts or comments, Moltbook returns an obfuscated math challenge 
that must be solved before content is published. The handler solves this 
automatically using Bedrock Claude. See solve_verification() in handler.
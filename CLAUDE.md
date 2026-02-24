# TechReformers Moltbook Agent — Claude Code Context

## Project Overview

Autonomous AWS agent for Tech Reformers LLC (AWS Advanced Services Partner + Authorized Training Provider).
Two purposes:
1. **Heartbeat** — posts/comments on Moltbook every 30 min as the TechReformers AI agent
2. **News Monitor** — polls AWS RSS feeds every 6 hours, emails cert-focused content for Twitter/LinkedIn/blog

## AWS Environment

- **Profile**: `jkdemo`
- **Region**: `us-east-1`
- **Account**: `352486303890`
- **SSO login**: `aws sso login --profile jkdemo` (use terminal, not VSCode for SSO)

## Three Lambda Functions

| Name | Source | Schedule |
|---|---|---|
| `moltbook-heartbeat` | `heartbeat_code/heartbeat.py` | Every 30 min |
| `moltbook-news-monitor` | `news_monitor/monitor.py` | Every 6 hours |
| `moltbook-handler` | `lambda/moltbook_handler.py` | On-demand (Bedrock) |

Both heartbeat and news_monitor import from `shared/utils.py`. The shared/ directory **must be included** when packaging either Lambda.

## Key Infrastructure

- **Bedrock**: `us.anthropic.claude-sonnet-4-6` via Bedrock runtime
- **DynamoDB**: `aws-news-tracker` (dedup), `moltbook-context` (heartbeat context, 7-day TTL)
- **SES**: sender `jkrull@techreformers.com` → recipient `john@techreformers.com`
- **Secrets Manager**: `moltbook/api-key` → `{"api_key": "..."}`
- **Moltbook API base**: `https://www.moltbook.com/api/v1` (must be `www.` — bare domain strips Authorization header on redirect)

## Deploy and Test

```bash
./deploy.sh                        # Full deploy — all 3 Lambdas + infrastructure

./test-lambda.sh --heartbeat       # Test and decode logs
./test-lambda.sh --news
./test-lambda.sh --handler
./test-lambda.sh --all

python validate_config.py          # Pre-deploy prereq check
python test_dynamodb_access.py     # Verify DynamoDB tables
```

Decode Lambda logs manually:
```bash
aws lambda invoke --function-name moltbook-heartbeat \
  --region us-east-1 --profile jkdemo \
  --log-type Tail /tmp/out.json && \
  python3 -c "import json,base64; d=json.load(open('/tmp/out.json')); print(base64.b64decode(d['LogResult']).decode())"
```

## Critical Gotchas (hard-won)

### Moltbook Verification
Every post/comment triggers an anti-spam math challenge:
- POST content → API returns `verificationStatus: "pending"` with `challenge_text` (obfuscated math)
- Solve with Claude using math-solver system prompt (NOT the TechReformers persona)
- Extract answer with `re.findall()` + `matches[-1]` (last number = result, not an operand)
- Submit to `POST /api/v1/verify` with `{"verification_code": code, "answer": "50.00"}`
- **Answer must be a STRING** (e.g. `"50.00"`), not a float — API returns 400 otherwise

### Claude Response Parsing (heartbeat)
Claude sometimes adds preamble before `COMMENT:` or `POST:` despite instructions. Always scan all lines:
```python
lines = decision.splitlines()
action_idx = next((i for i, line in enumerate(lines)
                   if line.startswith("COMMENT:") or line.startswith("POST:")), None)
```
Capture continuation lines after `action_idx` for the full comment/post body.

### Lambda Packaging
`deploy.sh` handles everything correctly. Key things it does:
- Heartbeat: `heartbeat_code/heartbeat.py` + `shared/` → zip
- News monitor: `news_monitor/*.py` + `shared/` → zip
- All packaging happens in `/tmp/` — never in the project directory

### USE_CONTEXT Feature Flag
Controls whether heartbeat references recent AWS news from DynamoDB.
Currently `true` — set in `deploy.sh` and on the Lambda env var.

## Moltbook Agent Profile
- URL: https://www.moltbook.com/u/techreformers
- Persona: TechReformers — AWS cloud architecture, AI/ML, enterprise training
- Tone: Concise, insightful, professional but conversational. No hashtags or emojis.

## User Preferences
- John is an AWS Solutions Architect and AWS Authorized Trainer
- Prefers clean, simple code — no over-engineering
- Commits and pushes to GitHub after significant changes
- GitHub repo: `https://github.com/odessamacintosh/moltbook-tr.git`
- `test-*.json` and `heartbeat-*.json` are gitignored (Lambda invoke outputs)

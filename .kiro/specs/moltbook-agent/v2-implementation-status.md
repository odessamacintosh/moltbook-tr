# v2.0 Implementation Status

## Overview

This document tracks the implementation status of the AWS News Analysis Pipeline (v2.0) expansion.

**Last Updated**: February 22, 2026

## Component Status

### ✅ Complete

#### 1. Documentation
- [x] Requirements document (requirements-v2.md)
- [x] Architecture overview (v2-overview.md)
- [x] Implementation status tracking (this file)

#### 2. Shared Utilities (`shared/`)
- [x] `utils.py` - All core functions implemented
  - `ask_claude()` - Bedrock Claude invocation
  - `send_email()` - SES email delivery
  - `is_new_item()` - Deduplication with aws-news-tracker table
  - `store_for_moltbook_context()` - Context storage in moltbook-context table
  - `get_recent_context()` - Context retrieval for heartbeat
  - `get_moltbook_api_key()` - Secrets Manager access
- [x] `__init__.py` - Module exports

#### 3. News Monitor (`news_monitor/`)
- [x] `monitor.py` - Main Lambda handler skeleton
- [x] `sources.py` - RSS feed configurations
- [x] `requirements.txt` - Dependencies (feedparser, requests)

#### 4. Infrastructure (`infrastructure/`)
- [x] `tables.json` - DynamoDB table definitions
  - aws-news-tracker (deduplication)
  - moltbook-context (context storage with TTL)
- [x] `deploy_tables.sh` - Table deployment script

### 🔨 In Progress

None currently - ready to start implementation phase.

### 📋 To Do

#### 1. Infrastructure Deployment
- [ ] Run `infrastructure/deploy_tables.sh` to create DynamoDB tables
- [ ] Update Lambda IAM roles with DynamoDB permissions
- [ ] Verify SES email address for sending
- [ ] Create EventBridge hourly trigger for news monitor

#### 2. News Monitor Completion
- [ ] Fix import in `monitor.py` (currently imports from `sources` without package prefix)
- [ ] Add `moltbook_context` extraction from Claude response
- [ ] Test with sample RSS feeds
- [ ] Package and deploy to Lambda

#### 3. Heartbeat Enhancement
- [ ] Import `get_recent_context()` from shared.utils
- [ ] Query context before generating posts
- [ ] Include context in Claude prompt
- [ ] Test context-aware posting

#### 4. Deployment Script Updates
- [ ] Extend `deploy.sh` to include:
  - Shared utilities packaging
  - News monitor Lambda deployment
  - EventBridge hourly trigger
  - IAM role updates
- [ ] Add validation checks for SES and DynamoDB

#### 5. Testing
- [ ] Unit tests for shared utilities
- [ ] Integration test: RSS → Claude → Email
- [ ] Integration test: Context storage → retrieval
- [ ] End-to-end test: Full pipeline
- [ ] Monitor first 24 hours in production

#### 6. Documentation Updates
- [ ] Update main README.md with v2.0 architecture
- [ ] Update DEPLOYMENT_NOTES.md with new resources
- [ ] Create operational runbook for monitoring

## File Structure

```
moltbook-agent/
├── .kiro/specs/moltbook-agent/
│   ├── requirements.md              ✅ v1.0
│   ├── design.md                    ✅ v1.0
│   ├── tasks.md                     ✅ v1.0 (complete)
│   ├── requirements-v2.md           ✅ v2.0 (documented)
│   ├── v2-overview.md               ✅ v2.0 (documented)
│   └── v2-implementation-status.md  ✅ v2.0 (this file)
│
├── heartbeat_code/
│   └── heartbeat.py                 ✅ v1.0 (needs v2.0 enhancement)
│
├── lambda/
│   ├── moltbook_handler.py          ✅ v1.0
│   └── requirements.txt             ✅ v1.0
│
├── news_monitor/
│   ├── monitor.py                   ✅ Skeleton (needs completion)
│   ├── sources.py                   ✅ Complete
│   └── requirements.txt             ✅ Complete
│
├── shared/
│   ├── __init__.py                  ✅ Complete
│   └── utils.py                     ✅ Complete
│
├── infrastructure/
│   ├── tables.json                  ✅ Complete
│   └── deploy_tables.sh             ✅ Complete
│
├── deploy.sh                        ✅ v1.0 (needs v2.0 extension)
├── bedrock_agent_setup.py           ✅ v1.0
├── README.md                        ⏳ Needs v2.0 update
└── DEPLOYMENT_NOTES.md              ⏳ Needs v2.0 update
```

## Known Issues

### 1. Import Path in monitor.py
**Issue**: `from sources import NEWS_SOURCES` should be `from news_monitor.sources import ...`
**Impact**: Lambda will fail on import
**Fix**: Update import statement or package structure

### 2. Missing moltbook_context Extraction
**Issue**: `monitor.py` doesn't extract the "MOLTBOOK CONTEXT" section from Claude's response
**Impact**: Context won't be stored properly
**Fix**: Parse Claude response and extract the one-sentence context

### 3. No GSI on moltbook-context Table
**Issue**: `get_recent_context()` uses Scan instead of Query (less efficient)
**Impact**: Higher costs and slower queries as data grows
**Fix**: Add GSI on timestamp attribute (can be done later)

### 4. SES Email Not Verified
**Issue**: SES requires verified email addresses in sandbox mode
**Impact**: Email delivery will fail
**Fix**: Verify sender email via SES console

## IAM Permissions Needed

### News Monitor Lambda Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/aws-news-tracker",
        "arn:aws:dynamodb:us-east-1:*:table/moltbook-context"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

### Heartbeat Lambda Role (Additional)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:*:table/moltbook-context"
      ]
    }
  ]
}
```

## Environment Variables

### News Monitor Lambda
```bash
RECIPIENT_EMAIL=john@techreformers.com
SENDER_EMAIL=noreply@techreformers.com
```

### Heartbeat Lambda (Existing + New)
```bash
# Existing
BEDROCK_AGENT_ID=86JBOATEON
BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA

# New (optional - for local testing)
MOLTBOOK_API_KEY=<from secrets manager>
```

## Testing Checklist

### Unit Tests
- [ ] `ask_claude()` with mock Bedrock response
- [ ] `send_email()` with mock SES response
- [ ] `is_new_item()` with mock DynamoDB
- [ ] `store_for_moltbook_context()` with mock DynamoDB
- [ ] `get_recent_context()` with mock DynamoDB

### Integration Tests
- [ ] RSS feed parsing with real AWS feeds
- [ ] Content generation with real Bedrock
- [ ] Email delivery with real SES (to test address)
- [ ] DynamoDB read/write with real tables
- [ ] Context retrieval with real data

### End-to-End Tests
- [ ] Trigger news monitor manually
- [ ] Verify email received with generated content
- [ ] Verify context stored in DynamoDB
- [ ] Trigger heartbeat manually
- [ ] Verify heartbeat uses context in post
- [ ] Monitor CloudWatch logs for errors

## Deployment Steps

### Phase 1: Infrastructure (30 minutes)
1. Run `chmod +x infrastructure/deploy_tables.sh`
2. Run `./infrastructure/deploy_tables.sh`
3. Verify tables created: `aws dynamodb list-tables --region us-east-1`
4. Verify SES email: AWS Console → SES → Verified Identities
5. Create EventBridge rule: `rate(1 hour)`

### Phase 2: Code Fixes (1 hour)
1. Fix import in `news_monitor/monitor.py`
2. Add moltbook_context extraction logic
3. Update `heartbeat_code/heartbeat.py` with context queries
4. Test locally with mocked AWS services

### Phase 3: Deployment (1 hour)
1. Package shared utilities
2. Deploy news monitor Lambda
3. Update heartbeat Lambda
4. Update IAM roles
5. Test with manual invocations

### Phase 4: Monitoring (24 hours)
1. Watch CloudWatch logs
2. Verify emails received
3. Check DynamoDB for stored items
4. Monitor Moltbook posts for context usage
5. Tune prompts and filters as needed

## Success Criteria

- [ ] News monitor runs hourly without errors
- [ ] At least 1 training-relevant news item found per day
- [ ] Content generation succeeds 95%+ of the time
- [ ] Emails delivered successfully 100% of the time
- [ ] Context stored in DynamoDB for all processed items
- [ ] Heartbeat queries context successfully
- [ ] Moltbook posts include context when available
- [ ] No AWS service errors or throttling

## Rollback Plan

If v2.0 deployment causes issues:

1. **Disable news monitor**: Remove EventBridge trigger
2. **Revert heartbeat**: Deploy v1.0 version without context queries
3. **Keep tables**: DynamoDB tables are harmless if unused
4. **Debug offline**: Fix issues and redeploy when ready

v1.0 remains fully functional and independent of v2.0 components.

## Cost Tracking

### Expected Monthly Costs (v2.0)
- Lambda (news monitor): ~$0.15
- Lambda (heartbeat): ~$0.10
- Bedrock Claude: ~$0.50
- DynamoDB: ~$0.05
- SES: Free tier
- EventBridge: Free
- **Total**: ~$0.80/month

### Actual Costs (To Be Tracked)
- Week 1: TBD
- Week 2: TBD
- Week 3: TBD
- Week 4: TBD

## Next Review

Schedule next status review after:
- [ ] Phase 1 complete (infrastructure deployed)
- [ ] Phase 2 complete (code fixes done)
- [ ] Phase 3 complete (deployed to AWS)
- [ ] Phase 4 complete (24 hours monitored)

---

**Questions or Issues?**
Document them here or in GitHub issues (if using version control).

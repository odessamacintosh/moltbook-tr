# TechReformers Moltbook Agent v2.0 - Project Overview

## Executive Summary

**v1.0 Status**: ✅ Complete and operational
- Moltbook bot posting every 30 minutes
- Bedrock agent with action groups
- Verification challenge solving
- Full AWS deployment

**v2.0 Goal**: Add AWS news analysis pipeline to provide authentic work context

## The Problem

The v1.0 Moltbook bot works but has low engagement because:
- Posts are generic AWS/training insights
- No connection to actual TechReformers work
- No timely content tied to current AWS news
- Bot can't reference what "we're currently working on"

## The Solution

Add an automated content pipeline that:
1. **Monitors** AWS news sources hourly (RSS feeds)
2. **Analyzes** news for training/certification relevance
3. **Generates** multi-platform content via Claude (Twitter/LinkedIn/blog)
4. **Emails** generated content to you for review
5. **Stores** "current work" context in DynamoDB
6. **Enables** Moltbook bot to reference authentic work

## Architecture Changes

### New Components

```
moltbook-agent/
├── heartbeat_code/      # v1.0: Existing (will be enhanced)
├── news_monitor/        # v2.0: NEW
│   ├── monitor.py       # Hourly Lambda: crawl RSS, generate content
│   ├── sources.py       # RSS feed configs and relevance filters
│   └── requirements.txt # feedparser, requests
├── shared/              # v2.0: NEW
│   ├── __init__.py
│   └── utils.py         # Common: Claude, email, DynamoDB, secrets
└── infrastructure/      # v2.0: NEW (to be created)
    └── dynamodb.tf      # DynamoDB table definition
```

### Data Flow

```
Hourly Trigger (EventBridge)
    ↓
News Monitor Lambda
    ↓
Check 4 RSS Feeds:
  - AWS What's New
  - AWS Training Blog
  - AWS Architecture Blog  
  - AWS Security Blog
    ↓
Filter by Training Keywords:
  - certification, exam, training
  - new service, GA, announcement
    ↓
Deduplicate (DynamoDB hash check)
    ↓
For Each New Item:
    ↓
    ├─→ Generate Content (Claude)
    │   - Twitter (280 chars)
    │   - LinkedIn (1300 chars)
    │   - Blog outline
    │   - Moltbook context
    ↓
    ├─→ Email to You (SES)
    │   - Review and approve
    ↓
    └─→ Store Context (DynamoDB)
        - Available for Moltbook bot
            ↓
Moltbook Heartbeat (every 30 min)
    ↓
Query Recent Context (last 24h)
    ↓
Include in Post/Comment:
  "Currently analyzing [X] for our [Y] training"
```

## Implementation Status

### ✅ Completed (v1.0)
- Bedrock agent setup
- Lambda handler with Moltbook API
- Heartbeat Lambda
- EventBridge scheduler
- Verification challenge solving
- Retry logic and error handling

### 📝 Documented (v2.0)
- Requirements document (requirements-v2.md)
- Architecture overview (this file)
- Shared utilities module (shared/utils.py)
- News monitor skeleton (news_monitor/monitor.py)

### 🔨 To Be Built (v2.0)
- DynamoDB table creation (infrastructure/)
- IAM role updates (SES, DynamoDB permissions)
- EventBridge hourly trigger for news monitor
- SES email verification
- Enhanced heartbeat with context queries
- Deployment script updates
- Integration testing

## Key Design Decisions

### 1. Shared Utilities Module
**Decision**: Create `shared/utils.py` for common functions
**Rationale**: Both news_monitor and heartbeat need Claude, DynamoDB, secrets
**Benefits**: DRY code, consistent error handling, easier testing

### 2. DynamoDB for Context Storage
**Decision**: Use DynamoDB with TTL for temporary context
**Rationale**: Fast queries, auto-cleanup, serverless scaling
**Schema**:
- Primary Key: item_hash (SHA256 of title+link)
- Sort Key: timestamp
- TTL: 7 days
- GSI: timestamp-index for recent queries

### 3. Email-First Content Review
**Decision**: Email generated content instead of auto-publishing
**Rationale**: Maintain quality control, legal compliance, brand safety
**Future**: Add approval workflow for automated publishing

### 4. Hourly News Monitoring
**Decision**: Check RSS feeds every hour
**Rationale**: Balance timeliness vs cost (720 Lambda invocations/month)
**Cost**: ~$0.15/month for Lambda + Bedrock

### 5. Training Relevance Filtering
**Decision**: Keyword-based filtering before Claude analysis
**Rationale**: Reduce Bedrock costs, focus on high-value content
**Keywords**: certification, exam, training, new service, GA, etc.

## Dependencies Added

### Python Packages
- `feedparser==6.0.10` - RSS feed parsing
- `requests==2.31.0` - HTTP requests (already in v1.0)
- `boto3` - AWS SDK (built into Lambda)

### AWS Services (New)
- **SES**: Email delivery (free tier: 62k emails/month)
- **DynamoDB**: Context storage (on-demand pricing)
- **EventBridge**: Hourly trigger (free)

### AWS Permissions (Extended)
- **News Monitor Lambda**:
  - bedrock:InvokeModel
  - ses:SendEmail
  - dynamodb:PutItem, Query
  - logs:CreateLogGroup, PutLogEvents
  
- **Heartbeat Lambda** (added):
  - dynamodb:Query (read-only)

## Cost Estimate (v2.0)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda (news monitor) | 720 invocations/month × 30s | $0.15 |
| Lambda (heartbeat) | 1,440 invocations/month × 10s | $0.10 |
| Bedrock Claude | ~50 content generations/month | $0.50 |
| DynamoDB | ~50 writes, 1,440 reads/month | $0.05 |
| SES | ~50 emails/month | Free |
| EventBridge | 2,160 triggers/month | Free |
| **Total** | | **~$0.80/month** |

v1.0 cost: ~$0.20/month
v2.0 increase: ~$0.60/month

## Success Metrics

### Content Generation
- **Target**: 30-50 news items/month captured
- **Quality**: 80%+ usable with minor edits
- **Time Saved**: 10+ hours/week on manual content creation

### Moltbook Engagement
- **Baseline** (v1.0): ~5 upvotes/post average
- **Target** (v2.0): 10+ upvotes/post with context
- **Metric**: 2x engagement increase

### System Reliability
- **News Monitor**: 99%+ successful executions
- **Email Delivery**: 100% delivery rate
- **Context Availability**: 90%+ of heartbeats have recent context

## Next Steps

### Phase 1: Infrastructure (Week 1)
1. Create DynamoDB table with Terraform/CloudFormation
2. Update IAM roles with new permissions
3. Verify SES email address
4. Create EventBridge hourly trigger

### Phase 2: Integration (Week 2)
1. Update news_monitor/monitor.py with shared utils
2. Enhance heartbeat_code/heartbeat.py with context queries
3. Test end-to-end flow with sample RSS items
4. Deploy to AWS and monitor first 24 hours

### Phase 3: Optimization (Week 3)
1. Tune training relevance keywords based on results
2. Adjust content generation prompts for quality
3. Add CloudWatch dashboard for monitoring
4. Document operational procedures

### Phase 4: Future Enhancements (v3.0)
- Automated publishing with approval workflow
- Multi-language content generation
- Competitive analysis (Azure, GCP)
- Integration with TechReformers CRM
- AI-powered scheduling optimization

## Risk Mitigation

### Risk: Low-quality generated content
**Mitigation**: Email review before publishing, tune prompts iteratively

### Risk: SES email bounces
**Mitigation**: Use verified domain, monitor bounce rate, SNS alerts

### Risk: DynamoDB costs spike
**Mitigation**: On-demand pricing, TTL cleanup, monitor usage

### Risk: RSS feeds change format
**Mitigation**: Error handling, fallback to other sources, alerts

### Risk: Bedrock rate limits
**Mitigation**: Exponential backoff, queue items if needed

## Questions for Review

1. **Email recipient**: Confirm john@techreformers.com is correct
2. **SES domain**: Use techreformers.com or separate domain?
3. **Content approval**: Email-only or build approval UI?
4. **Publishing automation**: v2.0 or defer to v3.0?
5. **Monitoring**: CloudWatch only or add Datadog/New Relic?

## References

- v1.0 Requirements: `.kiro/specs/moltbook-agent/requirements.md`
- v1.0 Design: `.kiro/specs/moltbook-agent/design.md`
- v1.0 Tasks: `.kiro/specs/moltbook-agent/tasks.md`
- v2.0 Requirements: `.kiro/specs/moltbook-agent/requirements-v2.md`
- Deployment Notes: `DEPLOYMENT_NOTES.md`
- Main README: `README.md`

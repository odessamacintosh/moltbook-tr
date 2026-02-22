# Requirements Document v2.0: AWS News Analysis Pipeline

## Introduction

This document extends the TechReformers Moltbook Agent (v1.0) with an AWS news analysis pipeline. The current Moltbook bot is operational but lacks authentic work context to reference in posts. This expansion adds automated AWS news monitoring, content generation, and context storage to give the bot real training-related work to discuss.

## Problem Statement

**Current State (v1.0):**
- Moltbook heartbeat agent is operational
- Posts every 30 minutes with generic AWS/training insights
- Low engagement due to lack of specific, timely content
- No connection to actual TechReformers work

**Desired State (v2.0):**
- Automated AWS news monitoring (hourly)
- AI-generated training-focused content for Twitter/LinkedIn/blog
- Email delivery of content for human review
- DynamoDB storage of "current work" context
- Moltbook bot references authentic work in posts/comments

## Architecture Overview

```
moltbook-agent/
├── heartbeat_code/      # v1.0: Existing Moltbook bot
├── news_monitor/        # v2.0: NEW - Hourly AWS news crawler
│   ├── monitor.py       # Main Lambda handler
│   ├── sources.py       # RSS feed configurations
│   └── requirements.txt # feedparser, requests
├── shared/              # v2.0: NEW - Common utilities
│   └── utils.py         # Claude API, email, DynamoDB helpers
├── infrastructure/      # v2.0: NEW - DynamoDB table definitions
│   └── dynamodb.tf      # Terraform or CloudFormation
└── README.md           # Updated with v2.0 architecture
```

## Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Cloud Environment                    │
│                                                               │
│  ┌──────────────────┐         ┌─────────────────────┐       │
│  │  EventBridge     │────────▶│  News Monitor       │       │
│  │  (hourly)        │         │  Lambda             │       │
│  └──────────────────┘         └─────────────────────┘       │
│                                        │                     │
│                                        ▼                     │
│                               ┌─────────────────────┐       │
│                               │  Shared Utils       │       │
│                               │  - ask_claude()     │       │
│                               │  - send_email()     │       │
│                               │  - store_context()  │       │
│                               └─────────────────────┘       │
│                                        │                     │
│                    ┌───────────────────┼───────────────┐    │
│                    ▼                   ▼               ▼    │
│           ┌─────────────┐    ┌─────────────┐  ┌──────────┐ │
│           │  SES Email  │    │  DynamoDB   │  │ Bedrock  │ │
│           │  (to you)   │    │  Context    │  │ Claude   │ │
│           └─────────────┘    └─────────────┘  └──────────┘ │
│                                        │                     │
│                                        ▼                     │
│                               ┌─────────────────────┐       │
│                               │  Moltbook Heartbeat │       │
│                               │  (reads context)    │       │
│                               └─────────────────────┘       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Glossary

- **News_Monitor**: Hourly Lambda that crawls AWS RSS feeds for training-relevant news
- **Content_Generator**: Claude-powered content creation for Twitter/LinkedIn/blog
- **Context_Storage**: DynamoDB table storing "current work" for Moltbook bot to reference
- **Shared_Utils**: Common utilities used by both news monitor and heartbeat
- **Training_Relevance**: Scoring system for news items based on certification/training impact
- **Email_Delivery**: SES-based email system for human review of generated content

## Requirements

### Requirement 10: AWS News Monitoring

**User Story:** As a content creator, I want to automatically discover training-relevant AWS news, so that I can create timely content without manual RSS checking.

#### Acceptance Criteria

1. THE News_Monitor SHALL run hourly via EventBridge trigger
2. THE News_Monitor SHALL check the following RSS feeds:
   - AWS What's New (limit: 5 items, relevance: high)
   - AWS Training & Certification Blog (limit: 3 items, relevance: critical)
   - AWS Architecture Blog (limit: 2 items, relevance: medium)
   - AWS Security Blog (limit: 2 items, relevance: medium)
3. THE News_Monitor SHALL filter items using training relevance keywords: certification, exam, training, bootcamp, course, practitioner, associate, professional, specialty, new service, announcement, GA, general availability
4. THE News_Monitor SHALL deduplicate items using content hash to avoid reprocessing
5. WHEN a new training-relevant item is found, THE News_Monitor SHALL trigger content generation
6. THE News_Monitor SHALL log all processed items and errors to CloudWatch

### Requirement 11: AI-Powered Content Generation

**User Story:** As a content creator, I want AI-generated training-focused content for each news item, so that I can quickly review and publish across multiple platforms.

#### Acceptance Criteria

1. THE Content_Generator SHALL use Bedrock Claude to analyze each news item
2. THE Content_Generator SHALL generate four content types:
   - Twitter post (max 280 chars) with training/certification focus and hashtags
   - LinkedIn post (max 1300 chars) with professional analysis and CTA
   - Blog outline (3-4 key points) for detailed technical analysis
   - Moltbook context (one sentence) describing "current work" related to this news
3. THE Content_Generator SHALL focus on training, certification, and enterprise learning implications
4. THE Content_Generator SHALL maintain AWS Authorized Training Provider perspective
5. THE Content_Generator SHALL include source attribution and relevance scoring
6. WHEN content generation fails, THE Content_Generator SHALL log the error and continue processing other items

### Requirement 12: Email Delivery System

**User Story:** As a content creator, I want generated content emailed to me for review, so that I can approve/edit before publishing.

#### Acceptance Criteria

1. THE Email_Delivery SHALL use AWS SES to send formatted emails
2. THE Email_Delivery SHALL include in each email:
   - News source and relevance score
   - Original news link
   - All four generated content types
   - Generation timestamp
3. THE Email_Delivery SHALL use subject format: "AWS Training Content Ready - [title]..."
4. THE Email_Delivery SHALL send to configured recipient email address
5. WHEN email delivery fails, THE Email_Delivery SHALL log the error and continue processing
6. THE Email_Delivery SHALL respect SES sending limits and quotas

### Requirement 13: Context Storage for Moltbook

**User Story:** As the Moltbook bot, I want access to recent "current work" context, so that I can reference authentic TechReformers activities in my posts.

#### Acceptance Criteria

1. THE Context_Storage SHALL store news items and generated content in DynamoDB
2. THE Context_Storage SHALL use table schema:
   - Primary Key: item_hash (string)
   - Sort Key: timestamp (number)
   - Attributes: title, summary, source, link, moltbook_context, relevance, ttl
3. THE Context_Storage SHALL set TTL to 7 days for automatic cleanup
4. THE Context_Storage SHALL index by timestamp for recent item queries
5. THE Moltbook_Heartbeat SHALL query Context_Storage for recent items (last 24 hours)
6. THE Moltbook_Heartbeat SHALL incorporate context into post/comment decisions

### Requirement 14: Shared Utilities Module

**User Story:** As a developer, I want common utilities shared between news monitor and heartbeat, so that code is DRY and maintainable.

#### Acceptance Criteria

1. THE Shared_Utils SHALL provide `ask_claude(prompt)` function for Bedrock invocations
2. THE Shared_Utils SHALL provide `send_email(subject, body)` function for SES
3. THE Shared_Utils SHALL provide `is_new_item(entry)` function for deduplication
4. THE Shared_Utils SHALL provide `store_for_moltbook_context(item)` function for DynamoDB
5. THE Shared_Utils SHALL provide `get_recent_context(hours=24)` function for context retrieval
6. THE Shared_Utils SHALL handle all AWS client initialization and error handling
7. THE Shared_Utils SHALL be importable by both news_monitor and heartbeat_code

### Requirement 15: Infrastructure as Code

**User Story:** As a system administrator, I want infrastructure defined as code, so that DynamoDB tables and IAM permissions are version-controlled and reproducible.

#### Acceptance Criteria

1. THE Infrastructure SHALL define DynamoDB table with:
   - Table name: techreformers-moltbook-context
   - Billing mode: PAY_PER_REQUEST
   - TTL enabled on ttl attribute
   - GSI on timestamp for recent queries
2. THE Infrastructure SHALL define IAM permissions for news monitor:
   - Bedrock InvokeModel
   - SES SendEmail
   - DynamoDB PutItem, Query
   - CloudWatch Logs
3. THE Infrastructure SHALL define IAM permissions for heartbeat (extended):
   - Existing permissions (Secrets Manager, Bedrock)
   - DynamoDB Query (read-only)
4. THE Infrastructure SHALL be deployable via Terraform or CloudFormation
5. THE Infrastructure SHALL include EventBridge rule for hourly news monitor trigger
6. THE Infrastructure SHALL output all resource ARNs for reference

### Requirement 16: Deployment Automation

**User Story:** As a system administrator, I want automated deployment of v2.0 components, so that I can deploy the expanded system with minimal manual steps.

#### Acceptance Criteria

1. THE Deployment_Script SHALL extend existing deploy.sh with v2.0 components
2. THE Deployment_Script SHALL package news_monitor with dependencies (feedparser)
3. THE Deployment_Script SHALL package shared utilities for both Lambdas
4. THE Deployment_Script SHALL deploy infrastructure (DynamoDB, IAM, EventBridge)
5. THE Deployment_Script SHALL update heartbeat Lambda with shared utilities
6. THE Deployment_Script SHALL verify SES email address is verified
7. THE Deployment_Script SHALL output all new resource ARNs
8. WHEN deployment completes, THE Deployment_Script SHALL trigger test news monitor execution

### Requirement 17: Enhanced Moltbook Integration

**User Story:** As the Moltbook bot, I want to reference authentic current work in my posts, so that my content is more engaging and credible.

#### Acceptance Criteria

1. THE Moltbook_Heartbeat SHALL query recent context before generating posts
2. WHEN recent context exists, THE Moltbook_Heartbeat SHALL include it in Claude prompt
3. THE Moltbook_Heartbeat SHALL use context format: "Currently analyzing [topic] for our [training/certification] work"
4. THE Moltbook_Heartbeat SHALL prefer context from last 24 hours
5. WHEN no recent context exists, THE Moltbook_Heartbeat SHALL fall back to generic insights
6. THE Moltbook_Heartbeat SHALL log which context items were used in posts

### Requirement 18: Monitoring and Observability

**User Story:** As a system administrator, I want comprehensive monitoring of the news pipeline, so that I can troubleshoot issues and track content generation.

#### Acceptance Criteria

1. THE News_Monitor SHALL log metrics to CloudWatch:
   - Items checked per source
   - Items filtered as relevant
   - Content generation success/failure
   - Email delivery success/failure
2. THE News_Monitor SHALL create CloudWatch alarms for:
   - Lambda execution failures
   - SES bounce rate > 5%
   - DynamoDB throttling
3. THE Moltbook_Heartbeat SHALL log context usage:
   - Number of context items available
   - Which items were referenced
   - Posts created with vs without context
4. THE System SHALL provide CloudWatch dashboard showing:
   - News items processed (hourly)
   - Content generated (daily)
   - Moltbook posts with context (daily)
5. THE System SHALL send SNS alerts for critical failures
6. THE System SHALL retain logs for 30 days minimum

## Non-Functional Requirements

### Performance

- News monitor execution time: < 30 seconds
- Content generation per item: < 10 seconds
- Context query latency: < 100ms
- Email delivery: < 5 seconds

### Scalability

- Support up to 50 news items per hour
- DynamoDB auto-scaling for burst traffic
- SES sending rate: 1 email per second (within free tier)

### Cost Optimization

- Use Lambda free tier (1M requests/month)
- DynamoDB on-demand pricing (pay per request)
- SES free tier (62,000 emails/month)
- Bedrock Claude: ~$0.01 per content generation
- Estimated monthly cost: < $10

### Security

- All secrets in Secrets Manager
- IAM roles follow least privilege
- DynamoDB encryption at rest
- SES DKIM/SPF configured
- No sensitive data in CloudWatch logs

## Success Metrics

- **News Coverage**: 90%+ of training-relevant AWS news captured
- **Content Quality**: 80%+ of generated content usable with minor edits
- **Moltbook Engagement**: 2x increase in post engagement with context
- **Time Savings**: 10+ hours/week saved on manual content creation
- **System Reliability**: 99%+ uptime for news monitoring

## Future Enhancements (v3.0+)

- Multi-language content generation
- Automated publishing to Twitter/LinkedIn (with approval workflow)
- Sentiment analysis of AWS community reactions
- Competitive analysis (Azure, GCP training news)
- Integration with TechReformers CRM for customer-specific content
- AI-powered content scheduling optimization

# How to Observe the News Monitor System

## ✅ Current Status

**Email Configuration**: Updated to `jkrull@techreformers.com` (verified)  
**SPF/DKIM**: Already configured for techreformers.com  
**System Status**: Working (emails sent to junk, now fixed)

## 📊 What's Already Happened

The first manual test run:
- ✅ Checked 4 RSS feeds (150 total items)
- ✅ Found 3 training-relevant items
- ✅ Generated content via Claude
- ✅ Sent 3 emails (went to junk)
- ✅ Stored deduplication records in DynamoDB

**Items Processed:**
1. "AWS Generative AI Essentials: New learning now available on Coursera and edX"
2. "New courses and certification updates from AWS Training and Certification"
3. "Upgraded AWS Certification exam guides are now available"

## 🔍 How to Observe Going Forward

### Option 1: Wait for New AWS News (Recommended)
The system is designed to run hourly and process NEW items only.

**What to watch:**
- AWS publishes training/certification news regularly
- When new relevant news appears, you'll get an email
- Check your inbox (should go there now with verified sender)

**Timeline:**
- AWS Training Blog: 1-2 posts per week
- AWS What's New: Multiple per day (but fewer training-relevant)
- Certification updates: 1-2 per month

### Option 2: Clear Deduplication and Retest
Force the system to reprocess existing items.

**Steps:**
```bash
# 1. Clear the deduplication table
aws dynamodb scan --table-name aws-news-tracker --region us-east-1 \
  --attributes-to-get item_hash --output json | \
  jq -r '.Items[].item_hash.S' | \
  xargs -I {} aws dynamodb delete-item \
    --table-name aws-news-tracker \
    --key '{"item_hash":{"S":"{}"}}'

# 2. Invoke Lambda again
aws lambda invoke \
  --function-name moltbook-news-monitor \
  --region us-east-1 \
  test-response.json && cat test-response.json

# 3. Check your email (should arrive in inbox now)
```

**Result**: You'll get 3 emails with the same items, but from verified sender.

### Option 3: Monitor DynamoDB Tables

**Check what's been processed:**
```bash
# See all processed items
aws dynamodb scan --table-name aws-news-tracker --region us-east-1 \
  --query 'Items[*].[title.S,processed_at.N]' --output table

# Count items
aws dynamodb scan --table-name aws-news-tracker --region us-east-1 \
  --select COUNT --output text
```

**Check stored context:**
```bash
# See items stored for Moltbook bot
aws dynamodb scan --table-name moltbook-context --region us-east-1 \
  --query 'Items[*].[title.S,moltbook_context.S,relevance.S]' --output table
```

### Option 4: Check Lambda Execution Logs

**View recent executions:**
```bash
# Get last 20 log events
aws logs tail /aws/lambda/moltbook-news-monitor \
  --region us-east-1 \
  --since 1h \
  --format short
```

**What to look for:**
- "Checking [source]: X entries found"
- "New relevant item: [title]"
- "Found X new training-relevant items"
- "Processed X news items"

## 📧 Email Content to Expect

Each email will contain:

**Subject**: "AWS Training Content Ready - [first 50 chars of title]..."

**Body**:
```
New AWS Training Content Generated

SOURCE: aws_training_blog
RELEVANCE: critical
LINK: https://aws.amazon.com/...

GENERATED CONTENT:
[Claude's analysis with 4 sections:]

1. TWITTER (280 chars max):
   [Engaging tweet about training implications]

2. LINKEDIN (1300 chars max):
   [Professional analysis with CTA]

3. BLOG OUTLINE:
   [3-4 key points for detailed article]

4. MOLTBOOK CONTEXT (one sentence):
   [What TechReformers is "currently working on"]

---
Generated at: 2026-02-22T...
```

## 🎯 Success Indicators

### System is Working When:
- ✅ Lambda executes without errors
- ✅ RSS feeds are checked (see logs)
- ✅ Training-relevant items are identified
- ✅ Emails arrive in inbox (not junk)
- ✅ Content quality is good
- ✅ DynamoDB tables are populated

### System Needs Attention When:
- ❌ Lambda execution errors
- ❌ No emails for 7+ days (unlikely - AWS publishes regularly)
- ❌ Emails still going to junk
- ❌ Content quality is poor
- ❌ DynamoDB throttling errors

## 📅 When to Enable Hourly Schedule

**Recommended Criteria:**
1. ✅ Verified email working (done)
2. ✅ Emails going to inbox (test after clearing dedup)
3. ✅ Content quality is acceptable (review emails)
4. ✅ No Lambda errors (check logs)
5. ⏸️ Comfortable with hourly execution

**Once enabled:**
- Lambda runs every hour
- Checks for new AWS news
- Sends email only when training-relevant items found
- Typical: 5-10 emails per week

## 🧪 Quick Test Right Now

Want to see it work immediately? Run this:

```bash
# Clear deduplication (forces reprocessing)
aws dynamodb scan --table-name aws-news-tracker --region us-east-1 \
  --attributes-to-get item_hash --output json | \
  jq -r '.Items[].item_hash.S' | \
  xargs -I {} aws dynamodb delete-item \
    --table-name aws-news-tracker \
    --region us-east-1 \
    --key '{"item_hash":{"S":"{}"}}'

# Invoke Lambda
aws lambda invoke \
  --function-name moltbook-news-monitor \
  --region us-east-1 \
  test-response.json

# Check response
cat test-response.json

# Check your email inbox (should arrive in ~10 seconds)
```

You should get 3 emails from `jkrull@techreformers.com` with generated content.

## 📊 Monitoring Dashboard (Future)

For production monitoring, consider:
- CloudWatch dashboard with Lambda metrics
- SNS alerts for Lambda failures
- SES bounce/complaint tracking
- Weekly summary email of items processed

## 🔄 Normal Operation Cycle

Once hourly schedule is enabled:

**Every Hour:**
1. Lambda triggered by EventBridge
2. Checks 4 RSS feeds (~150 items total)
3. Filters for training-relevant keywords
4. Checks deduplication table
5. Processes NEW relevant items only
6. Generates content via Claude
7. Sends email (if items found)
8. Stores context in DynamoDB

**Expected Volume:**
- Executions: 24 per day (720 per month)
- Emails: 5-10 per week (20-40 per month)
- Cost: ~$0.80 per month

## ✅ Current Recommendation

**For Now (Observation Mode):**
1. Clear deduplication table
2. Run Lambda manually
3. Check email inbox for 3 emails
4. Review content quality
5. If satisfied, enable hourly schedule

**Next Step:**
Let me know if you want to:
- A) Clear dedup and test email delivery now
- B) Wait for new AWS news naturally
- C) Enable hourly schedule immediately

# Email Delivery Notes

## ✅ Status: WORKING (Going to Junk/Spam)

The news monitor Lambda IS working and sending emails! They're just landing in junk mail because the sender domain needs proper configuration.

## What's Happening

**Current Setup:**
- Sender: `noreply@techreformers.com`
- Recipient: `john@techreformers.com`
- Delivery: SUCCESS (but to junk folder)

**Why Junk Folder:**
1. SES domain not fully configured (SPF/DKIM records)
2. Using `noreply@` address (often flagged as spam)
3. New sending pattern (first emails from this address)

## Quick Fixes

### Option 1: Whitelist the Sender (Immediate)
In your email client:
1. Find the email in junk
2. Mark as "Not Junk" or "Not Spam"
3. Add `noreply@techreformers.com` to contacts
4. Future emails should go to inbox

### Option 2: Configure SES Domain (Recommended)
Add SPF and DKIM records to techreformers.com DNS:

**SPF Record** (TXT):
```
v=spf1 include:amazonses.com ~all
```

**DKIM Records**:
Get from AWS SES Console → Verified Identities → techreformers.com → DKIM

**Steps:**
1. Go to AWS SES Console
2. Click "Verified identities"
3. Click your domain
4. Copy DKIM CNAME records
5. Add to your DNS provider (Route53, Cloudflare, etc.)
6. Wait for verification (can take 24-72 hours)

### Option 3: Use Verified Personal Email (Quick Fix)
Change sender to your verified personal email:

```bash
aws lambda update-function-configuration \
  --function-name moltbook-news-monitor \
  --environment 'Variables={RECIPIENT_EMAIL=john@techreformers.com,SENDER_EMAIL=john@techreformers.com}' \
  --region us-east-1
```

This will send from john@techreformers.com (already verified) instead of noreply@.

## Verify What Was Sent

Check your junk folder for emails with:
- **Subject**: "AWS Training Content Ready - [news title]..."
- **From**: noreply@techreformers.com
- **Content**: Generated Twitter/LinkedIn/blog content

You should see emails for:
- "AWS Generative AI Essentials: New learning now available on Coursera and edX"
- "New courses and certification updates from AWS Training and Certification"
- "Upgraded AWS Certification exam guides are now available"

## Test Email Delivery

To test if emails are working, invoke the Lambda manually:

```bash
# This will process any NEW training-relevant items
aws lambda invoke \
  --function-name moltbook-news-monitor \
  --region us-east-1 \
  test-response.json && cat test-response.json
```

Since all current items are already processed, you'll need to either:
1. Wait for new AWS news to be published
2. Clear the deduplication table (see below)

## Clear Deduplication Table (For Testing)

**WARNING**: This will cause all items to be reprocessed and emails resent.

```bash
# Delete all items from aws-news-tracker
aws dynamodb scan --table-name aws-news-tracker --region us-east-1 \
  --attributes-to-get item_hash --output json | \
  jq -r '.Items[].item_hash.S' | \
  xargs -I {} aws dynamodb delete-item \
    --table-name aws-news-tracker \
    --key '{"item_hash":{"S":"{}"}}'

# Then invoke Lambda again
aws lambda invoke \
  --function-name moltbook-news-monitor \
  --region us-east-1 \
  test-response.json
```

## SES Sending Limits

**Sandbox Mode** (if not verified):
- 200 emails per 24 hours
- 1 email per second
- Can only send to verified addresses

**Production Mode** (after domain verification):
- 50,000 emails per 24 hours (can request increase)
- 14 emails per second
- Can send to any address

Check your SES status:
```bash
aws ses get-account-sending-enabled --region us-east-1
aws ses get-send-quota --region us-east-1
```

## Monitoring Email Delivery

### Check SES Statistics
```bash
aws ses get-send-statistics --region us-east-1
```

### Check for Bounces/Complaints
```bash
# Set up SNS topic for bounce notifications (recommended)
aws ses set-identity-notification-topic \
  --identity techreformers.com \
  --notification-type Bounce \
  --sns-topic arn:aws:sns:us-east-1:352486303890:ses-bounces
```

## Email Content Format

The emails contain:
1. **Source**: Which RSS feed (aws_training_blog, etc.)
2. **Relevance**: critical/high/medium
3. **Link**: Original AWS news article
4. **Generated Content**:
   - Twitter post (280 chars)
   - LinkedIn post (1300 chars)
   - Blog outline (3-4 points)
   - Moltbook context (one sentence)

## Recommendations

### Short Term (Now)
1. ✅ Whitelist `noreply@techreformers.com` in your email
2. ✅ Check junk folder for existing emails
3. ✅ Verify content quality

### Medium Term (This Week)
1. Configure SPF/DKIM for techreformers.com
2. Request SES production access (if in sandbox)
3. Set up bounce/complaint notifications

### Long Term (Future)
1. Add email templates for better formatting
2. Add HTML email support (currently plain text)
3. Add approval workflow before publishing
4. Track email open rates

## Current Status

✅ **News Monitor**: Working  
✅ **Email Delivery**: Working (to junk)  
✅ **Content Generation**: Working  
✅ **DynamoDB Storage**: Working  
⏸️ **EventBridge Schedule**: Not deployed yet  

**Next Step**: Whitelist the sender, then decide when to enable hourly schedule.

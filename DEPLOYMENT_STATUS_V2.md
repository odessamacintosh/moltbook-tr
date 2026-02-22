# v2.0 Deployment Status

**Last Updated**: February 22, 2026

## ✅ Phase 1: DynamoDB Tables - COMPLETE

### Tables Deployed
- ✅ `aws-news-tracker` - Deduplication table
  - Status: ACTIVE
  - Billing: PAY_PER_REQUEST
  - Primary Key: item_hash (String)
  
- ✅ `moltbook-context` - Context storage table
  - Status: ACTIVE
  - Billing: PAY_PER_REQUEST
  - Primary Key: context_id (String)
  - TTL: ENABLED on `ttl` attribute (7-day auto-cleanup)

### Tests Passed
- ✅ Deduplication working (aws-news-tracker)
- ✅ Context storage working (moltbook-context)
- ✅ Context retrieval working (with reserved keyword fix)

### Issues Fixed
- ✅ Reserved keyword "timestamp" - now using ExpressionAttributeNames
- ✅ Test script updated to use unique items per run

## 📋 Next Steps

### Phase 2: IAM Permissions
- [ ] Update news_monitor Lambda role with DynamoDB permissions
- [ ] Update heartbeat Lambda role with DynamoDB read permissions
- [ ] Verify SES email address for sending

### Phase 3: Lambda Deployment
- [ ] Fix import in news_monitor/monitor.py
- [ ] Add moltbook_context extraction from Claude response
- [ ] Package and deploy news_monitor Lambda
- [ ] Update heartbeat Lambda with context queries

### Phase 4: EventBridge & Testing
- [ ] Create hourly EventBridge trigger
- [ ] Test news monitor manually
- [ ] Verify email delivery
- [ ] Test heartbeat with context
- [ ] Monitor for 24 hours

## Resources Created

### DynamoDB Tables
```
arn:aws:dynamodb:us-east-1:352486303890:table/aws-news-tracker
arn:aws:dynamodb:us-east-1:352486303890:table/moltbook-context
```

### Test Data
- 2 items in aws-news-tracker (test entries)
- 3 items in moltbook-context (test entries)

## Commands for Reference

### Check Table Status
```bash
aws dynamodb describe-table --table-name moltbook-context --region us-east-1
aws dynamodb describe-table --table-name aws-news-tracker --region us-east-1
```

### View Table Data
```bash
aws dynamodb scan --table-name moltbook-context --region us-east-1 --max-items 5
aws dynamodb scan --table-name aws-news-tracker --region us-east-1 --max-items 5
```

### Test Shared Utilities
```bash
python3 test_dynamodb_access.py
```

### Clean Up Test Data (if needed)
```bash
# Delete all items from moltbook-context
aws dynamodb scan --table-name moltbook-context --region us-east-1 \
  --attributes-to-get context_id --output json | \
  jq -r '.Items[].context_id.S' | \
  xargs -I {} aws dynamodb delete-item \
    --table-name moltbook-context \
    --key '{"context_id":{"S":"{}"}}'
```

## Cost Tracking

### Current Costs (Phase 1)
- DynamoDB: ~$0.00 (free tier, minimal usage)
- Total: ~$0.00/month

### Projected Costs (Full v2.0)
- DynamoDB: ~$0.05/month
- Lambda: ~$0.25/month
- Bedrock: ~$0.50/month
- SES: Free tier
- Total: ~$0.80/month

## Notes

- Tables are in us-east-1 (same region as v1.0)
- Using PAY_PER_REQUEST billing (no capacity planning needed)
- TTL enabled for automatic cleanup after 7 days
- Test data will expire automatically
- Shared utilities tested and working
- Ready for Lambda deployment phase

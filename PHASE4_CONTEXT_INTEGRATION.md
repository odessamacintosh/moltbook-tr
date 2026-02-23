# Phase 4: Heartbeat Context Integration

## Overview

This phase connects the AWS news analysis pipeline to the Moltbook heartbeat, enabling the bot to reference its current work naturally in posts and comments.

## What Changed

### Heartbeat Code Updates (`heartbeat_code/heartbeat.py`)

1. **Added context import**:
   ```python
   from shared.utils import get_recent_context
   ```

2. **New function: `get_work_context()`**:
   - Checks `USE_CONTEXT` environment variable (default: false)
   - Queries DynamoDB for recent news analysis work (48 hours)
   - Formats top 3 items for Claude's context
   - Graceful error handling - continues without context if fails

3. **Updated `ask_claude()` function**:
   - Now accepts optional `system_prompt` parameter
   - Allows dynamic system prompts with context

4. **Enhanced system prompt**:
   - Includes current work context when available
   - Prioritizes original posts over comments
   - Instructs bot to reference analysis work naturally

### IAM Permissions

Added DynamoDB read access to `moltbook-lambda-role`:
- `dynamodb:Scan` on `moltbook-context` table
- `dynamodb:Query` on `moltbook-context` table

### Environment Variables

- `USE_CONTEXT`: Feature flag (default: `false`)
- `BEDROCK_AGENT_ID`: Existing (86JBOATEON)
- `BEDROCK_AGENT_ALIAS_ID`: Existing (MFFMRB21UA)

## Safety Features

### Feature Flag
- Context integration is OFF by default
- Bot works exactly as before until flag is enabled
- Can be toggled instantly without code changes

### Graceful Degradation
- If DynamoDB query fails, bot continues without context
- No errors, no crashes - just logs warning and proceeds
- Ensures heartbeat reliability

### Easy Rollback
Three rollback options:
1. Set `USE_CONTEXT=false` (instant)
2. Redeploy v1.0 code
3. Delete environment variable

## Deployment Steps

### Automated Deployment

Run the deployment script:
```bash
./deploy-heartbeat-v2.sh
```

This will:
1. Add DynamoDB permissions to IAM role
2. Deploy updated Lambda code
3. Set environment variables (flag OFF)
4. Test with flag OFF
5. Display instructions for enabling context

### Manual Deployment

If you prefer manual steps:

1. **Add IAM permissions**:
```bash
aws iam put-role-policy \
  --role-name moltbook-lambda-role \
  --policy-name HeartbeatDynamoDBAccess \
  --policy-document file://infrastructure/heartbeat-dynamodb-policy.json \
  --profile jkdemo \
  --region us-east-1
```

2. **Deploy Lambda code**:
```bash
aws lambda update-function-code \
  --function-name moltbook-heartbeat \
  --zip-file fileb://heartbeat-v2.zip \
  --profile jkdemo \
  --region us-east-1
```

3. **Set environment variables (flag OFF)**:
```bash
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=false}" \
  --profile jkdemo \
  --region us-east-1
```

4. **Test with flag OFF**:
```bash
aws lambda invoke \
  --function-name moltbook-heartbeat \
  --profile jkdemo \
  --region us-east-1 \
  --log-type Tail \
  test-response-flag-off.json
```

## Testing

### Test 1: Flag OFF (Default Behavior)
```bash
aws lambda invoke \
  --function-name moltbook-heartbeat \
  --profile jkdemo \
  --region us-east-1 \
  --log-type Tail \
  test-response-flag-off.json
```

**Expected**: Bot posts/comments normally without referencing context

### Test 2: Enable Context
```bash
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=true}" \
  --profile jkdemo \
  --region us-east-1
```

### Test 3: Flag ON (With Context)
```bash
aws lambda invoke \
  --function-name moltbook-heartbeat \
  --profile jkdemo \
  --region us-east-1 \
  --log-type Tail \
  test-response-context-on.json
```

**Expected**: Bot references current AWS analysis work in posts/comments

### Test 4: Check Logs
```bash
aws logs tail /aws/lambda/moltbook-heartbeat --follow --profile jkdemo --region us-east-1
```

Look for:
- "Error getting work context" (if DynamoDB fails - should continue)
- Context items in decision prompt
- Successful post/comment creation

## Monitoring

### Check Moltbook Profile
https://www.moltbook.com/u/techreformers

Look for:
- Posts mentioning "analyzing", "reviewing", "working on"
- References to specific AWS services from news analysis
- More authentic, contextual content

### CloudWatch Metrics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=moltbook-heartbeat \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --profile jkdemo \
  --region us-east-1
```

### DynamoDB Context Check
```bash
aws dynamodb scan \
  --table-name moltbook-context \
  --profile jkdemo \
  --region us-east-1 \
  --max-items 5
```

## Rollback Procedures

### Option 1: Disable Feature Flag (Instant)
```bash
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=false}" \
  --profile jkdemo \
  --region us-east-1
```

### Option 2: Redeploy v1.0 Code
```bash
# Use the old heartbeat-fixed-v2.zip (without shared utils)
aws lambda update-function-code \
  --function-name moltbook-heartbeat \
  --zip-file fileb://heartbeat-fixed-v2.zip \
  --profile jkdemo \
  --region us-east-1
```

### Option 3: Remove Environment Variable
```bash
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA}" \
  --profile jkdemo \
  --region us-east-1
```

## Expected Behavior

### Before (Flag OFF)
```
POST: AWS Lambda Cold Starts | Let's talk about Lambda cold starts. 
They're often blamed for performance issues, but are they really the 
problem? In my experience...
```

### After (Flag ON)
```
POST: Oracle RDS Patches and Database Specialty Prep | I'm currently 
analyzing the latest Oracle RDS security patches for our Database 
Specialty training content. Interesting how AWS is handling the 
CVE-2024-21287 vulnerability...
```

## Success Criteria

- [ ] Deployment completes without errors
- [ ] Test with flag OFF succeeds (bot works as before)
- [ ] IAM permissions added successfully
- [ ] Flag can be toggled ON
- [ ] Test with flag ON succeeds
- [ ] Bot references context in posts/comments
- [ ] No increase in Lambda errors
- [ ] Heartbeat continues every 30 minutes
- [ ] Moltbook profile shows contextual posts

## Timeline

1. **Deploy** (5 minutes)
2. **Test flag OFF** (2 minutes)
3. **Monitor for 1 hour** (verify no issues)
4. **Enable flag** (1 minute)
5. **Test flag ON** (2 minutes)
6. **Monitor for 24 hours** (verify context integration)

## Files Created/Modified

### Created
- `infrastructure/heartbeat-dynamodb-policy.json` - IAM policy
- `deploy-heartbeat-v2.sh` - Deployment script
- `heartbeat-v2.zip` - Updated Lambda package
- `PHASE4_CONTEXT_INTEGRATION.md` - This document

### Modified
- `heartbeat_code/heartbeat.py` - Added context integration

## Next Steps

After successful deployment and testing:

1. Monitor for 24 hours with flag ON
2. Verify context appears in posts/comments
3. Check DynamoDB query costs (should be minimal)
4. Adjust context window if needed (currently 48 hours)
5. Consider adding more context formatting options

## Questions?

- **Q: What if DynamoDB is down?**
  - A: Bot continues without context, logs error, no crash

- **Q: How much does this cost?**
  - A: ~$0.01/month for DynamoDB reads (minimal)

- **Q: Can I change the context window?**
  - A: Yes, edit `hours=48` in `get_work_context()`

- **Q: What if context is too long?**
  - A: Currently limited to top 3 items, can adjust

- **Q: How do I know if context is being used?**
  - A: Check CloudWatch logs for context items in prompts

---

**Status**: Ready to deploy
**Risk**: Low (feature flag OFF by default)
**Rollback**: Instant (toggle flag)

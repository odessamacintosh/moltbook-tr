# Safe v2.0 Deployment Plan - Protecting Production Heartbeat

## Critical Principle: Don't Break What's Working

The v1.0 Moltbook heartbeat is **PRODUCTION** and posting every 30 minutes. We must:
- ✅ Keep v1.0 heartbeat running unchanged
- ✅ Deploy v2.0 components independently
- ✅ Test v2.0 thoroughly before integration
- ✅ Make heartbeat enhancement optional and reversible

## Deployment Strategy: Parallel Track

### Track 1: v2.0 News Monitor (Independent)
Deploy news monitor completely separately from heartbeat:
- New Lambda function: `moltbook-news-monitor`
- New IAM role: `moltbook-news-monitor-role`
- New EventBridge rule: `moltbook-news-monitor-hourly`
- Zero impact on existing heartbeat

### Track 2: Heartbeat Enhancement (Optional)
Only after news monitor is proven stable:
- Create new heartbeat version with context queries
- Test in isolation
- Deploy with feature flag
- Easy rollback if issues

## Phase-by-Phase Safety Plan

### ✅ Phase 1: DynamoDB (COMPLETE)
**Status**: Done, no impact on heartbeat
- Tables deployed independently
- Heartbeat doesn't know they exist
- Safe ✅

### Phase 2: News Monitor Lambda (SAFE - No Heartbeat Changes)

**Goal**: Get news monitoring working independently

**Steps**:
1. Create new Lambda function: `moltbook-news-monitor`
2. Create new IAM role with permissions:
   - Bedrock InvokeModel
   - SES SendEmail
   - DynamoDB PutItem, GetItem, Scan (both tables)
   - CloudWatch Logs
3. Package and deploy news_monitor code
4. Test manually (no EventBridge yet)
5. Verify emails received
6. Verify DynamoDB writes

**Heartbeat Impact**: NONE - completely separate Lambda

**Rollback**: Delete news monitor Lambda (heartbeat unaffected)

### Phase 3: EventBridge Hourly Trigger (SAFE)

**Goal**: Automate news monitoring

**Steps**:
1. Create new EventBridge rule: `moltbook-news-monitor-hourly`
2. Target: `moltbook-news-monitor` Lambda (NOT heartbeat)
3. Schedule: `rate(1 hour)`
4. Monitor for 24 hours

**Heartbeat Impact**: NONE - different EventBridge rule

**Rollback**: Disable EventBridge rule (heartbeat unaffected)

### Phase 4: Heartbeat Enhancement (CAREFUL - Optional)

**Goal**: Add context awareness to heartbeat

**Safety Measures**:
1. Create `heartbeat_v2.py` (don't modify existing)
2. Add feature flag: `USE_CONTEXT=false` (default off)
3. Test locally with mocked DynamoDB
4. Deploy as new version
5. Enable feature flag only after testing
6. Monitor closely for 24 hours

**Heartbeat Changes**:
```python
# In heartbeat_v2.py
import os
USE_CONTEXT = os.environ.get('USE_CONTEXT', 'false').lower() == 'true'

if USE_CONTEXT:
    try:
        from shared.utils import get_recent_context
        context_items = get_recent_context(hours=24)
        # Use context in prompt
    except Exception as e:
        print(f"Context retrieval failed, continuing without: {e}")
        context_items = []
else:
    context_items = []

# Rest of heartbeat logic unchanged
```

**Rollback Plan**:
- Option 1: Set `USE_CONTEXT=false` (instant)
- Option 2: Redeploy v1.0 heartbeat code
- Option 3: Update Lambda to point to v1.0 code

## Risk Mitigation

### Risk 1: News Monitor Breaks
**Impact**: No emails, no context stored
**Heartbeat Impact**: NONE (heartbeat doesn't depend on it yet)
**Mitigation**: Fix news monitor, heartbeat continues working

### Risk 2: DynamoDB Unavailable
**Impact**: News monitor fails, no context stored
**Heartbeat Impact**: NONE (heartbeat doesn't query DynamoDB yet)
**Mitigation**: Fix DynamoDB access, heartbeat continues working

### Risk 3: Heartbeat Enhancement Breaks
**Impact**: Heartbeat stops posting
**Heartbeat Impact**: CRITICAL
**Mitigation**: 
- Feature flag off by default
- Graceful error handling (continue without context)
- Immediate rollback capability
- Test thoroughly before enabling

### Risk 4: Shared Utils Import Breaks Heartbeat
**Impact**: Heartbeat import fails
**Heartbeat Impact**: CRITICAL
**Mitigation**: 
- Don't add shared utils to heartbeat until Phase 4
- Test imports in isolation first
- Keep v1.0 heartbeat code as backup

## Testing Checklist

### Before Touching Heartbeat
- [ ] News monitor deployed and working
- [ ] Emails being received successfully
- [ ] DynamoDB writes confirmed
- [ ] EventBridge trigger working hourly
- [ ] No errors in CloudWatch logs for 24 hours
- [ ] At least 5 successful news processing cycles

### Before Enabling Context in Heartbeat
- [ ] heartbeat_v2.py tested locally
- [ ] Feature flag tested (on/off)
- [ ] Error handling tested (DynamoDB unavailable)
- [ ] Import tested (shared.utils available)
- [ ] Deployed to Lambda but flag OFF
- [ ] Manual test with flag ON
- [ ] Rollback tested

## Deployment Commands

### Phase 2: Deploy News Monitor (Safe)

```bash
# Create IAM role
aws iam create-role \
  --role-name moltbook-news-monitor-role \
  --assume-role-policy-document file://news_monitor_trust_policy.json

# Attach policies (create separate from heartbeat)
aws iam put-role-policy \
  --role-name moltbook-news-monitor-role \
  --policy-name NewsMonitorPermissions \
  --policy-document file://news_monitor_policy.json

# Package Lambda
cd news_monitor
pip install -r requirements.txt -t .
cd ..
zip -r news_monitor.zip news_monitor/ shared/

# Create Lambda (NEW function, not updating heartbeat)
aws lambda create-function \
  --function-name moltbook-news-monitor \
  --runtime python3.11 \
  --role arn:aws:iam::352486303890:role/moltbook-news-monitor-role \
  --handler news_monitor.monitor.lambda_handler \
  --zip-file fileb://news_monitor.zip \
  --timeout 60 \
  --memory-size 256 \
  --region us-east-1

# Test manually (no EventBridge yet)
aws lambda invoke \
  --function-name moltbook-news-monitor \
  --region us-east-1 \
  output.json
```

### Phase 3: Add EventBridge (Safe)

```bash
# Create NEW rule (not modifying heartbeat rule)
aws events put-rule \
  --name moltbook-news-monitor-hourly \
  --schedule-expression "rate(1 hour)" \
  --state ENABLED \
  --region us-east-1

# Add permission
aws lambda add-permission \
  --function-name moltbook-news-monitor \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:352486303890:rule/moltbook-news-monitor-hourly \
  --region us-east-1

# Add target
aws events put-targets \
  --rule moltbook-news-monitor-hourly \
  --targets "Id=1,Arn=arn:aws:lambda:us-east-1:352486303890:function:moltbook-news-monitor" \
  --region us-east-1
```

### Phase 4: Heartbeat Enhancement (Careful)

```bash
# Create heartbeat_v2.py first
# Test locally
# Deploy with feature flag OFF

# Update heartbeat Lambda code (with v2 code but flag off)
cd heartbeat_code
zip -r ../heartbeat_v2.zip . ../shared/

aws lambda update-function-code \
  --function-name moltbook-heartbeat \
  --zip-file fileb://heartbeat_v2.zip \
  --region us-east-1

# Set environment variable (OFF by default)
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={USE_CONTEXT=false}" \
  --region us-east-1

# Test manually
aws lambda invoke \
  --function-name moltbook-heartbeat \
  --region us-east-1 \
  output.json

# If successful, enable context (ONLY after thorough testing)
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={USE_CONTEXT=true}" \
  --region us-east-1
```

## Rollback Procedures

### Rollback News Monitor
```bash
# Disable EventBridge
aws events disable-rule --name moltbook-news-monitor-hourly --region us-east-1

# Or delete entirely
aws events remove-targets --rule moltbook-news-monitor-hourly --ids 1 --region us-east-1
aws events delete-rule --name moltbook-news-monitor-hourly --region us-east-1
aws lambda delete-function --function-name moltbook-news-monitor --region us-east-1
```

### Rollback Heartbeat Enhancement
```bash
# Option 1: Disable feature flag (instant)
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={USE_CONTEXT=false}" \
  --region us-east-1

# Option 2: Redeploy v1.0 code
cd heartbeat_code
zip -r ../heartbeat_v1.zip heartbeat.py
aws lambda update-function-code \
  --function-name moltbook-heartbeat \
  --zip-file fileb://heartbeat_v1.zip \
  --region us-east-1
```

## Monitoring During Deployment

### Critical Metrics to Watch
- Heartbeat execution success rate (must stay 100%)
- Heartbeat post frequency (must stay every 30 minutes)
- Moltbook profile activity (must continue)
- CloudWatch errors for moltbook-heartbeat (must stay zero)

### Monitoring Commands
```bash
# Watch heartbeat logs (v1.0 - should be unchanged)
aws logs tail /aws/lambda/moltbook-heartbeat --follow --region us-east-1

# Watch news monitor logs (v2.0 - new)
aws logs tail /aws/lambda/moltbook-news-monitor --follow --region us-east-1

# Check heartbeat execution count (should be ~48/day)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=moltbook-heartbeat \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

## Success Criteria

### Phase 2 Success
- [ ] News monitor Lambda deployed
- [ ] Manual test successful
- [ ] Email received with generated content
- [ ] DynamoDB entries created
- [ ] Heartbeat still posting every 30 minutes (unchanged)

### Phase 3 Success
- [ ] EventBridge triggering hourly
- [ ] At least 24 successful executions
- [ ] Emails received hourly
- [ ] No errors in CloudWatch
- [ ] Heartbeat still posting every 30 minutes (unchanged)

### Phase 4 Success
- [ ] Heartbeat v2 deployed with flag OFF
- [ ] Heartbeat still posting every 30 minutes
- [ ] Flag enabled, context queries working
- [ ] Posts include context when available
- [ ] No increase in errors
- [ ] Heartbeat still posting every 30 minutes

## Decision Points

### Go/No-Go for Phase 2
- ✅ DynamoDB tables working
- ✅ Shared utils tested
- ✅ IAM policies prepared
- ✅ Rollback plan documented

**Decision**: PROCEED ✅

### Go/No-Go for Phase 3
- [ ] Phase 2 successful
- [ ] At least 5 manual tests passed
- [ ] Email delivery confirmed
- [ ] No errors in logs

**Decision**: PENDING

### Go/No-Go for Phase 4
- [ ] Phase 3 successful
- [ ] 24+ hours of stable news monitoring
- [ ] heartbeat_v2.py tested locally
- [ ] Feature flag tested
- [ ] Rollback tested

**Decision**: PENDING

## Communication Plan

If heartbeat breaks:
1. Immediate rollback (< 5 minutes)
2. Check Moltbook profile for missed posts
3. Document what went wrong
4. Fix in development
5. Test thoroughly before redeploying

## Summary

**Safe Approach**:
1. Deploy news monitor completely separately ✅
2. Test thoroughly before touching heartbeat ✅
3. Add heartbeat enhancement with feature flag ✅
4. Easy rollback at every step ✅

**Current Status**: Ready for Phase 2 (News Monitor deployment)

**Next Action**: Deploy news monitor Lambda (zero risk to heartbeat)

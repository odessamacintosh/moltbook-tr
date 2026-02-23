# Phase 4 Ready to Deploy

## What's Ready

✅ **Heartbeat code updated** with context integration  
✅ **Feature flag** implemented (OFF by default)  
✅ **IAM policy** created for DynamoDB access  
✅ **Deployment package** built (`heartbeat-v2.zip`)  
✅ **Deployment script** ready (`deploy-heartbeat-v2.sh`)  
✅ **Documentation** complete (`PHASE4_CONTEXT_INTEGRATION.md`)  

## Quick Deploy

Run this single command:

```bash
./deploy-heartbeat-v2.sh
```

This will:
1. Add DynamoDB permissions to IAM role
2. Deploy updated Lambda code
3. Set environment variables (USE_CONTEXT=false)
4. Test with flag OFF
5. Show instructions for enabling context

## Safety

- Feature flag is OFF by default
- Bot works exactly as before until you enable it
- Graceful error handling - continues without context if DynamoDB fails
- Easy rollback - just toggle the flag

## What It Does

When enabled, the bot will:
- Query DynamoDB for recent AWS news analysis work
- Include "Currently analyzing..." context in system prompt
- Reference this work naturally in posts/comments
- Make posts more authentic and engaging

Example:
> "I'm currently analyzing the latest Oracle RDS security patches for our Database Specialty training. Interesting how AWS is handling CVE-2024-21287..."

## Enable Context (After Testing)

```bash
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=true}" \
  --profile jkdemo \
  --region us-east-1
```

## Rollback (If Needed)

```bash
aws lambda update-function-configuration \
  --function-name moltbook-heartbeat \
  --environment "Variables={BEDROCK_AGENT_ID=86JBOATEON,BEDROCK_AGENT_ALIAS_ID=MFFMRB21UA,USE_CONTEXT=false}" \
  --profile jkdemo \
  --region us-east-1
```

---

**Ready when you are!** 🚀

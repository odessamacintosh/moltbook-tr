#!/bin/bash
# Test script for TechReformers Moltbook Agent Lambdas
# Usage:
#   ./test-lambda.sh --heartbeat
#   ./test-lambda.sh --news
#   ./test-lambda.sh --handler
#   ./test-lambda.sh --all

PROFILE="jkdemo"
REGION="us-east-1"
HEARTBEAT_LAMBDA="moltbook-heartbeat"
NEWS_LAMBDA="moltbook-news-monitor"
HANDLER_LAMBDA="moltbook-handler"
TMP_DIR="/tmp/moltbook-test"

mkdir -p "$TMP_DIR"

invoke_lambda() {
    local name="$1"
    local function="$2"
    local out="$TMP_DIR/${name}.json"

    echo ""
    echo "========================================="
    echo "Testing: $function"
    echo "========================================="

    aws lambda invoke \
        --function-name "$function" \
        --region "$REGION" \
        --profile "$PROFILE" \
        --log-type Tail \
        "$out" > "$TMP_DIR/${name}-meta.json" 2>&1

    local status=$?
    if [ $status -ne 0 ]; then
        echo "ERROR: Lambda invocation failed"
        cat "$TMP_DIR/${name}-meta.json"
        return 1
    fi

    echo ""
    echo "--- LOGS ---"
    python3 -c "
import json, base64, sys
with open('$TMP_DIR/${name}-meta.json') as f:
    meta = json.load(f)
log = base64.b64decode(meta.get('LogResult', '')).decode()
print(log)
"

    echo "--- RESPONSE ---"
    cat "$out"
    echo ""
}

run_heartbeat() { invoke_lambda "heartbeat" "$HEARTBEAT_LAMBDA"; }
run_news()      { invoke_lambda "news" "$NEWS_LAMBDA"; }
run_handler()   { invoke_lambda "handler" "$HANDLER_LAMBDA"; }

case "${1:-}" in
    --heartbeat) run_heartbeat ;;
    --news)      run_news ;;
    --handler)   run_handler ;;
    --all)
        run_heartbeat
        run_news
        run_handler
        ;;
    *)
        echo "Usage: $0 [--heartbeat | --news | --handler | --all]"
        echo ""
        echo "  --heartbeat   Test moltbook-heartbeat (posts/comments on Moltbook)"
        echo "  --news        Test moltbook-news-monitor (checks AWS feeds, emails content)"
        echo "  --handler     Test moltbook-handler (Bedrock agent action handler)"
        echo "  --all         Test all three Lambdas in sequence"
        exit 1
        ;;
esac

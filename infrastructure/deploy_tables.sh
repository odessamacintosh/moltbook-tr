#!/bin/bash
set -e

# Deploy DynamoDB tables for TechReformers Moltbook Agent v2.0

REGION="us-east-1"

echo "========================================="
echo "DynamoDB Tables Deployment"
echo "========================================="
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured"
    exit 1
fi

echo "✓ AWS credentials configured"
echo ""

# Function to create table if it doesn't exist
create_table_if_not_exists() {
    local table_name=$1
    local key_schema=$2
    local attribute_definitions=$3
    local billing_mode=$4
    local ttl_attribute=$5
    
    echo "Checking table: $table_name"
    
    if aws dynamodb describe-table --table-name "$table_name" --region "$REGION" &> /dev/null; then
        echo "✓ Table $table_name already exists"
    else
        echo "Creating table: $table_name"
        
        if [ -z "$ttl_attribute" ]; then
            # Create without TTL
            aws dynamodb create-table \
                --table-name "$table_name" \
                --key-schema "$key_schema" \
                --attribute-definitions "$attribute_definitions" \
                --billing-mode "$billing_mode" \
                --region "$REGION" > /dev/null
        else
            # Create with TTL
            aws dynamodb create-table \
                --table-name "$table_name" \
                --key-schema "$key_schema" \
                --attribute-definitions "$attribute_definitions" \
                --billing-mode "$billing_mode" \
                --region "$REGION" > /dev/null
            
            # Wait for table to be active before enabling TTL
            echo "Waiting for table to be active..."
            aws dynamodb wait table-exists --table-name "$table_name" --region "$REGION"
            
            # Enable TTL
            aws dynamodb update-time-to-live \
                --table-name "$table_name" \
                --time-to-live-specification "Enabled=true,AttributeName=$ttl_attribute" \
                --region "$REGION" > /dev/null
        fi
        
        echo "✓ Table $table_name created"
    fi
    echo ""
}

# Create aws-news-tracker table
create_table_if_not_exists \
    "aws-news-tracker" \
    "AttributeName=item_hash,KeyType=HASH" \
    "AttributeName=item_hash,AttributeType=S" \
    "PAY_PER_REQUEST" \
    ""

# Create moltbook-context table
create_table_if_not_exists \
    "moltbook-context" \
    "AttributeName=context_id,KeyType=HASH" \
    "AttributeName=context_id,AttributeType=S" \
    "PAY_PER_REQUEST" \
    "ttl"

echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Tables Created:"
echo "  1. aws-news-tracker (deduplication)"
echo "  2. moltbook-context (context storage with TTL)"
echo ""
echo "Next Steps:"
echo "  1. Update IAM roles with DynamoDB permissions"
echo "  2. Deploy news_monitor Lambda"
echo "  3. Update heartbeat Lambda with context queries"
echo "  4. Test end-to-end flow"
echo ""

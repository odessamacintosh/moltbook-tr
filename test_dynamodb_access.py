#!/usr/bin/env python3
"""
Test DynamoDB table access for v2.0 shared utilities
"""

import sys
import os

# Add shared module to path
sys.path.insert(0, os.path.dirname(__file__))

from shared.utils import (
    is_new_item,
    store_for_moltbook_context,
    get_recent_context
)

def test_deduplication():
    """Test aws-news-tracker table access"""
    print("Testing deduplication (aws-news-tracker)...")
    
    # Create a test entry with timestamp to make it unique
    import time
    timestamp = int(time.time())
    
    test_entry = {
        'title': f'Test AWS News Item {timestamp}',
        'link': f'https://aws.amazon.com/test-{timestamp}',
        'summary': 'This is a test news item'
    }
    
    # First check - should be new
    is_new = is_new_item(test_entry)
    print(f"  First check: is_new = {is_new}")
    
    if not is_new:
        print("  ✗ Expected True (new item)")
        return False
    
    # Second check - should NOT be new (already stored)
    is_new_again = is_new_item(test_entry)
    print(f"  Second check: is_new = {is_new_again}")
    
    if is_new_again:
        print("  ✗ Expected False (duplicate item)")
        return False
    
    print("  ✓ Deduplication working correctly")
    return True


def test_context_storage():
    """Test moltbook-context table access"""
    print("\nTesting context storage (moltbook-context)...")
    
    # Create test context item
    test_item = {
        'title': 'Test AWS Training News',
        'link': 'https://aws.amazon.com/training/test-456',
        'summary': 'New AWS certification announced',
        'source': 'aws_training_blog',
        'moltbook_context': 'Currently analyzing new certification requirements for our Q2 training schedule',
        'relevance': 'critical'
    }
    
    # Store the item
    try:
        store_for_moltbook_context(test_item)
        print("  ✓ Context stored successfully")
    except Exception as e:
        print(f"  ✗ Failed to store context: {e}")
        return False
    
    return True


def test_context_retrieval():
    """Test context retrieval"""
    print("\nTesting context retrieval...")
    
    try:
        items = get_recent_context(hours=24)
        print(f"  Retrieved {len(items)} context items")
        
        if len(items) > 0:
            print(f"  Sample item: {items[0]['title'][:50]}...")
        
        print("  ✓ Context retrieval working")
        return True
    except Exception as e:
        print(f"  ✗ Failed to retrieve context: {e}")
        return False


def main():
    print("=" * 60)
    print("DynamoDB Access Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Deduplication", test_deduplication()))
    results.append(("Context Storage", test_context_storage()))
    results.append(("Context Retrieval", test_context_retrieval()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nPassed: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n✓ All tests passed! DynamoDB tables are accessible.")
        return 0
    else:
        print("\n✗ Some tests failed. Check IAM permissions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

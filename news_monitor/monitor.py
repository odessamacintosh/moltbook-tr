import json
import boto3
import feedparser
import requests
import hashlib
from datetime import datetime, timedelta
from shared.utils import ask_claude, send_email, is_new_item, store_for_moltbook_context
from sources import NEWS_SOURCES, is_training_relevant

def lambda_handler(event, context):
    """Check AWS news sources and generate training content"""
    news_items = []
    
    # Check all configured news sources
    for source_name, config in NEWS_SOURCES.items():
        try:
            feed = feedparser.parse(config['url'])
            print(f"Checking {source_name}: {len(feed.entries)} entries found")
            
            for entry in feed.entries[:config['limit']]:
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                
                if is_new_item(entry) and is_training_relevant(title, summary):
                    news_items.append({
                        'title': title,
                        'link': link,
                        'summary': summary, 
                        'source': source_name,
                        'published': published,
                        'relevance': config['training_relevance']
                    })
                    print(f"New relevant item: {title}")
        except Exception as e:
            print(f"Error processing {source_name}: {e}")
            continue
    
    print(f"Found {len(news_items)} new training-relevant items")
    
    # Generate content for each news item
    for item in news_items:
        try:
            generate_and_send_content(item)
            store_for_moltbook_context(item)
        except Exception as e:
            print(f"Error processing item {item['title']}: {e}")
            continue
    
    return {
        'statusCode': 200, 
        'body': f'Processed {len(news_items)} news items'
    }

def generate_and_send_content(news_item):
    """Generate training-focused content and email it"""
    
    prompt = f"""
    You are TechReformers, an AWS Authorized Training Provider. A new AWS announcement just dropped.
    Your job is to translate this announcement into content that helps certification candidates and
    enterprise learners understand why it matters to them — even if the announcement isn't about
    training directly. Every AWS capability change has exam and career implications; make that angle explicit.

    ANNOUNCEMENT:
    Title: {news_item['title']}
    Summary: {news_item['summary']}
    Source: {news_item['source']}
    Link: {news_item['link']}

    Generate the following four sections:

    1. TWITTER (280 chars max):
       - Lead with the certification/career angle: which exam domain or job role does this affect?
       - Be direct and punchy. Include 2-3 relevant hashtags (e.g. #AWScert #CloudTraining #AWS).

    2. LINKEDIN (1300 chars max):
       - Open with a hook: "If you're studying for [cert], pay attention to this."
       - Explain what changed and which AWS service/feature is involved.
       - Name the specific certification exams or domains this is likely to appear in.
       - Give one practical example of how a Solutions Architect, Developer, or SysOps engineer
         would use this in the real world.
       - Close with a call-to-action (comment, share, or link to TechReformers).

    3. BLOG OUTLINE:
       - Title suggestion
       - 3-4 section headings with one-line descriptions
       - Which AWS cert domains this content supports

    4. MOLTBOOK CONTEXT (one sentence):
       - What TechReformers is "currently working on" related to this news.
       - Should sound natural, like: "analyzing X for our upcoming Y training" or
         "building a new lab on X for Solutions Architect students".

    As an ATP we teach official AWS curriculum but add real-world context, hands-on labs, and demos.
    """
    
    try:
        content = ask_claude(prompt)
        
        # Parse the MOLTBOOK CONTEXT from Claude's response
        moltbook_context = ""
        for line in content.split('\n'):
            if 'MOLTBOOK CONTEXT' in line.upper() or line.strip().startswith('4.'):
                # Extract the context sentence (everything after the label)
                parts = line.split(':', 1)
                if len(parts) > 1:
                    moltbook_context = parts[1].strip()
                    # Remove any leading dashes or bullets
                    moltbook_context = moltbook_context.lstrip('- ').strip()
                    break
        
        # Add the parsed context back to the item
        if moltbook_context:
            news_item['moltbook_context'] = moltbook_context
            print(f"Extracted moltbook_context: {moltbook_context}")
        
        # Email the generated content
        subject = f"AWS Training Content Ready - {news_item['title'][:50]}..."
        
        email_body = f"""
New AWS Training Content Generated

SOURCE: {news_item['source']}
RELEVANCE: {news_item['relevance']}
LINK: {news_item['link']}

GENERATED CONTENT:
{content}

---
Generated at: {datetime.now().isoformat()}
        """
        
        send_email(subject, email_body)
        print(f"Content generated and emailed for: {news_item['title']}")
        
    except Exception as e:
        print(f"Error generating content: {e}")
        raise
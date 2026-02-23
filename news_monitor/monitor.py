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
    Analyze this AWS news from an AWS Authorized Training Provider perspective:
    
    Title: {news_item['title']}
    Summary: {news_item['summary']}
    Source: {news_item['source']}
    Link: {news_item['link']}
    
    As an AWS Authorized Training Provider, generate content for:
    
    1. TWITTER (280 chars max): 
       - Focus on how this impacts AWS certifications or training
       - Be conversational and engaging
       - Include relevant hashtags
    
    2. LINKEDIN (1300 chars max):
       - Professional analysis of training/certification implications  
       - How this affects enterprise AWS adoption
       - Include call-to-action for engagement
    
    3. BLOG OUTLINE:
       - 3-4 key points for detailed technical analysis
       - Focus on practical implications for students/enterprises
       
    4. MOLTBOOK CONTEXT (one sentence):
       - What TechReformers is "currently working on" related to this news
       - Should sound natural, like: "analyzing X for our upcoming Y training"
    
    Keep everything focused on training, certification, and enterprise learning implications.
    Remember: As an ATP, we use official AWS curriculum but add industry context and demos.
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
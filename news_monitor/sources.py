# RSS feeds and their parsing configs
NEWS_SOURCES = {
    'aws_whats_new': {
        'url': 'https://aws.amazon.com/about-aws/whats-new/recent/feed/',
        'limit': 5,
        'training_relevance': 'high'  # New services = new exam content
    },
    'aws_training_blog': {
        'url': 'https://aws.amazon.com/blogs/training-and-certification/feed/', 
        'limit': 3,
        'training_relevance': 'critical'  # Direct training/cert content
    },
    'aws_architecture_blog': {
        'url': 'https://aws.amazon.com/blogs/architecture/feed/',
        'limit': 2, 
        'training_relevance': 'medium'  # Good for Solutions Architect content
    },
    'aws_security_blog': {
        'url': 'https://aws.amazon.com/blogs/security/feed/',
        'limit': 2,
        'training_relevance': 'medium'  # Security Specialty content
    }
}

# Keywords that indicate training/certification relevance
TRAINING_KEYWORDS = [
    'certification', 'exam', 'training', 'bootcamp', 'course',
    'practitioner', 'associate', 'professional', 'specialty',
    'new service', 'announcement', 'ga', 'general availability'
]

def is_training_relevant(title, summary):
    """Check if news item is relevant for training content"""
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in TRAINING_KEYWORDS)
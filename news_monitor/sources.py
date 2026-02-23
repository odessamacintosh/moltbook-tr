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

# Keywords that indicate a meaningful AWS announcement worth covering.
# Cast wide — any new capability, service, or feature has training implications.
TRAINING_KEYWORDS = [
    # Launch signals
    'now available', 'generally available', 'general availability', 'preview',
    'announces', 'introducing', 'launches', 'launched', 'new',
    # Service/feature terms common in AWS announcements
    'instance', 'service', 'feature', 'support', 'update', 'region',
    # Cert and learning terms
    'certification', 'exam', 'training', 'course', 'learning path',
    'practitioner', 'associate', 'professional', 'specialty',
    'architect', 'developer', 'sysops', 'devops', 'security',
]

def is_training_relevant(title, summary):
    """Check if news item is a meaningful AWS announcement worth covering.
    Most AWS announcements qualify — the training angle is applied in the prompt."""
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in TRAINING_KEYWORDS)
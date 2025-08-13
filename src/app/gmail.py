"""Gmail integration module for fetching tech news from Gmail inbox using IMAP."""
import imaplib
import email
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from .config import settings
from .url_cleaner import clean_url, resolve_canonical_url

logger = logging.getLogger(__name__)

# Common domains that typically contain tech news
TECH_DOMAINS = {
    'techcrunch.com', 'wired.com', 'arstechnica.com', 'theverge.com',
    'venturebeat.com', 'engadget.com', 'gizmodo.com', 'mashable.com',
    'recode.net', 'cnet.com', 'zdnet.com', 'computerworld.com',
    'infoworld.com', 'networkworld.com', 'pcworld.com', 'macworld.com',
    'androidcentral.com', 'imore.com', 'windowscentral.com',
    'producthunt.com', 'hackernoon.com', 'medium.com',
    'blog.google.com', 'blog.microsoft.com', 'blog.apple.com',
    'openai.com', 'deepmind.com', 'ai.googleblog.com'
}

# Keywords that suggest tech relevance
TECH_KEYWORDS = {
    'ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning',
    'neural network', 'gpt', 'llm', 'chatgpt', 'openai', 'google ai',
    'tech', 'technology', 'startup', 'venture capital', 'vc', 'funding',
    'software', 'hardware', 'app', 'application', 'platform', 'api',
    'cloud computing', 'saas', 'paas', 'iaas', 'aws', 'azure', 'gcp',
    'programming', 'developer', 'coding', 'github', 'open source',
    'cryptocurrency', 'crypto', 'blockchain', 'bitcoin', 'ethereum',
    'mobile', 'android', 'ios', 'iphone', 'ipad', 'smartphone',
    'vr', 'ar', 'xr', 'virtual reality', 'augmented reality', 'mixed reality',
    'metaverse', 'oculus', 'meta', 'apple vision',
    'music tech', 'musictech', 'audio', 'daw', 'vst', 'plugin', 'ableton',
    'pro tools', 'logic pro', 'cubase', 'fl studio', 'spotify', 'apple music'
}

async def connect_to_gmail() -> Optional[imaplib.IMAP4_SSL]:
    """Connect to Gmail using IMAP with app password."""
    try:
        if not settings.gmail_imap_user or not settings.gmail_imap_pass:
            logger.warning("Gmail IMAP credentials not configured")
            return None
            
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(settings.gmail_imap_user, settings.gmail_imap_pass)
        logger.info("Successfully connected to Gmail IMAP")
        return mail
    except Exception as e:
        logger.error(f"Failed to connect to Gmail IMAP: {e}")
        return None

def extract_links_from_text(text: str) -> List[str]:
    """Extract URLs from email text content."""
    # Regex pattern to match URLs
    url_pattern = r'https?://[^\s<>"\']+'  
    urls = re.findall(url_pattern, text)
    return urls

def is_tech_relevant(subject: str, content: str, sender: str) -> bool:
    """Check if email content is tech-relevant based on keywords and domains."""
    # Check if sender is from a known tech domain
    sender_domain = sender.split('@')[-1].lower() if '@' in sender else ''
    if any(domain in sender_domain for domain in TECH_DOMAINS):
        return True
    
    # Check subject and content for tech keywords
    combined_text = f"{subject} {content}".lower()
    return any(keyword in combined_text for keyword in TECH_KEYWORDS)

async def extract_tech_links_from_email(msg) -> List[Dict[str, Any]]:
    """Extract tech-relevant links from an email message."""
    links = []
    subject = msg.get('subject', '')
    sender = msg.get('from', '')
    date_str = msg.get('date', '')
    
    try:
        # Parse email date
        email_date = email.utils.parsedate_to_datetime(date_str)
    except:
        email_date = datetime.now()
    
    # Extract email content
    content = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
            elif part.get_content_type() == "text/html":
                try:
                    html_content = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    # Extract links from HTML
                    soup = BeautifulSoup(html_content, 'html.parser')
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        if href.startswith('http'):
                            links.append({
                                'url': href,
                                'title': a_tag.get_text(strip=True) or subject,
                                'source': 'Gmail',
                                'published': email_date,
                                'sender': sender,
                                'subject': subject
                            })
                except:
                    pass
    else:
        # Single part message
        try:
            content = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    
    # Extract links from plain text content
    text_urls = extract_links_from_text(content)
    for url in text_urls:
        links.append({
            'url': url,
            'title': subject,
            'source': 'Gmail',
            'published': email_date,
            'sender': sender,
            'subject': subject
        })
    
    # Filter for tech relevance
    tech_links = []
    for link in links:
        if is_tech_relevant(subject, content, sender) or is_tech_url(link['url']):
            tech_links.append(link)
    
    return tech_links

def is_tech_url(url: str) -> bool:
    """Check if URL is from a known tech domain."""
    try:
        domain = urlparse(url).netloc.lower()
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return any(tech_domain in domain for tech_domain in TECH_DOMAINS)
    except:
        return False

async def fetch_gmail_articles(max_emails: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent tech articles from Gmail inbox."""
    try:
        mail = await connect_to_gmail()
        if not mail:
            return []
        
        # Select inbox
        mail.select('inbox')
        
        # Search for recent emails (last 7 days)
        since_date = (datetime.now() - timedelta(days=7)).strftime('%d-%b-%Y')
        search_criteria = f'(SINCE "{since_date}")'
        
        result, message_numbers = mail.search(None, search_criteria)
        
        if result != 'OK':
            logger.error("Failed to search emails")
            return []
        
        message_ids = message_numbers[0].split()
        logger.info(f"Found {len(message_ids)} emails in last 7 days")
        
        # Limit to most recent emails
        recent_ids = message_ids[-max_emails:] if len(message_ids) > max_emails else message_ids
        
        all_articles = []
        
        for msg_id in recent_ids:
            try:
                result, msg_data = mail.fetch(msg_id, '(RFC822)')
                if result != 'OK':
                    continue
                
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract tech links from this email
                tech_links = await extract_tech_links_from_email(email_message)
                
                # Clean and resolve URLs
                for link in tech_links:
                    try:
                        # Clean tracking parameters
                        link['url'] = clean_url(link['url'])
                        
                        # Try to resolve canonical URL
                        canonical_url = await resolve_canonical_url(link['url'])
                        if canonical_url:
                            link['url'] = canonical_url
                            
                        all_articles.append({
                            'title': link['title'],
                            'link': link['url'],
                            'description': f"From {link['sender']}: {link['subject']}",
                            'published': link['published'],
                            'source': f"Gmail ({link['sender']})" 
                        })
                    except Exception as e:
                        logger.warning(f"Failed to process link {link['url']}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"Failed to process email {msg_id}: {e}")
                continue
        
        mail.close()
        mail.logout()
        
        logger.info(f"Extracted {len(all_articles)} tech articles from Gmail")
        return all_articles
        
    except Exception as e:
        logger.error(f"Error fetching Gmail articles: {e}")
        return []

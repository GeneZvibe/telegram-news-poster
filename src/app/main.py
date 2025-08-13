"""Main application script for Telegram News Poster.
Fetch -> Filter -> Summarize -> Dedupe -> Compose -> Send
"""
import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import yaml
import feedparser
from dateutil import parser as date_parser
from .config import settings, SOURCES_PATH
from .utils import fetch_url, clean_html, hash_item
from .summarize import create_summary
from .gmail import fetch_gmail_articles  # New Gmail integration
from .url_cleaner import clean_and_resolve_url  # New URL cleaner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store for deduplication
processed_articles = set()

async def load_sources() -> Dict[str, List[Dict[str, str]]]:
    """Load RSS sources from YAML configuration."""
    try:
        with open(SOURCES_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config['sources']
    except Exception as e:
        logger.error(f"Failed to load sources: {e}")
        return {}

async def fetch_feed_articles(feed_url: str, max_articles: int = 5) -> List[Dict[str, Any]]:
    """Fetch articles from a single RSS/Atom feed."""
    try:
        feed_content = await fetch_url(feed_url)
        if not feed_content:
            return []
            
        feed = feedparser.parse(feed_content)
        articles = []
        
        for entry in feed.entries[:max_articles]:
            try:
                # Parse publication date
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    published_date = date_parser.parse(entry.published)
                
                # Skip old articles - FIX: Use total_seconds() instead of .hours
                if published_date and (datetime.now() - published_date).total_seconds() / 3600 > 48:
                    continue
                    
                # Clean and resolve the article URL
                article_url = entry.get('link', '')
                if article_url:
                    article_url = clean_and_resolve_url(article_url)
                    
                article = {
                    'title': entry.get('title', '').strip(),
                    'link': article_url,
                    'description': clean_html(entry.get('description', '')),
                    'published': published_date,
                    'source': feed.feed.get('title', 'Unknown Source')
                }
                
                # Filter by minimum length
                if len(article['description']) >= 200:
                    articles.append(article)
                    
            except Exception as e:
                logger.warning(f"Error processing entry: {e}")
                continue
                
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching feed {feed_url}: {e}")
        return []

async def filter_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter articles by keywords and relevance."""
    filtered = []
    
    for article in articles:
        # Create searchable text from title and description
        searchable_text = f"{article['title']} {article['description']}".lower()
        
        # Check if any keyword matches
        for keyword in settings.keywords:
            if keyword.lower() in searchable_text:
                article['matched_keyword'] = keyword
                filtered.append(article)
                break
                
    return filtered

async def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate articles based on content hash and URL."""
    global processed_articles
    
    unique_articles = []
    current_hashes = set()
    current_urls = set()
    
    for article in articles:
        # Create hash from title and description
        article_hash = hash_item(article['title'] + article['description'])
        
        # Also check URL for duplicates
        article_url = article.get('link', '').lower()
        
        # Skip if we've seen this article recently or in current batch
        if (article_hash not in processed_articles and 
            article_hash not in current_hashes and
            article_url not in current_urls):
            
            unique_articles.append(article)
            current_hashes.add(article_hash)
            if article_url:
                current_urls.add(article_url)
            
    # Update processed articles set (keep last 1000 for memory management)
    processed_articles.update(current_hashes)
    if len(processed_articles) > 1000:
        # Remove oldest half
        processed_articles = set(list(processed_articles)[500:])
    
    return unique_articles

async def compose_telegram_messages(articles: List[Dict[str, Any]]) -> List[str]:
    """Compose separate Telegram messages for each article with simplified format."""
    if not articles:
        return ["📰 No relevant news found today."]
        
    messages = []
    
    for article in articles:
        # Create summary
        summary = create_summary(article['description'])
        
        # Format: 1) Bold TLDR headline, 2) blank line, 3) TLDR body, 4) blank line, 5) Read more link
        article_msg = (
            f"**{article['title']}**\n\n"
            f"{summary}\n\n"
            f"[Read more]({article['link']})"
        )
        
        messages.append(article_msg)
                
    return messages

async def send_telegram_message(message: str) -> bool:
    """Send message to Telegram channel using Bot API."""
    try:
        import requests
        
        # Skip sending if in dry run mode
        if settings.dry_run:
            logger.info("DRY RUN: Would send message to Telegram:")
            logger.info("=" * 50)
            logger.info(message)
            logger.info("=" * 50)
            return True
        
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            'chat_id': settings.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        logger.info("Message sent successfully to Telegram")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

async def send_telegram_messages(messages: List[str]) -> bool:
    """Send multiple messages to Telegram channel."""
    success_count = 0
    
    for i, message in enumerate(messages):
        logger.info(f"Sending message {i + 1} of {len(messages)}")
        success = await send_telegram_message(message)
        if success:
            success_count += 1
        
        # Add delay between messages to avoid rate limiting
        if i < len(messages) - 1:
            await asyncio.sleep(1)
    
    logger.info(f"Successfully sent {success_count} of {len(messages)} messages")
    return success_count == len(messages)

async def main():
    """Main application workflow."""
    logger.info("Starting Telegram News Poster")
    
    try:
        # Load sources
        sources = await load_sources()
        if not sources:
            logger.error("No sources loaded, exiting")
            return
            
        all_articles = []
        
        # Fetch articles from RSS feeds
        for category, source_list in sources.items():
            logger.info(f"Processing {category} RSS sources")
            
            for source in source_list:
                logger.info(f"Fetching from {source['name']}")
                articles = await fetch_feed_articles(
                    source['url'], 
                    settings.max_articles_per_source
                )
                all_articles.extend(articles)
        
        # Fetch articles from Gmail if configured
        gmail_articles = fetch_gmail_articles(
            max_emails=settings.max_articles_per_source * 2  # Allow more emails to be processed
        )
        if gmail_articles:
            logger.info(f"Fetched {len(gmail_articles)} articles from Gmail")
            all_articles.extend(gmail_articles)
        else:
            logger.info("No Gmail articles fetched (credentials not configured or no relevant emails)")
        
        logger.info(f"Fetched {len(all_articles)} total articles from all sources")
        
        # Process articles through the pipeline
        filtered_articles = await filter_articles(all_articles)
        logger.info(f"Filtered to {len(filtered_articles)} relevant articles")
        
        unique_articles = await deduplicate_articles(filtered_articles)
        logger.info(f"Deduplicated to {len(unique_articles)} unique articles")
        
        # Skip posting if no relevant articles found
        if not unique_articles and not settings.force_run:
            logger.info("No relevant articles found and FORCE_RUN not set. Skipping post.")
            return
        
        # Compose messages
        messages = await compose_telegram_messages(unique_articles)
        logger.info(f"Composed {len(messages)} messages for Telegram")
        
        # Only send if we have actual content (not just "no news found")
        if len(messages) == 1 and "No relevant news found" in messages[0] and not settings.force_run:
            logger.info("No relevant news content to post and FORCE_RUN not set. Skipping.")
            return
        
        success = await send_telegram_messages(messages)
        
        if success:
            logger.info("News posting completed successfully")
        else:
            logger.error("Failed to send some messages")
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

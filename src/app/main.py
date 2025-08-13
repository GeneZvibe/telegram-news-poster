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
                
                # Skip old articles
                if published_date and (datetime.now() - published_date).hours > 48:
                    continue
                    
                article = {
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', ''),
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
    """Remove duplicate articles based on content hash."""
    global processed_articles
    
    unique_articles = []
    current_hashes = set()
    
    for article in articles:
        article_hash = hash_item(article['title'] + article['description'])
        
        # Skip if we've seen this article recently or in current batch
        if article_hash not in processed_articles and article_hash not in current_hashes:
            unique_articles.append(article)
            current_hashes.add(article_hash)
            
    # Update processed articles set (keep last 1000 for memory management)
    processed_articles.update(current_hashes)
    if len(processed_articles) > 1000:
        # Remove oldest half
        processed_articles = set(list(processed_articles)[500:])
    
    return unique_articles


async def compose_telegram_message(articles: List[Dict[str, Any]]) -> str:
    """Compose a Telegram message from filtered articles."""
    if not articles:
        return "📰 No relevant news found today."
        
    # Group articles by category based on matched keywords
    categories = {
        'AI': [],
        'MusicTech': [],
        'XR': []
    }
    
    for article in articles:
        keyword = article['matched_keyword']
        if any(ai_kw in keyword.lower() for ai_kw in ['ai', 'artificial intelligence', 'machine learning', 'ml', 'gpt', 'llm']):
            categories['AI'].append(article)
        elif any(music_kw in keyword.lower() for music_kw in ['music', 'audio', 'daw', 'vst', 'plugin']):
            categories['MusicTech'].append(article)
        elif any(xr_kw in keyword.lower() for xr_kw in ['xr', 'vr', 'ar', 'mr', 'virtual', 'augmented', 'mixed reality']):
            categories['XR'].append(article)
            
    # Compose message
    message_parts = [f"📰 **Daily Tech News - {datetime.now().strftime('%B %d, %Y')}**\n"]
    
    for category, cat_articles in categories.items():
        if cat_articles:
            emoji = {'AI': '🤖', 'MusicTech': '🎵', 'XR': '🥽'}
            message_parts.append(f"\n{emoji[category]} **{category}**")
            
            for article in cat_articles[:3]:  # Limit to 3 per category
                summary = create_summary(article['description'])
                message_parts.append(
                    f"• *{article['title']}*\n"
                    f"  TL;DR: {summary}\n"
                    f"  🔗 [Read more]({article['link']})"
                )
                
    message_parts.append("\n---\n📱 *Powered by @GeneFrankelBot*")
    return "\n".join(message_parts)


async def send_telegram_message(message: str) -> bool:
    """Send message to Telegram channel using Bot API."""
    try:
        import requests
        
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
        
        # Fetch articles from all sources
        for category, source_list in sources.items():
            logger.info(f"Processing {category} sources")
            
            for source in source_list:
                logger.info(f"Fetching from {source['name']}")
                articles = await fetch_feed_articles(
                    source['url'], 
                    settings.max_articles_per_source
                )
                all_articles.extend(articles)
                
        logger.info(f"Fetched {len(all_articles)} total articles")
        
        # Process articles through the pipeline
        filtered_articles = await filter_articles(all_articles)
        logger.info(f"Filtered to {len(filtered_articles)} relevant articles")
        
        unique_articles = await deduplicate_articles(filtered_articles)
        logger.info(f"Deduplicated to {len(unique_articles)} unique articles")
        
        # Compose and send message
        message = await compose_telegram_message(unique_articles)
        logger.info("Composed message for Telegram")
        
        success = await send_telegram_message(message)
        
        if success:
            logger.info("News posting completed successfully")
        else:
            logger.error("Failed to send message")
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

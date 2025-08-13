"""Utility functions for Telegram News Poster."""

import hashlib
import re
import asyncio
import aiohttp
from typing import Optional
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch content from URL with retries and error handling.
    
    Args:
        url: The URL to fetch
        timeout: Timeout in seconds
        
    Returns:
        The response text, or None if failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            ) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
                    
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def clean_html(html_content: str) -> str:
    """Clean HTML content and extract plain text.
    
    Args:
        html_content: Raw HTML string
        
    Returns:
        Cleaned plain text
    """
    if not html_content:
        return ""
        
    try:
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing spaces
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Remove empty lines
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
        
    except Exception as e:
        print(f"Error cleaning HTML: {e}")
        return html_content.strip() if html_content else ""


def hash_item(content: str) -> str:
    """Generate a hash for content to enable deduplication.
    
    Args:
        content: Content to hash
        
    Returns:
        SHA256 hash string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def truncate_text(text: str, max_length: int = 280) -> str:
    """Truncate text to specified length while preserving words.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
        
    # Find last space before max_length
    truncated = text[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."


def extract_keywords(text: str, keywords: list) -> list:
    """Extract matching keywords from text.
    
    Args:
        text: Text to search
        keywords: List of keywords to match
        
    Returns:
        List of matched keywords
    """
    text_lower = text.lower()
    matched = []
    
    for keyword in keywords:
        if keyword.lower() in text_lower:
            matched.append(keyword)
            
    return matched


def format_datetime(dt) -> str:
    """Format datetime for display.
    
    Args:
        dt: datetime object
        
    Returns:
        Formatted date string
    """
    if dt:
        return dt.strftime('%Y-%m-%d %H:%M UTC')
    return 'Unknown'


def validate_url(url: str) -> bool:
    """Validate if string is a proper URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain...
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # host...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram Markdown.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text safe for Markdown
    """
    # Characters that need escaping in Telegram Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
        
    return text


def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Calculate estimated reading time for text.
    
    Args:
        text: Text to analyze
        words_per_minute: Reading speed
        
    Returns:
        Reading time in minutes
    """
    word_count = len(text.split())
    reading_time = max(1, round(word_count / words_per_minute))
    return reading_time

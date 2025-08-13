"""URL cleaning utilities for removing tracking parameters and resolving canonical links."""
import re
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common tracking parameters to remove
TRACKING_PARAMS = {
    # UTM parameters
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'utm_id',
    'utm_source_platform', 'utm_creative_format', 'utm_marketing_tactic',
    
    # Facebook tracking
    'fbclid', 'fb_action_ids', 'fb_action_types', 'fb_ref', 'fb_source',
    
    # Google tracking
    'gclid', 'gclsrc', 'gbraid', 'wbraid', 'dclid', 'msclkid',
    
    # Email marketing
    'mc_cid', 'mc_eid', 'ml_subscriber', 'ml_subscriber_hash',
    
    # Affiliate tracking
    'aff', 'affiliate', 'aff_id', 'affiliate_id', 'partner', 'partner_id',
    'ref', 'ref_src', 'referrer', 'source', 'campaign',
    
    # Social media
    'igshid', 'igsh', 'si', 'share', 'shared',
    
    # Version/tracking
    'ver', 'version', 'v', '_ga', '_gl', '_hsenc', '_hsmi',
    
    # Platform specific
    'feature', 'app', 'at_medium', 'at_campaign', 'at_custom1', 'at_custom2',
    'iesrc', 'mkt_tok', 'trk', 'trkCampaign', 'sc_campaign', 'sc_channel',
    
    # Newsletter/email
    'newsletter', 'email', 'em', 'subscriber', 'sub_id',
    
    # Misc tracking
    'hash', 'track', 'tracking', 'tid', 'cid', 'eid',
}

def clean_url(url: str) -> str:
    """Remove tracking parameters from URL."""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Remove tracking parameters
        cleaned_params = {
            key: value for key, value in query_params.items() 
            if key.lower() not in TRACKING_PARAMS
        }
        
        # Rebuild URL without tracking parameters
        cleaned_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ''
        cleaned_parsed = parsed._replace(query=cleaned_query)
        
        return urlunparse(cleaned_parsed)
    except Exception as e:
        logger.warning(f"Failed to clean URL {url}: {e}")
        return url

def follow_redirects(url: str, max_redirects: int = 5) -> str:
    """Follow redirects to get final destination URL."""
    try:
        response = requests.head(
            url, 
            allow_redirects=True, 
            timeout=10,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        # Return the final URL after all redirects
        return response.url
    except Exception as e:
        logger.warning(f"Failed to follow redirects for {url}: {e}")
        return url

async def resolve_canonical_url(url: str) -> Optional[str]:
    """Try to resolve canonical URL using rel=canonical or og:url."""
    try:
        # First, follow redirects
        final_url = follow_redirects(url)
        
        # Then try to fetch the page and find canonical URL
        response = requests.get(
            final_url,
            timeout=15,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        response.raise_for_status()
        
        # Parse HTML to find canonical URL
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for canonical link
        canonical_link = soup.find('link', rel='canonical')
        if canonical_link and canonical_link.get('href'):
            canonical_url = canonical_link['href']
            # Make sure it's absolute
            if canonical_url.startswith('//'):
                canonical_url = f"https:{canonical_url}"
            elif canonical_url.startswith('/'):
                parsed_base = urlparse(final_url)
                canonical_url = f"{parsed_base.scheme}://{parsed_base.netloc}{canonical_url}"
            elif not canonical_url.startswith('http'):
                # Relative URL, make it absolute
                parsed_base = urlparse(final_url)
                base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
                if parsed_base.path:
                    base_url += parsed_base.path.rsplit('/', 1)[0]
                canonical_url = f"{base_url}/{canonical_url}"
            
            # Clean the canonical URL too
            return clean_url(canonical_url)
        
        # Check for Open Graph URL
        og_url_meta = soup.find('meta', property='og:url')
        if og_url_meta and og_url_meta.get('content'):
            og_url = og_url_meta['content']
            # Make sure it's absolute
            if og_url.startswith('//'):
                og_url = f"https:{og_url}"
            elif og_url.startswith('/'):
                parsed_base = urlparse(final_url)
                og_url = f"{parsed_base.scheme}://{parsed_base.netloc}{og_url}"
            elif not og_url.startswith('http'):
                # Relative URL, make it absolute
                parsed_base = urlparse(final_url)
                base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
                if parsed_base.path:
                    base_url += parsed_base.path.rsplit('/', 1)[0]
                og_url = f"{base_url}/{og_url}"
            
            # Clean the OG URL too
            return clean_url(og_url)
            
        # If no canonical URL found, return the cleaned final URL
        return clean_url(final_url)
        
    except Exception as e:
        logger.warning(f"Failed to resolve canonical URL for {url}: {e}")
        # Return the cleaned original URL as fallback
        return clean_url(url)

def is_shortened_url(url: str) -> bool:
    """Check if URL appears to be from a URL shortening service."""
    shortening_domains = {
        'bit.ly', 'tinyurl.com', 'short.link', 'ow.ly', 't.co', 'goo.gl',
        'buff.ly', 'amzn.to', 'youtu.be', 'l.facebook.com', 'l.messenger.com',
        'lnkd.in', 'is.gd', 'j.mp', 'po.st', 'bc.vc', 'smarturl.it',
        'tiny.cc', 'cli.re', 'go2l.ink', 'cutt.ly', 'rb.gy', 'short.io'
    }
    
    try:
        domain = urlparse(url).netloc.lower()
        return any(shortener in domain for shortener in shortening_domains)
    except:
        return False

def clean_and_resolve_url(url: str) -> str:
    """Complete URL cleaning and resolution pipeline."""
    try:
        # First clean basic tracking parameters
        cleaned_url = clean_url(url)
        
        # If it's a shortened URL, try to resolve it fully
        if is_shortened_url(cleaned_url):
            # For shortened URLs, always follow redirects
            final_url = follow_redirects(cleaned_url)
            return clean_url(final_url)  # Clean again after resolving
        
        return cleaned_url
        
    except Exception as e:
        logger.error(f"Error in complete URL cleaning for {url}: {e}")
        return url  # Return original on error

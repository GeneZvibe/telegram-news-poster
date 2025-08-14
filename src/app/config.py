"""Configuration settings for Telegram News Poster."""
import os
import re
import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

def load_blocklist():
    """Load and compile blocklist patterns from YAML file."""
    try:
        blocklist_path = Path(__file__).parent.parent.parent / "data" / "blocklist.yml"
        if not blocklist_path.exists():
            return []
        
        with open(blocklist_path, 'r') as f:
            blocklist_data = yaml.safe_load(f)
        
        patterns = []
        if 'vr_gaming_posts' in blocklist_data:
            for item in blocklist_data['vr_gaming_posts']:
                pattern = item.get('pattern', '')
                if pattern:
                    patterns.append(re.compile(pattern, re.IGNORECASE))
        
        return patterns
    except Exception as e:
        print(f"Warning: Failed to load blocklist: {e}")
        return []

class Settings(BaseSettings):
    """Application settings managed by Pydantic."""
    
    # Sources configuration
    sources_file: str = Field(default="sources.yaml", description="Path to sources YAML file")
    
    # Keyword filtering - UPDATED: Tech-first allowlist and gaming blocklist
    allowlist_keywords: List[str] = Field(
        default=[
            # AI/ML/LLM terms
            "AI", "artificial intelligence", "machine learning", "ML", "LLM", "GPT",
            
            # XR/VR/AR/MR terms
            "XR", "AR", "VR", "augmented reality", "virtual reality", "mixed reality",
            "headset", "optics", "pass-through", "SLAM", "hand tracking", "computer vision",
            
            # Research and development
            "research", "paper", "benchmark",
            
            # Development tools and frameworks
            "SDK", "API", "framework", "model", "dataset", "tooling", "compiler", "library", "plugin",
            
            # Audio/music tech
            "DAW", "synth", "synthesis", "DSP", "audio engineering", "MIDI", "VST", "AAX", "AU",
            
            # Hardware and tech
            "firmware", "hardware", "silicon", "chip", "semiconductor", "sensor"
        ],
        description="Keywords that must be present for tech-focused filtering"
    )
    
    blocklist_keywords: List[str] = Field(
        default=[
            # Gaming and entertainment exclusions
            "game review", "walkthrough", "let's play", "let us play", "trailer", "teaser",
            "DLC", "season pass", "patch notes", "speedrun", "esports", "tournament",
            "giveaway", "preorder", "pre-order", "merch", "skins", "loot", "boss fight",
            "build guide", "weapon", "quest", "raid", "console", "PS5", "Xbox", "Switch",
            
            # MusicTech plugin exclusions - routine posts without innovation
            "preset pack", "sample pack", "expansion", "soundbank", "deal", "discount",
            "Black Friday", "freebie", "bundle", "preset browser", "theme",
            "Kontakt library", "rompler", "loop pack", "drum kit", "template",
            "review", "updated to v", "changelog", "compatibility update"
        ],
        description="Keywords that exclude articles from gaming/entertainment posts and routine plugin announcements"
    )
    
    # Legacy keywords field (kept for backward compatibility)
    keywords: List[str] = Field(
        default=["AI", "artificial intelligence", "machine learning", "ML", "GPT", "LLM", 
                "XR", "virtual reality", "VR", "augmented reality", "AR", "mixed reality", "MR",
                "MusicTech", "music technology", "audio", "DAW", "VST", "plugin"],
        description="Legacy keywords field for backward compatibility"
    )
    
    # URL filtering - blocked domains and banned path keywords
    blocked_domains: List[str] = Field(
        default=[
            # Social media login/register pages
            "accounts.google.com", "login.microsoftonline.com", "auth0.com", "okta.com",
            "id.atlassian.com", "github.com/login", "gitlab.com/users/sign_in",
            
            # Paywalls and subscription gates
            "subscribe.", "paywall.", "premium.", "plus.",  # Common subdomain patterns
            "pro.", "upgrade.", 
            
            # Common tracker and ad domains
            "google-analytics.com", "googletagmanager.com", "facebook.com/tr",
            "doubleclick.net", "googlesyndication.com", "amazon-adsystem.com",
            "adsystem.amazon.com", "googlepubads.g.doubleclick.net",
            
            # Newsletter/tracker redirector domains
            "ct.sendgrid.net", "sendgrid.net", "mailchi.mp", "l.facebook.com", "l.messenger.com",
            "t.co", "lnkd.in", "mail.google.com", "click.email.*", "links.mail.*",
            "go.pardot.com", "urldefense.com", "mandrillapp.com", "click.icptrack.com",
            "sparkloop.app", "beehiiv.com", "verge.link",
            
            # URL shorteners and redirectors that might hide login/paywall
            "bit.ly", "tinyurl.com", "goo.gl", "ow.ly", "short.link",
        ],
        description="Domains to block from URL processing"
    )
    
    banned_path_keywords: List[str] = Field(
        default=[
            # Authentication and account management
            "/login", "/signin", "/sign-in", "/register", "/signup", "/sign-up",
            "/auth", "/oauth", "/sso", "/authenticate",
            "/account", "/profile", "/dashboard", "/settings",
            
            # Subscription and payment
            "/subscribe", "/subscription", "/premium", "/upgrade", "/pricing",
            "/checkout", "/payment", "/billing", "/paywall",
            "/plus", "/pro", "/member", "/membership",
            
            # Tracking and analytics
            "/track", "/analytics", "/pixel", "/beacon", "/metrics",
            "/utm_", "?utm_", "&utm_", "/click", "/redirect",
            
            # Administrative and system pages
            "/admin", "/wp-admin", "/administrator", "/control",
            "/api/", "/webhook", "/callback", "/ping", "/health",
            
            # Newsletter and email-specific (updated)
            "/unsubscribe", "/newsletter", "/email", "/mailchimp",
            "/campaign", "/drip", "/convertkit", "/mailgun",
            
            # Newsletter/tracker path keywords
            "/ss/c", "/list-manage", "/r/?u=", "/tracking", "/ref",
            "mc_cid", "mc_eid",
        ],
        description="Path keywords to ban from URLs"
    )
    
    # Scheduling
    post_time: str = Field(default="12:00", description="Time to post daily updates (HH:MM)")
    timezone: str = Field(default="US/Eastern", description="Timezone for posting schedule")
    
    # Deduplication
    dedupe_days: int = Field(default=7, description="Days to look back for duplicate detection")
    
    # Telegram configuration
    channel_username: str = Field(default="@GeneFrankelBot", description="Telegram channel username")
    telegram_bot_token: str = Field(description="Telegram bot token")
    telegram_chat_id: str = Field(description="Telegram chat/channel ID")
    
    # Gmail IMAP configuration
    gmail_imap_user: Optional[str] = Field(default=None, description="Gmail IMAP username/email")
    gmail_imap_pass: Optional[str] = Field(default=None, description="Gmail IMAP app password")
    
    # Runtime control settings
    dry_run: bool = Field(default=False, description="Run in dry mode without actually posting")
    force_run: bool = Field(default=False, description="Force run even if no new articles found")
    manual_run_only: bool = Field(default=True, description="Require explicit confirmation to run")
    
    # Content filtering settings
    max_articles_total: int = Field(default=10, description="Maximum total articles to post per run")
    min_article_quality_score: float = Field(default=0.5, description="Minimum quality score for articles")
    
    # Optional OpenAI for advanced summarization
    openai_api_key: str = Field(default="", description="OpenAI API key (optional)")
    
    # Request settings
    max_articles_per_source: int = Field(default=3, description="Maximum articles to fetch per RSS source")
    max_summary_tokens: int = Field(default=150, description="Maximum tokens for article summary")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Map environment variable names
        fields = {
            "telegram_bot_token": {"env": "TELEGRAM_BOT_TOKEN"},
            "telegram_chat_id": {"env": "TELEGRAM_CHAT_ID"},
            "gmail_imap_user": {"env": "GMAIL_IMAP_USER"},
            "gmail_imap_pass": {"env": "GMAIL_IMAP_PASS"},
            "dry_run": {"env": "DRY_RUN"},
            "force_run": {"env": "FORCE_RUN"},
            "manual_run_only": {"env": "MANUAL_RUN_ONLY"},
            "openai_api_key": {"env": "OPENAI_API_KEY"},
        }

def filter_articles(articles, settings):
    """
    Filter articles based on allowlist and blocklist keywords.
    Requires at least one allowlist keyword and zero blocklist matches.
    Prefers title over description weighting.
    UPDATED: Also checks URL patterns against blocklist for immediate exclusion.
    
    Args:
        articles: List of article dictionaries with 'title', 'description', and 'link' fields
        settings: Settings object with allowlist_keywords and blocklist_keywords
        
    Returns:
        List of filtered articles that meet the criteria
    """
    filtered_articles = []
    
    # Load blocklist patterns once for efficiency
    blocklist_patterns = load_blocklist()
    
    for article in articles:
        title = (article.get('title', '') or '').lower()
        description = (article.get('description', '') or '').lower()
        link = article.get('link', '') or ''
        
        # EARLY BLOCKLIST CHECK: Check URL patterns first (immediate exclusion)
        url_blocked = False
        for pattern in blocklist_patterns:
            if pattern.search(link):
                url_blocked = True
                break
        
        if url_blocked:
            continue
        
        # Check for blocklist keywords (immediate exclusion)
        has_blocked_content = False
        for blocked_word in settings.blocklist_keywords:
            if blocked_word.lower() in title or blocked_word.lower() in description:
                has_blocked_content = True
                break
        
        if has_blocked_content:
            continue
            
        # Check for allowlist keywords (must have at least one)
        has_allowed_content = False
        title_score = 0
        desc_score = 0
        
        for allowed_word in settings.allowlist_keywords:
            word_lower = allowed_word.lower()
            if word_lower in title:
                has_allowed_content = True
                title_score += 1
            elif word_lower in description:
                has_allowed_content = True
                desc_score += 1
                
        if has_allowed_content:
            # Calculate relevance score (title weighted higher than description)
            relevance_score = (title_score * 2) + desc_score
            article['relevance_score'] = relevance_score
            filtered_articles.append(article)
    
    # Sort by relevance score (title matches get priority)
    filtered_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return filtered_articles

# Create global settings instance
settings = Settings()

# Get the app directory path
APP_DIR = Path(__file__).parent
SOURCES_PATH = APP_DIR / settings.sources_file

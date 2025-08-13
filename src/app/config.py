"""Configuration settings for Telegram News Poster."""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings managed by Pydantic."""
    
    # Sources configuration
    sources_file: str = Field(default="sources.yaml", description="Path to sources YAML file")
    
    # Keyword filtering
    keywords: List[str] = Field(
        default=["AI", "artificial intelligence", "machine learning", "ML", "GPT", "LLM", 
                "XR", "virtual reality", "VR", "augmented reality", "AR", "mixed reality", "MR",
                "MusicTech", "music technology", "audio", "DAW", "VST", "plugin"],
        description="Keywords to filter news articles"
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
    
    # Runtime control settings - UPDATED TO PREVENT AUTO-RUN
    dry_run: bool = Field(default=True, description="Run in dry mode without actually posting")
    force_run: bool = Field(default=False, description="Force run even if no new articles found")
    manual_run_only: bool = Field(default=True, description="Require explicit confirmation to run")
    
    # Content filtering settings (NEW)
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

# Create global settings instance
settings = Settings()

# Get the app directory path
APP_DIR = Path(__file__).parent
SOURCES_PATH = APP_DIR / settings.sources_file

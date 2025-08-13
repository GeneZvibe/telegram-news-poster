"""Configuration settings for Telegram News Poster."""
import os
from pathlib import Path
from typing import List
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
    
    # Optional OpenAI for advanced summarization (placeholder for future use)
    openai_api_key: str = Field(default="", description="OpenAI API key (optional)")
    
    # Request settings
    max_articles_per_source: int = Field(default=5, description="Maximum articles to fetch per RSS source")
    max_summary_tokens: int = Field(default=150, description="Maximum tokens for article summary")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Map environment variable names
        fields = {
            "telegram_bot_token": {"env": "TELEGRAM_BOT_TOKEN"},
            "telegram_chat_id": {"env": "TELEGRAM_CHAT_ID"},
            "openai_api_key": {"env": "OPENAI_API_KEY"},
        }

# Create global settings instance
settings = Settings()

# Get the app directory path
APP_DIR = Path(__file__).parent
SOURCES_PATH = APP_DIR / settings.sources_file

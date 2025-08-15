"""Bot approval system for Telegram DM-based curation.

This module implements a Telegram bot for manual curation of news articles.
The bot sends articles to a designated user/channel for approval via DM,
allowing for approve/reject/edit actions before posting to the main channel.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Telegram bot imports
try:
    from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
except ImportError:
    print("Warning: python-telegram-bot not installed. Install with: pip install python-telegram-bot")
    Bot = Update = InlineKeyboardButton = InlineKeyboardMarkup = None
    Application = CommandHandler = CallbackQueryHandler = MessageHandler = filters = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ApprovalConfig:
    """Configuration for the approval bot."""
    # Telegram bot settings
    bot_token: str
    approval_user_id: Optional[int] = None  # User ID for approval DMs
    approval_channel_id: Optional[str] = None  # Channel ID for approval messages
    target_channel_id: str = ""  # Final posting channel
    
    # File paths
    pending_articles_file: str = "data/pending_articles.json"
    approval_log_file: str = "data/approval_log.jsonl"
    
    @classmethod
    def from_env(cls) -> 'ApprovalConfig':
        """Load configuration from environment variables."""
        return cls(
            bot_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            approval_user_id=int(os.getenv('APPROVAL_USER_ID', 0)) or None,
            approval_channel_id=os.getenv('APPROVAL_CHANNEL_ID'),
            target_channel_id=os.getenv('TELEGRAM_CHAT_ID', ''),
            pending_articles_file=os.getenv('PENDING_ARTICLES_FILE', 'data/pending_articles.json'),
            approval_log_file=os.getenv('APPROVAL_LOG_FILE', 'data/approval_log.jsonl')
        )


@dataclass
class PendingArticle:
    """Represents an article pending approval."""
    id: str
    title: str
    summary: str
    url: str
    source: str
    category: str
    timestamp: str
    message_id: Optional[int] = None  # Telegram message ID for tracking
    
    def to_telegram_message(self) -> str:
        """Format article for Telegram message."""
        return f"📰 **{self.title}**\n\n{self.summary}\n\n🔗 {self.url}\n\n📍 Source: {self.source} | Category: {self.category}"


class ArticleStore:
    """Manages pending articles storage."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
    def save_article(self, article: PendingArticle) -> None:
        """Save a pending article."""
        articles = self.load_all_articles()
        articles[article.id] = asdict(article)
        
        with open(self.file_path, 'w') as f:
            json.dump(articles, f, indent=2)
            
    def load_article(self, article_id: str) -> Optional[PendingArticle]:
        """Load a specific article by ID."""
        articles = self.load_all_articles()
        if article_id in articles:
            return PendingArticle(**articles[article_id])
        return None
        
    def load_all_articles(self) -> Dict[str, Dict[str, Any]]:
        """Load all pending articles."""
        if not self.file_path.exists():
            return {}
            
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
            
    def remove_article(self, article_id: str) -> None:
        """Remove an article from pending list."""
        articles = self.load_all_articles()
        if article_id in articles:
            del articles[article_id]
            with open(self.file_path, 'w') as f:
                json.dump(articles, f, indent=2)


class CurationLogger:
    """Logs curation decisions for analysis."""
    
    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log_decision(self, article_id: str, action: str, user_id: int, 
                    article_data: Optional[Dict] = None, notes: str = "") -> None:
        """Log a curation decision."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "article_id": article_id,
            "action": action,  # 'approved', 'rejected', 'edited'
            "user_id": user_id,
            "notes": notes,
            "article_data": article_data
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')


class TelegramApprovalHandler:
    """Handles Telegram DM-based approval workflow."""
    
    def __init__(self, config: ApprovalConfig):
        self.config = config
        self.store = ArticleStore(config.pending_articles_file)
        self.logger = CurationLogger(config.approval_log_file)
        self.bot = None
        
    async def initialize_bot(self) -> None:
        """Initialize the Telegram bot."""
        if not Bot:
            raise ImportError("python-telegram-bot not installed")
            
        self.bot = Bot(token=self.config.bot_token)
        
    def create_approval_keyboard(self, article_id: str) -> InlineKeyboardMarkup:
        """Create inline keyboard for article approval."""
        if not InlineKeyboardButton or not InlineKeyboardMarkup:
            raise ImportError("python-telegram-bot not installed")
            
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{article_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{article_id}")
            ],
            [
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{article_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
        
    async def send_for_approval(self, article: PendingArticle) -> bool:
        """Send article to approval user/channel."""
        if not self.bot:
            await self.initialize_bot()
            
        target_id = self.config.approval_user_id or self.config.approval_channel_id
        if not target_id:
            logger.error("No approval target configured")
            return False
            
        try:
            keyboard = self.create_approval_keyboard(article.id)
            message = await self.bot.send_message(
                chat_id=target_id,
                text=article.to_telegram_message(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            # Update article with message ID for tracking
            article.message_id = message.message_id
            self.store.save_article(article)
            
            logger.info(f"Sent article {article.id} for approval")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send article for approval: {e}")
            return False
            
    async def handle_approval_callback(self, update: Update, context) -> None:
        """Handle approval/rejection callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        action, article_id = data.split('_', 1)
        
        article = self.store.load_article(article_id)
        if not article:
            await query.edit_message_text("❌ Article not found")
            return
            
        if action == "approve":
            await self._handle_approve(query, article)
        elif action == "reject":
            await self._handle_reject(query, article)
        elif action == "edit":
            await self._handle_edit_request(query, article)
            
    async def _handle_approve(self, query, article: PendingArticle) -> None:
        """Handle article approval."""
        # TODO: Implement posting to target channel
        # For now, just log the approval
        self.logger.log_decision(
            article.id, "approved", query.from_user.id, 
            asdict(article)
        )
        
        self.store.remove_article(article.id)
        await query.edit_message_text(
            f"✅ **APPROVED**\n\n{article.to_telegram_message()}",
            parse_mode='Markdown'
        )
        
    async def _handle_reject(self, query, article: PendingArticle) -> None:
        """Handle article rejection."""
        self.logger.log_decision(
            article.id, "rejected", query.from_user.id,
            asdict(article)
        )
        
        self.store.remove_article(article.id)
        await query.edit_message_text(
            f"❌ **REJECTED**\n\n{article.to_telegram_message()}",
            parse_mode='Markdown'
        )
        
    async def _handle_edit_request(self, query, article: PendingArticle) -> None:
        """Handle edit request - placeholder for future implementation."""
        await query.edit_message_text(
            f"✏️ **EDIT REQUESTED**\n\n{article.to_telegram_message()}\n\n*Edit functionality coming soon...*",
            parse_mode='Markdown'
        )


class ManualPostIntake:
    """Handles manual submission of articles for approval."""
    
    def __init__(self, config: ApprovalConfig):
        self.config = config
        self.store = ArticleStore(config.pending_articles_file)
        
    def submit_article(self, title: str, summary: str, url: str, 
                      source: str = "Manual", category: str = "Manual") -> str:
        """Submit an article for manual approval."""
        article_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        article = PendingArticle(
            id=article_id,
            title=title,
            summary=summary,
            url=url,
            source=source,
            category=category,
            timestamp=datetime.now().isoformat()
        )
        
        self.store.save_article(article)
        logger.info(f"Manually submitted article: {article_id}")
        return article_id


def main():
    """Main function for approval bot."""
    # Load configuration
    config = ApprovalConfig.from_env()
    
    if not config.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured")
        return
        
    logger.info("Starting approval bot...")
    
    # Initialize components
    handler = TelegramApprovalHandler(config)
    intake = ManualPostIntake(config)
    
    # Example usage - this would be replaced with actual bot application setup
    logger.info("Approval bot components initialized")
    logger.info(f"Pending articles file: {config.pending_articles_file}")
    logger.info(f"Approval log file: {config.approval_log_file}")
    
    # TODO: Set up Telegram bot application with handlers
    # app = Application.builder().token(config.bot_token).build()
    # app.add_handler(CallbackQueryHandler(handler.handle_approval_callback))
    # app.run_polling()
    
    print("Approval bot scaffolding complete - ready for integration")


if __name__ == "__main__":
    main()

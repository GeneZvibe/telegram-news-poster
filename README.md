# Telegram News Poster

An automated news aggregation system that fetches RSS feeds, filters for relevant tech topics (AI, MusicTech, XR), summarizes articles, and posts them to a Telegram channel.

## Features

🤖 **AI-Powered**: Filters news on AI, Machine Learning, and GPT developments  
🎵 **MusicTech Focus**: Covers music production tools, DAWs, plugins, and audio technology  
🥽 **XR Coverage**: Virtual Reality, Augmented Reality, and Mixed Reality news  
📰 **Smart Summarization**: Generates concise TL;DR summaries for each article  
🔄 **Deduplication**: Prevents posting duplicate articles  
⏰ **Automated Scheduling**: Runs daily at 12:00 PM ET (configurable timezone)  
🚀 **Manual Triggers**: Support for manual runs and testing via GitHub Actions  

## Repository Structure

```
telegram-news-poster/
├── .github/workflows/          # GitHub Actions workflows
│   ├── schedule.yml           # Daily scheduled runs at 15:55 UTC
│   └── manual.yml            # Manual workflow dispatch
├── src/app/                  # Main application code
│   ├── __init__.py          # Package initialization
│   ├── main.py              # Core application logic
│   ├── config.py            # Configuration settings
│   ├── utils.py             # Utility functions
│   ├── summarize.py         # Text summarization module
│   └── sources.yaml         # RSS feed sources configuration
├── requirements.txt          # Python dependencies
├── pyproject.toml           # Project metadata
└── README.md               # This file
```

## Setup Instructions

### 1. Prerequisites

- A Telegram bot token (create via [@BotFather](https://t.me/botfather))
- Telegram channel or chat ID where the bot has posting permissions
- GitHub repository with Actions enabled

### 2. Configure GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Target channel/chat ID (use `@username` for public channels)

### 3. Customize News Sources

Edit `src/app/sources.yaml` to add/remove RSS feeds:

```yaml
sources:
  ai:
    - name: "Your AI News Source"
      url: "https://example.com/ai-news/feed"
      description: "AI industry news"
  musictech:
    - name: "Your Music Tech Source"
      url: "https://example.com/musictech/feed"
      description: "Music production news"
  xr:
    - name: "Your XR Source"
      url: "https://example.com/xr/feed"
      description: "VR/AR news"
```

### 4. Modify Keywords (Optional)

Update the keyword filters in `src/app/config.py`:

```python
keywords: List[str] = Field(
    default=[
        "AI", "artificial intelligence", "machine learning", "ML", "GPT", "LLM",
        "XR", "virtual reality", "VR", "augmented reality", "AR", "mixed reality", "MR",
        "MusicTech", "music technology", "audio", "DAW", "VST", "plugin"
        # Add your custom keywords here
    ]
)
```

## Usage

### Automatic Posting

The system automatically runs daily at 15:55 UTC (11:55 AM ET standard time) via GitHub Actions. The schedule can be modified in `.github/workflows/schedule.yml`.

### Manual Execution

#### Via GitHub Actions

1. Go to the Actions tab in your GitHub repository
2. Select "News Poster - Manual Run"
3. Click "Run workflow"
4. Configure options:
   - **dry_run**: Set to true to test without posting
   - **force_run**: Set to true to run even if no new articles

#### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-bot-token"
   export TELEGRAM_CHAT_ID="your-chat-id"
   export DRY_RUN="true"  # Optional: prevents actual posting
   ```

3. Run the application:
   ```bash
   python -m src.app.main
   ```

### Testing

1. **Dry Run Mode**: Set `DRY_RUN=true` to test without posting to Telegram
2. **Manual Testing**: Use the manual workflow with `dry_run: true`
3. **Check Logs**: Monitor GitHub Actions logs for debugging

## Configuration Options

| Environment Variable | Description | Default |
|----------------------|-------------|----------|
| TELEGRAM_BOT_TOKEN | Telegram bot token | Required |
| TELEGRAM_CHAT_ID | Target chat/channel ID | Required |
| DRY_RUN | Test mode (no posting) | false |
| FORCE_RUN | Run even without new articles | false |
| OPENAI_API_KEY | OpenAI API key (optional) | Empty |

## Workflow Details

### Scheduled Workflow (.github/workflows/schedule.yml)

• **Trigger**: Daily at 15:55 UTC  
• **Features**: Automatic run with dry_run support  
• **Environment**: Uses repository secrets for tokens  

### Manual Workflow (.github/workflows/manual.yml)

• **Trigger**: Manual workflow dispatch  
• **Options**:  
  - **dry_run** (boolean): Test without posting  
  - **force_run** (boolean): Run even without new articles  

## How It Works

1. **Fetch**: Downloads RSS feeds from configured sources
2. **Filter**: Applies keyword matching for relevant topics
3. **Summarize**: Creates TL;DR summaries using extractive summarization
4. **Deduplicate**: Prevents reposting recent articles
5. **Format**: Composes Telegram messages with emojis and categories
6. **Post**: Sends individual messages for each news item to Telegram

## Message Format

Each news post follows this format:

```
📰 **Daily Tech News - August 13, 2025**

🤖 **AI**
• *OpenAI Releases New GPT Model*
  TL;DR: Major performance improvements in reasoning...
  🔗 [Read more](https://example.com/article)

🎵 **MusicTech** 
• *New DAW Plugin Revolutionizes Audio*
  TL;DR: Innovative effects processing for producers...
  🔗 [Read more](https://example.com/article)

---
📱 *Powered by @GeneFrankelBot*
```

## Troubleshooting

### Common Issues

1. **No articles posted**: Check if sources are returning recent articles
2. **Authentication errors**: Verify bot token and chat ID are correct
3. **Permission errors**: Ensure bot is added to channel with posting rights
4. **Workflow failures**: Check GitHub Actions logs for detailed error messages

### Debug Commands

```bash
# Test RSS feed parsing
python -c "import feedparser; print(feedparser.parse('YOUR_FEED_URL'))"

# Validate environment variables
echo $TELEGRAM_BOT_TOKEN | cut -c1-10
echo $TELEGRAM_CHAT_ID

# Test bot permissions
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Changelog

### August 13, 2025

**🔧 Technical Improvements**
- Added Gmail UNSEEN sync for last 2 days with tech-only filtering
- Enhanced URL validation with real-time link verification during compose
- Expanded blocklist with newsletter/redirect trackers (SendGrid, Mailchimp, SparkPost)
- Updated schedule: 3x daily runs at 8am/2pm/8pm ET (replacing single daily run)

**⚙️ Configuration Updates**
- DRY_RUN now defaults to `false` (was `true`)
- FORCE_RUN defaults to `false`, set to `true` for manual override
- Manual workflow triggers available via GitHub Actions interface

## Maintainer Notes

### For Future Contributors

**Configuration Locations:**
- RSS sources: `src/app/sources.yaml`
- Keyword filters: `src/app/config.py` (keywords field)
- Schedule timing: `.github/workflows/schedule.yml` (cron expression)
- Environment defaults: `src/app/config.py`

**Schedule Management:**
- Current: 3x daily at `12:00`, `18:00`, `00:00` UTC (8am/2pm/8pm ET)
- Modify cron in `.github/workflows/schedule.yml`
- Use [crontab.guru](https://crontab.guru) for cron expression help

**Managing Blocked Domains/Keywords:**
- Blocklist: `src/app/utils.py` (BLOCKED_DOMAINS, BLOCKED_KEYWORDS)
- Add domains: append to `BLOCKED_DOMAINS` list
- Add keywords: append to `BLOCKED_KEYWORDS` list
- Test changes with DRY_RUN=true

**Tech-First Content Filtering:**
- **Allowlist System**: Articles must contain at least one keyword from `allowlist_keywords` in `src/app/config.py`
- **Gaming/Entertainment Exclusions**: Articles containing any `blocklist_keywords` are automatically excluded
- **Title Preference**: Matches in article titles are weighted 2x higher than description matches
- **Current Allowlist**: AI/ML, XR/VR/AR, research terms, development tools, audio tech, hardware terms
- **Current Blocklist**: Gaming reviews, walkthroughs, esports, console-specific content, game merchandising
- **Filter Function**: `filter_articles()` in `config.py` implements the dual-filter logic with relevance scoring
- **Customization**: Modify `allowlist_keywords` and `blocklist_keywords` lists in Settings class

**Local Development:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export DRY_RUN="true"  # Prevents actual posting

# Run locally
python -m src.app.main
```

**Troubleshooting:**
- **Feed issues**: Check RSS feed validity and network connectivity
- **Gmail sync**: Verify GMAIL_CREDENTIALS and IMAP permissions
- **Rate limits**: Telegram allows ~30 messages/minute, adjust delays in `main.py`
- **Memory**: Large feed processing may need workflow timeout adjustment
- **Debugging**: Enable verbose logging in `src/app/config.py`

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

For issues and questions:
- Create a GitHub issue
- Check the Actions logs for error details
- Verify your configuration matches the examples above

---
**Happy news aggregating! 🚀📰**

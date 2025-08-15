# Telegram News Poster

🧪 **Testing Edit Capability** - This line added by Comet Assistant for testing purposes

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

- **TELEGRAM_BOT_TOKEN**: Your Telegram bot token
- **TELEGRAM_CHAT_ID**: Target channel/chat ID (use @username for public channels)

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

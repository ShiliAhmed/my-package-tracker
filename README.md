# My Package Tracker - Telegram Bot

This repository contains a simple package tracker originally written as `AliExpress.py` and extended with a Telegram bot wrapper in `telegram_bot.py` so you can check package status from your phone.

## Quick start

1. Create a Telegram bot and get its token from BotFather.
2. Put the token in an environment variable named `TELEGRAM_BOT_TOKEN` or create a file named `telegram_token.txt` with the token as plaintext in the project root.
3. Install dependencies (preferably in a virtualenv):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

4. Run the bot:

```powershell
python telegram_bot.py
```

## Commands

- `/start` - Start the bot and see interactive buttons
- `/checkall` - Check all packages from `package_list.json` (may take a while)
- `/check <TRACKING>` - Check one specific tracking number

## Features

- ✅ **Interactive buttons** - Quick actions without typing commands
- ✅ **Copyable tracking numbers** - Tap to copy any tracking number
- ✅ **Mobile-friendly output** - Optimized for phone screens
- ✅ **Auto-refresh** - Check packages again with one button press
- ✅ **Help system** - Built-in help with navigation

## Deploy to Cloud (Free Options)

Want to run your bot 24/7 in the cloud? Check out **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** for:
- **Railway.app** (Recommended - Easiest setup) ⚡ **Native uv support**
- **Render.com** (Great for 24/7 bots)
- **Fly.io** (Most powerful free tier)
- And more!

All platforms offer free tiers perfect for personal use!

**💡 Bonus:** This project uses [uv](https://docs.astral.sh/uv/) for ultra-fast builds! See **[UV_WITH_RAILWAY.md](UV_WITH_RAILWAY.md)**.

## Notes

- The bot calls the same scraping logic as `AliExpress.py`. Scraping may be rate-limited by the target site.
- Desktop version still works - original `fetch_package_updates` function preserved for computer use.
- Mobile version uses `create_mobile_output` for better phone readability.

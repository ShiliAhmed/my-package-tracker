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

Commands:
- /start - greet the bot
- /checkall - check all packages from `package_list.json` (may take a while)
- /check <TRACKING> - check one tracking number

Notes:
- The bot calls the same scraping logic as `AliExpress.py`. Scraping may be rate-limited by the target site.
- This setup is suitable for personal use. To keep it running 24/7 you can deploy to a free cloud VM or use a free tier hosting provider.

import os
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
load_dotenv()

from AliExpress import fetch_package_updates, load_packages_from_file

# Basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# Fallback to token file if env var not set
if not TOKEN:
    token_path = Path("telegram_token.txt")
    if token_path.exists():
        TOKEN = token_path.read_text().strip()

if not TOKEN:
    raise RuntimeError("Telegram bot token not found. Set TELEGRAM_BOT_TOKEN or create telegram_token.txt")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm your package tracker bot. Use /checkall to check all packages or /check <TRACKING> to check one."
    )

async def checkall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking all packages, this may take a while...")
    packages = load_packages_from_file()
    with_update, no_update, log_output = fetch_package_updates(packages, show_only_updates=True)
    
    # Send the formatted log output directly
    final = "\n".join(log_output)
    for chunk in [final[i:i+3500] for i in range(0, len(final), 3500)]:
        await update.message.reply_text(chunk)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <TRACKING_NUMBER>")
        return
    tracking = context.args[0]
    await update.message.reply_text(f"Checking {tracking}...")
    packages = [{"package_number": tracking, "package orders": []}]
    with_update, no_update, log_output = fetch_package_updates(packages, show_only_updates=False)
    
    # Send the formatted log output directly
    final = "\n".join(log_output)
    for chunk in [final[i:i+3500] for i in range(0, len(final), 3500)]:
        await update.message.reply_text(chunk)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkall", checkall))
    app.add_handler(CommandHandler("check", check))

    print("Bot started. Press Ctrl-C to stop.")
    app.run_polling()


if __name__ == '__main__':
    main()

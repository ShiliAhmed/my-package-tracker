import os
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
load_dotenv()

from AliExpress import fetch_package_updates, create_mobile_output, load_packages_from_file

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
    keyboard = [
        [InlineKeyboardButton("🔄 Check All Packages", callback_data='checkall')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📦 **Welcome to Package Tracker Bot!**\n\n"
        "Use the buttons below for quick actions or commands:\n"
        "• `/checkall` - Check all packages\n"
        "• `/check <TRACKING>` - Check specific package",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def checkall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Checking all packages, this may take a while...")
    try:
        packages = load_packages_from_file()
        logger.info(f"Loaded {len(packages)} packages")
        with_update, no_update, mobile_output = create_mobile_output(packages, show_only_updates=True)
    except Exception as e:
        logger.error(f"Error in checkall: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return
    
    # Format package numbers for easy copying (wrap in backticks for monospace)
    formatted_output = []
    for line in mobile_output:
        # Replace package tracking numbers with code-formatted versions
        if '┌─' in line and any(char.isdigit() or char.isupper() for char in line):
            # Extract tracking number and wrap in backticks
            tracking_num = line.split('┌─')[1].strip().split()[0] if '┌─' in line else None
            if tracking_num:
                line = line.replace(tracking_num, f'`{tracking_num}`')
        formatted_output.append(line)
    
    # Send the mobile-friendly formatted output
    final = "\n".join(formatted_output)
    
    # Send messages with refresh button on last chunk
    chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
    for idx, chunk in enumerate(chunks):
        if idx == len(chunks) - 1:
            # Add refresh button to last message
            keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='checkall')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(chunk, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(chunk, parse_mode='Markdown')

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <TRACKING_NUMBER>")
        return
    tracking = context.args[0]
    await update.message.reply_text(f"🔍 Checking `{tracking}`...", parse_mode='Markdown')
    packages = [{"package_number": tracking, "package orders": []}]
    with_update, no_update, mobile_output = create_mobile_output(packages, show_only_updates=False)
    
    # Format package numbers for easy copying
    formatted_output = []
    for line in mobile_output:
        if '┌─' in line:
            tracking_num = line.split('┌─')[1].strip().split()[0] if '┌─' in line else None
            if tracking_num:
                line = line.replace(tracking_num, f'`{tracking_num}`')
        formatted_output.append(line)
    
    # Send the mobile-friendly formatted output
    final = "\n".join(formatted_output)
    
    chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
    for idx, chunk in enumerate(chunks):
        if idx == len(chunks) - 1:
            # Add refresh button to last message
            keyboard = [[InlineKeyboardButton("🔄 Check Again", callback_data=f'check_{tracking}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(chunk, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(chunk, parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    if query.data == 'checkall':
        # Simulate the checkall command
        await query.message.reply_text("🔍 Checking all packages, this may take a while...")
        packages = load_packages_from_file()
        with_update, no_update, mobile_output = create_mobile_output(packages, show_only_updates=True)
        
        # Format package numbers for easy copying
        formatted_output = []
        for line in mobile_output:
            if '┌─' in line:
                tracking_num = line.split('┌─')[1].strip().split()[0] if '┌─' in line else None
                if tracking_num:
                    line = line.replace(tracking_num, f'`{tracking_num}`')
            formatted_output.append(line)
        
        final = "\n".join(formatted_output)
        chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
        for idx, chunk in enumerate(chunks):
            if idx == len(chunks) - 1:
                keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='checkall')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(chunk, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await query.message.reply_text(chunk, parse_mode='Markdown')
    
    elif query.data == 'help':
        help_text = (
            "📦 **Package Tracker Bot - Help**\n\n"
            "**Commands:**\n"
            "• `/start` - Start the bot and see quick actions\n"
            "• `/checkall` - Check all packages in your list\n"
            "• `/check <TRACKING>` - Check a specific package\n\n"
            "**Quick Actions:**\n"
            "• Use the 🔄 Refresh button to check again\n"
            "• Tap any tracking number to copy it\n"
            "• All buttons are available throughout the bot\n"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'back':
        # Return to start screen
        keyboard = [
            [InlineKeyboardButton("🔄 Check All Packages", callback_data='checkall')],
            [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📦 **Welcome to Package Tracker Bot!**\n\n"
            "Use the buttons below for quick actions or commands:\n"
            "• `/checkall` - Check all packages\n"
            "• `/check <TRACKING>` - Check specific package",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('check_'):
        # Handle individual package check from callback
        tracking = query.data.replace('check_', '')
        await query.message.reply_text(f"🔍 Checking `{tracking}`...", parse_mode='Markdown')
        packages = [{"package_number": tracking, "package orders": []}]
        with_update, no_update, mobile_output = create_mobile_output(packages, show_only_updates=False)
        
        # Format package numbers for easy copying
        formatted_output = []
        for line in mobile_output:
            if '┌─' in line:
                tracking_num = line.split('┌─')[1].strip().split()[0] if '┌─' in line else None
                if tracking_num:
                    line = line.replace(tracking_num, f'`{tracking_num}`')
            formatted_output.append(line)
        
        final = "\n".join(formatted_output)
        chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
        for idx, chunk in enumerate(chunks):
            if idx == len(chunks) - 1:
                keyboard = [[InlineKeyboardButton("🔄 Check Again", callback_data=f'check_{tracking}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(chunk, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await query.message.reply_text(chunk, parse_mode='Markdown')


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkall", checkall))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started. Press Ctrl-C to stop.")
    app.run_polling()


if __name__ == '__main__':
    main()

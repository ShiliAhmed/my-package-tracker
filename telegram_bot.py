import os
import logging
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
load_dotenv()

from AliExpress import fetch_package_updates, create_mobile_output, load_packages_from_file, fetch_single_package
from single_package_formatter import format_single_package_detail

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages - greetings or any other text"""
    text = update.message.text.lower() if update.message.text else ""
    
    # Greetings list
    greetings = ['hi', 'hello', 'hey', 'hey there', 'hi there', 'greetings', 'salut', 'bonjour', 'مرحبا']
    
    # Check if it's a greeting
    is_greeting = any(greeting in text for greeting in greetings)
    
    # Send start message for greetings or any other text
    keyboard = [
        [InlineKeyboardButton("🔄 Check All Packages", callback_data='checkall')],
        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_greeting:
        message = "👋 **Hi there!**\n\n📦 **Welcome to Package Tracker Bot!**\n\nUse the buttons below for quick actions or commands:\n• `/checkall` - Check all packages\n• `/check <TRACKING>` - Check specific package"
    else:
        message = "📦 **Welcome to Package Tracker Bot!**\n\nUse the buttons below for quick actions or commands:\n• `/checkall` - Check all packages\n• `/check <TRACKING>` - Check specific package"
    
    await update.message.reply_text(
        message,
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
    
    # Extract tracking numbers ONLY from packages with updates AND not delivered (exclude no-update and delivered packages)
    tracking_numbers = []
    for pkg in with_update:
        # Skip delivered packages
        if pkg.get("delivered", False):
            continue
        tracking_num = pkg.get("package_number")
        if tracking_num:
            tracking_numbers.append(tracking_num)
    
    # Format output text with backticks for tracking numbers
    formatted_output = []
    for line in mobile_output:
        # Extract tracking numbers and wrap in backticks
        if '┌─' in line:
            parts = line.split('┌─')
            if len(parts) > 1:
                tracking_num = parts[1].strip().split()[0]
                if tracking_num and any(c.isalnum() for c in tracking_num):
                    # Only format if it's in our tracking_numbers list (has updates)
                    if tracking_num in tracking_numbers:
                        line = line.replace(tracking_num, f'`{tracking_num}`')
        formatted_output.append(line)
    
    # Send the mobile-friendly formatted output
    final = "\n".join(formatted_output)
    
    # Create buttons ONLY for packages with updates (max 100 buttons per message)
    tracking_buttons = []
    for tn in tracking_numbers[:99]:  # Telegram limit is 100 buttons
        tracking_buttons.append([InlineKeyboardButton(f"📦 {tn}", callback_data=f"confirm_check_{tn}")])
    
    # Send messages with buttons on last chunk
    chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
    for idx, chunk in enumerate(chunks):
        if idx == len(chunks) - 1:
            # Add tracking buttons and refresh button
            keyboard = tracking_buttons + [[InlineKeyboardButton("🔄 Refresh", callback_data='checkall')]]
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
    
    try:
        # Try to find package in list to get orders
        packages = load_packages_from_file()
        package_orders = []
        for pkg in packages:
            if pkg.get("package_number") == tracking or tracking in pkg.get("package_number", ""):
                package_orders = pkg.get("package orders", [])
                break
        
        # Fetch single package with full details
        package_result = fetch_single_package(tracking, package_orders)
        
        if not package_result:
            await update.message.reply_text(f"❌ No updates found for `{tracking}`", parse_mode='Markdown')
            return
        
        # Format detailed output
        detailed_output = format_single_package_detail(package_result)
        final = "\n".join(detailed_output)
        
        # Send in chunks if needed
        chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
        for idx, chunk in enumerate(chunks):
            if idx == len(chunks) - 1:
                keyboard = [
                    [InlineKeyboardButton("🔄 Check Again", callback_data=f'check_{tracking}')],
                    [InlineKeyboardButton("📦 Check All", callback_data='checkall')]
                    [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(chunk, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text(chunk, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in check: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    
    if query.data == 'checkall':
        # Simulate the checkall command
        await query.message.reply_text("🔍 Checking all packages, this may take a while...")
        packages = load_packages_from_file()
        with_update, no_update, mobile_output = create_mobile_output(packages, show_only_updates=True)
        
        # Extract tracking numbers ONLY from packages with updates AND not delivered (exclude no-update and delivered packages)
        tracking_numbers = []
        for pkg in with_update:
            # Skip delivered packages
            if pkg.get("delivered", False):
                continue
            tracking_num = pkg.get("package_number")
            if tracking_num:
                tracking_numbers.append(tracking_num)
        
        # Format output text with backticks for tracking numbers
        formatted_output = []
        for line in mobile_output:
            if '┌─' in line:
                parts = line.split('┌─')
                if len(parts) > 1:
                    tracking_num = parts[1].strip().split()[0]
                    if tracking_num and any(c.isalnum() for c in tracking_num):
                        # Only format if it's in our tracking_numbers list (has updates)
                        if tracking_num in tracking_numbers:
                            line = line.replace(tracking_num, f'`{tracking_num}`')
            formatted_output.append(line)
        
        final = "\n".join(formatted_output)
        # Create buttons ONLY for packages with updates
        tracking_buttons = []
        for tn in tracking_numbers[:99]:
            tracking_buttons.append([InlineKeyboardButton(f"📦 {tn}", callback_data=f"confirm_check_{tn}")])
        
        chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
        for idx, chunk in enumerate(chunks):
            if idx == len(chunks) - 1:
                keyboard = tracking_buttons + [[InlineKeyboardButton("🔄 Refresh", callback_data='checkall')]]
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
    
    elif query.data.startswith('confirm_check_'):
        # Show confirmation with Yes/No buttons as a NEW message
        tracking = query.data.replace('confirm_check_', '')
        await query.answer()  # Acknowledge the button click
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=f'check_{tracking}'),
                InlineKeyboardButton("❌ No", callback_data='cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        # Send as new message, don't edit the original
        await query.message.reply_text(
            f"Do you want to check package `{tracking}`?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'cancel':
        await query.answer("Cancelled")
        # Don't edit, just acknowledge
    
    elif query.data.startswith('check_'):
        # Handle individual package check from callback
        tracking = query.data.replace('check_', '')
        await query.answer()
        await query.message.reply_text(f"🔍 Checking `{tracking}`...", parse_mode='Markdown')
        
        try:
            # Try to find package in list to get orders
            packages = load_packages_from_file()
            package_orders = []
            for pkg in packages:
                if pkg.get("package_number") == tracking or tracking in pkg.get("package_number", ""):
                    package_orders = pkg.get("package orders", [])
                    break
            
            # Fetch single package with full details
            package_result = fetch_single_package(tracking, package_orders)
            
            if not package_result:
                await query.message.reply_text(f"❌ No updates found for `{tracking}`", parse_mode='Markdown')
                return
            
            # Format detailed output
            detailed_output = format_single_package_detail(package_result)
            final = "\n".join(detailed_output)
            
            # Send in chunks if needed (always as new message)
            chunks = [final[i:i+3500] for i in range(0, len(final), 3500)]
            for idx, chunk in enumerate(chunks):
                if idx == len(chunks) - 1:
                    keyboard = [
                        [InlineKeyboardButton("🔄 Check Again", callback_data=f'check_{tracking}')],
                        [InlineKeyboardButton("📦 Check All", callback_data='checkall')],
                        [InlineKeyboardButton("ℹ️ Help", callback_data='help')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.reply_text(chunk, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await query.message.reply_text(chunk, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in check callback: {e}", exc_info=True)
            await query.message.reply_text(f"❌ Error: {str(e)}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkall", checkall))
    app.add_handler(CommandHandler("check", check))
    app.add_handler(CallbackQueryHandler(button_handler))
    # Handle text messages (greetings and any other text) - must be after command handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # For cloud deployment, use polling with drop_pending_updates
    logger.info("Bot starting...")
    print("Bot started. Press Ctrl-C to stop.")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

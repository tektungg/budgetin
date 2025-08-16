"""
Bot initialization and setup for the Budgetin Telegram bot.
Handles command registration, error handling, and bot lifecycle.
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context):
    """Enhanced global error handler with timeout handling"""
    error_msg = str(context.error)
    
    # Log the error with more details
    logger.error(f"Exception while handling update: {context.error}")
    
    # Handle different types of errors
    if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
        logger.warning("Timeout error detected - user may need to retry")
        
        # Try to send a helpful message to user if possible
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⏰ *Operasi timeout*\n\n"
                         "Proses memakan waktu lebih lama dari biasanya. "
                         "Silakan coba lagi dalam beberapa saat.\n\n"
                         "💡 *Tips:*\n"
                         "• Pastikan koneksi internet stabil\n"
                         "• Tunggu 1-2 menit lalu coba lagi\n"
                         "• Jika masalah berlanjut, gunakan /help",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send timeout message: {e}")
    
    elif "rate" in error_msg.lower() or "quota" in error_msg.lower():
        logger.warning("Rate limit or quota error detected")
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ *Google API sedang sibuk*\n\n"
                         "Terlalu banyak permintaan dalam waktu singkat. "
                         "Silakan tunggu 1-2 menit lalu coba lagi.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send rate limit message: {e}")
    
    elif "network" in error_msg.lower() or "connection" in error_msg.lower():
        logger.warning("Network connection error detected")
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🌐 *Masalah koneksi*\n\n"
                         "Terjadi masalah koneksi jaringan. "
                         "Pastikan internet stabil dan coba lagi.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send network error message: {e}")
    
    else:
        # Generic error
        logger.error(f"Unhandled error type: {context.error}")
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ *Terjadi kesalahan*\n\n"
                         "Silakan coba lagi. Jika masalah berlanjut, "
                         "gunakan /help untuk bantuan.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send generic error message: {e}")


def create_handler_wrappers(expense_tracker):
    """Create handler wrapper functions"""
    from handlers.command_handlers import (
        start, help_command, summary_command, categories_command, sheet, balance_command
    )
    from handlers.auth_handlers import login, logout
    from handlers.expense_handlers import handle_expense, button_callback
    from handlers.budget_handlers import (
        budget_command, insights_command, alerts_command, 
        budget_callback_handler, handle_budget_input
    )
    
    # Command wrappers
    async def start_wrapper(update: Update, context):
        await start(update, context, expense_tracker)

    async def help_wrapper(update: Update, context):
        await help_command(update, context, expense_tracker)

    async def login_wrapper(update: Update, context):
        await login(update, context, expense_tracker)

    async def logout_wrapper(update: Update, context):
        await logout(update, context, expense_tracker)

    async def expense_wrapper(update: Update, context):
        await handle_expense(update, context, expense_tracker)

    async def button_wrapper(update: Update, context):
        await button_callback(update, context, expense_tracker)

    async def summary_wrapper(update: Update, context):
        await summary_command(update, context, expense_tracker)

    async def balance_wrapper(update: Update, context):
        await balance_command(update, context, expense_tracker)

    async def sheet_wrapper(update: Update, context):
        await sheet(update, context, expense_tracker)

    async def budget_wrapper(update: Update, context):
        await budget_command(update, context)

    async def insights_wrapper(update: Update, context):
        await insights_command(update, context)

    async def alerts_wrapper(update: Update, context):
        await alerts_command(update, context)

    async def categories_wrapper(update: Update, context):
        await categories_command(update, context, expense_tracker)

    # Combined handlers
    async def budget_input_wrapper(update: Update, context):
        # Check if this is budget input
        if context.user_data.get('setting_budget_category'):
            await handle_budget_input(update, context)
        else:
            await expense_wrapper(update, context)
    
    async def combined_callback_wrapper(update: Update, context):
        query = update.callback_query
        if query.data.startswith(('budget_', 'insights_', 'alerts_', 'set_budget_', 'delete_budget_')):
            await budget_callback_handler(update, context)
        else:
            await button_wrapper(update, context)

    return {
        'start_wrapper': start_wrapper,
        'help_wrapper': help_wrapper,
        'login_wrapper': login_wrapper,
        'logout_wrapper': logout_wrapper,
        'expense_wrapper': expense_wrapper,
        'button_wrapper': button_wrapper,
        'summary_wrapper': summary_wrapper,
        'balance_wrapper': balance_wrapper,
        'sheet_wrapper': sheet_wrapper,
        'budget_wrapper': budget_wrapper,
        'insights_wrapper': insights_wrapper,
        'alerts_wrapper': alerts_wrapper,
        'categories_wrapper': categories_wrapper,
        'budget_input_wrapper': budget_input_wrapper,
        'combined_callback_wrapper': combined_callback_wrapper,
    }


async def initialize_bot(bot_token, expense_tracker):
    """Initialize and configure the Telegram bot"""
    try:
        # Create bot application
        application = Application.builder().token(bot_token).build()
        
        # Create handler wrappers
        handlers = create_handler_wrappers(expense_tracker)
        
        # Add command handlers
        application.add_handler(CommandHandler("start", handlers['start_wrapper']))
        application.add_handler(CommandHandler("help", handlers['help_wrapper']))
        application.add_handler(CommandHandler("login", handlers['login_wrapper']))
        application.add_handler(CommandHandler("logout", handlers['logout_wrapper']))
        application.add_handler(CommandHandler("ringkasan", handlers['summary_wrapper']))
        application.add_handler(CommandHandler("saldo", handlers['balance_wrapper']))
        application.add_handler(CommandHandler("sheet", handlers['sheet_wrapper']))
        application.add_handler(CommandHandler("budget", handlers['budget_wrapper']))
        application.add_handler(CommandHandler("insights", handlers['insights_wrapper']))
        application.add_handler(CommandHandler("alerts", handlers['alerts_wrapper']))
        application.add_handler(CommandHandler("kategori", handlers['categories_wrapper']))
        
        # Add message and callback handlers
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers['budget_input_wrapper']))
        application.add_handler(CallbackQueryHandler(handlers['combined_callback_wrapper']))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Initialize application
        await application.initialize()
        await application.start()
        
        logger.info("✅ Bot initialized successfully")
        return application
        
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        raise


def setup_bot_thread(bot_token, expense_tracker, application_callback):
    """Setup bot in separate thread"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize bot
        application = loop.run_until_complete(
            initialize_bot(bot_token, expense_tracker)
        )
        
        # Store application reference
        application_callback(application)
        
        logger.info("🤖 Bot thread started successfully")
        
        # Keep the thread alive
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"Bot thread error: {e}")
        raise

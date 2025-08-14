import os
import logging
import asyncio
import threading
import sys
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Local imports
from config import Config
from models.expense_tracker import ExpenseTracker
from handlers.command_handlers import (
    start, help_command, summary_command, categories_command, sheet, balance_command
)
from handlers.auth_handlers import login, logout
from handlers.expense_handlers import handle_expense, button_callback
from utils.config_validator import ConfigValidator
from utils.date_utils import get_jakarta_now
from datetime import datetime

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
flask_app = Flask(__name__)
bot_application = None
expense_tracker = ExpenseTracker()

@flask_app.route('/', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'service': 'Budgetin Bot',
            'version': '1.0.0',
            'timestamp': get_jakarta_now().isoformat(),
            'checks': {
                'bot_initialized': bot_application is not None,
                'config_valid': ConfigValidator.validate()[0],
                'active_users': len(expense_tracker.user_credentials) if expense_tracker else 0,
                'environment': {
                    'has_bot_token': bool(Config.BOT_TOKEN),
                    'has_google_oauth': bool(Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET),
                    'port': Config.PORT
                }
            }
        }
        
        # Check if all critical components are working
        all_healthy = all([
            health_status['checks']['bot_initialized'],
            health_status['checks']['config_valid']
        ])
        
        status_code = 200 if all_healthy else 503
        if not all_healthy:
            health_status['status'] = 'unhealthy'
        
        return health_status, status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }, 500

@flask_app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook"""
    if bot_application:
        try:
            update_data = request.get_json()
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(process_telegram_update(update_data), loop)
            else:
                loop.run_until_complete(process_telegram_update(update_data))
            return "OK", 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return "Error", 500
    return "Bot not initialized", 500

async def process_telegram_update(update_data):
    """Process Telegram update"""
    try:
        update = Update.de_json(update_data, bot_application.bot)
        await bot_application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")

# Wrapper functions to pass expense_tracker to handlers
async def start_wrapper(update: Update, context):
    await start(update, context, expense_tracker)

async def login_wrapper(update: Update, context):
    await login(update, context, expense_tracker)

async def logout_wrapper(update: Update, context):
    await logout(update, context, expense_tracker)

async def sheet_wrapper(update: Update, context):
    await sheet(update, context, expense_tracker)

async def summary_wrapper(update: Update, context):
    await summary_command(update, context, expense_tracker)

async def balance_wrapper(update: Update, context):
    await balance_command(update, context, expense_tracker)

async def expense_wrapper(update: Update, context):
    await handle_expense(update, context, expense_tracker)

async def button_wrapper(update: Update, context):
    await button_callback(update, context, expense_tracker)

async def error_handler(update: Update, context):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

async def setup_bot():
    """Setup bot application"""
    global bot_application
    
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is required")
        return None
    
    bot_application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Add command handlers
    bot_application.add_handler(CommandHandler("start", start_wrapper))
    bot_application.add_handler(CommandHandler("help", help_command))
    bot_application.add_handler(CommandHandler("login", login_wrapper))
    bot_application.add_handler(CommandHandler("logout", logout_wrapper))
    bot_application.add_handler(CommandHandler("sheet", sheet_wrapper))
    bot_application.add_handler(CommandHandler("ringkasan", summary_wrapper))
    bot_application.add_handler(CommandHandler("balance", balance_wrapper))
    bot_application.add_handler(CommandHandler("kategori", categories_command))
    
    # Add callback query handler for buttons
    bot_application.add_handler(CallbackQueryHandler(button_wrapper))
    
    # Handle text messages (expenses and OAuth codes)
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, expense_wrapper))
    
    # Add error handler
    bot_application.add_error_handler(error_handler)
    
    # Initialize bot
    await bot_application.initialize()
    
    # Set webhook
    webhook_url = get_webhook_url()
    await bot_application.bot.set_webhook(url=webhook_url)
    logger.info(f"Bot initialized with webhook: {webhook_url}")

    return bot_application

def get_webhook_url():
    """Get webhook URL based on environment"""
    if Config.PUBLIC_URL:
        return f"{Config.PUBLIC_URL}/{Config.BOT_TOKEN}"
    elif Config.NGROK_URL:
        return f"{Config.NGROK_URL}/{Config.BOT_TOKEN}"
    else:
        # Default to Render hostname
        hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-app-name.onrender.com')
        return f"https://{hostname}/{Config.BOT_TOKEN}"

def main():
    """Main function to run the bot with configuration validation"""
    
    # Validate configuration before starting
    print("🚀 Starting Budgetin Bot...")
    is_valid = ConfigValidator.print_status()
    
    if not is_valid:
        print("\n❌ Configuration validation failed. Please fix the errors above.")
        sys.exit(1)
    
    print("✅ Configuration validated successfully!")
    
    def setup_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup_bot())
            print("✅ Bot setup completed successfully!")
        except Exception as e:
            logger.error(f"Failed to setup bot: {e}")
            sys.exit(1)
    
    bot_thread = threading.Thread(target=setup_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Wait a bit for bot to initialize
    import time
    time.sleep(3)
    
    # Start Flask app
    try:
        print(f"🌐 Starting Flask server on port {Config.PORT}")
        flask_app.run(host='0.0.0.0', port=Config.PORT, debug=False)
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

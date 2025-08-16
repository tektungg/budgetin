"""
Budgetin Bot - Personal Finance Telegram Bot
Main application entry point

This is a clean, refactored version of the main application.
All major components have been separated into their respective modules:
- routes/ : Flask route handlers
- webhooks/ : Webhook processing and timeout handling
- bot/ : Bot initialization and command setup
- utils/ : Utilities and helper functions
"""

import threading
from flask import Flask

# Core imports
from config import Config
from models.expense_tracker import ExpenseTracker

# Component imports
from routes import register_routes
from webhooks import setup_webhook_handler
from bot import setup_bot_thread
from utils.app_utils import setup_logging, validate_environment, handle_startup_error
from utils.config_validator import ConfigValidator

# Setup logging
logger = setup_logging()

# Global variables
flask_app = Flask(__name__)
bot_application = None
expense_tracker = ExpenseTracker()


def set_bot_application(application):
    """Callback to set bot application reference"""
    global bot_application
    bot_application = application


def main():
    """Main application entry point"""
    try:
        logger.info("🚀 Starting Budgetin Bot...")
        
        # Validate environment and configuration
        validate_environment()
        
        # Validate configuration with detailed checking
        is_valid, config_errors = ConfigValidator.validate()
        if not is_valid:
            raise EnvironmentError(f"Configuration validation failed: {'; '.join(config_errors)}")
        
        logger.info("✅ Configuration validated")
        
        # Register Flask routes
        register_routes(flask_app)
        logger.info("✅ Flask routes registered")
        
        # Setup webhook handler
        setup_webhook_handler(flask_app, Config.BOT_TOKEN, lambda: bot_application)
        logger.info("✅ Webhook handler configured")
        
        # Start bot in separate thread
        bot_thread = threading.Thread(
            target=setup_bot_thread, 
            args=(Config.BOT_TOKEN, expense_tracker, set_bot_application),
            daemon=True
        )
        bot_thread.start()
        logger.info("✅ Bot thread started")
        
        # Start Flask server
        logger.info(f"🌐 Starting Flask server on port {Config.PORT}...")
        print(f"\n🤖 Budgetin Bot is running!")
        print(f"📡 Webhook endpoint: http://localhost:{Config.PORT}/{Config.BOT_TOKEN}")
        print(f"🌐 Health check: http://localhost:{Config.PORT}/")
        print(f"📊 OAuth callback: http://localhost:{Config.PORT}/oauth/callback")
        print(f"\n✅ Bot is ready to receive messages!")
        
        flask_app.run(host='0.0.0.0', port=Config.PORT, debug=False)
        
    except Exception as e:
        handle_startup_error(e, logger)


if __name__ == '__main__':
    main()

"""
Application utilities for the Budgetin bot.
Contains logging, configuration, and other utility functions.
"""

import logging
import os
import sys


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    return logging.getLogger(__name__)


def validate_environment():
    """Validate required environment variables and dependencies"""
    required_env_vars = [
        'BOT_TOKEN',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
    
    return True


def handle_startup_error(error, logger):
    """Handle startup errors gracefully"""
    logger.error(f"Startup error: {error}")
    
    # Print user-friendly error message
    print(f"\n❌ Failed to start Budgetin Bot")
    print(f"Error: {error}")
    print(f"\n🔧 Troubleshooting:")
    print(f"1. Check your .env file configuration")
    print(f"2. Verify Google credentials JSON is valid")
    print(f"3. Ensure BOT_TOKEN is correct")
    print(f"4. Check if port {os.getenv('PORT', '5000')} is available")
    print(f"\nFor more help, check the README.md file.")
    
    sys.exit(1)

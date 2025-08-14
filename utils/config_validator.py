import os
import logging
from typing import List

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Validate configuration and environment variables"""
    
    REQUIRED_VARS = [
        'BOT_TOKEN',
        'GOOGLE_CLIENT_ID', 
        'GOOGLE_CLIENT_SECRET'
    ]
    
    OPTIONAL_VARS = [
        'NGROK_URL',
        'PUBLIC_URL',
        'PORT',
        'OAUTH_REDIRECT_URI'
    ]
    
    @classmethod
    def validate(cls) -> tuple[bool, List[str]]:
        """Validate all required configuration"""
        errors = []
        
        # Check required environment variables
        missing_vars = []
        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            if not value or value.strip() == "":
                missing_vars.append(var)
        
        if missing_vars:
            errors.append(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate BOT_TOKEN format
        bot_token = os.getenv('BOT_TOKEN')
        if bot_token and not cls._is_valid_bot_token(bot_token):
            errors.append("BOT_TOKEN format is invalid (should be like '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')")
        
        # Validate Google OAuth credentials format
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        if google_client_id and not google_client_id.endswith('.apps.googleusercontent.com'):
            errors.append("GOOGLE_CLIENT_ID should end with '.apps.googleusercontent.com'")
        
        # Validate PORT
        port = os.getenv('PORT', '8080')
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                errors.append(f"PORT must be between 1 and 65535, got {port}")
        except ValueError:
            errors.append(f"PORT must be a valid integer, got '{port}'")
        
        # Check webhook URL configuration
        if not any(os.getenv(var) for var in ['PUBLIC_URL', 'NGROK_URL']):
            logger.warning("Neither PUBLIC_URL nor NGROK_URL is set. Bot will use default Render hostname.")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _is_valid_bot_token(token: str) -> bool:
        """Check if bot token has valid format"""
        if ':' not in token:
            return False
        
        parts = token.split(':')
        if len(parts) != 2:
            return False
        
        # First part should be digits (bot ID)
        if not parts[0].isdigit():
            return False
        
        # Second part should be at least 35 characters
        if len(parts[1]) < 35:
            return False
        
        return True
    
    @classmethod
    def print_status(cls):
        """Print configuration status"""
        print("\n🔍 Configuration Check:")
        print("=" * 40)
        
        is_valid, errors = cls.validate()
        
        if is_valid:
            print("✅ All configurations are valid!")
        else:
            print("❌ Configuration errors found:")
            for error in errors:
                print(f"  - {error}")
        
        print("\n📋 Environment Variables:")
        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            status = "✅" if value else "❌"
            display_value = "***hidden***" if value and "TOKEN" in var or "SECRET" in var else value
            print(f"  {status} {var}: {display_value}")
        
        print("\n📋 Optional Variables:")
        for var in cls.OPTIONAL_VARS:
            value = os.getenv(var)
            status = "✅" if value else "⚪"
            print(f"  {status} {var}: {value or 'Not set'}")
        
        print("\n" + "=" * 40)
        return is_valid

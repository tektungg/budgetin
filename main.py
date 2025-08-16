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
from handlers.budget_handlers import (
    budget_command, insights_command, alerts_command, 
    budget_callback_handler, handle_budget_input
)
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
    """Enhanced health check endpoint with OAuth code display"""
    try:
        # Check if this is an OAuth callback with code parameter
        code = request.args.get('code')
        state = request.args.get('state')
        
        if code and state:
            # Display OAuth code in a user-friendly format
            html_response = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Budgetin Bot - OAuth Authorization</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
                    .success {{ color: #27ae60; font-size: 18px; margin-bottom: 20px; }}
                    .code-container {{ background-color: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    .code {{ font-family: monospace; font-size: 14px; word-break: break-all; color: #2c3e50; }}
                    .instructions {{ background-color: #e8f6f3; padding: 20px; border-radius: 8px; border-left: 4px solid #27ae60; margin: 20px 0; }}
                    .copy-btn {{ background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }}
                    .copy-btn:hover {{ background-color: #2980b9; }}
                    .footer {{ text-align: center; color: #7f8c8d; margin-top: 30px; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🤖 Budgetin Bot</h1>
                        <h2>Google OAuth Authorization</h2>
                    </div>
                    
                    <div class="success">
                        ✅ <strong>Login Google berhasil!</strong>
                    </div>
                    
                    <div class="instructions">
                        <strong>📝 Langkah selanjutnya:</strong>
                        <ol>
                            <li>Copy kode autorisasi di bawah ini</li>
                            <li>Buka chat Telegram dengan Budgetin Bot</li>
                            <li>Kirim kode tersebut ke bot</li>
                            <li>Bot akan otomatis memverifikasi dan membuat Google Sheet Anda</li>
                        </ol>
                    </div>
                    
                    <div class="code-container">
                        <strong>🔑 Kode Autorisasi Anda:</strong>
                        <div class="code" id="auth-code">{code}</div>
                        <button class="copy-btn" onclick="copyCode()">📋 Copy Kode</button>
                    </div>
                    
                    <div class="instructions">
                        <strong>💡 Tips:</strong>
                        <ul>
                            <li>Kode ini hanya berlaku 10 menit</li>
                            <li>Hanya kirim kode, bukan seluruh URL</li>
                            <li>Jika ada masalah, gunakan /login ulang di bot</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>State: <code>{state}</code></p>
                        <p>Timestamp: {get_jakarta_now().strftime('%Y-%m-%d %H:%M:%S WIB')}</p>
                    </div>
                </div>
                
                <script>
                    function copyCode() {{
                        const code = document.getElementById('auth-code').textContent;
                        navigator.clipboard.writeText(code).then(function() {{
                            const btn = document.querySelector('.copy-btn');
                            btn.textContent = '✅ Copied!';
                            btn.style.backgroundColor = '#27ae60';
                            setTimeout(() => {{
                                btn.textContent = '📋 Copy Kode';
                                btn.style.backgroundColor = '#3498db';
                            }}, 2000);
                        }});
                    }}
                </script>
            </body>
            </html>
            """
            return html_response
        
        # Regular health check
        health_status = {
            'status': 'healthy',
            'service': 'Budgetin Bot',
            'version': '2.0.0',
            'timestamp': get_jakarta_now().isoformat(),
            'checks': {
                'bot_initialized': bot_application is not None,
                'config_valid': ConfigValidator.validate()[0],
                'active_users': len(expense_tracker.user_credentials) if expense_tracker else 0,
                'environment': {
                    'has_bot_token': bool(Config.BOT_TOKEN),
                    'has_google_oauth': bool(Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET),
                    'port': Config.PORT
                },
                'features': {
                    'budget_planning': True,
                    'smart_alerts': True,
                    'anomaly_detection': True,
                    'spending_analytics': True
                }
            }
        }
        return health_status, 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {'status': 'error', 'message': str(e)}, 500

@flask_app.route('/oauth/callback', methods=['GET'])
def oauth_callback():
    """OAuth callback endpoint for Google authorization"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            html_response = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Budgetin Bot - OAuth Error</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; color: #e74c3c; margin-bottom: 30px; }}
                    .error {{ color: #e74c3c; font-size: 18px; margin-bottom: 20px; }}
                    .instructions {{ background-color: #fdf2f2; padding: 20px; border-radius: 8px; border-left: 4px solid #e74c3c; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🤖 Budgetin Bot</h1>
                        <h2>OAuth Authorization</h2>
                    </div>
                    
                    <div class="error">
                        ❌ <strong>Login Google gagal!</strong>
                    </div>
                    
                    <div class="instructions">
                        <strong>📝 Yang dapat Anda lakukan:</strong>
                        <ol>
                            <li>Buka chat Telegram dengan Budgetin Bot</li>
                            <li>Gunakan perintah /login untuk mencoba lagi</li>
                            <li>Pastikan Anda memberikan izin akses yang diperlukan</li>
                        </ol>
                        <p><strong>Error:</strong> {error}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return html_response
        
        if not code or not state:
            return "Missing authorization code or state parameter", 400
        
        # Display OAuth code in a user-friendly format
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Budgetin Bot - OAuth Authorization</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
                .success {{ color: #27ae60; font-size: 18px; margin-bottom: 20px; }}
                .code-container {{ background-color: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .code {{ font-family: monospace; font-size: 14px; word-break: break-all; color: #2c3e50; }}
                .instructions {{ background-color: #e8f6f3; padding: 20px; border-radius: 8px; border-left: 4px solid #27ae60; margin: 20px 0; }}
                .copy-btn {{ background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }}
                .copy-btn:hover {{ background-color: #2980b9; }}
                .footer {{ text-align: center; color: #7f8c8d; margin-top: 30px; font-size: 14px; }}
                .telegram-btn {{ background-color: #0088cc; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; margin-top: 15px; text-decoration: none; display: inline-block; }}
                .telegram-btn:hover {{ background-color: #006ca8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Budgetin Bot</h1>
                    <h2>Google OAuth Authorization</h2>
                </div>
                
                <div class="success">
                    ✅ <strong>Login Google berhasil!</strong>
                </div>
                
                <div class="instructions">
                    <strong>📝 Langkah selanjutnya:</strong>
                    <ol>
                        <li>Copy kode autorisasi di bawah ini</li>
                        <li>Buka chat Telegram dengan Budgetin Bot</li>
                        <li>Kirim kode tersebut ke bot</li>
                        <li>Bot akan otomatis memverifikasi dan membuat Google Sheet Anda</li>
                    </ol>
                </div>
                
                <div class="code-container">
                    <strong>🔑 Kode Autorisasi Anda:</strong>
                    <div class="code" id="auth-code">{code}</div>
                    <button class="copy-btn" onclick="copyCode()">📋 Copy Kode</button>
                    <a href="https://t.me/your_bot_username" class="telegram-btn">📱 Buka Telegram Bot</a>
                </div>
                
                <div class="instructions">
                    <strong>💡 Tips:</strong>
                    <ul>
                        <li>Kode ini hanya berlaku 10 menit</li>
                        <li>Hanya kirim kode, bukan seluruh URL</li>
                        <li>Jika ada masalah, gunakan /login ulang di bot</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>State: <code>{state}</code></p>
                    <p>Timestamp: {get_jakarta_now().strftime('%Y-%m-%d %H:%M:%S WIB')}</p>
                </div>
            </div>
            
            <script>
                function copyCode() {{
                    const code = document.getElementById('auth-code').textContent;
                    navigator.clipboard.writeText(code).then(function() {{
                        const btn = document.querySelector('.copy-btn');
                        btn.textContent = '✅ Copied!';
                        btn.style.backgroundColor = '#27ae60';
                        setTimeout(() => {{
                            btn.textContent = '📋 Copy Kode';
                            btn.style.backgroundColor = '#3498db';
                        }}, 2000);
                    }});
                }}
            </script>
        </body>
        </html>
        """
        return html_response
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return f"Error processing OAuth callback: {str(e)}", 500

@flask_app.route('/oauth/info', methods=['GET'])
def oauth_info():
    """Information page about OAuth process"""
    html_response = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Budgetin Bot - OAuth Info</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 700px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; color: #2c3e50; margin-bottom: 30px; }}
            .step {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #3498db; }}
            .step-number {{ background-color: #3498db; color: white; border-radius: 50%; width: 30px; height: 30px; display: inline-flex; align-items: center; justify-content: center; margin-right: 15px; }}
            .telegram-btn {{ background-color: #0088cc; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; margin-top: 15px; text-decoration: none; display: inline-block; }}
            .telegram-btn:hover {{ background-color: #006ca8; }}
            .footer {{ text-align: center; color: #7f8c8d; margin-top: 30px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Budgetin Bot</h1>
                <h2>Cara Login Google OAuth</h2>
            </div>
            
            <div class="step">
                <span class="step-number">1</span>
                <strong>Mulai dari Telegram Bot</strong>
                <p>Buka chat dengan Budgetin Bot dan gunakan perintah <code>/login</code></p>
            </div>
            
            <div class="step">
                <span class="step-number">2</span>
                <strong>Klik Login ke Google</strong>
                <p>Bot akan memberikan tombol "Login ke Google", klik tombol tersebut</p>
            </div>
            
            <div class="step">
                <span class="step-number">3</span>
                <strong>Authorize Google Account</strong>
                <p>Masuk dengan akun Google Anda dan berikan izin akses untuk Google Sheets dan Drive</p>
            </div>
            
            <div class="step">
                <span class="step-number">4</span>
                <strong>Copy Kode Autorisasi</strong>
                <p>Setelah login berhasil, Anda akan diarahkan ke halaman yang menampilkan kode autorisasi. Copy kode tersebut.</p>
            </div>
            
            <div class="step">
                <span class="step-number">5</span>
                <strong>Kirim Kode ke Bot</strong>
                <p>Kembali ke chat Telegram dan kirim kode autorisasi yang sudah di-copy ke bot</p>
            </div>
            
            <div class="step">
                <span class="step-number">6</span>
                <strong>Setup Saldo Awal</strong>
                <p>Bot akan membuat Google Sheet dan meminta Anda mengatur saldo awal</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://t.me/your_bot_username" class="telegram-btn">📱 Buka Budgetin Bot</a>
            </div>
            
            <div class="footer">
                <p>Timestamp: {get_jakarta_now().strftime('%Y-%m-%d %H:%M:%S WIB')}</p>
                <p>💡 Jika ada masalah, gunakan /help di bot untuk bantuan lebih lanjut</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_response

@flask_app.route(f'/{Config.BOT_TOKEN}', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram updates"""
    global bot_application
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

async def initialize_bot():
    """Initialize Telegram bot with handlers"""
    global bot_application
    
    # Build bot application with custom timeout settings
    bot_application = (Application.builder()
                      .token(Config.BOT_TOKEN)
                      .read_timeout(30)  # 30 seconds for reading responses
                      .write_timeout(30)  # 30 seconds for sending requests  
                      .connect_timeout(20)  # 20 seconds for initial connection
                      .pool_timeout(20)  # 20 seconds for connection pool
                      .build())
    
    # Wrapper functions to pass expense_tracker
    async def start_wrapper(update: Update, context):
        await start(update, context, expense_tracker)
    
    async def help_wrapper(update: Update, context):
        await help_command(update, context)
    
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
    
    # Add command handlers
    bot_application.add_handler(CommandHandler("start", start_wrapper))
    bot_application.add_handler(CommandHandler("help", help_wrapper))
    bot_application.add_handler(CommandHandler("login", login_wrapper))
    bot_application.add_handler(CommandHandler("logout", logout_wrapper))
    bot_application.add_handler(CommandHandler("sheet", sheet_wrapper))
    bot_application.add_handler(CommandHandler("ringkasan", summary_wrapper))
    bot_application.add_handler(CommandHandler("balance", balance_wrapper))
    bot_application.add_handler(CommandHandler("kategori", categories_command))
    
    # NEW: Add smart feature commands
    bot_application.add_handler(CommandHandler("budget", budget_wrapper))
    bot_application.add_handler(CommandHandler("insights", insights_wrapper))
    bot_application.add_handler(CommandHandler("analytics", insights_wrapper))  # Alias
    bot_application.add_handler(CommandHandler("alerts", alerts_wrapper))
    
    # Add callback query handler for buttons (combined handler)
    bot_application.add_handler(CallbackQueryHandler(combined_callback_wrapper))
    
    # Handle text messages with priority for budget input
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, budget_input_wrapper))
    
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
    print("🚀 Starting Budgetin Bot v2.0.0 with Smart Features...")
    is_valid = ConfigValidator.print_status()
    
    if not is_valid:
        print("\n❌ Configuration validation failed. Please fix the errors above.")
        sys.exit(1)
    
    print("✅ Configuration validated successfully!")
    
    def setup_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_bot())
            print(f"✅ Bot initialized successfully!")
            print(f"🌐 Webhook URL: {get_webhook_url()}")
            print(f"🏥 Health check: http://localhost:{Config.PORT}/")
            print(f"📱 Bot is ready to receive messages!")
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Bot initialization error: {e}")
        finally:
            loop.close()

    # Run bot in separate thread
    bot_thread = threading.Thread(target=setup_bot_thread, daemon=True)
    bot_thread.start()
    
    # Start Flask server
    print(f"🌐 Starting Flask server on port {Config.PORT}...")
    flask_app.run(host='0.0.0.0', port=Config.PORT, debug=False)

if __name__ == '__main__':
    main()

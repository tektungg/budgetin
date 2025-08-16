"""
Webhook handling for Telegram bot updates.
Handles timeout, retry logic, and OAuth-specific processing.
"""

import logging
import asyncio
from flask import request
from telegram import Update

logger = logging.getLogger(__name__)


def is_oauth_operation(update_data):
    """Check if this is an OAuth-related operation that needs longer timeout"""
    try:
        if not update_data or 'message' not in update_data:
            return False
        
        message = update_data['message']
        if 'text' not in message:
            return False
        
        text = message['text'].strip()
        
        # Check if this looks like an OAuth code
        # OAuth codes are typically long strings with specific characters
        if len(text) > 20 and ('/' in text or '-' in text or '_' in text):
            return True
        
        return False
    except Exception:
        return False


async def send_retry_message(update_data, bot_application):
    """Send retry message to user after first attempt timeout"""
    try:
        update = Update.de_json(update_data, bot_application.bot)
        if update and update.effective_chat:
            await bot_application.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ *Proses lebih lama dari biasanya...*\n\n"
                     "Sedang mencoba ulang (percobaan 2/2)...",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error sending retry message: {e}")


async def send_final_error_message(update_data, bot_application, is_oauth=False):
    """Send final error message to user after both attempts failed"""
    try:
        update = Update.de_json(update_data, bot_application.bot)
        if update and update.effective_chat:
            if is_oauth:
                # Specific error message for OAuth operations
                text = ("❌ *Login Google gagal setelah 2 percobaan (masing-masing 30 detik)*\n\n"
                       "🔧 *Yang bisa Anda lakukan:*\n"
                       "• Tunggu 2-3 menit lalu gunakan /login lagi\n"
                       "• Pastikan koneksi internet stabil\n"
                       "• Pastikan kode OAuth yang dikirim benar\n"
                       "• Gunakan /help untuk bantuan\n\n"
                       "⚙️ *Kemungkinan penyebab:*\n"
                       "• Google OAuth API sedang lambat\n"
                       "• Kode OAuth sudah kedaluwarsa\n"
                       "• Koneksi internet tidak stabil\n"
                       "• Google Drive API sedang sibuk\n\n"
                       "💡 *Tips:* Proses login membutuhkan waktu lebih lama karena harus membuat Google Sheet baru.")
            else:
                # Standard error message for regular operations
                text = ("❌ *Operasi gagal setelah 2 percobaan (masing-masing 6 detik)*\n\n"
                       "🔧 *Yang bisa Anda lakukan:*\n"
                       "• Tunggu 1-2 menit lalu coba lagi\n"
                       "• Pastikan koneksi internet stabil\n"
                       "• Gunakan /help untuk bantuan\n"
                       "• Cek apakah data sudah tersimpan dengan /ringkasan\n\n"
                       "⚙️ *Kemungkinan penyebab:*\n"
                       "• Google API sedang lambat\n"
                       "• Koneksi internet tidak stabil\n"
                       "• Server sedang sibuk")
            
            await bot_application.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error sending final error message: {e}")


async def process_telegram_update_with_retry(update_data, bot_application, attempt=1):
    """Process Telegram update with attempt tracking"""
    try:
        logger.info(f"Processing update attempt {attempt}/2")
        update = Update.de_json(update_data, bot_application.bot)
        await bot_application.process_update(update)
        logger.info(f"Update processed successfully on attempt {attempt}")
    except Exception as e:
        logger.error(f"Error processing update on attempt {attempt}: {e}")
        raise  # Re-raise to trigger retry mechanism


async def process_telegram_update(update_data, bot_application):
    """Process Telegram update with enhanced error handling"""
    try:
        update = Update.de_json(update_data, bot_application.bot)
        await bot_application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        # Try to send error message to user if possible
        try:
            if update and update.effective_chat:
                await bot_application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Terjadi kesalahan saat memproses pesan. Silakan coba lagi.",
                    parse_mode='Markdown'
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")


def setup_webhook_handler(app, bot_token, bot_application_getter):
    """Setup webhook handler for the Flask app"""
    
    @app.route(f'/{bot_token}', methods=['POST'])
    def webhook():
        """Webhook endpoint with OAuth-specific timeout handling"""
        bot_application = bot_application_getter()
        if bot_application:
            try:
                update_data = request.get_json()
                
                # Determine timeout based on operation type
                # OAuth operations get 30 seconds, others get 6 seconds
                is_oauth = is_oauth_operation(update_data)
                timeout_duration = 30 if is_oauth else 6
                
                logger.info(f"Processing update with {timeout_duration}s timeout ({'OAuth' if is_oauth else 'regular'} operation)")
                
                # Process update with dynamic timeout and retry
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # First attempt with dynamic timeout
                success = False
                try:
                    if loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            process_telegram_update_with_retry(update_data, bot_application, attempt=1), 
                            loop
                        )
                        future.result(timeout=timeout_duration)
                    else:
                        loop.run_until_complete(
                            asyncio.wait_for(process_telegram_update_with_retry(update_data, bot_application, attempt=1), timeout=timeout_duration)
                        )
                    success = True
                except Exception as e:
                    logger.warning(f"First attempt failed after {timeout_duration}s: {e}")
                    
                    # Send retry message to user (only for non-OAuth operations)
                    # OAuth operations are complex and may not need retry messaging
                    if not is_oauth:
                        try:
                            if loop.is_running():
                                retry_future = asyncio.run_coroutine_threadsafe(
                                    send_retry_message(update_data, bot_application), 
                                    loop
                                )
                                retry_future.result(timeout=3)  # Quick 3s for retry message
                            else:
                                loop.run_until_complete(
                                    asyncio.wait_for(send_retry_message(update_data, bot_application), timeout=3)
                                )
                        except Exception as retry_error:
                            logger.error(f"Failed to send retry message: {retry_error}")
                    
                    # Second attempt with same timeout
                    try:
                        if loop.is_running():
                            future = asyncio.run_coroutine_threadsafe(
                                process_telegram_update_with_retry(update_data, bot_application, attempt=2), 
                                loop
                            )
                            future.result(timeout=timeout_duration)
                        else:
                            loop.run_until_complete(
                                asyncio.wait_for(process_telegram_update_with_retry(update_data, bot_application, attempt=2), timeout=timeout_duration)
                            )
                        success = True
                    except Exception as final_error:
                        logger.error(f"Final attempt failed after {timeout_duration}s: {final_error}")
                        
                        # Send final error message with operation-specific text
                        try:
                            if loop.is_running():
                                error_future = asyncio.run_coroutine_threadsafe(
                                    send_final_error_message(update_data, bot_application, is_oauth=is_oauth), 
                                    loop
                                )
                                error_future.result(timeout=3)  # Quick 3s for error message
                            else:
                                loop.run_until_complete(
                                    asyncio.wait_for(send_final_error_message(update_data, bot_application, is_oauth=is_oauth), timeout=3)
                                )
                        except Exception as error_send_error:
                            logger.error(f"Failed to send final error message: {error_send_error}")
                
                return "OK", 200
                
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return "Error", 500
        return "Bot not initialized", 500

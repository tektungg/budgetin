"""
Flask routes for the Budgetin bot application.
Handles health check, OAuth callback, and OAuth info endpoints.
"""

import logging
from flask import request, Flask
from utils.date_utils import get_jakarta_now

logger = logging.getLogger(__name__)


def register_routes(app: Flask):
    """Register all Flask routes with the app"""
    
    @app.route('/', methods=['GET'])
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
                    <title>Budgetin Bot - OAuth Success</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .header {{ text-align: center; color: #2ecc71; margin-bottom: 30px; }}
                        .oauth-code {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; border: 2px dashed #2ecc71; margin: 20px 0; font-family: monospace; font-size: 14px; word-break: break-all; text-align: center; }}
                        .copy-btn {{ background-color: #2ecc71; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; font-size: 12px; margin-top: 10px; transition: background-color 0.3s; }}
                        .copy-btn:hover {{ background-color: #27ae60; }}
                        .copy-btn:active {{ background-color: #229954; }}
                        .copy-success {{ background-color: #27ae60; }}
                        .instructions {{ background-color: #e8f5e8; padding: 20px; border-radius: 8px; border-left: 4px solid #2ecc71; margin: 20px 0; }}
                        .telegram-btn {{ display: inline-block; background-color: #0088cc; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                        .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>🤖 Budgetin Bot</h1>
                            <h2>✅ Login Google Berhasil!</h2>
                        </div>
                        
                        <div class="oauth-code">
                            <strong>🔑 Kode Autorisasi OAuth:</strong><br>
                            <span id="oauth-code-text">{code}</span>
                            <br><br>
                            <button onclick="copyOAuthCode()" class="copy-btn" id="copy-btn">
                                📋 Copy Kode
                            </button>
                        </div>
                        
                        <div class="instructions">
                            <strong>📝 Langkah selanjutnya:</strong>
                            <ol>
                                <li>Salin kode di atas</li>
                                <li>Buka chat Telegram dengan Budgetin Bot</li>
                                <li>Kirim kode tersebut ke bot (paste saja, tanpa perintah apapun)</li>
                                <li>Bot akan memproses login dan membuat Google Sheet untuk Anda</li>
                            </ol>
                            <p><strong>⚠️ Penting:</strong> Kirim HANYA kode di atas, bukan seluruh URL halaman ini!</p>
                        </div>
                        
                        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 20px 0;">
                            <strong>💡 Tips:</strong>
                            <p>Bot akan membuat Google Sheet dan meminta Anda mengatur saldo awal</p>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px;">
                            <a href="https://t.me/tbudgetin_bot" class="telegram-btn">📱 Buka Budgetin Bot</a>
                        </div>
                        
                        <div class="footer">
                            <p>Timestamp: {get_jakarta_now().strftime('%Y-%m-%d %H:%M:%S WIB')}</p>
                            <p>💡 Jika ada masalah, gunakan /help di bot untuk bantuan lebih lanjut</p>
                        </div>
                    </div>
                    
                    <script>
                        function copyOAuthCode() {{
                            const codeText = document.getElementById('oauth-code-text').textContent;
                            const copyBtn = document.getElementById('copy-btn');
                            
                            // Try modern clipboard API first
                            if (navigator.clipboard && window.isSecureContext) {{
                                navigator.clipboard.writeText(codeText).then(function() {{
                                    // Success feedback
                                    copyBtn.innerHTML = '✅ Tersalin!';
                                    copyBtn.classList.add('copy-success');
                                    
                                    // Reset button after 2 seconds
                                    setTimeout(function() {{
                                        copyBtn.innerHTML = '📋 Copy Kode';
                                        copyBtn.classList.remove('copy-success');
                                    }}, 2000);
                                }}).catch(function() {{
                                    fallbackCopy(codeText, copyBtn);
                                }});
                            }} else {{
                                // Fallback for older browsers
                                fallbackCopy(codeText, copyBtn);
                            }}
                        }}
                        
                        function fallbackCopy(text, copyBtn) {{
                            // Create temporary textarea
                            const textArea = document.createElement('textarea');
                            textArea.value = text;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-999999px';
                            textArea.style.top = '-999999px';
                            document.body.appendChild(textArea);
                            textArea.focus();
                            textArea.select();
                            
                            try {{
                                document.execCommand('copy');
                                // Success feedback
                                copyBtn.innerHTML = '✅ Tersalin!';
                                copyBtn.classList.add('copy-success');
                                
                                // Reset button after 2 seconds
                                setTimeout(function() {{
                                    copyBtn.innerHTML = '📋 Copy Kode';
                                    copyBtn.classList.remove('copy-success');
                                }}, 2000);
                            }} catch (err) {{
                                // Error feedback
                                copyBtn.innerHTML = '❌ Gagal';
                                setTimeout(function() {{
                                    copyBtn.innerHTML = '📋 Copy Kode';
                                }}, 2000);
                            }}
                            
                            document.body.removeChild(textArea);
                        }}
                    </script>
                </body>
                </html>
                """
                return html_response
            
            # Regular health check without OAuth code
            health_status = {
                'status': 'healthy',
                'timestamp': get_jakarta_now().isoformat(),
                'message': 'Budgetin Bot is running smoothly',
                'version': '2.0.0',
                'services': {
                    'flask': 'running',
                    'telegram_bot': 'running',
                    'google_api': 'connected'
                }
            }
            return health_status, 200
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {'status': 'error', 'message': str(e)}, 500

    @app.route('/oauth/callback', methods=['GET'])
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
                        
                        <div style="text-align: center; margin-top: 30px;">
                            <a href="https://t.me/tbudgetin_bot" style="display: inline-block; background-color: #0088cc; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px;">📱 Buka Budgetin Bot</a>
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px; color: #666; font-size: 12px;">
                            <p>Timestamp: {get_jakarta_now().strftime('%Y-%m-%d %H:%M:%S WIB')}</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                return html_response, 400
            
            if code and state:
                # Success - redirect to health check with code parameter
                return app.redirect(f'/?code={code}&state={state}')
            
            return "Invalid OAuth callback", 400
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            return f"OAuth callback error: {str(e)}", 500

    @app.route('/oauth/info', methods=['GET'])
    def oauth_info():
        """OAuth information endpoint for debugging"""
        try:
            return {
                'oauth_status': 'ready',
                'timestamp': get_jakarta_now().isoformat(),
                'message': 'OAuth endpoint is ready to handle authorization codes',
                'instructions': {
                    'step1': 'Use /login command in Telegram bot',
                    'step2': 'Click the Google login link',
                    'step3': 'Complete authorization',
                    'step4': 'Copy and send the authorization code to the bot'
                }
            }, 200
        except Exception as e:
            logger.error(f"OAuth info error: {e}")
            return {'status': 'error', 'message': str(e)}, 500

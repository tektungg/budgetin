import os
import re
import logging
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ExpenseTracker:
    def __init__(self):
        # Categories for expense classification
        self.categories = {
            'daily_needs': ['makan', 'minum', 'beras', 'sayur', 'buah', 'daging', 'ikan', 'telur', 'susu', 'roti', 'nasi', 'lauk', 'snack', 'cemilan', 'grocery', 'belanja', 'pasar', 'supermarket'],
            'transportation': ['bensin', 'ojek', 'grab', 'gojek', 'taxi', 'bus', 'kereta', 'parkir', 'tol', 'transport'],
            'utilities': ['listrik', 'air', 'internet', 'wifi', 'pulsa', 'token', 'pln', 'pdam', 'indihome'],
            'health': ['obat', 'dokter', 'rumah sakit', 'rs', 'klinik', 'vitamin', 'medical', 'kesehatan'],
            'urgent': ['darurat', 'urgent', 'penting', 'mendadak', 'emergency'],
            'entertainment': ['nonton', 'bioskop', 'game', 'musik', 'streaming', 'netflix', 'spotify', 'hiburan', 'jalan', 'mall', 'cafe', 'restaurant']
        }
        
        # Initialize Google Sheets
        self.setup_google_sheets()
    
    def setup_google_sheets(self):
        """Setup Google Sheets connection"""
        try:
            # Try multiple ways to load credentials
            creds_dict = None
            
            # Method 1: From environment variable (as JSON string)
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                try:
                    creds_dict = json.loads(creds_json)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in GOOGLE_CREDENTIALS_JSON")
            
            # Method 2: From individual environment variables
            if not creds_dict:
                private_key = os.getenv('GOOGLE_PRIVATE_KEY')
                client_email = os.getenv('GOOGLE_CLIENT_EMAIL')
                project_id = os.getenv('GOOGLE_PROJECT_ID')
                
                if private_key and client_email and project_id:
                    # Replace \\n with actual newlines in private key
                    private_key = private_key.replace('\\n', '\n')
                    creds_dict = {
                        "type": "service_account",
                        "project_id": project_id,
                        "client_email": client_email,
                        "private_key": private_key,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                    }
            
            # Method 3: From local file (for development)
            if not creds_dict:
                try:
                    with open('credentials.json', 'r') as f:
                        creds_dict = json.load(f)
                except FileNotFoundError:
                    pass
            
            if not creds_dict:
                raise Exception("No valid Google credentials found")
            
            # Setup credentials
            scope = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            
            # Initialize gspread client
            self.gc = gspread.authorize(creds)
            
            # Open spreadsheet by ID (you'll need to set this)
            spreadsheet_id = os.getenv('SPREADSHEET_ID', 'YOUR_SPREADSHEET_ID_HERE')
            self.sh = self.gc.open_by_key(spreadsheet_id)
            
            # Setup worksheet structure
            self.setup_worksheet()
            
        except Exception as e:
            logger.error(f"Error setting up Google Sheets: {e}")
            self.gc = None
            self.sh = None
    
    def setup_worksheet(self):
        """Setup worksheet headers if not exists"""
        try:
            # Try to get or create main worksheet
            try:
                ws = self.sh.worksheet("Pengeluaran")
            except gspread.exceptions.WorksheetNotFound:
                ws = self.sh.add_worksheet("Pengeluaran", rows=1000, cols=6)
            
            # Check if headers exist
            headers = ws.row_values(1)
            if not headers:
                # Add headers
                ws.update('A1:F1', [['Tanggal', 'Waktu', 'Jumlah', 'Keterangan', 'Kategori', 'User']])
                # Format headers
                ws.format('A1:F1', {
                    "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True}
                })
            
            self.worksheet = ws
            
        except Exception as e:
            logger.error(f"Error setting up worksheet: {e}")
            self.worksheet = None
    
    def extract_amount(self, text):
        """Extract amount from text"""
        # Pattern to match numbers with 'rb', 'ribu', 'k', or just numbers
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:rb|ribu)',  # 50rb, 50 rb, 50ribu
            r'(\d+(?:\.\d+)?)\s*k',           # 50k
            r'(\d+(?:\.\d+)?)\s*juta',        # 1.5juta
            r'(\d{1,3}(?:\.\d{3})*)',         # 50.000
            r'(\d+)'                          # plain number
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount_str = match.group(1)
                amount = float(amount_str.replace('.', ''))
                
                # Convert based on suffix
                if 'rb' in text_lower or 'ribu' in text_lower:
                    amount *= 1000
                elif 'k' in text_lower and 'juta' not in text_lower:
                    amount *= 1000
                elif 'juta' in text_lower:
                    amount *= 1000000
                
                return int(amount), match.start(), match.end()
        
        return None, None, None
    
    def classify_category(self, description):
        """Classify expense into category based on description"""
        description_lower = description.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category.replace('_', ' ').title()
        
        return 'Other'
    
    def get_description(self, text, start_pos, end_pos):
        """Extract description by removing the amount part"""
        before_amount = text[:start_pos].strip()
        after_amount = text[end_pos:].strip()
        
        # Combine and clean
        description = (before_amount + ' ' + after_amount).strip()
        
        # Remove common words
        remove_words = ['beli', 'bayar', 'untuk', 'ke', 'di', 'dengan', 'pakai', 'rb', 'ribu', 'k', 'juta']
        words = description.split()
        cleaned_words = [word for word in words if word.lower() not in remove_words]
        
        return ' '.join(cleaned_words).strip() or 'Pengeluaran'
    
    def add_expense(self, amount, description, category, user_name):
        """Add expense to Google Sheets"""
        try:
            if not self.worksheet:
                return False, "Google Sheets tidak tersedia"
            
            # Get current datetime in Jakarta timezone
            now = datetime.now(timezone.utc)  # You might want to adjust timezone
            date_str = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%H:%M:%S')
            
            # Add row to sheet
            row = [date_str, time_str, amount, description, category, user_name]
            self.worksheet.append_row(row)
            
            return True, "Berhasil dicatat"
            
        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            return False, f"Gagal menyimpan: {str(e)}"
    
    def get_monthly_summary(self, year=None, month=None):
        """Get monthly expense summary"""
        try:
            if not self.worksheet:
                return "Google Sheets tidak tersedia"
            
            # Get current month if not specified
            if not year or not month:
                now = datetime.now()
                year = year or now.year
                month = month or now.month
            
            # Get all records
            records = self.worksheet.get_all_records()
            
            # Filter by month
            monthly_records = []
            for record in records:
                try:
                    date_obj = datetime.strptime(record['Tanggal'], '%Y-%m-%d')
                    if date_obj.year == year and date_obj.month == month:
                        monthly_records.append(record)
                except:
                    continue
            
            if not monthly_records:
                return f"Tidak ada data untuk bulan {month}/{year}"
            
            # Calculate summary
            total = sum(int(record['Jumlah']) for record in monthly_records)
            count = len(monthly_records)
            
            # Category breakdown
            categories = {}
            for record in monthly_records:
                cat = record['Kategori']
                categories[cat] = categories.get(cat, 0) + int(record['Jumlah'])
            
            # Format response
            response = f"📊 *Ringkasan Pengeluaran {month}/{year}*\n\n"
            response += f"💰 Total: Rp {total:,}\n"
            response += f"📝 Jumlah transaksi: {count}\n"
            response += f"📈 Rata-rata per transaksi: Rp {total//count:,}\n\n"
            response += "*Per Kategori:*\n"
            
            for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total) * 100
                response += f"• {cat}: Rp {amount:,} ({percentage:.1f}%)\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting monthly summary: {e}")
            return f"Error mengambil ringkasan: {str(e)}"

# Initialize expense tracker
expense_tracker = ExpenseTracker()

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = """
🤖 *Selamat datang di Bot Pencatat Pengeluaran!*

Cara menggunakan:
📝 Kirim pesan dengan format bebas, contoh:
• "beli beras 50rb"
• "makan siang 25000"
• "bensin motor 30k"

📊 Perintah lainnya:
• /ringkasan - Lihat ringkasan bulan ini
• /help - Bantuan lengkap

Bot akan otomatis mendeteksi jumlah uang dan menyimpannya ke Google Sheets! 💾
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
📋 *Bantuan Bot Pencatat Pengeluaran*

*Cara mencatat pengeluaran:*
Kirim pesan dengan format bebas yang mengandung jumlah uang:

• "beli sayur 15rb"
• "isi bensin 50000"
• "bayar listrik 200k"
• "makan di warteg 12ribu"

*Format jumlah yang didukung:*
• 50rb, 50 rb, 50ribu
• 50k, 50 k
• 1.5juta, 2juta
• 50000 (angka biasa)
• 50.000 (dengan titik)

*Kategori otomatis:*
• Daily Needs (makan, minum, belanja)
• Transportation (bensin, ojek, grab)
• Utilities (listrik, air, internet)
• Health (obat, dokter, RS)
• Urgent (darurat, mendadak)
• Entertainment (nonton, game, jalan)

*Perintah:*
• /ringkasan - Ringkasan bulan ini
• /kategori - Lihat semua kategori

Semua data otomatis tersimpan ke Google Sheets! 📊
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summary command handler"""
    summary = expense_tracker.get_monthly_summary()
    await update.message.reply_text(summary, parse_mode='Markdown')

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Categories command handler"""
    cat_text = """
📂 *Kategori Pengeluaran:*

🥘 *Daily Needs*
makan, minum, beras, sayur, buah, grocery, belanja

🚗 *Transportation*  
bensin, ojek, grab, gojek, taxi, parkir, tol

⚡ *Utilities*
listrik, air, internet, pulsa, token

🏥 *Health*
obat, dokter, rumah sakit, vitamin

🚨 *Urgent*
darurat, urgent, mendadak, emergency

🎮 *Entertainment*
nonton, game, musik, cafe, restaurant

Kategori akan dipilih otomatis berdasarkan kata kunci dalam keterangan Anda.
    """
    await update.message.reply_text(cat_text, parse_mode='Markdown')

async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense input from messages"""
    text = update.message.text
    user = update.effective_user
    user_name = user.first_name or user.username or "Unknown"
    
    # Extract amount from message
    amount, start_pos, end_pos = expense_tracker.extract_amount(text)
    
    if not amount:
        await update.message.reply_text(
            "❌ Tidak dapat mendeteksi jumlah uang.\n"
            "Contoh: 'beli beras 50rb' atau 'makan siang 25000'"
        )
        return
    
    # Get description
    description = expense_tracker.get_description(text, start_pos, end_pos)
    
    # Classify category
    category = expense_tracker.classify_category(description)
    
    # Add to spreadsheet
    success, message = expense_tracker.add_expense(amount, description, category, user_name)
    
    if success:
        response = f"""
✅ *Pengeluaran berhasil dicatat!*

💰 Jumlah: Rp {amount:,}
📝 Keterangan: {description}
📂 Kategori: {category}
👤 User: {user_name}
📅 Tersimpan ke Google Sheets!
        """
        await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Gagal menyimpan: {message}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

from flask import Flask, request
import asyncio
import threading

# Flask app for webhook
flask_app = Flask(__name__)

# Global variable for bot application
bot_application = None

@flask_app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return "Bot is running!", 200

@flask_app.route(f'/{os.getenv("BOT_TOKEN", "webhook")}', methods=['POST'])
def telegram_webhook():
    """Handle Telegram webhook"""
    if bot_application:
        try:
            # Get update from Telegram
            update_data = request.get_json()
            
            # Process update asynchronously
            asyncio.run(process_telegram_update(update_data))
            
            return "OK", 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return "Error", 500
    
    return "Bot not initialized", 500

async def process_telegram_update(update_data):
    """Process Telegram update"""
    try:
        from telegram import Update
        update = Update.de_json(update_data, bot_application.bot)
        await bot_application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")

async def setup_bot():
    """Setup bot application"""
    global bot_application
    
    # Get bot token from environment
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is required")
        return None
    
    # Create application
    bot_application = Application.builder().token(bot_token).build()
    
    # Add handlers
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(CommandHandler("help", help_command))
    bot_application.add_handler(CommandHandler("ringkasan", summary_command))
    bot_application.add_handler(CommandHandler("kategori", categories_command))
    
    # Handle all text messages as potential expense entries
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))
    
    # Add error handler
    bot_application.add_error_handler(error_handler)
    
    # Initialize bot
    await bot_application.initialize()
    
    # Set webhook
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-app-name.onrender.com')}/{bot_token}"
    await bot_application.bot.set_webhook(url=webhook_url)
    
    logger.info(f"Bot initialized with webhook: {webhook_url}")
    
    return bot_application

def main():
    """Main function to run the bot"""
    # Setup bot in background thread
    def setup_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_bot())
    
    # Start bot setup in background
    bot_thread = threading.Thread(target=setup_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Wait a moment for bot to initialize
    import time
    time.sleep(3)
    
    # Start Flask app
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
import os
import re
import logging
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from dotenv import load_dotenv
import json
import pytz

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ExpenseTracker:
    """
    Main class for handling expense tracking logic, Google Sheets integration,
    category classification, and formatting utilities.
    """
    def __init__(self):
        # Categories for expense classification
        self.categories = {
            'daily_needs': ['makan', 'minum', 'beras', 'sayur', 'buah', 'daging', 'ikan', 'telur', 'susu', 'roti', 'nasi', 'lauk', 'snack', 'cemilan', 'grocery', 'belanja', 'pasar', 'supermarket'],
            'transportation': ['bensin', 'ojek', 'grab', 'gojek', 'taxi', 'bus', 'kereta', 'parkir', 'tol', 'transport'],
            'utilities': ['listrik', 'air', 'internet', 'wifi', 'pulsa', 'token', 'pln', 'pdam', 'indihome'],
            'health': ['obat', 'dokter', 'rumah sakit', 'rs', 'klinik', 'vitamin', 'medical', 'kesehatan'],
            'urgent': ['darurat', 'urgent', 'penting', 'mendadak', 'emergency'],
            'entertainment': ['nonton', 'bioskop', 'game', 'musik', 'streaming', 'netflix', 'spotify', 'hiburan', 'jalan', 'mall', 'cafe', 'restaurant', 'film', 'nongkrong']
        }
        
        # Initialize Google Sheets
        self.setup_google_sheets()

    def format_tanggal_indo(self, tanggal_str):
        """
        Format date from YYYY-MM-DD to Indonesian format: Day, DD Month YYYY.
        Example: "2025-08-12" -> "Selasa, 12 Agustus 2025"
        """
        bulan_indo = [
            "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        hari_indo = [
            "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"
        ]
        try:
            dt = datetime.strptime(tanggal_str, "%Y-%m-%d")
            hari = hari_indo[dt.weekday()]
            bulan = bulan_indo[dt.month]
            return f"{hari}, {dt.day} {bulan} {dt.year}"
        except Exception:
            return tanggal_str
        
    def parse_tanggal_indo(self, tanggal_str):
        """
        Parse Indonesian date format to datetime object.
        Supports both "Day, DD Month YYYY" and "YYYY-MM-DD".
        """
        bulan_map = {
            'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
            'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
        }
        try:
            # Example: "Selasa, 12 Agustus 2025"
            parts = tanggal_str.split(',')
            if len(parts) == 2:
                _, tgl_bulan_tahun = parts
                tgl_bulan_tahun = tgl_bulan_tahun.strip()
                tgl_split = tgl_bulan_tahun.split(' ')
                if len(tgl_split) == 3:
                    hari_num = int(tgl_split[0])
                    bulan_num = bulan_map.get(tgl_split[1], 1)
                    tahun_num = int(tgl_split[2])
                    return datetime(tahun_num, bulan_num, hari_num)
            # fallback
            return datetime.strptime(tanggal_str, '%Y-%m-%d')
        except Exception:
            return None   
    
    def setup_google_sheets(self):
        """
        Setup Google Sheets connection using credentials from environment variables.
        Supports multiple credential loading methods.
        """
        try:
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
            
            # Open spreadsheet by ID
            spreadsheet_id = os.getenv('SPREADSHEET_ID', 'YOUR_SPREADSHEET_ID_HERE')
            self.sh = self.gc.open_by_key(spreadsheet_id)
            
            # Setup worksheet structure
            self.setup_worksheet()
            
        except Exception as e:
            logger.error(f"Error setting up Google Sheets: {e}")
            self.gc = None
            self.sh = None
    
    def setup_worksheet(self):
        """
        Ensure the main worksheet 'Pengeluaran' exists and has the correct headers.
        """
        try:
            # Try to get or create main worksheet
            try:
                ws = self.sh.worksheet("Pengeluaran")
            except gspread.exceptions.WorksheetNotFound:
                ws = self.sh.add_worksheet("Pengeluaran", rows=1000, cols=5)
            
            # Check if headers exist
            headers = ws.row_values(1)
            if not headers:
                # Add headers
                ws.update('A1:E1', [['Tanggal', 'Waktu', 'Jumlah', 'Keterangan', 'Kategori']])
                ws.format('A1:E1', {
                    "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True}
                })
            
            self.worksheet = ws
            
        except Exception as e:
            logger.error(f"Error setting up worksheet: {e}")
            self.worksheet = None
    
    def extract_amount(self, text):
        """
        Extract amount from text, supporting formats like 1,5 juta, 1.500.000, 1,5rb, etc.
        Returns (amount, start_pos, end_pos) or (None, None, None) if not found.
        """
        text_lower = text.lower().replace(',', '.')
        patterns = [
            r'(\d+(?:[\.,]\d+)?)(?:\s*)(rb|ribu|k|juta)',  # 1.5juta, 1,5rb, 1.500rb
            r'(\d{4,})'  # 4 digits or more
        ]
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                if len(match.groups()) == 2:
                    amount_str, satuan = match.groups()
                    amount = float(amount_str.replace('.', '').replace(',', '.'))
                    if satuan in ['rb', 'ribu', 'k']:
                        amount *= 1000
                    elif satuan == 'juta':
                        amount *= 1000000
                    return int(amount), match.start(), match.end()
                else:
                    amount_str = match.group(1)
                    amount = int(amount_str.replace('.', ''))
                    return amount, match.start(), match.end()
        # 3 digits or more
        match = re.search(r'(\d{3,})', text_lower)
        if match:
            amount_str = match.group(1)
            amount = int(amount_str.replace('.', ''))
            return amount, match.start(), match.end()
        return None, None, None
    
    def classify_category(self, description):
        """
        Classify expense into a category based on description keywords.
        Returns the category name or 'Other'.
        """
        description_lower = description.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category.replace('_', ' ').title()
        
        return 'Other'
    
    def get_description(self, text, start_pos, end_pos):
        """
        Extract description by removing the amount part from the text.
        Cleans up common words.
        """
        before_amount = text[:start_pos].strip()
        after_amount = text[end_pos:].strip()
        
        # Combine and clean
        description = (before_amount + ' ' + after_amount).strip()
        
        # Remove common words
        remove_words = ['beli', 'bayar', 'untuk', 'ke', 'di', 'dengan', 'pakai', 'rb', 'ribu', 'k', 'juta']
        words = description.split()
        cleaned_words = [word for word in words if word.lower() not in remove_words]
        
        return ' '.join(cleaned_words).strip() or 'Pengeluaran'
    
    def get_or_create_user_worksheet(self, user_name):
        """
        Get or create a worksheet for a specific user.
        Worksheet name is based on the user's Telegram name.
        """
        try:
            ws_name = user_name.strip().title()
            try:
                ws = self.sh.worksheet(ws_name)
            except gspread.exceptions.WorksheetNotFound:
                ws = self.sh.add_worksheet(ws_name, rows=1000, cols=5)
                ws.update('A1:E1', [['Tanggal', 'Waktu', 'Jumlah', 'Keterangan', 'Kategori']])
                ws.format('A1:E1', {
                    "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                    "textFormat": {"bold": True}
                })
            return ws
        except Exception as e:
            logger.error(f"Error getting/creating worksheet for user {user_name}: {e}")
            return None

    def add_expense(self, amount, description, category, user_name):
        """
        Add an expense row to the user's worksheet in Google Sheets.
        Returns (success: bool, message: str).
        """
        if amount <= 0:
            return False, "Amount must be greater than zero."
        try:
            ws = self.get_or_create_user_worksheet(user_name)
            if not ws:
                return False, "Google Sheets is not available for this user. Check connection or credentials."
            # Get current datetime in Asia/Jakarta timezone
            jakarta = pytz.timezone('Asia/Jakarta')
            now = datetime.now(jakarta)
            date_str = self.format_tanggal_indo(now.strftime('%Y-%m-%d'))
            time_str = now.strftime('%H:%M:%S')
            row = [date_str, time_str, amount, description, category]
            try:
                ws.append_row(row)
            except Exception as e:
                # Retry once if failed
                logger.error(f"Error adding expense, retrying: {e}")
                try:
                    ws.append_row(row)
                except Exception as e2:
                    logger.error(f"Retry failed: {e2}")
                    return False, f"Failed to save to Google Sheets: {str(e2)}"
            return True, "Saved successfully"
        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            return False, f"Failed to save: {str(e)}"
        
    def get_monthly_summary(self, user_name=None, year=None, month=None):
        """
        Get monthly expense summary for a user (or main worksheet if user not found).
        Returns a formatted string summary.
        """
        try:
            ws = None
            if user_name:
                ws = self.get_or_create_user_worksheet(user_name)
            if not ws:
                ws = self.worksheet
            if not ws:
                return "Google Sheets is not available"
            # Get current month if not specified
            if not year or not month:
                now = datetime.now()
                year = year or now.year
                month = month or now.month
            records = ws.get_all_records()
            # Filter by month
            monthly_records = []
            for record in records:
                try:
                    date_obj = self.parse_tanggal_indo(record['Tanggal'])
                    if date_obj and date_obj.year == year and date_obj.month == month:
                        monthly_records.append(record)
                except:
                    continue
            if not monthly_records:
                return f"No data for {month}/{year}"
            total = sum(int(record['Jumlah']) for record in monthly_records)
            count = len(monthly_records)
            categories = {}
            for record in monthly_records:
                cat = record['Kategori']
                categories[cat] = categories.get(cat, 0) + int(record['Jumlah'])
            bulan_indo = [
                "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"
            ]
            nama_bulan = bulan_indo[month]
            response = f"📊 *Ringkasan Pengeluaran untuk Bulan {nama_bulan} {year}*\n\n"
            response += f"💰 Total: Rp {total:,}\n"
            response += f"📝 Jumlah transaksi: {count}\n"
            response += f"📈 Rata-rata per transaksi: Rp {total//count:,}\n\n"
            response += "*Berdasarkan Kategori:*\n"
            for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total) * 100
                response += f"• {cat}: Rp {amount:,} ({percentage:.1f}%)\n"
            return response
        except Exception as e:
            logger.error(f"Error getting monthly summary: {e}")
            return f"Error getting summary: {str(e)}"

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
    user = update.effective_user
    user_name = user.first_name or user.username or "Unknown"
    summary = expense_tracker.get_monthly_summary(user_name=user_name)
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
nonton, game, musik, cafe, restaurant, film, nongkrong

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

    # Validasi jumlah uang
    if amount is None:
        await update.message.reply_text(
            "❌ Tidak dapat mendeteksi jumlah uang.\n"
            "Contoh: 'beli beras 50rb' atau 'makan siang 25000'"
        )
        return
    if amount <= 0:
        await update.message.reply_text("❌ Jumlah uang tidak boleh nol atau negatif.")
        return

    # Get description
    description = expense_tracker.get_description(text, start_pos, end_pos)

    # Classify category
    category = expense_tracker.classify_category(description)

    # Add to spreadsheet
    success, message = expense_tracker.add_expense(amount, description, category, user_name)

    if success:
        # Ambil tanggal hari ini dalam format Indonesia
        jakarta = pytz.timezone('Asia/Jakarta')
        now = datetime.now(jakarta)
        tanggal_indo = expense_tracker.format_tanggal_indo(now.strftime('%Y-%m-%d'))
        response = f"""
✅ *Pengeluaran berhasil dicatat!*

💰 Jumlah: Rp {amount:,}
📝 Keterangan: {description}
📂 Kategori: {category}
👤 User: {user_name}
📅 Tanggal: {tanggal_indo}
Tersimpan ke Google Sheets!
        """
        # Ambil link Google Sheet dari .env
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

        keyboard = [
            [InlineKeyboardButton("📄 Buka Google Sheet", url=sheet_url)],
            [InlineKeyboardButton("📊 Lihat Ringkasan", callback_data="show_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(f"❌ Gagal menyimpan: {message}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Segera acknowledge callback

    # Kirim pesan loading dulu agar user tidak menunggu lama
    loading_message = await query.message.reply_text("⏳ Mengambil ringkasan, mohon tunggu...")

    try:
        user = query.from_user
        user_name = user.first_name or user.username or "Unknown"
        summary = expense_tracker.get_monthly_summary(user_name=user_name)
        # Edit pesan loading menjadi ringkasan
        await loading_message.edit_text(summary, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await loading_message.edit_text("❌ Gagal mengambil ringkasan.")
                
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
    bot_application.add_handler(CallbackQueryHandler(button_callback))
    
    # Handle all text messages as potential expense entries
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))
    
    # Add error handler
    bot_application.add_error_handler(error_handler)
    
    # Initialize bot
    await bot_application.initialize()
    
    # Set webhook
    ngrok_url = os.getenv('NGROK_URL')
    if ngrok_url:
        webhook_url = f"{ngrok_url}/{bot_token}"
    else:
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
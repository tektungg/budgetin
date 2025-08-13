import os
import re
import logging
from datetime import datetime, timezone
import hashlib
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
import json
import pytz
import pickle
from urllib.parse import quote
import hashlib

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
    Enhanced Budgetin with OAuth 2.0 support for user-specific Google Sheets
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
        
        # OAuth 2.0 configuration
        self.oauth_config = {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': os.getenv('OAUTH_REDIRECT_URI', 'urn:ietf:wg:oauth:2.0:oob'),
            'scopes': [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
        }
        
        # Store user credentials in memory (in production, use database)
        self.user_credentials = {}
        self.user_spreadsheets = {}  # Store spreadsheet IDs per user
        
        # Load saved credentials if exists
        self.load_user_credentials()

    def save_user_credentials(self):
        """Save user credentials to file"""
        try:
            with open('user_credentials.pkl', 'wb') as f:
                pickle.dump({
                    'credentials': self.user_credentials,
                    'spreadsheets': self.user_spreadsheets
                }, f)
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")

    def load_user_credentials(self):
        """Load user credentials from file"""
        try:
            with open('user_credentials.pkl', 'rb') as f:
                data = pickle.load(f)
                self.user_credentials = data.get('credentials', {})
                self.user_spreadsheets = data.get('spreadsheets', {})
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")

    def get_oauth_url(self, user_id):
        """Generate OAuth authorization URL for user"""
        try:
            flow = Flow.from_client_config({
                'web': {
                    'client_id': self.oauth_config['client_id'],
                    'client_secret': self.oauth_config['client_secret'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [self.oauth_config['redirect_uri']]
                }
            }, scopes=self.oauth_config['scopes'])
            
            flow.redirect_uri = self.oauth_config['redirect_uri']
            
            # Generate state with user_id for security
            state = f"{user_id}_{hashlib.md5(str(user_id).encode()).hexdigest()[:8]}"
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state
            )
            
            return auth_url, state
        except Exception as e:
            logger.error(f"Error generating OAuth URL: {e}")
            return None, None

    def exchange_code_for_credentials(self, code, user_id):
        """Exchange authorization code for credentials"""
        try:
            flow = Flow.from_client_config({
                'web': {
                    'client_id': self.oauth_config['client_id'],
                    'client_secret': self.oauth_config['client_secret'],
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [self.oauth_config['redirect_uri']]
                }
            }, scopes=self.oauth_config['scopes'])
            
            flow.redirect_uri = self.oauth_config['redirect_uri']
            flow.fetch_token(code=code)
            
            # Store credentials
            self.user_credentials[str(user_id)] = flow.credentials
            self.save_user_credentials()
            
            return True
        except Exception as e:
            logger.error(f"Error exchanging code: {e}")
            return False

    def get_user_credentials(self, user_id):
        """Get stored credentials for user"""
        creds = self.user_credentials.get(str(user_id))
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.save_user_credentials()
            except Exception as e:
                logger.error(f"Error refreshing credentials: {e}")
                return None
        return creds

    def create_user_spreadsheet(self, user_id, user_name):
        """Create a new spreadsheet for user in their Google Drive, inside 'Budgetin' folder"""
        try:
            creds = self.get_user_credentials(user_id)
            if not creds:
                return None

            gc = gspread.authorize(creds)
            drive_service = build('drive', 'v3', credentials=creds)  # Gunakan Google Drive API

            # 1. Cari folder 'Budgetin' di My Drive user, jika tidak ada maka buat
            folder_name = "Budgetin"
            folder_id = None
            results = drive_service.files().list(
                q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false",
                spaces='drive',
                fields="files(id, name)"
            ).execute()
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
            else:
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')

            # 2. Buat spreadsheet di root, lalu pindahkan ke folder
            spreadsheet_title = f"Budgetin - {user_name}"
            spreadsheet = gc.create(spreadsheet_title)

            # Pindahkan file ke folder
            drive_service.files().update(
                fileId=spreadsheet.id,
                addParents=folder_id,
                removeParents='root',
                fields='id, parents'
            ).execute()

            # Store spreadsheet ID
            self.user_spreadsheets[str(user_id)] = spreadsheet.id
            self.save_user_credentials()

            # Setup initial worksheet for current month
            self.setup_monthly_worksheet(user_id, datetime.now().year, datetime.now().month)

            logger.info(f"Created spreadsheet for user {user_id}: {spreadsheet.id} in folder {folder_id}")
            return spreadsheet.id

        except Exception as e:
            logger.error(f"Error creating spreadsheet for user {user_id}: {e}")
            return None        
        
    def get_user_spreadsheet(self, user_id):
        """Get user's spreadsheet, create if doesn't exist"""
        spreadsheet_id = self.user_spreadsheets.get(str(user_id))
        if not spreadsheet_id:
            return None
            
        try:
            creds = self.get_user_credentials(user_id)
            if not creds:
                return None
                
            gc = gspread.authorize(creds)
            return gc.open_by_key(spreadsheet_id)
        except Exception as e:
            logger.error(f"Error accessing spreadsheet for user {user_id}: {e}")
            return None

    def get_month_worksheet_name(self, year, month):
        """Generate worksheet name for specific month"""
        bulan_indo = [
            "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        return f"{bulan_indo[month]} {year}"

    def setup_monthly_worksheet(self, user_id, year, month):
        """Setup worksheet for specific month"""
        try:
            spreadsheet = self.get_user_spreadsheet(user_id)
            if not spreadsheet:
                return None
                
            ws_name = self.get_month_worksheet_name(year, month)
            
            # Try to get existing worksheet
            try:
                ws = spreadsheet.worksheet(ws_name)
                return ws
            except gspread.exceptions.WorksheetNotFound:
                # Create new worksheet
                ws = spreadsheet.add_worksheet(ws_name, rows=1000, cols=6)
                
                # Add headers
                headers = ['Tanggal', 'Waktu', 'Jumlah', 'Keterangan', 'Kategori', 'Notes']
                ws.update('A1:F1', [headers])
                
                # Format headers
                ws.format('A1:F1', {
                    "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                })
                
                # Set column widths
                ws.columns_auto_resize(0, 5)
                
                return ws
                
        except Exception as e:
            logger.error(f"Error setting up monthly worksheet: {e}")
            return None

    def format_tanggal_indo(self, tanggal_str):
        """Format date to Indonesian format"""
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
        """Parse Indonesian date format to datetime object"""
        bulan_map = {
            'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
            'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
        }
        try:
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
            return datetime.strptime(tanggal_str, '%Y-%m-%d')
        except Exception:
            return None

    def extract_amount(self, text):
        """Extract amount from text"""
        text_lower = text.lower().replace(',', '.')
        patterns = [
            r'(\d+(?:[\.,]\d+)?)(?:\s*)(rb|ribu|k|juta)',
            r'(\d{4,})'
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
        
        match = re.search(r'(\d{3,})', text_lower)
        if match:
            amount_str = match.group(1)
            amount = int(amount_str.replace('.', ''))
            return amount, match.start(), match.end()
        return None, None, None

    def classify_category(self, description):
        """Classify expense into category"""
        description_lower = description.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category.replace('_', ' ').title()
        
        return 'Other'

    def get_description(self, text, start_pos, end_pos):
        """Extract description by removing amount part"""
        before_amount = text[:start_pos].strip()
        after_amount = text[end_pos:].strip()
        
        description = (before_amount + ' ' + after_amount).strip()
        
        remove_words = ['beli', 'bayar', 'untuk', 'ke', 'di', 'dengan', 'pakai', 'rb', 'ribu', 'k', 'juta']
        words = description.split()
        cleaned_words = [word for word in words if word.lower() not in remove_words]
        
        return ' '.join(cleaned_words).strip() or 'Pengeluaran'

    def add_expense(self, user_id, amount, description, category):
        """Add expense to user's monthly worksheet"""
        if amount <= 0:
            return False, "Amount must be greater than zero."
        
        try:
            # Get current datetime in Asia/Jakarta timezone
            jakarta = pytz.timezone('Asia/Jakarta')
            now = datetime.now(jakarta)
            
            # Get or create monthly worksheet
            ws = self.setup_monthly_worksheet(user_id, now.year, now.month)
            if not ws:
                return False, "Could not access your Google Sheet. Please login again."
            
            # Prepare row data
            date_str = self.format_tanggal_indo(now.strftime('%Y-%m-%d'))
            time_str = now.strftime('%H:%M:%S')
            row = [date_str, time_str, amount, description, category, '']
            
            # Add to worksheet
            ws.append_row(row)
            
            # Format the new row
            last_row = len(ws.get_all_values())
            ws.format(f'A{last_row}:F{last_row}', {
                "borders": {
                    "top": {"style": "SOLID", "width": 1},
                    "bottom": {"style": "SOLID", "width": 1},
                    "left": {"style": "SOLID", "width": 1},
                    "right": {"style": "SOLID", "width": 1}
                }
            })
            
            return True, "Successfully saved"
            
        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            return False, f"Failed to save: {str(e)}"

    def get_monthly_summary(self, user_id, year=None, month=None):
        """Get monthly summary for user"""
        try:
            if not year or not month:
                now = datetime.now()
                year = year or now.year
                month = month or now.month
            
            ws = self.setup_monthly_worksheet(user_id, year, month)
            if not ws:
                return "Could not access your Google Sheet. Please login again."
            
            records = ws.get_all_records()
            
            if not records:
                ws_name = self.get_month_worksheet_name(year, month)
                return f"No expenses recorded for {ws_name}"
            
            total = sum(int(record.get('Jumlah', 0)) for record in records)
            count = len(records)
            
            categories = {}
            for record in records:
                cat = record.get('Kategori', 'Other')
                amount = int(record.get('Jumlah', 0))
                categories[cat] = categories.get(cat, 0) + amount
            
            ws_name = self.get_month_worksheet_name(year, month)
            response = f"📊 *Ringkasan Pengeluaran {ws_name}*\n\n"
            response += f"💰 Total: Rp {total:,}\n"
            response += f"📝 Jumlah transaksi: {count}\n"
            
            if count > 0:
                response += f"📈 Rata-rata per transaksi: Rp {total//count:,}\n\n"
            
            response += "*Berdasarkan Kategori:*\n"
            for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total) * 100 if total > 0 else 0
                response += f"• {cat}: Rp {amount:,} ({percentage:.1f}%)\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting monthly summary: {e}")
            return f"Error getting summary: {str(e)}"

    def is_user_authenticated(self, user_id):
        """Check if user is authenticated"""
        return str(user_id) in self.user_credentials and str(user_id) in self.user_spreadsheets

# Initialize Budgetin
expense_tracker = ExpenseTracker()

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"
    
    if expense_tracker.is_user_authenticated(user_id):
        welcome_text = f"""
🤖 *Selamat datang kembali, {user_name}!*

Bot Budgetin Anda sudah siap digunakan!

📝 *Cara mencatat pengeluaran:*
Kirim pesan dengan format bebas, contoh:
• "beli beras 50rb"
• "makan siang 25000"
• "bensin motor 30k"

📊 *Perintah tersedia:*
• /ringkasan - Lihat ringkasan bulan ini
• /sheet - Buka Google Sheet Anda
• /logout - Keluar dari akun Google
• /help - Bantuan lengkap

✨ Data Anda tersimpan otomatis di Google Sheet pribadi dengan worksheet terpisah per bulan!
        """
    else:
        welcome_text = f"""
🤖 *Selamat datang di Budgetin Bot, {user_name}!*

Bot ini akan membantu Anda mencatat pengeluaran secara otomatis ke Google Sheet pribadi Anda.

🔐 *Untuk memulai, Anda perlu login ke Google:*
Gunakan perintah /login untuk menghubungkan akun Google Anda

✨ *Fitur unggulan:*
• 📊 Google Sheet pribadi di Drive Anda
• 📅 Worksheet terpisah per bulan  
• 🤖 Deteksi otomatis jumlah dan kategori
• 📱 Interface interaktif dengan tombol
• 📈 Ringkasan bulanan otomatis

Ketik /login untuk memulai!
        """
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Login command to initiate OAuth"""
    user_id = update.effective_user.id
    
    if expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "✅ Anda sudah login! Gunakan /logout untuk keluar dari akun Google."
        )
        return
    
    # Generate OAuth URL
    auth_url, state = expense_tracker.get_oauth_url(user_id)
    
    if not auth_url:
        await update.message.reply_text(
            "❌ Maaf, terjadi kesalahan saat membuat link login. Silakan coba lagi nanti."
        )
        return
    
    # Store state for verification
    context.user_data['oauth_state'] = state
    
    keyboard = [[InlineKeyboardButton("🔗 Login ke Google", url=auth_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    login_text = """
🔐 *Login ke Google Account*

1. Klik tombol di bawah untuk login ke Google
2. Berikan izin akses ke Google Sheets dan Drive
3. Copy kode yang muncul
4. Kirim kode tersebut ke bot ini

*Catatan:* Bot tidak akan menyimpan password Anda, hanya token akses untuk Google Sheets.
    """
    
    await update.message.reply_text(
        login_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_oauth_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OAuth authorization code"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"
    code = update.message.text.strip()

    # Check if this looks like an OAuth code
    if not (len(code) > 20 and ('/' in code or '-' in code or '_' in code)):
        return False  # Not an OAuth code

    loading_msg = await update.message.reply_text("⏳ Memverifikasi kode dan membuat Google Sheet...")

    try:
        # Exchange code for credentials
        success = expense_tracker.exchange_code_for_credentials(code, user_id)

        if success:
            # Create user's spreadsheet
            spreadsheet_id = expense_tracker.create_user_spreadsheet(user_id, user_name)

            if spreadsheet_id:
                sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

                success_text = f"""
✅ *Login berhasil dan Google Sheet sudah dibuat!*

🎉 Selamat, {user_name}! Bot sudah terhubung dengan akun Google Anda.

📊 Google Sheet pribadi Anda: [Klik di sini]({sheet_url})

📅 *Fitur worksheet per bulan:*
Bot akan otomatis membuat worksheet baru setiap bulan dengan nama seperti "Januari 2025", "Februari 2025", dst.

🚀 *Mulai mencatat pengeluaran:*
Kirim pesan seperti: `beli sayur 15rb`, `isi bensin 50k`, dll.

Gunakan /help untuk melihat semua fitur!
                """

                keyboard = [
                    [InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)],
                    [InlineKeyboardButton("📋 Lihat Bantuan", callback_data="show_help")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await loading_msg.edit_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await loading_msg.edit_text(
                    "✅ *Login ke Google berhasil*, namun *gagal membuat Google Sheet baru* di Drive Anda.\n\n"
                    "🔄 Silakan coba /logout lalu /login ulang. Jika masalah berlanjut, pastikan akun Google Anda tidak melebihi batas quota Google Drive."
                )
        else:
            await loading_msg.edit_text(
                "❌ Kode tidak valid atau sudah kedaluwarsa.\n\n"
                "Silakan lakukan /login ulang dan pastikan Anda mengirim *kode* (bukan seluruh URL) yang didapat setelah login Google."
            )

    except Exception as e:
        logger.error(f"OAuth error: {e}")
        await loading_msg.edit_text(
            "❌ Terjadi kesalahan saat memproses login.\n\n"
            "Pastikan Anda mengirim *kode* (bukan seluruh URL) yang didapat setelah login Google.\n"
            "Jika masalah berlanjut, silakan coba /logout lalu /login ulang."
        )

    return True  # Indicates this was handled as OAuth code

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logout command"""
    user_id = update.effective_user.id
    
    if str(user_id) in expense_tracker.user_credentials:
        del expense_tracker.user_credentials[str(user_id)]
    if str(user_id) in expense_tracker.user_spreadsheets:
        del expense_tracker.user_spreadsheets[str(user_id)]
    
    expense_tracker.save_user_credentials()
    
    await update.message.reply_text(
        "✅ Anda telah logout dari Google Account. Gunakan /login untuk masuk kembali."
    )

async def sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open user's Google Sheet"""
    user_id = update.effective_user.id
    
    if not expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "❌ Anda belum login. Gunakan /login terlebih dahulu."
        )
        return
    
    spreadsheet_id = expense_tracker.user_spreadsheets.get(str(user_id))
    if spreadsheet_id:
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
        keyboard = [[InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 *Google Sheet Anda*\n\nKlik tombol di bawah untuk membuka:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ Google Sheet tidak ditemukan. Silakan /logout dan /login ulang."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
📋 *Bantuan Budgetin Bot*

🔐 *Autentikasi:*
• /login - Login ke Google Account
• /logout - Keluar dari akun Google  
• /sheet - Buka Google Sheet Anda

📝 *Cara mencatat pengeluaran:*
Kirim pesan dengan format bebas yang mengandung jumlah uang:
• "beli sayur 15rb"
• "isi bensin 50000" 
• "bayar listrik 200k"
• "makan di warteg 12ribu"

💰 *Format jumlah yang didukung:*
• 50rb, 50 rb, 50ribu, 50k
• 1.5juta, 2juta
• 50000 (angka biasa)
• 50.000 (dengan titik)

🏷️ *Kategori otomatis:*
• Daily Needs (makan, belanja, grocery)
• Transportation (bensin, ojek, grab)  
• Utilities (listrik, air, internet)
• Health (obat, dokter, RS)
• Urgent (darurat, mendadak)
• Entertainment (nonton, game, cafe)

📊 *Fitur laporan:*
• /ringkasan - Ringkasan bulan ini
• /kategori - Lihat semua kategori

✨ *Keunggulan:*
• Google Sheet pribadi di Drive Anda
• Worksheet terpisah per bulan otomatis
• Data aman dan terkontrol penuh oleh Anda
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summary command handler"""
    user_id = update.effective_user.id
    
    if not expense_tracker.is_user_authenticated(user_id):
        await update.message.reply_text(
            "❌ Anda belum login. Gunakan /login terlebih dahulu."
        )
        return
    
    loading_msg = await update.message.reply_text("⏳ Mengambil ringkasan...")
    
    summary = expense_tracker.get_monthly_summary(user_id)
    await loading_msg.edit_text(summary, parse_mode='Markdown')

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Categories command handler"""
    cat_text = """
📂 *Kategori Pengeluaran Otomatis:*

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
nonton, game, musik, cafe, restaurant, film

Bot akan mendeteksi kategori secara otomatis berdasarkan kata kunci dalam keterangan Anda.
    """
    await update.message.reply_text(cat_text, parse_mode='Markdown')

async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense input from messages"""
    text = update.message.text
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown"

    # Try to handle as OAuth code first (let user login tanpa harus /login ulang)
    if await handle_oauth_code(update, context):
        return

    # Check if user is authenticated
    if not expense_tracker.is_user_authenticated(user_id):
        keyboard = [[InlineKeyboardButton("🔗 Login ke Google", callback_data="start_login")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔐 Anda perlu login ke Google terlebih dahulu untuk mencatat pengeluaran.\n\n"
            "Klik tombol di bawah atau gunakan /login.\n\n"
            "*Tips:* Setelah login Google, *hanya kirim kode* (bukan seluruh URL) ke bot.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return

    # Extract amount from message
    amount, start_pos, end_pos = expense_tracker.extract_amount(text)

    if amount is None:
        await update.message.reply_text(
            "❌ Tidak dapat mendeteksi jumlah uang.\n\n"
            "💡 *Contoh format yang benar:*\n"
            "• `beli beras 50rb`\n"
            "• `makan siang 25000`\n"
            "• `bensin motor 30k`\n"
            "• `bayar listrik 200.000`\n\n"
            "*Tips:* Gunakan angka atau satuan seperti 'rb', 'k', 'ribu', atau 'juta'.",
            parse_mode='Markdown'
        )
        return

    if amount <= 0:
        await update.message.reply_text("❌ Jumlah uang tidak boleh nol atau negatif.")
        return

    # Get description and classify category
    description = expense_tracker.get_description(text, start_pos, end_pos)
    category = expense_tracker.classify_category(description)

    # Show loading message
    loading_msg = await update.message.reply_text("⏳ Menyimpan ke Google Sheet...")

    # Add to spreadsheet
    success, message = expense_tracker.add_expense(user_id, amount, description, category)

    if success:
        # Get current date in Indonesian format
        jakarta = pytz.timezone('Asia/Jakarta')
        now = datetime.now(jakarta)
        tanggal_indo = expense_tracker.format_tanggal_indo(now.strftime('%Y-%m-%d'))
        month_name = expense_tracker.get_month_worksheet_name(now.year, now.month)

        response = f"""
✅ *Pengeluaran berhasil dicatat!*

💰 *Jumlah:* Rp {amount:,}
📝 *Keterangan:* {description}
📂 *Kategori:* {category}
📅 *Tanggal:* {tanggal_indo}
📊 *Worksheet:* {month_name}

✨ Tersimpan ke Google Sheet pribadi Anda!
        """

        # Get user's spreadsheet URL
        spreadsheet_id = expense_tracker.user_spreadsheets.get(str(user_id))
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

        keyboard = [
            [InlineKeyboardButton("📊 Buka Google Sheet", url=sheet_url)],
            [InlineKeyboardButton("📈 Lihat Ringkasan", callback_data="show_summary")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await loading_msg.edit_text(response, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await loading_msg.edit_text(
            f"❌ Gagal menyimpan: {message}\n\n"
            "Pastikan Anda sudah login dan Google Sheet Anda dapat diakses."
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "start_login":
        # Trigger login process
        await login(update, context)  # <-- perbaiki di sini
        return
    
    if query.data == "show_summary":
        if not expense_tracker.is_user_authenticated(user_id):
            await query.message.reply_text(
                "❌ Anda perlu login terlebih dahulu. Gunakan /login"
            )
            return
            
        loading_message = await query.message.reply_text("⏳ Mengambil ringkasan...")
        
        try:
            summary = expense_tracker.get_monthly_summary(user_id)
            await loading_message.edit_text(summary, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            await loading_message.edit_text("❌ Gagal mengambil ringkasan.")
    
    elif query.data == "show_help":
        await help_command(query, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

# Flask app for webhook
from flask import Flask, request
import asyncio
import threading

flask_app = Flask(__name__)
bot_application = None

@flask_app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return "Budgetin Bot is running!", 200

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
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is required")
        return None
    
    bot_application = Application.builder().token(bot_token).build()
    
    # Add handlers
    bot_application.add_handler(CommandHandler("start", start))
    bot_application.add_handler(CommandHandler("help", help_command))
    bot_application.add_handler(CommandHandler("login", login))
    bot_application.add_handler(CommandHandler("logout", logout))
    bot_application.add_handler(CommandHandler("sheet", sheet))
    bot_application.add_handler(CommandHandler("ringkasan", summary_command))
    bot_application.add_handler(CommandHandler("kategori", categories_command))
    bot_application.add_handler(CallbackQueryHandler(button_callback))
    
    # Handle text messages (expenses and OAuth codes)
    bot_application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))
    
    # Add error handler
    bot_application.add_error_handler(error_handler)
    
    # Initialize bot
    await bot_application.initialize()
    
    # Set webhook
    ngrok_url = os.getenv('NGROK_URL')
    public_url = os.getenv('PUBLIC_URL')
    if public_url:
        webhook_url = f"{public_url}/{bot_token}"
    elif ngrok_url:
        webhook_url = f"{ngrok_url}/{bot_token}"
    else:
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'your-app-name.onrender.com')}/{bot_token}"

    await bot_application.bot.set_webhook(url=webhook_url)
    logger.info(f"Bot initialized with webhook: {webhook_url}")

    return bot_application

def main():
    """Main function to run the bot"""
    def setup_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_bot())
    
    bot_thread = threading.Thread(target=setup_bot_thread)
    bot_thread.daemon = True
    bot_thread.start()
    
    import time
    time.sleep(3)
    
    port = int(os.environ.get('PORT', 8080))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()
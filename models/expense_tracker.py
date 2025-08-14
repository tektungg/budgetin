import logging
import hashlib
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from datetime import datetime

from config import Config
from utils.date_utils import get_month_worksheet_name, format_tanggal_indo, get_jakarta_now

logger = logging.getLogger(__name__)

class ExpenseTracker:
    """
    Enhanced Budgetin with OAuth 2.0 support for user-specific Google Sheets
    """
    def __init__(self):
        # OAuth 2.0 configuration
        self.oauth_config = {
            'client_id': Config.GOOGLE_CLIENT_ID,
            'client_secret': Config.GOOGLE_CLIENT_SECRET,
            'redirect_uri': Config.OAUTH_REDIRECT_URI,
            'scopes': Config.OAUTH_SCOPES
        }
        
        # Store user credentials in memory (in production, use database)
        self.user_credentials = {}
        self.user_spreadsheets = {}  # Store spreadsheet IDs per user
        self.user_balances = {}  # Store user balances
        
        # Load saved credentials if exists
        self.load_user_credentials()

    def save_user_credentials(self):
        """Save user credentials to file"""
        try:
            with open(Config.USER_CREDENTIALS_FILE, 'wb') as f:
                pickle.dump({
                    'credentials': self.user_credentials,
                    'spreadsheets': self.user_spreadsheets,
                    'balances': self.user_balances
                }, f)
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")

    def load_user_credentials(self):
        """Load user credentials from file"""
        try:
            with open(Config.USER_CREDENTIALS_FILE, 'rb') as f:
                data = pickle.load(f)
                self.user_credentials = data.get('credentials', {})
                self.user_spreadsheets = data.get('spreadsheets', {})
                self.user_balances = data.get('balances', {})
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

    def setup_monthly_worksheet(self, user_id, year, month):
        """Setup worksheet for specific month"""
        try:
            spreadsheet = self.get_user_spreadsheet(user_id)
            if not spreadsheet:
                return None
                
            ws_name = get_month_worksheet_name(year, month)
            
            # Try to get existing worksheet
            try:
                ws = spreadsheet.worksheet(ws_name)
                return ws
            except gspread.exceptions.WorksheetNotFound:
                # Create new worksheet
                ws = spreadsheet.add_worksheet(ws_name, rows=1000, cols=7)
                
                # Add headers
                headers = ['Tanggal', 'Waktu', 'Jumlah', 'Keterangan', 'Kategori', 'Notes', 'Saldo']
                ws.update('A1:G1', [headers])
                
                # Format headers
                ws.format('A1:G1', {
                    "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                })
                
                # Set column widths
                ws.columns_auto_resize(0, 6)
                
                return ws
                
        except Exception as e:
            logger.error(f"Error setting up monthly worksheet: {e}")
            return None

    def add_expense(self, user_id, amount, description, category):
        """Add expense to user's monthly worksheet"""
        if amount <= 0:
            return False, "Amount must be greater than zero."
        
        try:
            # Get current datetime in Asia/Jakarta timezone
            now = get_jakarta_now()
            
            # Get or create monthly worksheet
            ws = self.setup_monthly_worksheet(user_id, now.year, now.month)
            if not ws:
                return False, "Could not access your Google Sheet. Please login again."
            
            # Update balance
            new_balance = self.subtract_balance(user_id, amount)
            
            # Prepare row data
            date_str = format_tanggal_indo(now.strftime('%Y-%m-%d'))
            time_str = now.strftime('%H:%M:%S')
            row = [date_str, time_str, amount, description, category, '', new_balance]
            
            # Add to worksheet
            ws.append_row(row)
            
            # Format the new row
            last_row = len(ws.get_all_values())
            ws.format(f'A{last_row}:G{last_row}', {
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
                ws_name = get_month_worksheet_name(year, month)
                return f"No expenses recorded for {ws_name}"
            
            total = sum(int(record.get('Jumlah', 0)) for record in records)
            count = len(records)
            
            categories = {}
            for record in records:
                cat = record.get('Kategori', 'Other')
                amount = int(record.get('Jumlah', 0))
                categories[cat] = categories.get(cat, 0) + amount
            
            ws_name = get_month_worksheet_name(year, month)
            response = f"📊 *Ringkasan Pengeluaran {ws_name}*\n\n"
            response += f"💰 Total pengeluaran: Rp {total:,}\n"
            response += f"💳 Saldo saat ini: Rp {self.get_user_balance(user_id):,}\n"
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

    def set_user_balance(self, user_id, balance):
        """Set initial balance for user"""
        self.user_balances[str(user_id)] = balance
        self.save_user_credentials()

    def get_user_balance(self, user_id):
        """Get current balance for user"""
        return self.user_balances.get(str(user_id), 0)

    def add_balance(self, user_id, amount):
        """Add amount to user balance"""
        current_balance = self.get_user_balance(user_id)
        new_balance = current_balance + amount
        self.user_balances[str(user_id)] = new_balance
        self.save_user_credentials()
        return new_balance

    def subtract_balance(self, user_id, amount):
        """Subtract amount from user balance"""
        current_balance = self.get_user_balance(user_id)
        new_balance = current_balance - amount
        self.user_balances[str(user_id)] = new_balance
        self.save_user_credentials()
        return new_balance

    def has_balance_set(self, user_id):
        """Check if user has set their balance"""
        return str(user_id) in self.user_balances

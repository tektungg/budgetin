import logging
import hashlib
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
from datetime import datetime, timedelta
import calendar
import time
from typing import Dict, List, Tuple, Optional

from config import Config
from utils.date_utils import get_month_worksheet_name, format_tanggal_indo, get_jakarta_now
from utils.error_handlers import retry_on_error, GoogleSheetsErrorHandler, rate_limiter, validate_user_input

# Import new models
from models.budget_planner import BudgetPlanner
from models.smart_alerts import SmartAlertSystem
from models.anomaly_detector import AnomalyDetector
from models.spending_analytics import SpendingAnalytics

logger = logging.getLogger(__name__)

class ExpenseTracker:
    """
    Enhanced Budgetin with OAuth 2.0 support for user-specific Google Sheets
    Now includes Budget Planning, Smart Alerts, Anomaly Detection, and Analytics
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
        
        # Initialize new smart features
        self.budget_planner = BudgetPlanner()
        self.alert_system = SmartAlertSystem(self.budget_planner)
        self.anomaly_detector = AnomalyDetector()
        self.analytics = SpendingAnalytics()
        
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

    @retry_on_error(max_retries=3, delay=3.0, timeout_delay=8.0)
    def create_user_spreadsheet(self, user_id, user_name):
        """Create a new spreadsheet for user in their Google Drive, inside 'Budgetin' folder with timeout handling"""
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
        """Add expense to user's monthly worksheet with enhanced error handling"""
        
        # Rate limiting check
        allowed, message = rate_limiter.is_allowed(user_id)
        if not allowed:
            return False, message
        
        # Input validation
        valid_input, validation_message = validate_user_input(description)
        if not valid_input:
            return False, validation_message
            
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
            
            # Add to worksheet with retry mechanism
            self._append_row_with_retry(ws, row)
            
            # Format the new row
            try:
                last_row = len(ws.get_all_values())
                ws.format(f'A{last_row}:G{last_row}', {
                    "borders": {
                        "top": {"style": "SOLID", "width": 1},
                        "bottom": {"style": "SOLID", "width": 1},
                        "left": {"style": "SOLID", "width": 1},
                        "right": {"style": "SOLID", "width": 1}
                    }
                })
            except Exception as format_error:
                # Formatting error shouldn't fail the entire operation
                logger.warning(f"Failed to format row: {format_error}")
            
            return True, "Successfully saved"
            
        except Exception as e:
            logger.error(f"Error adding expense: {e}")
            success, error_message = GoogleSheetsErrorHandler.handle_api_error(e)
            return success, error_message
    
    @retry_on_error(max_retries=3, delay=2.0, timeout_delay=5.0)
    def _append_row_with_retry(self, worksheet, row):
        """Append row to worksheet with enhanced retry mechanism and timeout handling"""
        try:
            worksheet.append_row(row)
            logger.info(f"Successfully appended row to worksheet")
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                logger.warning(f"Timeout when appending row: {e}")
                raise  # Will be caught by retry decorator
            elif "quota" in error_str or "rate" in error_str:
                logger.warning(f"Rate limit when appending row: {e}")
                raise  # Will be caught by retry decorator
            else:
                logger.error(f"Error appending row: {e}")
                raise

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
                # Calculate average per day in the month
                days_in_month = calendar.monthrange(year, month)[1]
                avg_per_day = total / days_in_month
                response += f"📈 Pengeluaran rata-rata per hari: Rp {avg_per_day:,.0f}\n\n"
            
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
    
    # === NEW SMART FEATURES ===
    
    def get_user_expenses_data(self, user_id: str, days_back: int = 30) -> List[Dict]:
        """Get user expenses data for analytics (from current month worksheet)"""
        try:
            now = get_jakarta_now()
            ws = self.setup_monthly_worksheet(user_id, now.year, now.month)
            if not ws:
                return []
            
            records = ws.get_all_records()
            expenses = []
            
            for record in records:
                try:
                    # Convert record to our format
                    expense_data = {
                        'amount': int(record.get('Jumlah', 0)),
                        'description': record.get('Keterangan', ''),
                        'category': record.get('Kategori', 'Other'),
                        'date': record.get('Tanggal', ''),
                        'time': record.get('Waktu', ''),
                        'datetime': self._parse_expense_datetime(record.get('Tanggal', ''), record.get('Waktu', ''))
                    }
                    
                    # Filter by days_back if specified
                    if days_back > 0:
                        cutoff_date = now - timedelta(days=days_back)
                        if expense_data['datetime'] >= cutoff_date:
                            expenses.append(expense_data)
                    else:
                        expenses.append(expense_data)
                        
                except Exception as e:
                    logger.warning(f"Error parsing expense record: {e}")
                    continue
            
            return expenses
            
        except Exception as e:
            logger.error(f"Error getting user expenses data: {e}")
            return []
    
    def _parse_expense_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse datetime from Indonesian date format"""
        try:
            # This is a simplified parser - you may need to enhance based on your date format
            # For now, return current time as fallback
            return get_jakarta_now()
        except:
            return get_jakarta_now()
    
    def add_expense_with_smart_features(self, user_id: str, amount: int, description: str, category: str) -> Tuple[bool, str, Dict]:
        """Enhanced add_expense with smart features"""
        
        # First, add expense normally
        success, message = self.add_expense(user_id, amount, description, category)
        
        smart_insights = {
            'budget_alert': None,
            'anomaly_detection': None,
            'spending_velocity_alert': None,
            'weekend_alert': None
        }
        
        if not success:
            return success, message, smart_insights
        
        try:
            # Get user's recent expenses for analysis
            user_expenses = self.get_user_expenses_data(user_id, days_back=30)
            
            # 1. Check Budget Alerts
            budget_alert = self.alert_system.check_budget_alerts(user_id, category, amount)
            if budget_alert:
                smart_insights['budget_alert'] = budget_alert
            
            # 2. Check Anomaly Detection
            new_expense = {
                'amount': amount,
                'category': category,
                'description': description,
                'time': get_jakarta_now().strftime('%H:%M:%S'),
                'datetime': get_jakarta_now()
            }
            
            anomaly_report = self.anomaly_detector.get_comprehensive_anomaly_report(
                user_id, user_expenses, new_expense
            )
            
            if anomaly_report['has_anomalies']:
                smart_insights['anomaly_detection'] = anomaly_report
            
            # 3. Check Spending Velocity Alert
            velocity_alert = self.alert_system.check_spending_velocity_alert(user_id, user_expenses[-10:])
            if velocity_alert:
                smart_insights['spending_velocity_alert'] = velocity_alert
            
            # 4. Check Weekend Spending Alert
            weekend_alert = self.alert_system.check_weekend_spending_alert(user_id, amount, category)
            if weekend_alert:
                smart_insights['weekend_alert'] = weekend_alert
            
        except Exception as e:
            logger.error(f"Error in smart features analysis: {e}")
        
        return success, message, smart_insights
    
    def get_budget_status_for_category(self, user_id: str, category: str) -> Dict:
        """Get budget status for specific category"""
        try:
            # Get current month expenses for this category
            user_expenses = self.get_user_expenses_data(user_id, days_back=30)
            category_expenses = [e for e in user_expenses if e['category'] == category]
            total_spent = sum(e['amount'] for e in category_expenses)
            
            return self.budget_planner.get_budget_status(user_id, category, total_spent)
        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return {'status': 'error', 'message': f'Error: {str(e)}'}
    
    def get_monthly_insights_report(self, user_id: str) -> str:
        """Generate comprehensive monthly insights report"""
        try:
            user_expenses = self.get_user_expenses_data(user_id, days_back=30)
            return self.analytics.generate_monthly_insights_report(user_expenses, user_id)
        except Exception as e:
            logger.error(f"Error generating insights report: {e}")
            return f"❌ Error generating report: {str(e)}"
    
    def get_spending_trends(self, user_id: str, months_back: int = 6) -> Dict:
        """Get spending trends analysis"""
        try:
            # For now, get current month data - can be enhanced to get multiple months
            user_expenses = self.get_user_expenses_data(user_id, days_back=months_back * 30)
            return self.analytics.get_monthly_trends(user_expenses, months_back)
        except Exception as e:
            logger.error(f"Error getting spending trends: {e}")
            return {'error': f'Error: {str(e)}'}
    
    def get_category_insights(self, user_id: str, period_days: int = 30) -> Dict:
        """Get detailed category insights"""
        try:
            user_expenses = self.get_user_expenses_data(user_id, days_back=period_days)
            return self.analytics.get_category_insights(user_expenses, period_days)
        except Exception as e:
            logger.error(f"Error getting category insights: {e}")
            return {'error': f'Error: {str(e)}'}
    
    def get_daily_summary_with_alerts(self, user_id: str) -> Dict:
        """Get daily summary with smart alerts"""
        try:
            # Get today's expenses
            user_expenses = self.get_user_expenses_data(user_id, days_back=1)
            today_expenses = []
            today = get_jakarta_now().date()
            
            for expense in user_expenses:
                if expense['datetime'].date() == today:
                    today_expenses.append(expense)
            
            return self.alert_system.generate_daily_reminder(user_id, today_expenses)
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {'error': f'Error: {str(e)}'}
    
    def get_weekly_budget_review(self, user_id: str) -> Dict:
        """Get weekly budget review"""
        try:
            # Get last 7 days expenses
            user_expenses = self.get_user_expenses_data(user_id, days_back=7)
            
            # Group by category
            weekly_expenses = {}
            for expense in user_expenses:
                category = expense['category']
                weekly_expenses[category] = weekly_expenses.get(category, 0) + expense['amount']
            
            return self.alert_system.get_weekly_budget_review(user_id, weekly_expenses)
        except Exception as e:
            logger.error(f"Error getting weekly review: {e}")
            return {'error': f'Error: {str(e)}'}

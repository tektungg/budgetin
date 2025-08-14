import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Budgetin Bot"""
    
    # Bot Configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8080')
    
    # OAuth Scopes
    OAUTH_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    # Webhook Configuration
    NGROK_URL = os.getenv('NGROK_URL')
    PUBLIC_URL = os.getenv('PUBLIC_URL')
    PORT = int(os.environ.get('PORT', 8080))
    
    # File paths
    USER_CREDENTIALS_FILE = 'user_credentials.pkl'
    
    # Categories for expense classification
    CATEGORIES = {
        'daily_needs': ['makan', 'minum', 'beras', 'sayur', 'buah', 'daging', 'ikan', 'telur', 'susu', 'roti', 'nasi', 'lauk', 'snack', 'cemilan', 'grocery', 'belanja', 'pasar', 'supermarket'],
        'transportation': ['bensin', 'ojek', 'grab', 'gojek', 'taxi', 'bus', 'kereta', 'parkir', 'tol', 'transport'],
        'utilities': ['listrik', 'air', 'internet', 'wifi', 'pulsa', 'token', 'pln', 'pdam', 'indihome'],
        'health': ['obat', 'dokter', 'rumah sakit', 'rs', 'klinik', 'vitamin', 'medical', 'kesehatan'],
        'urgent': ['darurat', 'urgent', 'penting', 'mendadak', 'emergency'],
        'entertainment': ['nonton', 'bioskop', 'game', 'musik', 'streaming', 'netflix', 'spotify', 'hiburan', 'jalan', 'mall', 'cafe', 'restaurant', 'film', 'nongkrong']
    }

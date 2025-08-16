import logging
import time
from functools import wraps
from typing import Callable, Any, Tuple

logger = logging.getLogger(__name__)

def retry_on_error(max_retries: int = 3, delay: float = 1.0, timeout_delay: float = 5.0):
    """Enhanced decorator untuk retry operasi yang gagal dengan timeout handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Log attempt with error type
                    if "timeout" in error_str or "timed out" in error_str:
                        logger.warning(f"Timeout on attempt {attempt + 1} for {func.__name__}: {e}")
                    elif "quota" in error_str or "rate" in error_str:
                        logger.warning(f"Rate limit on attempt {attempt + 1} for {func.__name__}: {e}")
                    else:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    
                    if attempt < max_retries - 1:
                        # Different backoff strategies for different error types
                        if "timeout" in error_str or "timed out" in error_str:
                            sleep_time = timeout_delay * (attempt + 1)  # Linear backoff for timeouts
                        elif "quota" in error_str or "rate" in error_str:
                            sleep_time = delay * (3 ** attempt)  # Aggressive backoff for rate limits
                        else:
                            sleep_time = delay * (2 ** attempt)  # Exponential backoff for others
                        
                        logger.info(f"Waiting {sleep_time:.1f}s before retry {attempt + 2}/{max_retries}")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator

class GoogleSheetsErrorHandler:
    """Enhanced error handling for Google Sheets operations"""
    
    @staticmethod
    def handle_api_error(error: Exception) -> Tuple[bool, str]:
        """Convert API errors to user-friendly messages"""
        error_str = str(error).lower()
        
        if "quota" in error_str or "rate" in error_str:
            return False, "⚠️ Google API sedang sibuk. Coba lagi dalam 1-2 menit."
        
        elif "permission" in error_str or "forbidden" in error_str:
            return False, "❌ Akses ditolak. Silakan /logout dan /login ulang."
        
        elif "not found" in error_str:
            return False, "❌ Google Sheet tidak ditemukan. Silakan /logout dan /login ulang."
        
        elif "network" in error_str or "connection" in error_str:
            return False, "🌐 Masalah koneksi internet. Pastikan koneksi stabil dan coba lagi."
        
        elif "invalid" in error_str and "credentials" in error_str:
            return False, "🔑 Token akses kedaluwarsa. Silakan /logout dan /login ulang."
        
        else:
            logger.error(f"Unhandled API error: {error}")
            return False, f"❌ Terjadi kesalahan: {str(error)[:100]}..."

class RateLimiter:
    """Simple rate limiter per user"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.user_requests = {}
    
    def is_allowed(self, user_id: str) -> tuple[bool, str]:
        """Check if user is within rate limit"""
        current_time = time.time()
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_requests:
            self.user_requests[user_id_str] = []
        
        # Remove old requests outside time window
        self.user_requests[user_id_str] = [
            req_time for req_time in self.user_requests[user_id_str]
            if current_time - req_time < self.time_window
        ]
        
        # Check if within limit
        if len(self.user_requests[user_id_str]) >= self.max_requests:
            return False, f"⚠️ Terlalu banyak permintaan. Coba lagi dalam {self.time_window} detik."
        
        # Add current request
        self.user_requests[user_id_str].append(current_time)
        return True, ""

# Global rate limiter instance
rate_limiter = RateLimiter()

def validate_user_input(text: str) -> tuple[bool, str]:
    """Validate user input for security"""
    if len(text) > 1000:
        return False, "❌ Pesan terlalu panjang (maksimal 1000 karakter)."
    
    # Check for potential malicious content
    malicious_patterns = ['<script', 'javascript:', 'eval(', 'exec(']
    if any(pattern in text.lower() for pattern in malicious_patterns):
        return False, "❌ Input mengandung konten yang tidak diizinkan."
    
    return True, ""

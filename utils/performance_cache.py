# Quick Performance Cache for Expense Tracker

import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """Simple cache to reduce repeated Google API calls"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires']:
                logger.debug(f"Cache HIT for key: {key}")
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"Cache EXPIRED for key: {key}")
        
        logger.debug(f"Cache MISS for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache[key] = {
            'value': value,
            'expires': time.time() + ttl
        }
        logger.debug(f"Cache SET for key: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache DELETE for key: {key}")
    
    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
        logger.debug("Cache CLEARED")
    
    def size(self) -> int:
        """Get current cache size"""
        # Clean expired entries first
        current_time = time.time()
        expired_keys = [k for k, v in self._cache.items() if current_time >= v['expires']]
        for key in expired_keys:
            del self._cache[key]
        
        return len(self._cache)

# Global cache instance
performance_cache = SimpleCache(default_ttl=180)  # 3 minutes cache

def cache_key_for_user_balance(user_id: str) -> str:
    """Generate cache key for user balance"""
    return f"balance_{user_id}"

def cache_key_for_worksheet(user_id: str, year: int, month: int) -> str:
    """Generate cache key for worksheet reference"""
    return f"worksheet_{user_id}_{year}_{month}"

def cache_key_for_spreadsheet(user_id: str) -> str:
    """Generate cache key for spreadsheet reference"""
    return f"spreadsheet_{user_id}"

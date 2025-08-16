# Timeout Fix Wrapper

import asyncio
import logging
from typing import Callable, Any, Tuple

logger = logging.getLogger(__name__)

async def run_with_timeout_protection(operation_func: Callable, 
                                    operation_args: tuple = (), 
                                    operation_kwargs: dict = None,
                                    operation_name: str = "operation",
                                    timeout_seconds: int = 25) -> Tuple[bool, Any]:
    """
    Run an operation with timeout protection for Telegram bot operations
    
    Args:
        operation_func: Function to execute
        operation_args: Arguments for the function
        operation_kwargs: Keyword arguments for the function
        operation_name: Name of operation for logging
        timeout_seconds: Timeout in seconds
    
    Returns:
        Tuple of (success: bool, result: Any)
    """
    if operation_kwargs is None:
        operation_kwargs = {}
    
    try:
        # Run the operation in an executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: operation_func(*operation_args, **operation_kwargs)),
            timeout=timeout_seconds
        )
        return True, result
    
    except asyncio.TimeoutError:
        logger.warning(f"Timeout occurred during {operation_name} after {timeout_seconds}s")
        return False, f"⏰ Operasi {operation_name} timeout - silakan coba lagi"
    
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Error during {operation_name}: {e}")
        
        if "timeout" in error_str or "timed out" in error_str:
            return False, f"⏰ {operation_name} timeout - silakan coba lagi"
        elif "quota" in error_str or "rate" in error_str:
            return False, "⚠️ Google API sedang sibuk - tunggu 1-2 menit lalu coba lagi"
        elif "network" in error_str or "connection" in error_str:
            return False, "🌐 Masalah koneksi - pastikan internet stabil"
        else:
            return False, f"❌ Terjadi kesalahan: {str(e)[:100]}"

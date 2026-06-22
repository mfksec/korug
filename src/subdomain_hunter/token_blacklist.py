"""Token blacklist/revocation system for logout and security."""
from datetime import datetime, timezone
from typing import Dict
import threading

# Thread-safe in-memory token blacklist
# In production, use Redis or database for distributed systems
_blacklist: Dict[str, float] = {}
_lock = threading.Lock()


def add_to_blacklist(token: str, expires_at: datetime) -> None:
    """Add token to blacklist (e.g., on logout).
    
    Args:
        token: JWT token to blacklist
        expires_at: Token expiration time (auto-cleanup after this)
    """
    with _lock:
        # Store expiration timestamp for automatic cleanup
        _blacklist[token] = expires_at.timestamp()


def is_blacklisted(token: str) -> bool:
    """Check if token is blacklisted.
    
    Args:
        token: JWT token to check
        
    Returns:
        True if token is blacklisted, False otherwise
    """
    with _lock:
        if token not in _blacklist:
            return False
        
        # Check if blacklist entry has expired (cleanup)
        expiration = _blacklist[token]
        if datetime.now(timezone.utc).timestamp() > expiration:
            del _blacklist[token]
            return False
        
        return True


def cleanup_expired_tokens() -> int:
    """Remove expired tokens from blacklist.
    
    Returns:
        Number of tokens cleaned up
    """
    with _lock:
        now = datetime.now(timezone.utc).timestamp()
        expired = [token for token, exp_time in _blacklist.items() if now > exp_time]
        
        for token in expired:
            del _blacklist[token]
        
        return len(expired)


def get_blacklist_stats() -> Dict[str, int]:
    """Get blacklist statistics for monitoring.
    
    Returns:
        Dictionary with blacklist size and expired count
    """
    with _lock:
        now = datetime.now(timezone.utc).timestamp()
        expired_count = sum(1 for exp_time in _blacklist.values() if now > exp_time)
        return {
            "total_blacklisted": len(_blacklist),
            "expired_entries": expired_count,
            "active_entries": len(_blacklist) - expired_count
        }

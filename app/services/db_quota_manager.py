"""
Database-driven quota management with intelligent caching
Uses client_api_access table for dynamic rate limiting with smart cache management
"""
from fastapi import HTTPException, Request
from typing import Dict, Optional
from datetime import datetime, timedelta
import time
from .rate_limit_cache import rate_limit_cache, CachedRateLimit
from .db_access_control import ClientAPIAccess, resolve_client_with_db_access_control, update_usage_stats
from .security_monitor import security_monitor
from .security_event_logger import security_logger
import asyncio

# In-memory usage tracking for rate limiting windows
# Format: {api_key: {minute: [], hour: [], day: []}}
usage_windows: Dict[str, Dict[str, list]] = {}

class DatabaseQuotaManager:
    """Quota manager using database-driven limits with intelligent caching"""
    
    def __init__(self):
        self.cache_manager = rate_limit_cache
    
    async def check_rate_limits_cached(self, api_key: str) -> tuple[bool, str, Optional[CachedRateLimit]]:
        """Check rate limits using cached database configuration"""
        
        # Get cached rate limit configuration
        cached_config = await self.cache_manager.get_rate_limit_config(api_key)
        
        if not cached_config:
            return False, "Invalid API key", None
        
        # Check account validity from cache
        is_valid, reason = cached_config.is_account_valid()
        if not is_valid:
            return False, reason, cached_config
        
        # If admin override is enabled, skip all limits
        if cached_config.override_all_limits:
            return True, "", cached_config
        
        now = datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Initialize tracking for this API key
        if api_key not in usage_windows:
            usage_windows[api_key] = {
                "minute": [],
                "hour": [],
                "day": []
            }
        
        windows = usage_windows[api_key]
        
        # Clean old timestamps
        self._cleanup_old_timestamps(windows, current_minute, current_hour, current_day)
        
        # Get limits from cached configuration
        limits = cached_config.get_rate_limits()
        
        # Check minute limit
        minute_count = len(windows["minute"])
        if minute_count >= limits["requests_per_minute"]:
            return False, f"Rate limit exceeded: {limits['requests_per_minute']} requests per minute", cached_config
        
        # Check hour limit
        hour_count = len(windows["hour"])
        if hour_count >= limits["requests_per_hour"]:
            return False, f"Rate limit exceeded: {limits['requests_per_hour']} requests per hour", cached_config
        
        # Check day limit
        day_count = len(windows["day"])
        if day_count >= limits["requests_per_day"]:
            return False, f"Rate limit exceeded: {limits['requests_per_day']} requests per day", cached_config
        
        return True, "", cached_config
    
    def record_request_cached(self, cached_config: CachedRateLimit):
        """Record a successful API request using cached config"""
        api_key = cached_config.api_key
        
        if cached_config.override_all_limits:
            return  # Skip tracking for unlimited accounts
        
        now = datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Initialize if needed
        if api_key not in usage_windows:
            usage_windows[api_key] = {
                "minute": [],
                "hour": [], 
                "day": []
            }
        
        windows = usage_windows[api_key]
        
        # Record timestamps
        windows["minute"].append(current_minute.isoformat())
        windows["hour"].append(current_hour.isoformat())
        windows["day"].append(current_day.isoformat())
        
        # Update database usage stats asynchronously (don't block the request)
        import asyncio
        try:
            asyncio.create_task(update_usage_stats(api_key, success=True))
        except Exception:
            pass  # Don't fail request if usage stats update fails
    
    def _cleanup_old_timestamps(self, windows: Dict[str, list], current_minute, current_hour, current_day):
        """Remove old timestamps to prevent memory leaks"""
        minute_cutoff = current_minute - timedelta(minutes=2)
        hour_cutoff = current_hour - timedelta(hours=2)
        day_cutoff = current_day - timedelta(days=2)
        
        # Clean minute window
        windows["minute"] = [
            ts for ts in windows["minute"]
            if datetime.fromisoformat(ts) > minute_cutoff
        ]
        
        # Clean hour window  
        windows["hour"] = [
            ts for ts in windows["hour"]
            if datetime.fromisoformat(ts) > hour_cutoff
        ]
        
        # Clean day window
        windows["day"] = [
            ts for ts in windows["day"]
            if datetime.fromisoformat(ts) > day_cutoff
        ]
    
    def get_usage_stats_cached(self, cached_config: CachedRateLimit) -> Dict:
        """Get current usage statistics using cached config"""
        api_key = cached_config.api_key
        
        if api_key not in usage_windows:
            current_usage = {"minute": 0, "hour": 0, "day": 0}
        else:
            windows = usage_windows[api_key]
            current_usage = {
                "minute": len(windows.get("minute", [])),
                "hour": len(windows.get("hour", [])),
                "day": len(windows.get("day", []))
            }
        
        limits = cached_config.get_rate_limits()
        
        return {
            "client_id": cached_config.client_id,
            "access_tier": cached_config.access_tier,
            "current_usage": current_usage,
            "limits": limits,
            "cache_info": {
                "cached_at": cached_config.cached_at.isoformat(),
                "last_refreshed": cached_config.last_refreshed.isoformat(),
                "refresh_count": cached_config.refresh_count
            },
            "account_status": {
                "is_active": cached_config.is_active,
                "is_suspended": cached_config.is_suspended,
                "is_auto_blocked": cached_config.is_auto_blocked,
                "override_limits": cached_config.override_all_limits
            }
        }

# Global instance
db_quota_manager = DatabaseQuotaManager()

async def resolve_client_with_db_quota_check_cached(request: Request) -> CachedRateLimit:
    """Enhanced authentication with cached database-driven quota checking"""
    start_time = time.time()
    client_ip = request.headers.get("x-forwarded-for", 
                                  request.client.host if request.client else "unknown")
    
    # Get API key from request
    api_key = request.query_params.get("key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        # Check rate limits using cached database configuration
        can_proceed, limit_reason, cached_config = await db_quota_manager.check_rate_limits_cached(api_key)
        
        if not cached_config:
            # Invalid API key
            security_monitor.log_suspicious_activity(
                "INVALID_API_KEY",
                client_ip,
                {"api_key": api_key[:8] + "...", "endpoint": request.url.path}
            )
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        if not can_proceed:
            # Log quota exceeded event
            security_monitor.log_suspicious_activity(
                "QUOTA_EXCEEDED",
                client_ip,
                {
                    "api_key": cached_config.api_key[:8] + "...",
                    "tier": cached_config.access_tier,
                    "limit_reason": limit_reason,
                    "client_id": cached_config.client_id
                }
            )
            
            # Log to database asynchronously - determine limit type and actual count
            limit_type = "MINUTE" if "minute" in limit_reason else ("HOUR" if "hour" in limit_reason else "DAY")
            # Extract numbers from limit_reason (format like "20 requests per minute")
            import re
            numbers = re.findall(r'\d+', limit_reason)
            actual_requests = int(numbers[0]) if numbers else 0
            limit_value = int(numbers[1]) if len(numbers) > 1 else 0
            
            asyncio.create_task(security_logger.log_rate_limit_violation(
                api_key=cached_config.api_key,
                client_id=cached_config.client_id,
                source_ip=client_ip,
                limit_type=limit_type,
                limit_value=limit_value,
                actual_requests=actual_requests,
                access_tier=cached_config.access_tier,
                requests_per_minute=cached_config.requests_per_minute,
                requests_per_hour=cached_config.requests_per_hour,
                requests_per_day=cached_config.requests_per_day,
                endpoint=request.url.path,
                user_agent=request.headers.get('user-agent')
            ))
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": limit_reason,
                    "tier": cached_config.access_tier,
                    "limits": cached_config.get_rate_limits()
                }
            )
        
        # Record the successful request
        db_quota_manager.record_request_cached(cached_config)
        
        # Log successful API usage
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=request.url.path,
            ip=client_ip,
            response_code=200,
            response_time=response_time
        )
        
        return cached_config
        
    except HTTPException:
        # Re-raise HTTP exceptions (auth failures, rate limits, etc.)
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=api_key,
            endpoint=request.url.path,
            ip=client_ip,
            response_code=429,  # Assuming rate limit error
            response_time=response_time
        )
        raise
    except Exception as e:
        # Handle unexpected errors
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=api_key,
            endpoint=request.url.path,
            ip=client_ip,
            response_code=500,
            response_time=response_time
        )
        raise HTTPException(status_code=500, detail=f"Quota check error: {str(e)}")

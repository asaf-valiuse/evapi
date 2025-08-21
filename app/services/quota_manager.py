"""
Enhanced authentication with usage tracking and quotas
"""
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from typing import Dict, Optional
import time
from datetime import datetime, timedelta
import json
import os

# In-memory usage tracking (consider Redis for production)
usage_tracker: Dict[str, Dict] = {}

class APIKeyQuotaManager:
    def __init__(self):
        # Daily limits - reasonable for 1 call/minute usage pattern
        self.daily_limits = {
            "free": 50,        # ~50 calls/day for free users
            "basic": 200,      # ~200 calls/day (3+ hours of usage)
            "premium": 500,    # ~500 calls/day (8+ hours of usage)
            "enterprise": 1500 # ~1500 calls/day (24+ hours of usage)
        }
        # Per-minute limits - strict since normal usage is 1/minute
        self.minute_limits = {
            "free": 2,         # Allow 2/minute for free (some tolerance)
            "basic": 3,        # Allow 3/minute for basic (some tolerance)  
            "premium": 5,      # Allow 5/minute for premium (more tolerance)
            "enterprise": 10   # Allow 10/minute for enterprise (burst capability)
        }
    
    def get_client_tier(self, client_id: int) -> str:
        """Get client tier from database - implement based on your schema"""
        # TODO: Implement actual database lookup
        # For now, return 'basic' as default
        return "basic"
    
    def check_quota(self, api_key: str, client_id: int) -> bool:
        """Check if client has exceeded their quota"""
        now = datetime.now()
        today = now.date()
        current_minute = now.replace(second=0, microsecond=0)
        
        # Initialize tracking for this API key
        if api_key not in usage_tracker:
            usage_tracker[api_key] = {
                "daily": {},
                "minute": {},
                "total_requests": 0,
                "client_id": client_id
            }
        
        tracker = usage_tracker[api_key]
        client_tier = self.get_client_tier(client_id)
        
        # Clean old data
        self._cleanup_old_data(tracker, today, current_minute)
        
        # Check daily limit
        daily_count = tracker["daily"].get(str(today), 0)
        if daily_count >= self.daily_limits.get(client_tier, 100):
            return False
        
        # Check minute limit
        minute_count = tracker["minute"].get(current_minute.isoformat(), 0)
        if minute_count >= self.minute_limits.get(client_tier, 2):
            return False
        
        return True
    
    def record_request(self, api_key: str, client_id: int):
        """Record a successful API request"""
        now = datetime.now()
        today = now.date()
        current_minute = now.replace(second=0, microsecond=0)
        
        if api_key not in usage_tracker:
            usage_tracker[api_key] = {
                "daily": {},
                "minute": {},
                "total_requests": 0,
                "client_id": client_id
            }
        
        tracker = usage_tracker[api_key]
        
        # Update counters
        tracker["daily"][str(today)] = tracker["daily"].get(str(today), 0) + 1
        tracker["minute"][current_minute.isoformat()] = tracker["minute"].get(current_minute.isoformat(), 0) + 1
        tracker["total_requests"] += 1
        tracker["last_request"] = now.isoformat()
    
    def _cleanup_old_data(self, tracker: Dict, today, current_minute):
        """Remove old tracking data to prevent memory leaks"""
        # Keep only today's daily data
        tracker["daily"] = {k: v for k, v in tracker["daily"].items() 
                           if k == str(today)}
        
        # Keep only last 5 minutes of data
        cutoff_time = current_minute - timedelta(minutes=5)
        tracker["minute"] = {k: v for k, v in tracker["minute"].items()
                           if datetime.fromisoformat(k) > cutoff_time}
    
    def get_usage_stats(self, api_key: str) -> Dict:
        """Get usage statistics for an API key"""
        if api_key not in usage_tracker:
            return {"daily": 0, "total": 0}
        
        tracker = usage_tracker[api_key]
        today = str(datetime.now().date())
        
        return {
            "daily_usage": tracker["daily"].get(today, 0),
            "total_requests": tracker["total_requests"],
            "last_request": tracker.get("last_request"),
            "client_id": tracker.get("client_id")
        }

quota_manager = APIKeyQuotaManager()

async def resolve_client_with_quota_check(request: Request) -> int:
    """Enhanced auth that includes quota checking"""
    from ..services.auth import resolve_client_from_key
    from ..services.security_monitor import security_monitor
    
    # Get API key from query params
    api_key = request.query_params.get("key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Validate API key and get client_id
    try:
        client_id = await resolve_client_from_key(request)
    except Exception as e:
        # Track failed authentication by API key
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        security_monitor.log_authentication_failure(client_ip, api_key)
        
        # Also track in IP blocking middleware for API key abuse
        from ..middleware.ip_blocking import IPBlockingMiddleware
        # Note: This would need access to the middleware instance
        # For now, we'll rely on the security monitor
        
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check quota before proceeding
    if not quota_manager.check_quota(api_key, client_id):
        client_tier = quota_manager.get_client_tier(client_id)
        daily_limit = quota_manager.daily_limits.get(client_tier, 50)
        minute_limit = quota_manager.minute_limits.get(client_tier, 2)
        
        # Log quota exceeded as suspicious activity
        client_ip = request.headers.get("x-forwarded-for", 
                                      request.client.host if request.client else "unknown")
        security_monitor.log_suspicious_activity(
            "QUOTA_EXCEEDED",
            client_ip,
            {
                "api_key": api_key[:8] + "..." if api_key else None,
                "tier": client_tier,
                "daily_limit": daily_limit,
                "minute_limit": minute_limit
            }
        )
        
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Quota exceeded",
                "daily_limit": daily_limit,
                "minute_limit": minute_limit,
                "message": f"You have exceeded your {client_tier} plan limits. Upgrade your plan for higher limits."
            }
        )
    
    # Record the successful request
    quota_manager.record_request(api_key, client_id)
    
    return client_id

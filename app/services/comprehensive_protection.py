"""
Comprehensive API Protection Middleware
Follows the exact flow specified:
1. Track all IPs for brutal attack detection
2. Validate call structure
3. Authenticate and get client_id  
4. Check cached rate limits with 5-minute refresh
"""
from fastapi import Request, HTTPException, Depends
from typing import Optional
import time
from .ip_brutal_tracker import ip_brutal_tracker
from .call_validator import call_validator
from .rate_limit_cache import rate_limit_cache, CachedRateLimit
from .security_monitor import security_monitor
from datetime import datetime, timedelta

# Helper function to add security events for background logging
def add_security_event_to_request(request: Request, event_type: str, **kwargs):
    """Add a security event to be logged in background after response"""
    try:
        from ..middleware.security_logging_middleware import add_security_event
        add_security_event(request, event_type, **kwargs)
    except ImportError:
        # Fallback to immediate file logging if middleware not available
        security_monitor.log_suspicious_activity(
            event_type, 
            request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown"),
            kwargs
        )

# In-memory usage tracking for rate limiting windows
# Format: {api_key: {minute: [], hour: [], day: []}}
usage_windows = {}

async def comprehensive_api_protection(request: Request) -> CachedRateLimit:
    """
    Comprehensive API protection following the exact flow:
    1. Track IP for brutal attack detection (regardless of call structure)
    2. Validate call structure 
    3. Authenticate and get client_id
    4. Check/refresh cached rate limits
    5. Apply rate limiting
    """
    start_time = time.time()
    
    # Step 1: Track IP for brutal attack detection (ALWAYS - regardless of call structure)
    client_ip = request.headers.get("x-forwarded-for", 
                                  request.client.host if request.client else "unknown")
    
    # Track this IP request for brutal attack detection
    is_ip_blocked = ip_brutal_tracker.track_ip_request(client_ip)
    
    if is_ip_blocked:
        blocked_reason = ip_brutal_tracker.is_ip_blocked(client_ip)[1]
        
        # Immediate file logging
        security_monitor.log_suspicious_activity(
            "IP_BLOCKED_BRUTAL_ATTACK",
            client_ip,
            {"reason": blocked_reason, "endpoint": request.url.path}
        )
        
        # Schedule background database logging
        add_security_event_to_request(
            request,
            "IP_BLOCKED_BRUTAL_ATTACK",
            event_description=f"IP blocked due to brutal attack: {blocked_reason}",
            response_code=429,
            severity="HIGH",
            event_data={"reason": blocked_reason, "endpoint": request.url.path}
        )
        
        raise HTTPException(
            status_code=429, 
            detail=f"IP blocked due to brutal attack: {blocked_reason}"
        )
    
    # Step 2: Validate call structure
    is_valid_structure, structure_error, validated_params = call_validator.validate_call_structure(request)
    
    if not is_valid_structure:
        # Wrong call structure - this counts toward IP brutal attack measure
        
        # Immediate file logging
        security_monitor.log_suspicious_activity(
            "INVALID_CALL_STRUCTURE",
            client_ip,
            {
                "error": structure_error,
                "endpoint": request.url.path,
                "query_params": dict(request.query_params)
            }
        )
        
        # Schedule background database logging
        add_security_event_to_request(
            request,
            "INVALID_CALL_STRUCTURE",
            event_description=f"Invalid call structure: {structure_error}",
            response_code=400,
            severity="MEDIUM",
            event_data={
                "error": structure_error,
                "endpoint": request.url.path,
                "query_params": dict(request.query_params)
            }
        )
        
        raise HTTPException(status_code=400, detail=f"Invalid call structure: {structure_error}")
    
    # Step 3: Authenticate and get client_id (only after structure is valid)
    api_key_or_token = validated_params["key"]
    
    try:
        # Check if it's a JWT token (starts with 'eyJ')
        if api_key_or_token.startswith('eyJ'):
            # JWT token authentication
            from .token_service import token_service
            payload = token_service.verify_token(api_key_or_token)
            client_id = payload.get("client_id")
            
            # For rate limiting, we need the original API key
            # Let's get it from the database using the client_id
            from .db import get_engine
            from sqlalchemy import text
            engine = get_engine()
            sql = text("""
                SELECT api_key
                FROM enervibe.accounts
                WHERE prev_id = :client_id 
            """)
            with engine.begin() as conn:
                row = conn.execute(sql, {"client_id": client_id}).first()
            
            if not row:
                from .error_codes import ErrorCode, get_error_response
                error_response = get_error_response(ErrorCode.AUTH_ACCESS_DENIED)
                raise HTTPException(status_code=401, detail=error_response)
                
            api_key = row[0]  # Use the original API key for rate limiting
        else:
            # API key authentication
            api_key = api_key_or_token
            
            # Import here to avoid circular imports
            from .db import get_engine
            from .error_codes import ErrorCode, get_error_response
            from sqlalchemy import text
            import re
            
            # Basic validation for GUID format
            guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            if not re.match(guid_pattern, api_key):
                error_response = get_error_response(ErrorCode.AUTH_INVALID_FORMAT)
                raise HTTPException(status_code=400, detail=error_response)
            
            # Direct database lookup
            engine = get_engine()
            sql = text("""
                SELECT prev_id as account_id
                FROM enervibe.accounts
                WHERE api_key = :k 
            """)
            with engine.begin() as conn:
                row = conn.execute(sql, {"k": api_key}).first()

            if not row:
                error_response = get_error_response(ErrorCode.AUTH_ACCESS_DENIED)
                raise HTTPException(status_code=401, detail=error_response)

            client_id = int(row[0])  # prev_id is the client_id
        
        # Log successful authentication
        security_monitor.log_api_usage(
            api_key=api_key[:8] + "..." if len(api_key) > 8 else api_key,
            endpoint=request.url.path,
            ip=client_ip,
            response_code=200,  # Auth success
            response_time=0
        )
        
    except HTTPException as auth_error:
        # Authentication failed
        security_monitor.log_suspicious_activity(
            "AUTH_FAILED",
            client_ip,
            {
                "api_key": api_key_or_token[:8] + "..." if len(api_key_or_token) > 8 else api_key_or_token,
                "endpoint": request.url.path,
                "auth_error": str(auth_error.detail)
            }
        )
        raise auth_error
    except Exception as e:
        security_monitor.log_suspicious_activity(
            "AUTH_ERROR",
            client_ip,
            {
                "api_key": api_key_or_token[:8] + "..." if len(api_key_or_token) > 8 else api_key_or_token,
                "endpoint": request.url.path,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Authentication service error")
    
    # Step 4: Check cached rate limits (only after successful auth)
    # Now we always use the api_key for rate limiting, whether it came from direct API key or JWT token
    try:
        # 4a) Check if key exists in cache
        cached_config = await rate_limit_cache.get_rate_limit_config(api_key)
        
        if not cached_config:
            # This shouldn't happen if auth succeeded, but handle it
            security_monitor.log_suspicious_activity(
                "RATE_LIMIT_CONFIG_NOT_FOUND",
                client_ip,
                {"api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key, "client_id": client_id}
            )
            raise HTTPException(status_code=500, detail="Rate limit configuration not found")
        
        # Verify the client_id matches (security check)
        if cached_config.client_id != client_id:
            security_monitor.log_suspicious_activity(
                "CLIENT_ID_MISMATCH", 
                client_ip,
                {
                    "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
                    "auth_client_id": client_id,
                    "cached_client_id": cached_config.client_id
                }
            )
            raise HTTPException(status_code=403, detail="Client ID mismatch")
        
    except HTTPException:
        raise
    except Exception as e:
        security_monitor.log_suspicious_activity(
            "RATE_LIMIT_CACHE_ERROR",
            client_ip,
            {
                "api_key": api_key[:8] + "...",
                "client_id": client_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Rate limit cache error")
    
    # Step 5: Apply rate limiting using cached configuration
    try:
        # Check account status from cache
        is_account_valid, account_reason = cached_config.is_account_valid()
        if not is_account_valid:
            security_monitor.log_suspicious_activity(
                "ACCOUNT_INVALID",
                client_ip,
                {
                    "api_key": api_key[:8] + "...",
                    "client_id": client_id,
                    "reason": account_reason
                }
            )
            raise HTTPException(status_code=403, detail=account_reason)
        
        # Apply rate limits
        can_proceed, rate_limit_reason = check_rate_limits_from_cache(cached_config)
        
        if not can_proceed:
            security_monitor.log_suspicious_activity(
                "RATE_LIMIT_EXCEEDED",
                client_ip,
                {
                    "api_key": api_key[:8] + "...",
                    "client_id": client_id,
                    "tier": cached_config.access_tier,
                    "limit_reason": rate_limit_reason
                }
            )
            
            # Schedule background database logging for rate limit violation
            add_security_event_to_request(
                request,
                "RATE_LIMIT_EXCEEDED",
                api_key=api_key,
                client_id=client_id,
                event_description=f"Rate limit exceeded: {rate_limit_reason}",
                response_code=429,
                severity="MEDIUM",
                event_data={
                    "tier": cached_config.access_tier,
                    "limit_reason": rate_limit_reason,
                    "limits": cached_config.get_rate_limits()
                }
            )
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": rate_limit_reason,
                    "tier": cached_config.access_tier,
                    "limits": cached_config.get_rate_limits()
                }
            )
        
        # Record successful request
        record_successful_request(cached_config)
        
        # Log successful protection check
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=api_key,
            endpoint=request.url.path,
            ip=client_ip,
            response_code=200,
            response_time=response_time
        )
        
        return cached_config
        
    except HTTPException:
        raise
    except Exception as e:
        security_monitor.log_suspicious_activity(
            "RATE_LIMITING_ERROR",
            client_ip,
            {
                "api_key": api_key[:8] + "...",
                "client_id": client_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Rate limiting error")

def check_rate_limits_from_cache(cached_config: CachedRateLimit) -> tuple[bool, str]:
    """Check rate limits using cached configuration"""
    api_key = cached_config.api_key
    
    # If admin override is enabled, skip all limits
    if cached_config.override_all_limits:
        return True, ""
    
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
    cleanup_old_timestamps(windows, current_minute, current_hour, current_day)
    
    # Get limits from cached configuration
    limits = cached_config.get_rate_limits()
    
    # Check minute limit
    minute_count = len(windows["minute"])
    if minute_count >= limits["requests_per_minute"]:
        return False, f"Rate limit exceeded: {limits['requests_per_minute']} requests per minute"
    
    # Check hour limit
    hour_count = len(windows["hour"])
    if hour_count >= limits["requests_per_hour"]:
        return False, f"Rate limit exceeded: {limits['requests_per_hour']} requests per hour"
    
    # Check day limit
    day_count = len(windows["day"])
    if day_count >= limits["requests_per_day"]:
        return False, f"Rate limit exceeded: {limits['requests_per_day']} requests per day"
    
    return True, ""

def record_successful_request(cached_config: CachedRateLimit):
    """Record a successful API request"""
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
    
    # Update database usage stats asynchronously
    import asyncio
    try:
        from .db_access_control import update_usage_stats
        asyncio.create_task(update_usage_stats(api_key, success=True))
    except Exception:
        pass  # Don't fail request if usage stats update fails

def cleanup_old_timestamps(windows, current_minute, current_hour, current_day):
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

def get_memory_usage_data() -> dict:
    """Get all in-memory usage tracking data for debugging"""
    memory_data = {}
    for api_key, windows in usage_windows.items():
        # Clean up first
        now = datetime.now()
        current_minute = now.replace(second=0, microsecond=0)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cleanup_old_timestamps(windows, current_minute, current_hour, current_day)
        
        memory_data[api_key[:8] + "..."] = {
            "minute_requests": len(windows["minute"]),
            "hour_requests": len(windows["hour"]),
            "day_requests": len(windows["day"]),
            "recent_minute_timestamps": [
                datetime.fromisoformat(ts).strftime("%H:%M:%S") 
                for ts in windows["minute"][-5:]  # Last 5
            ]
        }
    return memory_data

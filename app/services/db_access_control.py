"""
Database-driven API Access Control Service
Integrates with client_api_access table for dynamic rate limiting
"""
from fastapi import HTTPException, Request
from sqlalchemy import text
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from .db import get_engine
from .error_codes import ErrorCode, get_error_response

class ClientAPIAccess:
    """Client API access configuration from database"""
    
    def __init__(self, db_row: Dict[str, Any]):
        # Primary identification
        self.access_id = db_row.get('access_id')
        self.client_id = db_row.get('client_id') 
        self.api_key = db_row.get('api_key')
        
        # Rate limits from database
        self.requests_per_minute = db_row.get('requests_per_minute', 2)
        self.requests_per_hour = db_row.get('requests_per_hour', 10) 
        self.requests_per_day = db_row.get('requests_per_day', 100)
        
        # Tier and status
        self.access_tier = db_row.get('access_tier', 'free')
        self.is_active = bool(db_row.get('is_active', 1))
        self.is_suspended = bool(db_row.get('is_suspended', 0))
        self.suspension_reason = db_row.get('suspension_reason')
        self.suspended_until = db_row.get('suspended_until')
        
        # Advanced settings
        self.burst_requests_allowed = db_row.get('burst_requests_allowed', 0)
        self.max_concurrent_requests = db_row.get('max_concurrent_requests', 5)
        self.override_all_limits = bool(db_row.get('override_all_limits', 0))
        
        # Security settings
        self.failed_auth_attempts = db_row.get('failed_auth_attempts', 0)
        self.is_auto_blocked = bool(db_row.get('is_auto_blocked', 0))
        self.auto_block_reason = db_row.get('auto_block_reason')
        
        # Usage statistics
        self.total_requests_lifetime = db_row.get('total_requests_lifetime', 0)
        self.requests_today = db_row.get('requests_today', 0)
        self.last_request_at = db_row.get('last_request_at')
        
        # Endpoint restrictions
        self.allowed_endpoints = self._parse_json_field(db_row.get('allowed_endpoints'))
        self.blocked_endpoints = self._parse_json_field(db_row.get('blocked_endpoints'))
        
        # Timestamps
        self.created_at = db_row.get('created_at')
        self.updated_at = db_row.get('updated_at')
    
    def _parse_json_field(self, field_value) -> Optional[List[str]]:
        """Parse JSON field from database"""
        if not field_value:
            return None
        try:
            if isinstance(field_value, str):
                return json.loads(field_value)
            return field_value
        except (json.JSONDecodeError, TypeError):
            return None
    
    def is_account_valid(self) -> tuple[bool, str]:
        """Check if account can make API requests"""
        if not self.is_active:
            return False, "API access is deactivated for this account"
        
        if self.is_auto_blocked:
            return False, f"API key auto-blocked: {self.auto_block_reason or 'Suspicious activity'}"
        
        if self.is_suspended:
            if self.suspended_until:
                # Check if suspension has expired
                if isinstance(self.suspended_until, str):
                    suspended_until = datetime.fromisoformat(self.suspended_until.replace('Z', '+00:00'))
                else:
                    suspended_until = self.suspended_until
                
                if datetime.now() < suspended_until:
                    return False, f"API access suspended until {suspended_until}: {self.suspension_reason}"
                else:
                    # Suspension has expired - could auto-unsuspend here
                    return True, ""
            else:
                return False, f"API access suspended: {self.suspension_reason}"
        
        return True, ""
    
    def can_access_endpoint(self, endpoint: str) -> bool:
        """Check if client can access specific endpoint"""
        # Check blocked endpoints first
        if self.blocked_endpoints:
            for blocked in self.blocked_endpoints:
                if endpoint.startswith(blocked) or endpoint == blocked:
                    return False
        
        # Check allowed endpoints (if specified, only these are allowed)
        if self.allowed_endpoints:
            for allowed in self.allowed_endpoints:
                if endpoint.startswith(allowed) or endpoint == allowed:
                    return True
            return False  # Not in allowed list
        
        return True  # No restrictions
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Get current rate limits"""
        if self.override_all_limits:
            return {
                "requests_per_minute": 999999,
                "requests_per_hour": 999999,
                "requests_per_day": 999999
            }
        
        return {
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "requests_per_day": self.requests_per_day,
            "burst_requests_allowed": self.burst_requests_allowed
        }

async def get_client_api_access(api_key: str) -> ClientAPIAccess:
    """Get client API access configuration from database"""
    if not api_key:
        raise ValueError("API key is required")
    
    engine = get_engine()
    
    # Query to get comprehensive API access info - matching your actual table structure
    sql = text("""
        SELECT 
            access_id, client_id, api_key,
            requests_per_minute, requests_per_hour, requests_per_day,
            access_tier, is_active, is_suspended, suspension_reason, suspended_until,
            total_requests_lifetime, requests_today, last_request_at,
            failed_auth_attempts, is_auto_blocked, auto_block_reason,
            allowed_endpoints, blocked_endpoints, burst_requests_allowed,
            override_all_limits, created_at, updated_at
        FROM app.client_api_access 
        WHERE api_key = :api_key
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(sql, {"api_key": api_key}).first()
            
            if not result:
                raise ValueError("Invalid API key")
            
            # Convert row to structure matching your actual table
            row_dict = dict(result._mapping)
            
            # Create ClientAPIAccess with your actual database fields
            return ClientAPIAccess(row_dict)
            
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Handle database errors
        error_msg = str(e).lower()
        if "login failed" in error_msg or "cannot open database" in error_msg:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        else:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def update_usage_stats(api_key: str, success: bool = True):
    """Update usage statistics in database"""
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            if success:
                # Successful request - update counters
                conn.execute(text("""
                    UPDATE app.client_api_access 
                    SET total_requests_lifetime = total_requests_lifetime + 1,
                        requests_today = requests_today + 1,
                        last_request_at = GETDATE(),
                        updated_at = GETDATE()
                    WHERE api_key = :api_key
                """), {"api_key": api_key})
            else:
                # Failed request - update failed auth attempts
                conn.execute(text("""
                    UPDATE app.client_api_access 
                    SET failed_auth_attempts = failed_auth_attempts + 1,
                        updated_at = GETDATE()
                    WHERE api_key = :api_key
                """), {"api_key": api_key})
                
    except Exception as e:
        # Log error but don't fail the request
        print(f"Warning: Could not update usage stats for {api_key}: {e}")

async def auto_block_api_key(api_key: str, reason: str):
    """Auto-block an API key due to suspicious activity"""
    engine = get_engine()
    
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE app.client_api_access 
                SET is_auto_blocked = 1,
                    auto_block_reason = :reason,
                    updated_at = GETDATE()
                WHERE api_key = :api_key
            """), {"api_key": api_key, "reason": reason})
            
        print(f"Auto-blocked API key {api_key[:8]}... due to: {reason}")
        
    except Exception as e:
        print(f"Error auto-blocking API key {api_key}: {e}")

async def resolve_client_with_db_access_control(request: Request) -> ClientAPIAccess:
    """Enhanced authentication using database-driven access control"""
    # Get API key from request
    api_key = request.query_params.get("key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        # Get client access configuration from database
        client_access = await get_client_api_access(api_key)
        
        # Validate account status
        is_valid, reason = client_access.is_account_valid()
        if not is_valid:
            # Log failed authentication attempt
            await update_usage_stats(api_key, success=False)
            raise HTTPException(status_code=403, detail=reason)
        
        # Check endpoint access (if restrictions are configured)
        endpoint = request.url.path
        if not client_access.can_access_endpoint(endpoint):
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied to endpoint: {endpoint}"
            )
        
        return client_access
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Invalid API key
        await update_usage_stats(api_key, success=False)
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        # Database or other errors
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

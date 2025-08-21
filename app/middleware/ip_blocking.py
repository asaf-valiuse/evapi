"""
IP blocking and suspicious activity detection
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Set, Dict, List
import time
from datetime import datetime, timedelta
import ipaddress
import json
import os

class IPBlockingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.blocked_ips: Set[str] = set()
        self.blocked_api_keys: Set[str] = set()  # Track blocked API keys
        self.suspicious_activity: Dict[str, Dict] = {}
        self.api_key_abuse: Dict[str, Dict] = {}  # Track abuse by API key
        self.blocked_ranges: List[ipaddress.IPv4Network] = []
        
        # Load blocked IPs from file if exists
        self.load_blocked_ips()
        
        # Suspicious activity thresholds - more sensitive for 1 call/minute usage
        self.max_requests_per_minute = 10  # Reduced from 60 - anything over 10/min is suspicious
        self.max_failed_auth_attempts = 5  # Reduced from 10 - stricter on auth failures
        self.auto_ban_threshold = 3        # Reduced from 5 - faster banning
    
    def load_blocked_ips(self):
        """Load blocked IPs and API keys from configuration file"""
        blocked_file = "blocked_ips.json"
        if os.path.exists(blocked_file):
            try:
                with open(blocked_file, 'r') as f:
                    data = json.load(f)
                    self.blocked_ips = set(data.get('ips', []))
                    self.blocked_api_keys = set(data.get('api_keys', []))  # Load blocked API keys
                    
                    # Load blocked IP ranges
                    for range_str in data.get('ranges', []):
                        try:
                            self.blocked_ranges.append(ipaddress.IPv4Network(range_str))
                        except:
                            pass
            except Exception as e:
                print(f"Error loading blocked IPs: {e}")
    
    def save_blocked_ips(self):
        """Save blocked IPs and API keys to configuration file"""
        blocked_file = "blocked_ips.json"
        try:
            with open(blocked_file, 'w') as f:
                json.dump({
                    'ips': list(self.blocked_ips),
                    'api_keys': list(self.blocked_api_keys),  # Save blocked API keys
                    'ranges': [str(r) for r in self.blocked_ranges],
                    'updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving blocked IPs: {e}")
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers"""
        # Check for forwarded IP (from load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check other common headers
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if ip in self.blocked_ips:
            return True
        
        # Check if IP is in any blocked range
        try:
            ip_obj = ipaddress.IPv4Address(ip)
            for network in self.blocked_ranges:
                if ip_obj in network:
                    return True
        except:
            pass
        
        return False
    
    def is_api_key_blocked(self, api_key: str) -> bool:
        """Check if API key is blocked"""
        return api_key in self.blocked_api_keys
    
    def track_api_key_activity(self, api_key: str, activity_type: str):
        """Track suspicious activity for an API key"""
        if not api_key or len(api_key) < 8:
            return
            
        now = datetime.now()
        
        if api_key not in self.api_key_abuse:
            self.api_key_abuse[api_key] = {
                'requests': [],
                'failed_auth': [],
                'first_seen': now.isoformat()
            }
        
        activity = self.api_key_abuse[api_key]
        
        if activity_type == 'request':
            activity['requests'].append(now.isoformat())
            # Keep only last hour of requests
            cutoff = now - timedelta(hours=1)
            activity['requests'] = [
                req for req in activity['requests'] 
                if datetime.fromisoformat(req) > cutoff
            ]
        
        elif activity_type == 'failed_auth':
            activity['failed_auth'].append(now.isoformat())
            # Keep only last day of failed auth attempts
            cutoff = now - timedelta(days=1)
            activity['failed_auth'] = [
                attempt for attempt in activity['failed_auth']
                if datetime.fromisoformat(attempt) > cutoff
            ]
        
        # Check if we should auto-ban this API key
        self.check_api_key_auto_ban(api_key, activity)
    
    def track_suspicious_activity(self, ip: str, activity_type: str):
        """Track suspicious activity for an IP"""
        now = datetime.now()
        
        if ip not in self.suspicious_activity:
            self.suspicious_activity[ip] = {
                'requests': [],
                'failed_auth': [],
                'first_seen': now.isoformat()
            }
        
        activity = self.suspicious_activity[ip]
        
        if activity_type == 'request':
            activity['requests'].append(now.isoformat())
            # Keep only last hour of requests
            cutoff = now - timedelta(hours=1)
            activity['requests'] = [
                req for req in activity['requests'] 
                if datetime.fromisoformat(req) > cutoff
            ]
        
        elif activity_type == 'failed_auth':
            activity['failed_auth'].append(now.isoformat())
            # Keep only last day of failed auth attempts
            cutoff = now - timedelta(days=1)
            activity['failed_auth'] = [
                attempt for attempt in activity['failed_auth']
                if datetime.fromisoformat(attempt) > cutoff
            ]
        
        # Check if we should auto-ban this IP
        self.check_auto_ban(ip, activity)
    
    def check_auto_ban(self, ip: str, activity: Dict):
        """Check if IP should be automatically banned"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Count recent requests
        recent_requests = len([
            req for req in activity.get('requests', [])
            if datetime.fromisoformat(req) > minute_ago
        ])
        
        # Count recent failed auth attempts
        recent_failed_auth = len([
            attempt for attempt in activity.get('failed_auth', [])
            if datetime.fromisoformat(attempt) > minute_ago
        ])
        
        # Auto-ban conditions
        should_ban = (
            recent_requests > self.max_requests_per_minute or
            recent_failed_auth > self.max_failed_auth_attempts or
            len(activity.get('failed_auth', [])) > 50  # Too many failed attempts overall
        )
        
        # Don't auto-ban localhost/development IPs
        development_ips = {'127.0.0.1', '::1', 'localhost'}
        if ip in development_ips:
            if should_ban:
                print(f"WARNING: Would auto-ban development IP {ip}, but skipping for development")
            return
        
        if should_ban and ip not in self.blocked_ips:
            print(f"Auto-banning IP {ip} due to suspicious activity")
            self.blocked_ips.add(ip)
            self.save_blocked_ips()
    
    def check_api_key_auto_ban(self, api_key: str, activity: Dict):
        """Check if API key should be automatically banned"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Count recent requests
        recent_requests = len([
            req for req in activity.get('requests', [])
            if datetime.fromisoformat(req) > minute_ago
        ])
        
        # Count recent failed auth attempts
        recent_failed_auth = len([
            attempt for attempt in activity.get('failed_auth', [])
            if datetime.fromisoformat(attempt) > minute_ago
        ])
        
        # Auto-ban conditions for API keys (stricter than IP)
        should_ban = (
            recent_requests > self.max_requests_per_minute or
            recent_failed_auth > 3 or  # Even stricter for API key auth failures
            len(activity.get('failed_auth', [])) > 20  # Total failed attempts
        )
        
        if should_ban and api_key not in self.blocked_api_keys:
            print(f"Auto-banning API key {api_key[:8]}... due to suspicious activity")
            self.blocked_api_keys.add(api_key)
            self.save_blocked_ips()
            
            # Also track this in security monitor
            from ..services.security_monitor import security_monitor
            security_monitor.log_suspicious_activity(
                "API_KEY_AUTO_BLOCKED",
                "system",
                {
                    "api_key": api_key[:8] + "...",
                    "reason": f"Requests: {recent_requests}, Failed auth: {recent_failed_auth}",
                    "action": "API_KEY_BANNED"
                }
            )
    
    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)
        api_key = request.query_params.get("key", "")
        
        # Check if IP is blocked
        if self.is_ip_blocked(client_ip):
            raise HTTPException(
                status_code=403, 
                detail="Your IP address has been blocked due to suspicious activity"
            )
        
        # Check if API key is blocked (PRIMARY PROTECTION)
        if api_key and self.is_api_key_blocked(api_key):
            raise HTTPException(
                status_code=403,
                detail="This API key has been blocked due to abuse"
            )
        
        # Track activity by IP
        self.track_suspicious_activity(client_ip, 'request')
        
        # Track activity by API key (if present)
        if api_key:
            self.track_api_key_activity(api_key, 'request')
        
        # Add tracking info to response headers (for debugging)
        response = await call_next(request)
        response.headers["X-Client-IP"] = client_ip
        if api_key:
            response.headers["X-API-Key-Tracked"] = api_key[:8] + "..."
        
        return response

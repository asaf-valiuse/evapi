"""
Rate limiting middleware for API protection against abuse
"""
from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
from typing import Optional
import os
from functools import lru_cache

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ENABLE_REDIS = os.getenv("ENABLE_REDIS_RATE_LIMIT", "false").lower() == "true"

@lru_cache()
def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client if available, otherwise None for in-memory limiting"""
    if not ENABLE_REDIS:
        return None
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.ping()  # Test connection
        return client
    except Exception:
        print("Warning: Redis not available, using in-memory rate limiting")
        return None

def key_func(request: Request):
    """
    Generate rate limit key based on:
    1. API key (if provided and valid format) - PRIMARY rate limiting
    2. IP address - ONLY fallback for requests without keys
    
    This ensures each API key gets its own rate limit bucket,
    preventing users from bypassing limits by changing IPs.
    """
    # Try to get API key from query params
    api_key = request.query_params.get("key")
    if api_key and len(api_key) >= 8:  # Basic validation - must be at least 8 chars
        # Use API key as the primary rate limiting identifier
        return f"api_key:{api_key}"
    
    # Fallback to IP address only for requests without valid API keys
    # This protects against abuse of endpoints that don't require keys (like /healthz)
    forwarded_ip = request.headers.get("x-forwarded-for")
    if forwarded_ip:
        return f"ip:{forwarded_ip.split(',')[0].strip()}"
    
    return f"ip:{get_remote_address(request)}"

# Create limiter instance
limiter = Limiter(
    key_func=key_func,
    storage_uri=REDIS_URL if ENABLE_REDIS else None,
    default_limits=["200 per day", "10 per hour", "3 per minute"]  # More restrictive for 1 call/minute usage
)

def setup_rate_limiting(app):
    """Setup rate limiting on FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    return limiter

"""
Smart Rate Limit Cache Manager
Caches database rate limits per API key with intelligent refresh logic
"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from .db_access_control import get_client_api_access, ClientAPIAccess

@dataclass
class CachedRateLimit:
    """Cached rate limit configuration for an API key"""
    api_key: str
    client_id: int
    access_tier: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    is_active: bool
    is_suspended: bool
    is_auto_blocked: bool
    override_all_limits: bool
    
    # Cache metadata
    cached_at: datetime
    last_refreshed: datetime
    refresh_count: int
    
    def is_cache_expired(self, cache_ttl_minutes: int = 15) -> bool:
        """Check if cache entry needs refresh"""
        return datetime.now() - self.last_refreshed > timedelta(minutes=cache_ttl_minutes)
    
    def should_force_refresh(self, force_refresh_threshold_minutes: int = 60) -> bool:
        """Check if cache entry should be force refreshed (longer interval)"""
        return datetime.now() - self.cached_at > timedelta(minutes=force_refresh_threshold_minutes)
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Get current rate limits from cache"""
        if self.override_all_limits:
            return {
                "requests_per_minute": 999999,
                "requests_per_hour": 999999,
                "requests_per_day": 999999
            }
        
        return {
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "requests_per_day": self.requests_per_day
        }
    
    def is_account_valid(self) -> Tuple[bool, str]:
        """Validate account status from cache"""
        if not self.is_active:
            return False, "Account is not active"
        
        if self.is_auto_blocked:
            return False, "Account is auto-blocked due to suspicious activity"
        
        if self.is_suspended:
            return False, "Account is suspended"
        
        return True, ""

class RateLimitCacheManager:
    """Manages cached rate limits with intelligent refresh strategy"""
    
    def __init__(self):
        # In-memory cache: {api_key: CachedRateLimit}
        self._cache: Dict[str, CachedRateLimit] = {}
        
        # Configuration - Using 5 minutes as requested
        self.cache_ttl_minutes = 5   # Refresh interval reduced to 5 minutes
        self.force_refresh_threshold_minutes = 15  # Force refresh interval
        self.cleanup_interval_minutes = 60  # Cleanup old entries
        
        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0
        self.db_fetches = 0
        self.last_cleanup = datetime.now()
    
    async def get_rate_limit_config(self, api_key: str) -> Optional[CachedRateLimit]:
        """
        Get rate limit configuration for API key with intelligent caching
        
        Logic:
        1. Check if key exists in cache and is still fresh
        2. If cache miss or expired, fetch from database
        3. If database fetch fails, use stale cache if available
        4. Periodically cleanup old cache entries
        """
        now = datetime.now()
        
        # Check if we have cached data
        if api_key in self._cache:
            cached_config = self._cache[api_key]
            
            # Check if cache is still fresh
            if not cached_config.is_cache_expired(self.cache_ttl_minutes):
                self.cache_hits += 1
                return cached_config
            
            # Cache expired but not too old - refresh in background if needed
            if not cached_config.should_force_refresh(self.force_refresh_threshold_minutes):
                # Use cached data while refreshing in background
                asyncio.create_task(self._background_refresh(api_key))
                self.cache_hits += 1
                return cached_config
        
        # Cache miss or force refresh needed - fetch from database
        try:
            client_access = await get_client_api_access(api_key)
            if not client_access:
                return None
            
            # Create cached entry
            cached_config = CachedRateLimit(
                api_key=client_access.api_key,
                client_id=client_access.client_id,
                access_tier=client_access.access_tier,
                requests_per_minute=client_access.requests_per_minute,
                requests_per_hour=client_access.requests_per_hour,
                requests_per_day=client_access.requests_per_day,
                is_active=client_access.is_active,
                is_suspended=client_access.is_suspended,
                is_auto_blocked=client_access.is_auto_blocked,
                override_all_limits=client_access.override_all_limits,
                cached_at=now,
                last_refreshed=now,
                refresh_count=1
            )
            
            # Store in cache
            self._cache[api_key] = cached_config
            self.cache_misses += 1
            self.db_fetches += 1
            
            # Cleanup old entries periodically
            if now - self.last_cleanup > timedelta(minutes=self.cleanup_interval_minutes):
                await self._cleanup_cache()
            
            return cached_config
            
        except Exception as e:
            # Database error - use stale cache if available
            if api_key in self._cache:
                print(f"Warning: Database error for {api_key}, using stale cache: {e}")
                return self._cache[api_key]
            
            # No cache available and database failed
            print(f"Error: Cannot get rate limits for {api_key}: {e}")
            return None
    
    async def _background_refresh(self, api_key: str):
        """Background task to refresh cache entry"""
        try:
            client_access = await get_client_api_access(api_key)
            if client_access and api_key in self._cache:
                now = datetime.now()
                cached_config = self._cache[api_key]
                
                # Update cached entry with new data
                self._cache[api_key] = CachedRateLimit(
                    api_key=client_access.api_key,
                    client_id=client_access.client_id,
                    access_tier=client_access.access_tier,
                    requests_per_minute=client_access.requests_per_minute,
                    requests_per_hour=client_access.requests_per_hour,
                    requests_per_day=client_access.requests_per_day,
                    is_active=client_access.is_active,
                    is_suspended=client_access.is_suspended,
                    is_auto_blocked=client_access.is_auto_blocked,
                    override_all_limits=client_access.override_all_limits,
                    cached_at=cached_config.cached_at,  # Keep original cache time
                    last_refreshed=now,
                    refresh_count=cached_config.refresh_count + 1
                )
                
                self.db_fetches += 1
                
        except Exception as e:
            print(f"Warning: Background refresh failed for {api_key}: {e}")
    
    async def _cleanup_cache(self):
        """Remove old cache entries to prevent memory leaks"""
        now = datetime.now()
        cleanup_threshold = now - timedelta(minutes=self.cleanup_interval_minutes * 2)
        
        keys_to_remove = [
            key for key, cached_config in self._cache.items()
            if cached_config.last_refreshed < cleanup_threshold
        ]
        
        for key in keys_to_remove:
            del self._cache[key]
        
        self.last_cleanup = now
        
        if keys_to_remove:
            print(f"Cache cleanup: Removed {len(keys_to_remove)} old entries")
    
    def invalidate_cache(self, api_key: str):
        """Force invalidate cache for specific API key"""
        if api_key in self._cache:
            del self._cache[api_key]
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "db_fetches": self.db_fetches,
            "cached_keys_count": len(self._cache),
            "cache_ttl_minutes": self.cache_ttl_minutes,
            "force_refresh_threshold_minutes": self.force_refresh_threshold_minutes
        }
    
    def update_cache_settings(self, cache_ttl_minutes: int = None, force_refresh_threshold_minutes: int = None):
        """Update cache timing settings"""
        if cache_ttl_minutes is not None:
            self.cache_ttl_minutes = cache_ttl_minutes
        
        if force_refresh_threshold_minutes is not None:
            self.force_refresh_threshold_minutes = force_refresh_threshold_minutes

# Global cache manager instance
rate_limit_cache = RateLimitCacheManager()

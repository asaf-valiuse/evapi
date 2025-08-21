"""
Debug and monitoring endpoints for comprehensive API protection system
Shows in-memory cache and usage tracking data following the new protection flow
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime
from ..services.ip_brutal_tracker import ip_brutal_tracker
from ..services.rate_limit_cache import rate_limit_cache
from ..services.comprehensive_protection import get_memory_usage_data, comprehensive_api_protection
from ..services.security_monitor import security_monitor

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/memory-status")
def get_comprehensive_memory_status():
    """Show all in-memory data structures for comprehensive protection system"""
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "protection_flow": [
            "1. IP brutal attack tracking (50 req/min threshold) - ALL requests tracked",
            "2. Call structure validation (key format, required params)",
            "3. API key authentication via server", 
            "4. Cached rate limits check (5-minute refresh from database)",
            "5. Database-driven rate limiting enforcement"
        ],
        "ip_brutal_tracking": {
            "description": "Tracks ALL IPs regardless of call structure - 50 req/min blocking threshold",
            "stats": ip_brutal_tracker.get_ip_stats(),
            "memory_data": ip_brutal_tracker.get_memory_data(),
            "settings": {
                "brutal_attack_threshold": ip_brutal_tracker.brutal_attack_threshold,
                "blocked_ips_file": ip_brutal_tracker.blocked_ips_file
            }
        },
        "rate_limit_cache": {
            "description": "Cached database rate limits - refreshes every 5 minutes",
            "performance_stats": rate_limit_cache.get_cache_stats(),
            "settings": {
                "cache_ttl_minutes": rate_limit_cache.cache_ttl_minutes,
                "force_refresh_threshold_minutes": rate_limit_cache.force_refresh_threshold_minutes,
                "cleanup_interval_minutes": rate_limit_cache.cleanup_interval_minutes
            },
            "cached_api_keys": {
                key[:8] + "...": {
                    "client_id": config.client_id,
                    "access_tier": config.access_tier,
                    "database_limits": config.get_rate_limits(),
                    "cache_timing": {
                        "cached_at": config.cached_at.strftime("%H:%M:%S"),
                        "last_refreshed": config.last_refreshed.strftime("%H:%M:%S"),
                        "refresh_count": config.refresh_count,
                        "cache_age_minutes": round((datetime.now() - config.last_refreshed).total_seconds() / 60, 2)
                    },
                    "account_status": {
                        "is_active": config.is_active,
                        "is_suspended": config.is_suspended,
                        "is_auto_blocked": config.is_auto_blocked,
                        "override_all_limits": config.override_all_limits
                    }
                }
                for key, config in rate_limit_cache._cache.items()
            }
        },
        "usage_windows": {
            "description": "Active API key usage tracking for rate limiting",
            "data": get_memory_usage_data()
        },
        "system_summary": {
            "total_tracked_ips": len(ip_brutal_tracker._ip_tracking),
            "blocked_ips_count": sum(1 for info in ip_brutal_tracker._ip_tracking.values() if info.is_blocked),
            "cached_api_keys_count": len(rate_limit_cache._cache),
            "active_usage_windows_count": len(get_memory_usage_data()),
            "cache_hit_rate_percent": rate_limit_cache.get_cache_stats().get("hit_rate_percent", 0)
        }
    }

@router.get("/ip-details/{ip_address}")
def get_ip_detailed_info(ip_address: str):
    """Get detailed information for specific IP address"""
    return {
        "ip_address": ip_address,
        "tracking_info": ip_brutal_tracker.get_ip_stats(ip_address),
        "protection_note": "This IP is tracked for brutal attack detection (50 req/min threshold)"
    }

@router.get("/ip-summary") 
def get_ip_tracking_summary():
    """Get summary of all IP tracking"""
    return {
        "ip_tracking_summary": ip_brutal_tracker.get_ip_stats(),
        "brutal_attack_settings": {
            "threshold_requests_per_minute": ip_brutal_tracker.brutal_attack_threshold,
            "tracking_scope": "ALL requests regardless of call structure validation"
        }
    }

@router.get("/cache-performance")
def get_cache_performance_details():
    """Get detailed cache performance and settings"""
    return {
        "cache_performance": rate_limit_cache.get_cache_stats(),
        "cache_configuration": {
            "refresh_cycle": f"{rate_limit_cache.cache_ttl_minutes} minutes",
            "force_refresh_after": f"{rate_limit_cache.force_refresh_threshold_minutes} minutes", 
            "cleanup_interval": f"{rate_limit_cache.cleanup_interval_minutes} minutes",
            "data_source": "app.client_api_access database table"
        },
        "refresh_strategy": [
            f"Fresh cache (< {rate_limit_cache.cache_ttl_minutes} min): Use cached limits",
            f"Stale cache ({rate_limit_cache.cache_ttl_minutes}-{rate_limit_cache.force_refresh_threshold_minutes} min): Use cache + background refresh",
            f"Expired cache (> {rate_limit_cache.force_refresh_threshold_minutes} min): Force immediate refresh",
            "New API keys: Immediate database fetch"
        ]
    }

@router.get("/usage-windows/{api_key}")
def get_api_key_usage_details(api_key: str, cached_config = Depends(comprehensive_api_protection)):
    """Get detailed usage windows for authenticated API key"""
    usage_data = get_memory_usage_data()
    
    masked_key = api_key[:8] + "..."
    
    return {
        "api_key": masked_key,
        "client_id": cached_config.client_id,
        "access_tier": cached_config.access_tier,
        "current_limits": cached_config.get_rate_limits(),
        "current_usage": usage_data.get(masked_key, {"note": "No usage tracked yet"}),
        "cache_info": {
            "cached_at": cached_config.cached_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_refreshed": cached_config.last_refreshed.strftime("%Y-%m-%d %H:%M:%S"),
            "refresh_count": cached_config.refresh_count
        }
    }

@router.post("/admin/unblock-ip/{ip_address}")
def manually_unblock_ip(ip_address: str):
    """Manually unblock an IP address (admin function)"""
    success = ip_brutal_tracker.unblock_ip(ip_address)
    if success:
        return {
            "message": f"IP {ip_address} has been manually unblocked",
            "note": "IP will continue to be tracked for future brutal attack detection"
        }
    else:
        raise HTTPException(status_code=404, detail=f"IP {ip_address} not found in tracking system")

@router.post("/admin/clear-cache/{api_key}")
def manually_clear_cache(api_key: str):
    """Manually clear cache for specific API key (forces database refresh)"""
    rate_limit_cache.invalidate_cache(api_key)
    return {
        "message": f"Cache cleared for API key {api_key[:8]}...",
        "note": "Next request will fetch fresh limits from database"
    }

@router.get("/protection-flow")
def show_protection_flow():
    """Show the complete protection flow and settings"""
    return {
        "comprehensive_protection_flow": [
            {
                "step": 1,
                "name": "IP Brutal Attack Tracking",
                "description": "Track ALL incoming requests by IP address",
                "threshold": f"{ip_brutal_tracker.brutal_attack_threshold} requests per minute",
                "scope": "Every request regardless of structure validation",
                "action": "IP blocking with persistent storage"
            },
            {
                "step": 2, 
                "name": "Call Structure Validation",
                "description": "Validate API call structure and parameters",
                "requirements": ["API key (GUID format)", "Query code parameter 'q'"],
                "scope": "Only structurally valid calls proceed",
                "action": "Invalid calls count toward IP brutal attack measure"
            },
            {
                "step": 3,
                "name": "API Key Authentication", 
                "description": "Authenticate API key with server and get client_id",
                "scope": "Only after successful structure validation",
                "action": "Failed auth counts toward suspicious activity"
            },
            {
                "step": 4,
                "name": "Cached Rate Limit Check",
                "description": "Check/refresh cached database rate limits",
                "refresh_cycle": f"{rate_limit_cache.cache_ttl_minutes} minutes",
                "data_source": "app.client_api_access table",
                "action": "Database query only when cache expired or new key"
            },
            {
                "step": 5,
                "name": "Rate Limiting Enforcement",
                "description": "Apply database-driven rate limits",
                "tracking": "Per-API-key usage windows (minute/hour/day)",
                "action": "Block requests exceeding configured limits"
            }
        ],
        "system_benefits": [
            "IP protection against brutal attacks (50 req/min)",
            "Database-driven flexible rate limits",
            "5-minute cache refresh cycle",
            "Minimal database load via intelligent caching",
            "Comprehensive logging and monitoring"
        ]
    }

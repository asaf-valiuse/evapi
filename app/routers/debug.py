"""
Debug and monitoring endpoints for comprehensive API protection system
Shows in-memory cache and usage tracking data
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Dict, Any
from datetime import datetime
from ..services.ip_brutal_tracker import ip_brutal_tracker
from ..services.rate_limit_cache import rate_limit_cache
from ..services.comprehensive_protection import get_memory_usage_data, comprehensive_api_protection
from ..services.security_monitor import security_monitor
from ..services.db import get_engine
from ..services.db_quota_manager import usage_windows, db_quota_manager
from sqlalchemy import text

router = APIRouter(tags=["debug"], prefix="/debug")

@router.get("/cache-table")
async def get_cache_table():
    """Get current cache status in tabular format"""
    from ..services.db_quota_manager import usage_windows
    
    # Get cache statistics
    cache_stats = rate_limit_cache.get_cache_stats()
    
    # Prepare tabular data
    result = {
        "cache_summary": {
            "total_cached_keys": cache_stats["cached_keys_count"],
            "cache_hit_rate": f"{cache_stats['hit_rate_percent']}%",
            "total_db_fetches": cache_stats["db_fetches"],
            "cache_ttl_minutes": cache_stats["cache_ttl_minutes"]
        },
        "cached_keys_table": [],
        "usage_counters_table": [],
        "ip_tracking_table": [],
        "blocked_ips_table": []
    }
    
    # Build cached keys table
    for api_key, cached_config in rate_limit_cache._cache.items():
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else api_key[:4] + "..."
        
        cache_age_minutes = int((datetime.now() - cached_config.last_refreshed).total_seconds() / 60)
        is_fresh = cache_age_minutes < 5
        
        result["cached_keys_table"].append({
            "api_key": masked_key,
            "client_id": cached_config.client_id,
            "tier": cached_config.access_tier,
            "limits_per_min": cached_config.requests_per_minute,
            "limits_per_hour": cached_config.requests_per_hour,
            "limits_per_day": cached_config.requests_per_day,
            "is_active": cached_config.is_active,
            "is_suspended": cached_config.is_suspended,
            "is_blocked": cached_config.is_auto_blocked,
            "unlimited": cached_config.override_all_limits,
            "cache_age_min": cache_age_minutes,
            "is_fresh": is_fresh,
            "refresh_count": cached_config.refresh_count
        })
    
    # Build usage counters table
    for api_key, windows in usage_windows.items():
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else api_key[:4] + "..."
        
        # Get the cached config to show limits
        cached_config = rate_limit_cache._cache.get(api_key)
        if cached_config:
            limits = cached_config.get_rate_limits()
        else:
            limits = {"requests_per_minute": "N/A", "requests_per_hour": "N/A", "requests_per_day": "N/A"}
        
        current_minute = len(windows.get("minute", []))
        current_hour = len(windows.get("hour", []))
        current_day = len(windows.get("day", []))
        
        # Calculate usage percentages
        min_percent = f"{(current_minute/limits['requests_per_minute']*100):.1f}%" if isinstance(limits['requests_per_minute'], int) else "N/A"
        hour_percent = f"{(current_hour/limits['requests_per_hour']*100):.1f}%" if isinstance(limits['requests_per_hour'], int) else "N/A"
        day_percent = f"{(current_day/limits['requests_per_day']*100):.1f}%" if isinstance(limits['requests_per_day'], int) else "N/A"
        
        result["usage_counters_table"].append({
            "api_key": masked_key,
            "current_min": current_minute,
            "limit_min": limits['requests_per_minute'],
            "usage_min": min_percent,
            "current_hour": current_hour,
            "limit_hour": limits['requests_per_hour'],
            "usage_hour": hour_percent,
            "current_day": current_day,
            "limit_day": limits['requests_per_day'],
            "usage_day": day_percent
        })
    
    # Build IP tracking table
    for ip_address, tracking_info in ip_brutal_tracker._ip_tracking.items():
        # Mask IP for privacy (show first 2 octets)
        ip_parts = ip_address.split('.')
        if len(ip_parts) == 4:
            masked_ip = f"{ip_parts[0]}.{ip_parts[1]}.x.x"
        else:
            masked_ip = ip_address[:8] + "..."
        
        requests_last_minute = tracking_info.get_requests_in_last_minute()
        time_since_last = int((datetime.now() - tracking_info.last_request).total_seconds())
        
        result["ip_tracking_table"].append({
            "ip_address": masked_ip,
            "requests_last_min": requests_last_minute,
            "total_requests": tracking_info.total_requests,
            "is_blocked": tracking_info.is_blocked,
            "block_reason": tracking_info.block_reason,
            "last_request_sec_ago": time_since_last,
            "first_seen": tracking_info.first_seen.strftime("%H:%M:%S"),
            "should_block": tracking_info.should_be_blocked(50)  # 50 req/min threshold
        })
    
    # Build blocked IPs table (from IP blocking middleware)
    # Note: This would need access to the middleware instance
    # For now, let's read from the blocked_ips.json file
    try:
        import json
        import os
        
        blocked_file = "blocked_ips.json"
        if os.path.exists(blocked_file):
            with open(blocked_file, 'r') as f:
                blocked_data = json.load(f)
                
                for ip in blocked_data.get('ips', []):
                    ip_parts = ip.split('.')
                    masked_ip = f"{ip_parts[0]}.{ip_parts[1]}.x.x" if len(ip_parts) == 4 else ip[:8] + "..."
                    
                    result["blocked_ips_table"].append({
                        "ip_address": masked_ip,
                        "type": "IP",
                        "reason": "Manually blocked"
                    })
                
                for api_key in blocked_data.get('api_keys', []):
                    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else api_key[:4] + "..."
                    
                    result["blocked_ips_table"].append({
                        "ip_address": masked_key,
                        "type": "API_KEY",
                        "reason": "API key blocked"
                    })
    except Exception as e:
        result["blocked_ips_table"] = [{"error": f"Could not load blocked IPs: {str(e)}"}]
    
    return result

@router.get("/cache-status")
async def get_cache_status():
    """Get current cache status and statistics"""
    cache_stats = rate_limit_cache.get_cache_stats()
    
    # Get cache contents (sanitized)
    cache_contents = {}
    for api_key, cached_config in rate_limit_cache._cache.items():
        cache_contents[api_key[:8] + "..."] = {
            "client_id": cached_config.client_id,
            "access_tier": cached_config.access_tier,
            "limits": {
                "per_minute": cached_config.requests_per_minute,
                "per_hour": cached_config.requests_per_hour,
                "per_day": cached_config.requests_per_day
            },
            "status": {
                "is_active": cached_config.is_active,
                "is_suspended": cached_config.is_suspended,
                "is_auto_blocked": cached_config.is_auto_blocked,
                "override_limits": cached_config.override_all_limits
            },
            "cache_metadata": {
                "cached_at": cached_config.cached_at.isoformat(),
                "last_refreshed": cached_config.last_refreshed.isoformat(),
                "refresh_count": cached_config.refresh_count,
                "is_expired": cached_config.is_cache_expired(),
                "should_force_refresh": cached_config.should_force_refresh()
            }
        }
    
    return {
        "cache_statistics": cache_stats,
        "cache_contents": cache_contents,
        "cache_configuration": {
            "cache_ttl_minutes": rate_limit_cache.cache_ttl_minutes,
            "force_refresh_threshold_minutes": rate_limit_cache.force_refresh_threshold_minutes,
            "cleanup_interval_minutes": rate_limit_cache.cleanup_interval_minutes
        }
    }

@router.get("/usage-windows")
async def get_usage_windows():
    """Get current in-memory usage tracking windows"""
    current_time = datetime.now()
    
    # Sanitize and format usage windows
    sanitized_windows = {}
    for api_key, windows in usage_windows.items():
        sanitized_key = api_key[:8] + "..."
        
        sanitized_windows[sanitized_key] = {
            "current_usage": {
                "minute": len(windows.get("minute", [])),
                "hour": len(windows.get("hour", [])),
                "day": len(windows.get("day", []))
            },
            "timestamps": {
                "minute_window": windows.get("minute", [])[-5:],  # Last 5 timestamps
                "hour_window": windows.get("hour", [])[-5:],
                "day_window": windows.get("day", [])[-5:]
            }
        }
    
    return {
        "current_time": current_time.isoformat(),
        "usage_windows": sanitized_windows,
        "total_tracked_keys": len(usage_windows)
    }

@router.get("/my-usage/{api_key}")
async def get_my_usage(api_key: str, request: Request):
    """Get detailed usage information for a specific API key"""
    
    # Validate the key exists and get cached config
    try:
        cached_config = await rate_limit_cache.get_rate_limit_config(api_key)
        if not cached_config:
            raise HTTPException(status_code=404, detail="API key not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error retrieving API key info: {str(e)}")
    
    # Get usage statistics
    usage_stats = db_quota_manager.get_usage_stats_cached(cached_config)
    
    # Get current usage windows
    current_usage_windows = {}
    if api_key in usage_windows:
        windows = usage_windows[api_key]
        current_usage_windows = {
            "minute_timestamps": windows.get("minute", []),
            "hour_timestamps": windows.get("hour", []),
            "day_timestamps": windows.get("day", [])
        }
    
    return {
        "api_key": api_key[:8] + "...",
        "usage_statistics": usage_stats,
        "current_windows": current_usage_windows,
        "limits_source": "database_cached",
        "cache_info": {
            "cached_at": cached_config.cached_at.isoformat(),
            "last_refreshed": cached_config.last_refreshed.isoformat(),
            "refresh_count": cached_config.refresh_count,
            "cache_is_fresh": not cached_config.is_cache_expired(),
            "needs_force_refresh": cached_config.should_force_refresh()
        }
    }

@router.post("/refresh-cache/{api_key}")
async def force_refresh_cache(api_key: str):
    """Force refresh cache for specific API key"""
    try:
        # Invalidate current cache
        rate_limit_cache.invalidate_cache(api_key)
        
        # Force new fetch from database
        cached_config = await rate_limit_cache.get_rate_limit_config(api_key)
        
        if not cached_config:
            raise HTTPException(status_code=404, detail="API key not found in database")
        
        return {
            "message": f"Cache refreshed for API key {api_key[:8]}...",
            "new_limits": cached_config.get_rate_limits(),
            "refresh_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing cache: {str(e)}")

@router.get("/memory-summary")
async def get_memory_summary():
    """Get overall memory usage summary"""
    
    # Calculate memory usage estimates
    cache_entries = len(rate_limit_cache._cache)
    usage_window_keys = len(usage_windows)
    
    total_usage_timestamps = 0
    for windows in usage_windows.values():
        total_usage_timestamps += len(windows.get("minute", []))
        total_usage_timestamps += len(windows.get("hour", []))
        total_usage_timestamps += len(windows.get("day", []))
    
    return {
        "cache_summary": {
            "cached_api_keys": cache_entries,
            "cache_hit_rate": rate_limit_cache.get_cache_stats()["hit_rate_percent"]
        },
        "usage_tracking_summary": {
            "tracked_api_keys": usage_window_keys,
            "total_timestamp_entries": total_usage_timestamps,
            "average_timestamps_per_key": round(total_usage_timestamps / usage_window_keys, 2) if usage_window_keys > 0 else 0
        },
        "system_status": "operational",
        "last_cleanup": rate_limit_cache.last_cleanup.isoformat()
    }

@router.get("/security-events")
async def get_recent_security_events(limit: int = 20):
    """Get recent security events from database"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT TOP (:limit)
                    event_id,
                    event_type,
                    event_timestamp,
                    source_ip,
                    api_key,
                    client_id,
                    event_severity,
                    event_description,
                    action_taken,
                    endpoint,
                    response_code
                FROM app.security_events
                ORDER BY event_timestamp DESC
            """), {"limit": limit})
            
            events = []
            for row in result:
                events.append({
                    "event_id": row.event_id,
                    "event_type": row.event_type,
                    "timestamp": row.event_timestamp.isoformat(),
                    "source_ip": row.source_ip,
                    "api_key": row.api_key[:8] + "..." if row.api_key else None,
                    "client_id": row.client_id,
                    "severity": row.event_severity,
                    "description": row.event_description,
                    "action_taken": row.action_taken,
                    "endpoint": row.endpoint,
                    "response_code": row.response_code
                })
            
            return {
                "total_events": len(events),
                "events": events
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/security-stats")
async def get_security_statistics():
    """Get security statistics from database"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Get today's stats
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN event_type = 'BRUTAL_ATTACK' THEN 1 END) as brutal_attacks,
                    COUNT(CASE WHEN event_type = 'RATE_LIMIT_EXCEEDED' THEN 1 END) as rate_violations,
                    COUNT(CASE WHEN event_type = 'IP_BLOCKED' THEN 1 END) as ip_blocks,
                    COUNT(DISTINCT source_ip) as unique_ips
                FROM app.security_events 
                WHERE CAST(event_timestamp AS DATE) = CAST(GETDATE() AS DATE)
            """))
            
            today_stats = result.fetchone()
            
            # Get recent rate limit violations
            result = conn.execute(text("""
                SELECT TOP 10
                    api_key,
                    source_ip,
                    limit_type,
                    actual_requests,
                    limit_value,
                    violation_timestamp,
                    access_tier
                FROM app.rate_limit_violations
                ORDER BY violation_timestamp DESC
            """))
            
            violations = []
            for row in result:
                violations.append({
                    "api_key": row.api_key[:8] + "..." if row.api_key else None,
                    "source_ip": row.source_ip,
                    "limit_type": row.limit_type,
                    "actual_requests": row.actual_requests,
                    "limit_value": row.limit_value,
                    "timestamp": row.violation_timestamp.isoformat(),
                    "access_tier": row.access_tier
                })
            
            # Get recent IP blocks
            result = conn.execute(text("""
                SELECT TOP 10
                    ip_address,
                    block_reason,
                    requests_in_period,
                    block_timestamp
                FROM app.ip_blocking_events
                ORDER BY block_timestamp DESC
            """))
            
            blocks = []
            for row in result:
                blocks.append({
                    "ip_address": row.ip_address,
                    "block_reason": row.block_reason,
                    "requests_in_period": row.requests_in_period,
                    "timestamp": row.block_timestamp.isoformat()
                })
            
            return {
                "today_stats": {
                    "total_events": today_stats.total_events,
                    "brutal_attacks": today_stats.brutal_attacks,
                    "rate_violations": today_stats.rate_violations,
                    "ip_blocks": today_stats.ip_blocks,
                    "unique_ips": today_stats.unique_ips
                },
                "recent_rate_violations": violations,
                "recent_ip_blocks": blocks
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/clear-cache")
async def clear_memory_cache():
    """Clear all in-memory caches and reset security tracking"""
    try:
        # Clear rate limit cache
        rate_limit_cache.cache_data.clear()
        rate_limit_cache.last_refresh.clear()
        rate_limit_cache.db_fetch_count = 0
        
        # Clear IP tracking
        ip_brutal_tracker._ip_tracking.clear()
        
        # Clear usage windows
        usage_windows.clear()
        
        # Reset security monitor
        security_monitor._activity_log.clear()
        
        return {
            "status": "success",
            "message": "All in-memory caches cleared",
            "cleared_items": [
                "rate_limit_cache",
                "ip_tracking",
                "usage_windows", 
                "security_monitor_logs"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

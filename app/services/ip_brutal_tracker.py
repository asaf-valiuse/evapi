"""
IP-based Brutal Attack Protection
Tracks IP requests regardless of call structure validation
"""
from typing import Dict, List
from datetime import datetime, timedelta
import json
import os
import threading
from dataclasses import dataclass
from .security_event_logger import security_logger
import asyncio

@dataclass
class IPTrackingInfo:
    """IP tracking information for brutal attack detection"""
    ip_address: str
    requests_in_minute: List[datetime]
    total_requests: int
    first_seen: datetime
    last_request: datetime
    is_blocked: bool
    block_reason: str
    block_timestamp: datetime = None
    
    def cleanup_old_requests(self):
        """Remove requests older than 1 minute"""
        cutoff = datetime.now() - timedelta(minutes=1)
        self.requests_in_minute = [
            req_time for req_time in self.requests_in_minute 
            if req_time > cutoff
        ]
    
    def get_requests_in_last_minute(self) -> int:
        """Get count of requests in last minute"""
        self.cleanup_old_requests()
        return len(self.requests_in_minute)
    
    def should_be_blocked(self, threshold: int = 50) -> bool:
        """Check if IP should be blocked due to brutal usage"""
        return self.get_requests_in_last_minute() >= threshold

class IPBrutalAttackTracker:
    """Tracks all IP requests for brutal attack detection"""
    
    def __init__(self):
        # In-memory IP tracking: {ip_address: IPTrackingInfo}
        self._ip_tracking: Dict[str, IPTrackingInfo] = {}
        self.blocked_ips_file = "blocked_ips.json"
        self.brutal_attack_threshold = 50  # requests per minute
        self._load_blocked_ips()
    
    def _load_blocked_ips(self):
        """Load previously blocked IPs from file"""
        try:
            if os.path.exists(self.blocked_ips_file):
                with open(self.blocked_ips_file, 'r') as f:
                    file_data = json.load(f)
                    
                    # Handle both old format (direct IP mapping) and new format (with 'ips' array)
                    if isinstance(file_data, dict):
                        if 'ips' in file_data:
                            # New format: {"ips": [], "api_keys": [], "ranges": [], "updated": "..."}
                            # For now, we'll just initialize with empty tracking since this is a different format
                            # The brutal tracker will rebuild its data as requests come in
                            pass
                        else:
                            # Old format: direct IP to data mapping
                            blocked_data = file_data
                            for ip, data in blocked_data.items():
                                if isinstance(data, dict):  # Ensure data is a dict
                                    self._ip_tracking[ip] = IPTrackingInfo(
                                        ip_address=ip,
                                        requests_in_minute=[],
                                        total_requests=data.get('total_requests', 0),
                                        first_seen=datetime.fromisoformat(data.get('first_seen', datetime.now().isoformat())),
                                        last_request=datetime.fromisoformat(data.get('last_request', datetime.now().isoformat())),
                                        is_blocked=data.get('is_blocked', False),
                                        block_reason=data.get('block_reason', ''),
                                        block_timestamp=datetime.fromisoformat(data['block_timestamp']) if data.get('block_timestamp') else None
                                    )
        except Exception as e:
            print(f"Warning: Could not load blocked IPs: {e}")
    
    def _save_blocked_ips(self):
        """Save blocked IPs to file"""
        try:
            blocked_data = {}
            for ip, info in self._ip_tracking.items():
                if info.is_blocked:
                    blocked_data[ip] = {
                        'total_requests': info.total_requests,
                        'first_seen': info.first_seen.isoformat(),
                        'last_request': info.last_request.isoformat(),
                        'is_blocked': info.is_blocked,
                        'block_reason': info.block_reason,
                        'block_timestamp': info.block_timestamp.isoformat() if info.block_timestamp else None
                    }
            
            with open(self.blocked_ips_file, 'w') as f:
                json.dump(blocked_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save blocked IPs: {e}")
    
    def track_ip_request(self, ip_address: str) -> bool:
        """
        Track IP request and return True if IP should be blocked
        This is called for EVERY request regardless of structure validation
        """
        now = datetime.now()
        
        # Initialize IP tracking if not exists
        if ip_address not in self._ip_tracking:
            self._ip_tracking[ip_address] = IPTrackingInfo(
                ip_address=ip_address,
                requests_in_minute=[now],
                total_requests=1,
                first_seen=now,
                last_request=now,
                is_blocked=False,
                block_reason=""
            )
        else:
            # Update existing IP info
            ip_info = self._ip_tracking[ip_address]
            ip_info.requests_in_minute.append(now)
            ip_info.total_requests += 1
            ip_info.last_request = now
            ip_info.cleanup_old_requests()
        
        ip_info = self._ip_tracking[ip_address]
        
        # Check if already blocked
        if ip_info.is_blocked:
            return True
        
        # Check if should be blocked due to brutal usage
        if ip_info.should_be_blocked(self.brutal_attack_threshold):
            ip_info.is_blocked = True
            requests_count = ip_info.get_requests_in_last_minute()
            ip_info.block_reason = f"Brutal attack: {requests_count} requests in 1 minute"
            ip_info.block_timestamp = now
            self._save_blocked_ips()
            
            # Log to database asynchronously - use thread-safe approach
            try:
                # Try to get current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create task
                    asyncio.create_task(security_logger.log_ip_block_event(
                        ip_address=ip_address,
                        block_reason=ip_info.block_reason,
                        block_type="AUTO_BRUTAL_ATTACK",
                        requests_in_period=requests_count,
                        time_period_minutes=1,
                        total_requests_lifetime=ip_info.total_requests,
                        first_seen_timestamp=ip_info.first_seen
                    ))
                else:
                    # If no loop running, run in thread
                    import threading
                    def log_async():
                        asyncio.run(security_logger.log_ip_block_event(
                            ip_address=ip_address,
                            block_reason=ip_info.block_reason,
                            block_type="AUTO_BRUTAL_ATTACK",
                            requests_in_period=requests_count,
                            time_period_minutes=1,
                            total_requests_lifetime=ip_info.total_requests,
                            first_seen_timestamp=ip_info.first_seen
                        ))
                    threading.Thread(target=log_async, daemon=True).start()
            except RuntimeError:
                # No event loop, run in thread
                import threading
                def log_async():
                    asyncio.run(security_logger.log_ip_block_event(
                        ip_address=ip_address,
                        block_reason=ip_info.block_reason,
                        block_type="AUTO_BRUTAL_ATTACK",
                        requests_in_period=requests_count,
                        time_period_minutes=1,
                        total_requests_lifetime=ip_info.total_requests,
                        first_seen_timestamp=ip_info.first_seen
                    ))
                threading.Thread(target=log_async, daemon=True).start()
            except Exception as e:
                print(f"Warning: Could not log IP block event to database: {e}")
            
            print(f"🚨 IP {ip_address} blocked for brutal attack: {requests_count} requests/minute")
            return True
        
        return False
    
    def is_ip_blocked(self, ip_address: str) -> tuple[bool, str]:
        """Check if IP is blocked"""
        if ip_address in self._ip_tracking:
            ip_info = self._ip_tracking[ip_address]
            if ip_info.is_blocked:
                return True, ip_info.block_reason
        return False, ""
    
    def get_ip_stats(self, ip_address: str = None) -> Dict:
        """Get IP statistics"""
        if ip_address:
            if ip_address in self._ip_tracking:
                ip_info = self._ip_tracking[ip_address]
                ip_info.cleanup_old_requests()
                return {
                    "ip": ip_address,
                    "requests_last_minute": ip_info.get_requests_in_last_minute(),
                    "total_requests": ip_info.total_requests,
                    "first_seen": ip_info.first_seen.isoformat(),
                    "last_request": ip_info.last_request.isoformat(),
                    "is_blocked": ip_info.is_blocked,
                    "block_reason": ip_info.block_reason
                }
            return {"ip": ip_address, "status": "not_tracked"}
        
        # Return all IPs summary
        stats = {
            "total_tracked_ips": len(self._ip_tracking),
            "blocked_ips": 0,
            "active_ips_last_minute": 0,
            "brutal_attack_threshold": self.brutal_attack_threshold
        }
        
        for ip_info in self._ip_tracking.values():
            ip_info.cleanup_old_requests()
            if ip_info.is_blocked:
                stats["blocked_ips"] += 1
            if ip_info.get_requests_in_last_minute() > 0:
                stats["active_ips_last_minute"] += 1
        
        return stats
    
    def unblock_ip(self, ip_address: str) -> bool:
        """Manually unblock an IP"""
        if ip_address in self._ip_tracking:
            self._ip_tracking[ip_address].is_blocked = False
            self._ip_tracking[ip_address].block_reason = ""
            self._ip_tracking[ip_address].block_timestamp = None
            self._save_blocked_ips()
            print(f"IP {ip_address} manually unblocked")
            return True
        return False
    
    def get_memory_data(self) -> Dict:
        """Get all in-memory IP tracking data for debugging"""
        memory_data = {}
        for ip, info in self._ip_tracking.items():
            info.cleanup_old_requests()
            memory_data[ip] = {
                "requests_in_minute_count": len(info.requests_in_minute),
                "requests_timestamps": [t.isoformat() for t in info.requests_in_minute[-5:]],  # Last 5
                "total_requests": info.total_requests,
                "first_seen": info.first_seen.isoformat(),
                "last_request": info.last_request.isoformat(),
                "is_blocked": info.is_blocked,
                "block_reason": info.block_reason,
                "block_timestamp": info.block_timestamp.isoformat() if info.block_timestamp else None
            }
        return memory_data

# Global IP tracker instance
ip_brutal_tracker = IPBrutalAttackTracker()

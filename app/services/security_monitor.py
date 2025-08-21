"""
API monitoring and security logging
"""
import logging
from datetime import datetime
from typing import Dict, Any
import json
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_security.log'),
        logging.StreamHandler()
    ]
)

security_logger = logging.getLogger('security')

class SecurityMonitor:
    def __init__(self):
        self.alerts_enabled = os.getenv("ENABLE_SECURITY_ALERTS", "true").lower() == "true"
    
    def log_suspicious_activity(self, 
                              event_type: str, 
                              ip: str, 
                              details: Dict[str, Any]):
        """Log suspicious activity with structured data"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "ip_address": ip,
            "severity": self._get_severity(event_type),
            "details": details
        }
        
        security_logger.warning(f"SECURITY_EVENT: {json.dumps(log_entry)}")
        
        # Send alert if enabled and severity is high
        if self.alerts_enabled and log_entry["severity"] == "HIGH":
            self._send_security_alert(log_entry)
    
    def log_api_usage(self, 
                     api_key: str, 
                     endpoint: str, 
                     ip: str, 
                     response_code: int,
                     response_time: float):
        """Log normal API usage for monitoring"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "API_USAGE",
            "api_key": api_key[:8] + "..." if api_key else None,  # Masked for privacy
            "endpoint": endpoint,
            "ip_address": ip,
            "response_code": response_code,
            "response_time_ms": round(response_time * 1000, 2)
        }
        
        security_logger.info(f"API_USAGE: {json.dumps(log_entry)}")
    
    def log_rate_limit_exceeded(self, ip: str, api_key: str, limit_type: str):
        """Log rate limit violations"""
        self.log_suspicious_activity(
            "RATE_LIMIT_EXCEEDED",
            ip,
            {
                "api_key": api_key[:8] + "..." if api_key else None,
                "limit_type": limit_type,
                "action": "REQUEST_BLOCKED"
            }
        )
    
    def log_authentication_failure(self, ip: str, attempted_key: str):
        """Log failed authentication attempts"""
        self.log_suspicious_activity(
            "AUTH_FAILURE",
            ip,
            {
                "attempted_key": attempted_key[:8] + "..." if attempted_key else None,
                "action": "ACCESS_DENIED"
            }
        )
    
    def log_ip_blocked(self, ip: str, reason: str):
        """Log when an IP is automatically blocked"""
        self.log_suspicious_activity(
            "IP_AUTO_BLOCKED",
            ip,
            {
                "reason": reason,
                "action": "IP_BANNED"
            }
        )
    
    def _get_severity(self, event_type: str) -> str:
        """Determine severity level based on event type"""
        high_severity_events = [
            "IP_AUTO_BLOCKED",
            "MULTIPLE_AUTH_FAILURES",
            "QUOTA_ABUSE"
        ]
        
        if event_type in high_severity_events:
            return "HIGH"
        elif event_type in ["RATE_LIMIT_EXCEEDED", "AUTH_FAILURE"]:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _send_security_alert(self, log_entry: Dict[str, Any]):
        """Send security alert (implement your notification method here)"""
        # This is where you would integrate with your alerting system
        # Examples: email, Slack webhook, PagerDuty, etc.
        
        print(f"🚨 HIGH SEVERITY SECURITY ALERT: {log_entry['event_type']}")
        print(f"   IP: {log_entry['ip_address']}")
        print(f"   Time: {log_entry['timestamp']}")
        print(f"   Details: {log_entry['details']}")

# Global instance
security_monitor = SecurityMonitor()

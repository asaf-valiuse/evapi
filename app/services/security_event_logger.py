"""
Database Security Logger
Stores security events in database for long-term tracking and analysis
"""
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from .db import get_engine
import json
import asyncio

class SecurityEventLogger:
    """Database logger for security events"""
    
    def __init__(self):
        self.engine = get_engine()
    
    async def log_security_event(
        self,
        event_type: str,
        event_description: str,
        source_ip: Optional[str] = None,
        api_key: Optional[str] = None,
        client_id: Optional[int] = None,
        event_severity: str = "MEDIUM",
        action_taken: Optional[str] = None,
        endpoint: Optional[str] = None,
        response_code: Optional[int] = None,
        event_data: Optional[Dict] = None,
        user_agent: Optional[str] = None
    ) -> Optional[int]:
        """Log a security event to database"""
        
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text("""
                    INSERT INTO app.security_events (
                        event_type, event_timestamp, source_ip, api_key, client_id,
                        event_severity, event_description, event_data, action_taken,
                        endpoint, response_code, user_agent
                    )
                    OUTPUT INSERTED.event_id
                    VALUES (
                        :event_type, GETDATE(), :source_ip, :api_key, :client_id,
                        :event_severity, :event_description, :event_data, :action_taken,
                        :endpoint, :response_code, :user_agent
                    )
                """), {
                    "event_type": event_type,
                    "source_ip": source_ip,
                    "api_key": api_key,
                    "client_id": client_id,
                    "event_severity": event_severity,
                    "event_description": event_description,
                    "event_data": json.dumps(event_data) if event_data else None,
                    "action_taken": action_taken,
                    "endpoint": endpoint,
                    "response_code": response_code,
                    "user_agent": user_agent
                })
                
                event_id = result.scalar()
                return event_id
                
        except Exception as e:
            print(f"Error logging security event: {e}")
            return None
    
    async def log_rate_limit_violation(
        self,
        api_key: str,
        client_id: int,
        source_ip: str,
        limit_type: str,
        limit_value: int,
        actual_requests: int,
        access_tier: str,
        requests_per_minute: int,
        requests_per_hour: int,
        requests_per_day: int,
        endpoint: str,
        user_agent: Optional[str] = None
    ) -> Optional[int]:
        """Log rate limit violation to database"""
        
        # First log the main security event
        event_id = await self.log_security_event(
            event_type="RATE_LIMIT_EXCEEDED",
            event_description=f"Rate limit exceeded: {actual_requests}/{limit_value} requests per {limit_type.lower()}",
            source_ip=source_ip,
            api_key=api_key,
            client_id=client_id,
            event_severity="MEDIUM" if actual_requests < limit_value * 1.5 else "HIGH",
            action_taken="REQUEST_DENIED",
            endpoint=endpoint,
            response_code=429,
            user_agent=user_agent,
            event_data={
                "limit_type": limit_type,
                "limit_value": limit_value,
                "actual_requests": actual_requests,
                "excess_requests": actual_requests - limit_value,
                "access_tier": access_tier
            }
        )
        
        # Then log the detailed rate limit violation
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO app.rate_limit_violations (
                        api_key, client_id, source_ip, limit_type, limit_value, 
                        actual_requests, excess_requests, access_tier,
                        requests_per_minute, requests_per_hour, requests_per_day,
                        endpoint, user_agent, security_event_id
                    )
                    VALUES (
                        :api_key, :client_id, :source_ip, :limit_type, :limit_value,
                        :actual_requests, :excess_requests, :access_tier,
                        :requests_per_minute, :requests_per_hour, :requests_per_day,
                        :endpoint, :user_agent, :security_event_id
                    )
                """), {
                    "api_key": api_key,
                    "client_id": client_id,
                    "source_ip": source_ip,
                    "limit_type": limit_type,
                    "limit_value": limit_value,
                    "actual_requests": actual_requests,
                    "excess_requests": actual_requests - limit_value,
                    "access_tier": access_tier,
                    "requests_per_minute": requests_per_minute,
                    "requests_per_hour": requests_per_hour,
                    "requests_per_day": requests_per_day,
                    "endpoint": endpoint,
                    "user_agent": user_agent,
                    "security_event_id": event_id
                })
                
        except Exception as e:
            print(f"Error logging rate limit violation: {e}")
        
        return event_id
    
    async def log_ip_block_event(
        self,
        ip_address: str,
        block_reason: str,
        block_type: str = "AUTO_BRUTAL_ATTACK",
        requests_in_period: Optional[int] = None,
        time_period_minutes: Optional[int] = None,
        total_requests_lifetime: Optional[int] = None,
        first_seen_timestamp: Optional[datetime] = None
    ) -> Optional[int]:
        """Log IP blocking event to database"""
        
        # First log the main security event
        event_id = await self.log_security_event(
            event_type="IP_BLOCKED",
            event_description=f"IP blocked: {block_reason}",
            source_ip=ip_address,
            event_severity="HIGH",
            action_taken="IP_BLOCKED",
            event_data={
                "block_type": block_type,
                "requests_in_period": requests_in_period,
                "time_period_minutes": time_period_minutes,
                "total_requests_lifetime": total_requests_lifetime
            }
        )
        
        # Then log the detailed IP blocking event
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO app.ip_blocking_events (
                        ip_address, block_reason, block_type, requests_in_period,
                        time_period_minutes, total_requests_lifetime, first_seen_timestamp,
                        security_event_id
                    )
                    VALUES (
                        :ip_address, :block_reason, :block_type, :requests_in_period,
                        :time_period_minutes, :total_requests_lifetime, :first_seen_timestamp,
                        :security_event_id
                    )
                """), {
                    "ip_address": ip_address,
                    "block_reason": block_reason,
                    "block_type": block_type,
                    "requests_in_period": requests_in_period,
                    "time_period_minutes": time_period_minutes,
                    "total_requests_lifetime": total_requests_lifetime,
                    "first_seen_timestamp": first_seen_timestamp,
                    "security_event_id": event_id
                })
                
        except Exception as e:
            print(f"Error logging IP block event: {e}")
        
        return event_id
    
    async def log_api_key_security_event(
        self,
        api_key: str,
        client_id: int,
        event_type: str,
        event_description: str,
        source_ip: Optional[str] = None,
        endpoint: Optional[str] = None,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        action_automatic: bool = True,
        action_by: Optional[str] = None
    ):
        """Log API key security event to database"""
        
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO app.api_key_security_events (
                        api_key, client_id, event_type, event_description,
                        source_ip, endpoint, previous_status, new_status,
                        action_automatic, action_by
                    )
                    VALUES (
                        :api_key, :client_id, :event_type, :event_description,
                        :source_ip, :endpoint, :previous_status, :new_status,
                        :action_automatic, :action_by
                    )
                """), {
                    "api_key": api_key,
                    "client_id": client_id,
                    "event_type": event_type,
                    "event_description": event_description,
                    "source_ip": source_ip,
                    "endpoint": endpoint,
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "action_automatic": action_automatic,
                    "action_by": action_by
                })
                
        except Exception as e:
            print(f"Error logging API key security event: {e}")
    
    async def update_daily_statistics(self):
        """Update daily security statistics"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    MERGE app.security_statistics_daily AS target
                    USING (
                        SELECT CAST(GETDATE() AS DATE) AS stat_date,
                               COUNT(*) AS total_events,
                               COUNT(CASE WHEN event_type = 'BRUTAL_ATTACK' THEN 1 END) AS brutal_attacks,
                               COUNT(CASE WHEN event_type = 'RATE_LIMIT_EXCEEDED' THEN 1 END) AS rate_limited_requests,
                               COUNT(CASE WHEN event_type = 'IP_BLOCKED' THEN 1 END) AS new_blocked_ips,
                               COUNT(DISTINCT source_ip) AS unique_ips
                        FROM app.security_events 
                        WHERE CAST(event_timestamp AS DATE) = CAST(GETDATE() AS DATE)
                    ) AS source ON target.stat_date = source.stat_date
                    WHEN MATCHED THEN
                        UPDATE SET 
                            brutal_attacks = source.brutal_attacks,
                            rate_limited_requests = source.rate_limited_requests,
                            new_blocked_ips = source.new_blocked_ips,
                            unique_ips = source.unique_ips,
                            updated_at = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (stat_date, brutal_attacks, rate_limited_requests, new_blocked_ips, unique_ips)
                        VALUES (source.stat_date, source.brutal_attacks, source.rate_limited_requests, source.new_blocked_ips, source.unique_ips);
                """))
                
        except Exception as e:
            print(f"Error updating daily statistics: {e}")

# Global instance
security_logger = SecurityEventLogger()

# Utility functions for easy integration
async def log_brutal_attack(ip_address: str, requests_count: int, time_period: int = 1):
    """Quick function to log brutal attack"""
    await security_logger.log_ip_block_event(
        ip_address=ip_address,
        block_reason=f"Brutal attack: {requests_count} requests in {time_period} minute(s)",
        block_type="AUTO_BRUTAL_ATTACK",
        requests_in_period=requests_count,
        time_period_minutes=time_period
    )

async def log_rate_limit_exceeded(api_key: str, client_id: int, source_ip: str, 
                                limit_type: str, actual: int, limit: int, 
                                tier: str, endpoint: str):
    """Quick function to log rate limit violation"""
    await security_logger.log_rate_limit_violation(
        api_key=api_key,
        client_id=client_id,
        source_ip=source_ip,
        limit_type=limit_type,
        limit_value=limit,
        actual_requests=actual,
        access_tier=tier,
        requests_per_minute=0,  # These would need to be passed in
        requests_per_hour=0,
        requests_per_day=0,
        endpoint=endpoint
    )

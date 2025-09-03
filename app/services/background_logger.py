"""
Background Database Logger
Utility functions for asynchronous database logging that runs after responses are sent
"""
from typing import Dict, Any, Optional
from .security_event_logger import SecurityEventLogger
from .security_monitor import security_monitor

# Global database logger instance
db_logger = SecurityEventLogger()

async def log_api_request_background(
    api_key: str,
    client_id: int,
    endpoint: str,
    client_ip: str,
    response_code: int,
    response_time: float,
    query_params: Dict[str, Any],
    user_agent: Optional[str] = None,
    error_details: Optional[str] = None
):
    """Background task to log API request to database"""
    try:
        event_data = {
            "query_params": query_params,
            "response_time_seconds": response_time
        }
        
        if error_details:
            event_data["error_details"] = error_details
        
        # Log to both security_events AND api_request_log tables
        await db_logger.log_security_event(
            event_type="API_REQUEST",
            event_description=f"API request to {endpoint}",
            source_ip=client_ip,
            api_key=api_key[:8] + "..." if len(api_key) > 8 else api_key,  # Only log partial key
            client_id=client_id,
            event_severity="INFO" if response_code < 400 else "WARN",
            endpoint=endpoint,
            response_code=response_code,
            event_data=event_data,
            user_agent=user_agent
        )
        
        # Also log to the specific api_request_log table if it exists
        await log_to_api_request_log_table(
            api_key=api_key,
            client_id=client_id,
            endpoint=endpoint,
            client_ip=client_ip,
            response_code=response_code,
            response_time=response_time,
            query_params=query_params,
            user_agent=user_agent,
            error_details=error_details
        )
        
    except Exception as e:
        # Log to file as fallback if database logging fails
        security_monitor.log_suspicious_activity(
            f"Database logging failed for API request: {str(e)}", 
            client_ip, 
            api_key[:8] + "..." if len(api_key) > 8 else api_key
        )

async def log_to_api_request_log_table(
    api_key: str,
    client_id: int,
    endpoint: str,
    client_ip: str,
    response_code: int,
    response_time: float,
    query_params: Dict[str, Any],
    user_agent: Optional[str] = None,
    error_details: Optional[str] = None
):
    """Log specifically to app.api_request_log table"""
    try:
        from .db import get_engine
        from sqlalchemy import text
        import json
        
        engine = get_engine()
        
        with engine.begin() as conn:
            # Check if the table exists first
            table_check = conn.execute(text("""
                SELECT COUNT(*) as table_exists 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'app' AND TABLE_NAME = 'api_request_log'
            """)).scalar()
            
            if table_check > 0:
                conn.execute(text("""
                    INSERT INTO app.api_request_log (
                        request_timestamp, api_key, client_id, endpoint, 
                        source_ip, response_code, response_time_seconds, 
                        query_params, user_agent, error_details
                    )
                    VALUES (
                        GETDATE(), :api_key, :client_id, :endpoint,
                        :source_ip, :response_code, :response_time,
                        :query_params, :user_agent, :error_details
                    )
                """), {
                    "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
                    "client_id": client_id,
                    "endpoint": endpoint,
                    "source_ip": client_ip,
                    "response_code": response_code,
                    "response_time": response_time,
                    "query_params": json.dumps(query_params) if query_params else None,
                    "user_agent": user_agent,
                    "error_details": error_details
                })
            else:
                # Table doesn't exist, log this info
                security_monitor.log_suspicious_activity(
                    "Table app.api_request_log does not exist for logging", 
                    client_ip, 
                    api_key[:8] + "..." if len(api_key) > 8 else api_key
                )
                
    except Exception as e:
        # Log the specific error
        security_monitor.log_suspicious_activity(
            f"Failed to log to app.api_request_log table: {str(e)}", 
            client_ip, 
            api_key[:8] + "..." if len(api_key) > 8 else api_key
        )

async def log_security_event_background(
    event_type: str,
    client_ip: str,
    api_key: Optional[str] = None,
    client_id: Optional[int] = None,
    endpoint: Optional[str] = None,
    response_code: Optional[int] = None,
    event_description: Optional[str] = None,
    event_data: Optional[Dict] = None,
    user_agent: Optional[str] = None,
    severity: str = "MEDIUM"
):
    """Background task to log security events to database"""
    try:
        await db_logger.log_security_event(
            event_type=event_type,
            event_description=event_description or f"Security event: {event_type}",
            source_ip=client_ip,
            api_key=api_key[:8] + "..." if api_key and len(api_key) > 8 else api_key,
            client_id=client_id,
            event_severity=severity,
            endpoint=endpoint,
            response_code=response_code,
            event_data=event_data,
            user_agent=user_agent
        )
    except Exception as e:
        # Log to file as fallback if database logging fails
        security_monitor.log_suspicious_activity(
            f"Database logging failed for security event {event_type}: {str(e)}", 
            client_ip, 
            api_key[:8] + "..." if api_key and len(api_key) > 8 else api_key
        )

async def log_rate_limit_violation_background(
    client_ip: str,
    api_key: str,
    client_id: int,
    endpoint: str,
    violation_type: str,
    current_usage: int,
    limit_value: int,
    user_agent: Optional[str] = None
):
    """Background task to log rate limit violations to database"""
    try:
        await db_logger.log_rate_limit_violation(
            source_ip=client_ip,
            api_key=api_key[:8] + "..." if len(api_key) > 8 else api_key,
            client_id=client_id,
            endpoint=endpoint,
            violation_type=violation_type,
            current_usage=current_usage,
            limit_value=limit_value,
            user_agent=user_agent
        )
    except Exception as e:
        # Log to file as fallback if database logging fails
        security_monitor.log_suspicious_activity(
            f"Database logging failed for rate limit violation: {str(e)}", 
            client_ip, 
            api_key[:8] + "..." if len(api_key) > 8 else api_key
        )

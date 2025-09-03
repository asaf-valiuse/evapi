"""
Security Logging Middleware
Middleware to handle background security logging for all requests
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import json
import time
from starlette.middleware.base import BaseHTTPMiddleware
from ..services.background_logger import log_security_event_background
import asyncio

class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log security events in the background after response"""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_events = {}  # Store events during request processing
    
    async def dispatch(self, request: Request, call_next):
        # Store request start time
        request.state.start_time = time.time()
        request.state.security_events = []
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Log any accumulated security events in background
            if hasattr(request.state, 'security_events') and request.state.security_events:
                for event in request.state.security_events:
                    # Schedule background logging without waiting
                    asyncio.create_task(self._log_security_event_async(event))
            
            return response
            
        except Exception as e:
            # Log the error event
            if hasattr(request.state, 'security_events'):
                error_event = {
                    "event_type": "API_ERROR",
                    "client_ip": request.headers.get("x-forwarded-for", 
                                                   request.client.host if request.client else "unknown"),
                    "endpoint": request.url.path,
                    "response_code": 500,
                    "event_description": f"API error: {str(e)}",
                    "severity": "ERROR"
                }
                asyncio.create_task(self._log_security_event_async(error_event))
            
            raise e
    
    async def _log_security_event_async(self, event_data):
        """Background task to log security event"""
        try:
            await log_security_event_background(
                event_type=event_data.get("event_type", "UNKNOWN"),
                client_ip=event_data.get("client_ip", "unknown"),
                api_key=event_data.get("api_key"),
                client_id=event_data.get("client_id"),
                endpoint=event_data.get("endpoint"),
                response_code=event_data.get("response_code"),
                event_description=event_data.get("event_description"),
                event_data=event_data.get("event_data"),
                user_agent=event_data.get("user_agent"),
                severity=event_data.get("severity", "MEDIUM")
            )
        except Exception as e:
            # Silent fail - don't break the application
            print(f"Background security logging failed: {e}")

# Helper function to add security events to the request context
def add_security_event(request: Request, event_type: str, **kwargs):
    """Add a security event to be logged in background after response"""
    if not hasattr(request.state, 'security_events'):
        request.state.security_events = []
    
    client_ip = request.headers.get("x-forwarded-for", 
                                  request.client.host if request.client else "unknown")
    
    event = {
        "event_type": event_type,
        "client_ip": client_ip,
        "endpoint": request.url.path,
        "user_agent": request.headers.get("user-agent"),
        **kwargs
    }
    
    request.state.security_events.append(event)

"""
Request protection middleware
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import asyncio
from typing import Callable

class RequestProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        max_request_size: int = 1024 * 1024,  # 1MB
        request_timeout: float = 30.0,  # 30 seconds
        max_concurrent_requests: int = 100
    ):
        super().__init__(app)
        self.max_request_size = max_request_size
        self.request_timeout = request_timeout
        self.max_concurrent_requests = max_concurrent_requests
        self.active_requests = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check concurrent requests limit
        if self.active_requests >= self.max_concurrent_requests:
            raise HTTPException(status_code=429, detail="Server busy, too many concurrent requests")
        
        # Check request size (for POST/PUT requests)
        if hasattr(request, 'headers'):
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > self.max_request_size:
                raise HTTPException(status_code=413, detail="Request too large")

        self.active_requests += 1
        start_time = time.time()
        
        try:
            # Set timeout for the request
            response = await asyncio.wait_for(
                call_next(request), 
                timeout=self.request_timeout
            )
            return response
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Request timeout")
        finally:
            self.active_requests -= 1
            # Log slow requests
            duration = time.time() - start_time
            if duration > 10:  # Log requests taking more than 10 seconds
                print(f"Slow request: {request.url.path} took {duration:.2f}s")

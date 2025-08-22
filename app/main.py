from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .routers import telemetry
# Removed old rate limiting middleware - now using database-driven system
from .middleware.request_protection import RequestProtectionMiddleware
from .middleware.ip_blocking import IPBlockingMiddleware
from .services.auth import resolve_client_from_key
from datetime import datetime
import os
from pathlib import Path

# Disable docs in production for security
app = FastAPI(
    title="Direct Link API", 
    version="1.0.0",
    docs_url=None,      # Disables /docs
    redoc_url=None,     # Disables /redoc
    openapi_url=None    # Disables /openapi.json
)

# ——— Security Middleware (order matters!) ———

# 1. IP and API Key blocking (first line of defense)
app.add_middleware(IPBlockingMiddleware)

# 2. Request protection (size, timeout, concurrent requests)
app.add_middleware(
    RequestProtectionMiddleware,
    max_request_size=1024 * 1024,  # 1MB max request size
    request_timeout=30.0,          # 30 second timeout
    max_concurrent_requests=100    # Max 100 concurrent requests
)

# 3. CORS (be more restrictive in production)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],         # Only allow GET requests for your API
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(telemetry.router)

# Serve API manual at /api_doc
public_dir = Path(__file__).resolve().parent / "public"
if public_dir.exists():
    # Mount assets and directory browsing under /api_doc/*
    app.mount("/api_doc", StaticFiles(directory=str(public_dir), html=True), name="api_doc")

    # Ensure /api_doc (exact) serves the index.html
    @app.get("/api_doc", include_in_schema=False)
    async def api_doc_index():
        index_path = public_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path), media_type="text/html")
        raise HTTPException(status_code=404, detail="API manual not found")

@app.get("/healthz")
def healthz(request: Request):
    """Health check endpoint with brutal attack protection"""
    # Import here to avoid circular imports
    from .services.ip_brutal_tracker import ip_brutal_tracker
    
    # Get client IP
    client_ip = request.headers.get("x-forwarded-for", 
                                  request.client.host if request.client else "unknown")
    
    # Track IP for brutal attack detection
    is_ip_blocked = ip_brutal_tracker.track_ip_request(client_ip)
    
    if is_ip_blocked:
        blocked_reason = ip_brutal_tracker.is_ip_blocked(client_ip)[1]
        
        # Return blocked response with details
        return {
            "status": "blocked",
            "reason": blocked_reason,
            "message": f"IP blocked due to brutal attack: {blocked_reason}",
            "endpoint": "/healthz",
            "timestamp": datetime.now().isoformat()
        }
    
    return {"ok": True}

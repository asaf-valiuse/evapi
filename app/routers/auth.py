# app/routers/auth.py
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import time
from ..services.token_service import token_service
from ..services.security_monitor import security_monitor

router = APIRouter(tags=["authentication"])

@router.post("/auth/token")
async def get_token(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Exchange API key for JWT token
    
    Usage:
    POST /auth/token
    Authorization: Bearer YOUR_API_KEY
    
    Returns:
    {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "Bearer",
        "expires_in": 3600,
        "expires_at": "2025-08-24T11:30:00",
        "client_id": 123
    }
    """
    start_time = time.time()
    client_ip = request.headers.get("x-forwarded-for", 
                                  request.client.host if request.client else "unknown")
    
    if not authorization:
        security_monitor.log_suspicious_activity(
            "TOKEN_REQUEST_NO_AUTH",
            client_ip,
            {"endpoint": "/auth/token"}
        )
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required"
        )
    
    try:
        # Create token using the token service
        token_data = await token_service.create_token(authorization)
        
        # Log successful token creation
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=authorization.replace("Bearer ", "")[:8] + "...",
            endpoint="/auth/token",
            ip=client_ip,
            response_code=200,
            response_time=response_time
        )
        
        return JSONResponse(content=token_data)
        
    except HTTPException as e:
        # Log failed token creation
        response_time = time.time() - start_time
        security_monitor.log_suspicious_activity(
            "TOKEN_REQUEST_FAILED",
            client_ip,
            {
                "endpoint": "/auth/token",
                "error": str(e.detail),
                "status_code": e.status_code
            }
        )
        raise e
    except Exception as e:
        # Log unexpected errors
        response_time = time.time() - start_time
        security_monitor.log_suspicious_activity(
            "TOKEN_REQUEST_ERROR",
            client_ip,
            {
                "endpoint": "/auth/token",
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Token service error")

@router.get("/auth/verify")
async def verify_token(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Verify JWT token validity
    
    Usage:
    GET /auth/verify
    Authorization: Bearer JWT_TOKEN
    
    Returns token payload if valid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Bearer token required")
    
    token = authorization[7:]  # Remove 'Bearer ' prefix
    
    try:
        payload = token_service.verify_token(token)
        return {
            "valid": True,
            "client_id": payload.get("client_id"),
            "expires_at": payload.get("exp"),
            "issued_at": payload.get("iat")
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Token verification error")

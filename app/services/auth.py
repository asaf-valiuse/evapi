# app/services/auth.py
from fastapi import HTTPException, Header
from typing import Optional
from sqlalchemy import text
from .db import get_engine
from .error_codes import ErrorCode, get_error_response

def extract_api_key_from_header(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract API key from Authorization header.
    Supports both 'Bearer TOKEN' and 'TOKEN' formats.
    Also supports JWT tokens.
    """
    if not authorization:
        error_response = get_error_response(ErrorCode.AUTH_ACCESS_DENIED)
        raise HTTPException(status_code=401, detail=error_response)
    
    # Handle 'Bearer TOKEN' format
    if authorization.startswith('Bearer '):
        return authorization[7:]  # Remove 'Bearer ' prefix
    
    # Handle direct token format
    return authorization

async def resolve_client_from_jwt_token(token: str) -> int:
    """
    Resolve client_id from JWT token
    """
    try:
        from .token_service import token_service
        payload = token_service.verify_token(token)
        return payload.get("client_id")
    except Exception:
        error_response = get_error_response(ErrorCode.AUTH_ACCESS_DENIED)
        raise HTTPException(status_code=401, detail=error_response)

async def resolve_account_from_header(authorization: Optional[str] = Header(None)) -> int:
    """
    Accepts Authorization header with API key or JWT token.
    Looks up the client_id for this key in SQL Server or decodes from JWT.
    Returns the client_id (prev_id) associated with the API key/token.
    """
    # Extract API key/token from header
    token_or_key = extract_api_key_from_header(authorization)
    
    # Check if it's a JWT token (starts with 'eyJ')
    if token_or_key.startswith('eyJ'):
        return await resolve_client_from_jwt_token(token_or_key)
    
    # Otherwise, treat it as an API key
    # Basic validation for GUID format
    import re
    guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    if not re.match(guid_pattern, token_or_key):
        error_response = get_error_response(ErrorCode.AUTH_INVALID_FORMAT)
        raise HTTPException(status_code=400, detail=error_response)
    
    try:
        engine = get_engine()
        sql = text("""
            SELECT prev_id as account_id
            FROM enervibe.accounts
            WHERE api_key = :k 
        """)
        with engine.begin() as conn:
            row = conn.execute(sql, {"k": token_or_key}).first()

        if not row:
            error_response = get_error_response(ErrorCode.AUTH_ACCESS_DENIED)
            raise HTTPException(status_code=401, detail=error_response)

        client_id = int(row[0])  # prev_id is the client_id

        # (Optional) audit: last_used_at
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE app.api_keys
                    SET last_api_key_used = SYSUTCDATETIME()
                    WHERE token = :k
                """), {"k": token_or_key})
        except Exception:
            pass

        return client_id
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Handle database connection or other errors
        error_msg = str(e).lower()
        if "conversion failed" in error_msg and "uniqueidentifier" in error_msg:
            error_response = get_error_response(ErrorCode.AUTH_INVALID_FORMAT)
            raise HTTPException(status_code=400, detail=error_response)
        elif "login failed" in error_msg or "cannot open database" in error_msg:
            error_response = get_error_response(ErrorCode.AUTH_SERVICE_UNAVAILABLE)
            raise HTTPException(status_code=503, detail=error_response)
        else:
            error_response = get_error_response(ErrorCode.AUTH_SERVICE_UNAVAILABLE)
            raise HTTPException(status_code=500, detail=error_response)

# Alias for consistency
async def resolve_client_from_header(authorization: Optional[str] = Header(None)) -> int:
    """
    Accepts Authorization header with API key or JWT token.
    Returns the client_id associated with the API key/token.
    """
    return await resolve_account_from_header(authorization)

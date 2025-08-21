# app/services/auth.py
from fastapi import Query, HTTPException
from sqlalchemy import text
from .db import get_engine
from .error_codes import ErrorCode, get_error_response

async def resolve_account_from_query(key: str = Query(...)) -> int:
    """
    Accepts ?key=... as a query parameter.
    Looks up the client_id for this key in SQL Server.
    Returns the client_id (prev_id) associated with the API key.
    """
    # Basic validation for GUID format
    import re
    guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    if not re.match(guid_pattern, key):
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
            row = conn.execute(sql, {"k": key}).first()

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
                """), {"k": key})
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

async def resolve_client_from_key(key: str = Query(...)) -> int:
    """
    Accepts ?key=... as a query parameter.
    Looks up the client_id for this key in SQL Server.
    This is an alias for resolve_account_from_query but returns client_id.
    """
    return await resolve_account_from_query(key)

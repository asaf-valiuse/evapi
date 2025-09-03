# app/routers/telemetry.py
from fastapi import APIRouter, Depends, Query, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, Optional, List
import csv, io

from ..services.comprehensive_protection import comprehensive_api_protection
from ..services.query_service import run_saved_query
from ..services.error_codes import CodedError, ErrorCode
from ..services.security_monitor import security_monitor
from ..services.background_logger import log_api_request_background

router = APIRouter(tags=["queries"])

@router.get("/run")
async def run_saved(
    background_tasks: BackgroundTasks,
    request: Request,
    q: str = Query(..., description="Query code (catalog key)"),
    cached_config = Depends(comprehensive_api_protection),  # Comprehensive API protection flow
    format: str = Query("json", pattern="^(json|csv)$"),
    demo: bool = Query(False, description="Return demo data instead of actual results"),
    minutes: int = Query(None, description="Custom time window in minutes for the query")
):
    import time
    start_time = time.time()
    
    # Get client IP for logging
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    
    # API key is now extracted from headers via comprehensive protection
    # Get the first 8 characters for logging (it's already been validated)
    authorization = request.headers.get("authorization", "")
    api_key_for_logging = ""
    if authorization:
        if authorization.startswith('Bearer '):
            api_key_for_logging = authorization[7:15] + "..."  # First 8 chars + "..."
        else:
            api_key_for_logging = authorization[:8] + "..."
    
    # Collect all query params (leave them raw; service will filter/validate)
    incoming: Dict[str, Any] = dict(request.query_params)
    # Remove non-data params (keep minutes as it's a query parameter)
    for drop in ("q", "format", "demo"):
        incoming.pop(drop, None)

    # Server-provided values (you can add more later)
    server_context = {
        "client_id": cached_config.client_id
    }

    try:
        rows, fieldnames = run_saved_query(query_id=q,
                                           incoming_params=incoming,
                                           server_context=server_context,
                                           demo_mode=demo)
        
        # Calculate response time for logging
        response_time = time.time() - start_time
        
        # Log successful API usage with file logging (immediate)
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=f"/run?q={q}",
            ip=client_ip,
            response_code=200,
            response_time=response_time
        )
        
        # Schedule database logging as background task (after response)
        background_tasks.add_task(
            log_api_request_background,
            api_key=cached_config.api_key,
            client_id=cached_config.client_id,
            endpoint=f"/run?q={q}",
            client_ip=client_ip,
            response_code=200,
            response_time=response_time,
            query_params={"q": q, "format": format, "demo": demo, "minutes": minutes, **incoming},
            user_agent=request.headers.get("user-agent")
        )
        
    except CodedError as e:
        # Log the error for monitoring with appropriate status code
        response_time = time.time() - start_time
        status = 404 if getattr(e, "error_code", None) == ErrorCode.QUERY_NOT_FOUND else 400
        
        # Immediate file logging
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=f"/run?q={q}",
            ip=client_ip,
            response_code=status,
            response_time=response_time
        )
        
        # Schedule database logging as background task
        background_tasks.add_task(
            log_api_request_background,
            api_key=cached_config.api_key,
            client_id=cached_config.client_id,
            endpoint=f"/run?q={q}",
            client_ip=client_ip,
            response_code=status,
            response_time=response_time,
            query_params={"q": q, "format": format, "demo": demo, "minutes": minutes, **incoming},
            user_agent=request.headers.get("user-agent"),
            error_details=str(e.to_dict())
        )
        
        raise HTTPException(status_code=status, detail=e.to_dict())
    except ValueError as e:
        # Fallback for any remaining simple string errors
        response_time = time.time() - start_time
        
        # Immediate file logging
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=f"/run?q={q}",
            ip=client_ip,
            response_code=400,
            response_time=response_time
        )
        
        # Schedule database logging as background task
        background_tasks.add_task(
            log_api_request_background,
            api_key=cached_config.api_key,
            client_id=cached_config.client_id,
            endpoint=f"/run?q={q}",
            client_ip=client_ip,
            response_code=400,
            response_time=response_time,
            query_params={"q": q, "format": format, "demo": demo, "minutes": minutes, **incoming},
            user_agent=request.headers.get("user-agent"),
            error_details=str(e)
        )
        
        raise HTTPException(status_code=400, detail=str(e))

    if format == "json":
        return JSONResponse(rows)

    # CSV stream with dynamic columns
    def iter_csv():
        buf = io.StringIO()
        fn = fieldnames or (rows[0].keys() if rows else [])
        writer = csv.DictWriter(buf, fieldnames=fn, extrasaction="ignore")
        writer.writeheader(); yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for r in rows:
            writer.writerow(r); yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    return StreamingResponse(iter_csv(), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename=\"{q}.csv\"'})

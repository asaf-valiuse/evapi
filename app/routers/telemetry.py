# app/routers/run.py
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, Optional, List
import csv, io

from ..services.auth import resolve_client_from_key  # ?key=... -> client_id
from ..services.comprehensive_protection import comprehensive_api_protection
from ..services.query_service import run_saved_query
from ..services.error_codes import CodedError, ErrorCode
from ..services.security_monitor import security_monitor

router = APIRouter(tags=["queries"])

@router.get("/run")
async def run_saved(
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
    api_key = request.query_params.get("key", "")
    
    # Collect all query params (leave them raw; service will filter/validate)
    incoming: Dict[str, Any] = dict(request.query_params)
    # Remove non-data params (keep minutes as it's a query parameter)
    for drop in ("key", "q", "format", "demo"):
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
        
        # Log successful API usage with database tier info
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=f"/run?q={q}",
            ip=client_ip,
            response_code=200,
            response_time=response_time
        )
        
    except CodedError as e:
        # Log the error for monitoring with appropriate status code
        response_time = time.time() - start_time
        status = 404 if getattr(e, "error_code", None) == ErrorCode.QUERY_NOT_FOUND else 400
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=f"/run?q={q}",
            ip=client_ip,
            response_code=status,
            response_time=response_time
        )
        raise HTTPException(status_code=status, detail=e.to_dict())
    except ValueError as e:
        # Fallback for any remaining simple string errors
        response_time = time.time() - start_time
        security_monitor.log_api_usage(
            api_key=cached_config.api_key,
            endpoint=f"/run?q={q}",
            ip=client_ip,
            response_code=400,
            response_time=response_time
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

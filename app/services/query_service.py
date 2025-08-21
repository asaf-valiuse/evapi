# app/services/query_service.py
from typing import Dict, Any, List, Tuple
from sqlalchemy import text
from .db import get_engine
from .error_codes import ErrorCode, CodedError, raise_coded_error

def _cast_value(raw: Any, sql_type: str) -> Any:
    """
    Cast raw string (from URL or catalog default) to a Python value matching sql_type.
    Supported: INT, BIGINT, DECIMAL(p,s), FLOAT, BIT, NVARCHAR(n)/VARCHAR(n), DATETIME2, DATE, TIME.
    """
    if raw is None:
        return None
    t = sql_type.strip().upper()

    # Numeric
    if t.startswith("INT") or t.startswith("BIGINT") or t == "SMALLINT" or t == "TINYINT":
        return int(raw)
    if t.startswith("DECIMAL") or t.startswith("NUMERIC") or t == "FLOAT" or t == "REAL":
        return float(raw)

    # Boolean (BIT): accept 1/0/true/false
    if t == "BIT":
        s = str(raw).strip().lower()
        if s in ("1", "true", "yes", "y", "on"): return 1
        if s in ("0", "false", "no", "n", "off"): return 0
        # fallback: int cast
        return int(raw)

    # Date/Time
    if t in ("DATETIME2", "DATETIME", "SMALLDATETIME"):
        # Accept ISO-like strings; let driver handle precise formatting
        return str(raw)
    if t == "DATE" or t == "TIME":
        return str(raw)

    # Strings (NVARCHAR/VARCHAR/CHAR/etc.)
    return str(raw)

def _within_bounds(val: Any, sql_type: str, min_v: str | None, max_v: str | None) -> Any:
    """Clamp or validate numeric/date ranges if provided."""
    if val is None:
        return None
    t = sql_type.strip().upper()

    # Numeric range
    if t.startswith(("INT","BIGINT","SMALLINT","TINYINT","DECIMAL","NUMERIC","FLOAT","REAL")):
        try:
            if min_v is not None: val = max(float(min_v), float(val))
            if max_v is not None: val = min(float(max_v), float(val))
            # cast back to int if integer type
            if t.startswith(("INT","BIGINT","SMALLINT","TINYINT")):
                val = int(val)
        except Exception:
            pass
        return val

    # For dates/times we rely on SQL (optional: add parser/compare if needed)
    return val

def _enforce_allowed_values(val: Any, allowed_csv: str | None) -> Any:
    if val is None or not allowed_csv:
        return val
    allowed = [x.strip() for x in allowed_csv.split(",") if x.strip() != ""]
    if str(val) not in allowed:
        raise_coded_error(ErrorCode.QUERY_INVALID_VALUE)
    return val

def run_saved_query(
    query_id: str,
    incoming_params: Dict[str, Any],
    server_context: Dict[str, Any],
    demo_mode: bool = False
) -> Tuple[List[dict], List[str]]:
    """
    Agnostic runner:
    - Loads SQL + param metadata by `query_id`
    - Builds a params dict using:
      * server_context for 'server' params
      * incoming_params for 'client' params
      * both for 'either' (URL wins if present)
      * default_value when missing
    - Casts to sql_type, applies min/max and allowed_values
    - Executes with safe binding
    """
    eng = get_engine()

    # 1) Load SQL & param metadata (fresh query)
    try:
        with eng.begin() as conn:
            qrow = conn.execute(text("""
                SELECT id, sql_text, is_active, example_json
                FROM app.api_request_queries
                WHERE id = :query_id
            """), {"query_id": query_id}).mappings().first()

            if not qrow or not qrow["is_active"]:
                raise_coded_error(ErrorCode.QUERY_NOT_FOUND)

            params_meta = conn.execute(text("""
                SELECT param_name, sql_type, is_required, default_value, min_value, max_value, allowed_values, source
                FROM app.api_request_query_params
                WHERE query_id = :qid
            """), {"qid": qrow["id"]}).mappings().all()
            
            # Debug: print what parameters we got from the database
            print(f"DEBUG: Found {len(params_meta)} parameters for query {query_id}")
            for param in params_meta:
                print(f"  - {param['param_name']}: source={param['source']}, required={param['is_required']} (type: {type(param['is_required'])}), default={param['default_value']}")
    
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid object name" in error_msg or "object not found" in error_msg:
            raise_coded_error(ErrorCode.DB_SCHEMA_ERROR)
        elif "unknown or inactive query id" in error_msg:
            raise_coded_error(ErrorCode.QUERY_NOT_FOUND)
        else:
            raise_coded_error(ErrorCode.QUERY_SERVICE_UNAVAILABLE)

    allow = {r["param_name"]: dict(r) for r in params_meta}

    # Debug: print what we received as input
    print(f"DEBUG: Incoming params: {incoming_params}")
    print(f"DEBUG: Server context: {server_context}")
    print(f"DEBUG: Demo mode: {demo_mode}")

    # 2) Build the bound params dictionary generically
    bound: Dict[str, Any] = {}
    missing_params = []  # Collect all missing required parameters
    
    for name, meta in allow.items():
        src = (meta["source"] or "client").lower()
        raw_val = None

        print(f"DEBUG: Processing param '{name}' with source='{src}', required={meta['is_required']}, default={meta['default_value']}")

        if src == "server":
            # Only from server context
            if name in server_context:
                raw_val = server_context[name]
            elif meta["is_required"]:  # bit type returns True/False
                missing_params.append(f"'{name}' (server parameter)")
        elif src == "client":
            # Only from URL - but special case for client_id which should come from auth
            if name == "client_id" and name in server_context:
                # client_id should come from authenticated user, not URL
                raw_val = server_context[name]
            elif name in incoming_params:
                raw_val = incoming_params[name]
            elif meta["is_required"]:  # Check required BEFORE default value
                param_info = f"'{name}'"
                if meta.get("sql_type"):
                    param_info += f" (type: {meta['sql_type']})"
                missing_params.append(param_info)
            elif meta["default_value"] is not None:
                raw_val = meta["default_value"]
        else:  # 'either'
            if name in incoming_params:
                raw_val = incoming_params[name]
            elif name in server_context:
                raw_val = server_context[name]
            elif meta["is_required"]:  # Check required BEFORE default value
                param_info = f"'{name}'"
                if meta.get("sql_type"):
                    param_info += f" (type: {meta['sql_type']})"
                missing_params.append(param_info)
            elif meta["default_value"] is not None:
                raw_val = meta["default_value"]

        print(f"DEBUG: Param '{name}' raw_val before processing: {raw_val}")

        # Cast, bounds, allowed_values
        if raw_val is not None:
            val = _cast_value(raw_val, meta["sql_type"])
            val = _within_bounds(val, meta["sql_type"], meta["min_value"], meta["max_value"])
            val = _enforce_allowed_values(val, meta["allowed_values"])
        else:
            val = None

        print(f"DEBUG: Param '{name}' final value: {val}")
        bound[name] = val

    # Check if we have any missing required parameters
    if missing_params:
        raise_coded_error(ErrorCode.QUERY_REQUIRED_INFO_MISSING)

    print(f"DEBUG: Final bound parameters: {bound}")
    print(f"DEBUG: SQL query: {qrow['sql_text']}")

    # 3) Execute safely with bound params
    with eng.begin() as conn:
        try:
            rows = conn.execute(text(qrow["sql_text"]), bound).mappings().all()
        except Exception as e:
            print(f"DEBUG: SQL execution failed: {e}")
            print(f"DEBUG: Bound params: {bound}")
            raise_coded_error(ErrorCode.QUERY_PROCESSING_FAILED)

        # Convert result to list of dicts and handle datetime serialization
        result_rows = []
        for row in rows:
            row_dict = {}
            for key, value in row.items():
                # Convert datetime objects to ISO format strings for JSON serialization
                if hasattr(value, 'isoformat'):  # datetime, date, time objects
                    row_dict[key] = value.isoformat()
                else:
                    row_dict[key] = value
            result_rows.append(row_dict)

        # field order for CSV (optional)
        field_order = list(result_rows[0].keys()) if result_rows else []

    # If demo mode is enabled, return example_json from query metadata
    if demo_mode:
        print(f"DEBUG: Demo mode enabled - returning example_json from query metadata")
        
        # Get example_json from query metadata if available
        example_json = qrow.get('example_json')
        if example_json:
            try:
                # Parse the example JSON string into actual data
                import json
                demo_data = json.loads(example_json)
                # Ensure it's a list for consistency
                if isinstance(demo_data, dict):
                    demo_data = [demo_data]
                field_order = list(demo_data[0].keys()) if demo_data else []
                print(f"DEBUG: Successfully parsed example_json with {len(demo_data)} records")
                return demo_data, field_order
            except (json.JSONDecodeError, KeyError) as e:
                print(f"DEBUG: Could not parse example_json: {e}")
                raise_coded_error(ErrorCode.QUERY_PROCESSING_FAILED)
        else:
            print(f"DEBUG: No example_json found in query metadata")
            raise_coded_error(ErrorCode.QUERY_PROCESSING_FAILED)
    
    return result_rows, field_order

import json
import os
import urllib.parse
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    # Check if running in Azure (connection string takes precedence)
    azure_conn_string = os.getenv("api_db_conn")
    if azure_conn_string:
        # Azure uses direct connection string
        connection_url = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(azure_conn_string)}"
        _engine = create_engine(connection_url, echo=False, pool_pre_ping=True)
        return _engine
    
    # Check for individual Azure environment variables (alternative method)
    azure_server = os.getenv("AZURE_SQL_SERVER")
    if azure_server:
        # Azure SQL Database configuration with individual variables
        host = azure_server
        port = int(os.getenv("AZURE_SQL_PORT", "1433"))
        db = os.getenv("AZURE_SQL_DATABASE")
        user = os.getenv("AZURE_SQL_USERNAME")
        pwd = os.getenv("AZURE_SQL_PASSWORD")
        driver = "ODBC Driver 17 for SQL Server"
        encrypt = "yes"
        tsc = "no"
    else:
        # Local configuration from db_config.json
        cfg_path = Path(__file__).resolve().parent.parent.parent / "db_config.json"
        with cfg_path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)

        host = cfg.get("host")
        port = cfg.get("port", 1433)
        db = cfg.get("database")
        user = cfg.get("username")
        pwd = cfg.get("password")
        driver = cfg.get("driver", "ODBC Driver 17 for SQL Server")
        encrypt = cfg.get("encrypt", "yes")
        tsc = cfg.get("trust_server_certificate", "no")

    # Build ODBC connection string
    odbc_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={tsc};"
    )

    conn_str = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_str)}"
    _engine = create_engine(conn_str, pool_pre_ping=True, pool_recycle=1800)
    return _engine

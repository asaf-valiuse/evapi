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

    # Check if running in Azure (environment variables take precedence)
    azure_server = os.getenv("AZURE_SQL_SERVER")
    if azure_server:
        # Azure SQL Database configuration
        host = azure_server
        port = int(os.getenv("AZURE_SQL_PORT", "1433"))
        db = os.getenv("AZURE_SQL_DATABASE")
        user = os.getenv("AZURE_SQL_USERNAME")
        pwd = os.getenv("AZURE_SQL_PASSWORD")
        driver = "ODBC Driver 17 for SQL Server"
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
        
    encrypt = "yes" if azure_server else cfg.get("encrypt", "yes") if not azure_server else "yes"
    tsc = "no" if azure_server else cfg.get("trust_server_certificate", "no") if not azure_server else "no"

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

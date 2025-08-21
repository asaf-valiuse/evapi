# FastAPI Direct-Link Service (SQL Server)

This project exposes a **direct link** (URL) that returns account-specific data (JSON or CSV)
from SQL Server. Authentication is done via an API key (either in a header or as a query token).

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Update **db_config.json** with your SQL Server connection details.

3. (Optional) Create schema/tables:
   ```bash
   sqlcmd -S <server> -d <db> -U <user> -P <password> -i sql/schema.sql
   ```

4. Run the API:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Test with curl:
   ```bash
   curl -H "X-API-Key: val_live_demo_123" "http://localhost:8000/telemetry"
   curl "http://localhost:8000/telemetry?token=token_demo_123"
   ```

## Endpoints

- `GET /telemetry` — returns JSON telemetry for the resolved account.
  - Auth via header: `X-API-Key: <key>`
  - OR via query: `?token=<token>` (easier but less secure)

- `GET /telemetry.csv` — returns CSV for the same data.

## Notes

- Keys are looked up in `app.api_keys` (see `sql/schema.sql`).
- Example uses **pyodbc** + SQLAlchemy to reach SQL Server.
- Replace demo queries with your real tables/views.

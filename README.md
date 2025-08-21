# EnerVibe API

A FastAPI-based REST API service for accessing vehicle telemetry and sensor data.

## 🚀 Live API
**Base URL:** `https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net`

## 📖 Documentation
- **[Full API Documentation](API_DOCUMENTATION.md)** - Complete API reference
- **[Quick Reference](QUICK_REFERENCE.md)** - Essential usage examples

## 🔑 Features
- **Authentication** - API key-based access control
- **Multiple Formats** - JSON and CSV response formats
- **Demo Mode** - Test with sample data
- **Real-time Data** - Live vehicle telemetry access
- **Error Handling** - Structured error codes and messages
- **CORS Support** - Web browser compatibility

## ⚡ Quick Test
```bash
# Health check
curl "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/healthz"

# Get vehicle data
curl "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID"
```

## 🏗️ Architecture
- **FastAPI** - Modern Python web framework
- **Azure App Service** - Cloud hosting  
- **SQL Server** - Database backend
- **GitHub Actions** - CI/CD deployment

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

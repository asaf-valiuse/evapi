# EnerVibe API - Quick Reference

## Base URL
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net
```

## Available Queries

### 1. Vehicle Weight
- **ID:** `5EF690DC-092B-4176-A7B4-16408FAF0B9E`
- **Data:** Vehicle weight from last X minutes
- **Parameter:** `minutes` (1-500, default: 15)

### 2. Tire Telemetry  
- **ID:** `8394F36D-2C9C-4871-AB8A-5489175E32E4`
- **Data:** Tire pressure, temperature, load
- **Parameter:** `minutes` (1-500, default: 15)

### 3. Active Alerts
- **ID:** `47CE71C4-7406-4207-A0E9-ACBA0382CC18`
- **Data:** Vehicle alerts (flat tire, overload, etc.)
- **Parameters:** `hours` (1-2200, default: 168), `include_closed` (0/1, default: 0)

## Quick Examples

### Health Check
```
GET /healthz
Response: {"ok": true}
```

### Get Tire Data (JSON)
```
GET /run?key=YOUR_API_KEY&q=8394F36D-2C9C-4871-AB8A-5489175E32E4
```

### Get Weight Data (CSV, Last 60 Minutes)
```
GET /run?key=YOUR_API_KEY&q=5EF690DC-092B-4176-A7B4-16408FAF0B9E&format=csv&minutes=60
```

### Get Alerts (Last 48 Hours, Including Closed)
```
GET /run?key=YOUR_API_KEY&q=47CE71C4-7406-4207-A0E9-ACBA0382CC18&hours=48&include_closed=1
```

### Demo Mode
```
GET /run?key=YOUR_API_KEY&q=QUERY_ID&demo=true
```

## Parameters
- `key` (required) - Your API key
- `q` (required) - Query ID from table above
- `format` (optional) - "json" or "csv"
- `demo` (optional) - true/false
- `minutes` (optional) - For weight/tire queries
- `hours` (optional) - For alert queries  
- `include_closed` (optional) - 0 or 1 for alerts

## Test with cURL
```bash
curl "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4"
```

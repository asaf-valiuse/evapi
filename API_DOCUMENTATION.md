# EnerVibe API Documentation

## Base URL
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net
```

## Authentication
All API requests require a valid API key passed as a query parameter.

**Parameter:** `key`  
**Type:** String (GUID format)  
**Required:** Yes

## Endpoints

### 1. Health Check
**GET** `/healthz`

Returns the health status of the API service.

**Response:**
```json
{
  "ok": true
}
```

### 2. Execute Query
**GET** `/run`

Executes a saved query and returns the results in JSON or CSV format.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | String | Yes | API authentication key (GUID format) |
| `q` | String | Yes | Query identifier (can be numeric ID or GUID) |
| `format` | String | No | Response format: `json` (default) or `csv` |
| `demo` | Boolean | No | Return demo data instead of live data (default: false) |
| `[custom]` | Various | No | Query-specific parameters (varies by query) |

**Example Requests:**

**JSON Response (Default):**
```
GET /run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4
```

**CSV Response:**
```
GET /run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4&format=csv
```

**Demo Mode:**
```
GET /run?key=541EF73D-DD9C-4636-BA45-9866B5EE8D09&q=5&demo=true
```

**Sample JSON Response:**
```json
[
  {
    "vehicle_number": "84823302",
    "wheel_position": "21",
    "device_id": "8D310548",
    "message_timestamp": "21/08/2025 6:29:58",
    "pressure": 131,
    "temp": 50,
    "load": 0
  },
  {
    "vehicle_number": "84824302",
    "wheel_position": "11",
    "device_id": "B3CAA090",
    "message_timestamp": "21/08/2025 6:31:17",
    "pressure": 118,
    "temp": 45,
    "load": 1488
  }
]
```

**Sample CSV Response:**
```csv
vehicle_number,wheel_position,device_id,message_timestamp,pressure,temp,load
84823302,21,8D310548,21/08/2025 6:29:58,131,50,0
84824302,11,B3CAA090,21/08/2025 6:31:17,118,45,1488
```

## Error Responses

The API uses structured error codes for better error handling:

**Error Format:**
```json
{
  "detail": {
    "error": "Error description",
    "code": 1001,
    "ref": "ERROR_CODE_REFERENCE"
  }
}
```

**Common Error Codes:**

| Code | Reference | Description |
|------|-----------|-------------|
| 1001 | INVALID_API_KEY | API key is invalid or missing |
| 1002 | CLIENT_NOT_FOUND | No client found for the provided API key |
| 2001 | QUERY_NOT_FOUND | Query ID does not exist |
| 2002 | QUERY_SERVICE_UNAVAILABLE | Database service temporarily unavailable |
| 3001 | DATABASE_CONNECTION_FAILED | Unable to connect to database |
| 3002 | DATABASE_QUERY_FAILED | Database query execution failed |

## Response Codes

| HTTP Code | Description |
|-----------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 404 | Not Found |
| 500 | Internal Server Error |

## Rate Limiting
Currently no rate limiting is implemented, but it may be added in future versions.

## Data Types

### Vehicle Telemetry Data
Typical fields returned for vehicle telemetry queries:

| Field | Type | Description |
|-------|------|-------------|
| `vehicle_number` | String | Vehicle identification number |
| `wheel_position` | String | Position of the wheel/sensor |
| `device_id` | String | Sensor device identifier |
| `message_timestamp` | String | Timestamp of the measurement |
| `pressure` | Integer | Tire pressure reading |
| `temp` | Integer | Temperature reading |
| `load` | Integer | Load/weight measurement |

## Usage Examples

### PowerShell
```powershell
# JSON Response
Invoke-RestMethod -Uri "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID" -Method Get

# CSV Response  
Invoke-RestMethod -Uri "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID&format=csv" -Method Get
```

### cURL
```bash
# JSON Response
curl "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID"

# CSV Response
curl "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID&format=csv"
```

### JavaScript/Fetch
```javascript
// JSON Response
const response = await fetch('https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID');
const data = await response.json();

// CSV Response
const csvResponse = await fetch('https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=QUERY_ID&format=csv');
const csvData = await csvResponse.text();
```

### Python
```python
import requests

# JSON Response
response = requests.get('https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run', 
                       params={'key': 'YOUR_API_KEY', 'q': 'QUERY_ID'})
data = response.json()

# CSV Response
csv_response = requests.get('https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run', 
                           params={'key': 'YOUR_API_KEY', 'q': 'QUERY_ID', 'format': 'csv'})
csv_data = csv_response.text
```

## Notes
- All timestamps are in DD/MM/YYYY HH:MM:SS format
- The API supports CORS for web browser requests
- Demo mode provides sample data for testing without affecting live data
- Query IDs can be either numeric or GUID format depending on the specific query
- Custom parameters may be required for specific queries - consult your query documentation

## Support
For API key requests or technical support, contact your system administrator.

---
*Last Updated: August 21, 2025*
*API Version: 1.0.0*

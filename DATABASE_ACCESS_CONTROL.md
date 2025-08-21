# Database-Driven API Access Control

## Overview
Your API now uses the `client_api_access` table for dynamic access control, replacing hardcoded rate limits with database-driven configuration.

## Database Table Structure

The `client_api_access` table should have these columns:

```sql
-- Example table structure (adjust as needed)
CREATE TABLE client_api_access (
    id INT IDENTITY(1,1) PRIMARY KEY,
    client_id INT NOT NULL,
    api_key NVARCHAR(255) NOT NULL,
    access_tier NVARCHAR(50) NOT NULL DEFAULT 'basic',
    
    -- Rate limiting configuration
    requests_per_minute INT NOT NULL DEFAULT 1,
    requests_per_hour INT NOT NULL DEFAULT 60,
    requests_per_day INT NOT NULL DEFAULT 1440,
    
    -- Account status
    is_active BIT NOT NULL DEFAULT 1,
    is_suspended BIT NOT NULL DEFAULT 0,
    is_auto_blocked BIT NOT NULL DEFAULT 0,
    override_all_limits BIT NOT NULL DEFAULT 0,
    
    -- Usage tracking
    total_requests_lifetime BIGINT NOT NULL DEFAULT 0,
    requests_today INT NOT NULL DEFAULT 0,
    last_request_at DATETIME2 NULL,
    
    -- Timestamps
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    -- Indexes
    UNIQUE(api_key),
    INDEX IX_client_api_access_client_id (client_id),
    INDEX IX_client_api_access_api_key (api_key)
);
```

## Sample Data

Insert test records for different access tiers:

```sql
-- Basic tier (1 req/minute for your use case)
INSERT INTO client_api_access 
(client_id, api_key, access_tier, requests_per_minute, requests_per_hour, requests_per_day)
VALUES 
(1, 'your-test-api-key-here', 'basic', 1, 60, 1440);

-- Premium tier (higher limits)
INSERT INTO client_api_access 
(client_id, api_key, access_tier, requests_per_minute, requests_per_hour, requests_per_day)
VALUES 
(2, 'premium-api-key-example', 'premium', 10, 600, 14400);

-- Admin override (unlimited)
INSERT INTO client_api_access 
(client_id, api_key, access_tier, requests_per_minute, requests_per_hour, requests_per_day, override_all_limits)
VALUES 
(99, 'admin-unlimited-key', 'admin', 1000, 60000, 1440000, 1);
```

## Access Tiers

The system supports flexible access tiers:

### Basic Tier
- **Default**: 1 request/minute, 60/hour, 1440/day
- **Use Case**: Your client's 1 call per minute requirement
- **Best For**: Standard monitoring applications

### Premium Tier  
- **Default**: 10 requests/minute, 600/hour, 14400/day
- **Use Case**: Higher frequency monitoring
- **Best For**: Real-time dashboards

### Admin/Unlimited
- **Feature**: `override_all_limits = 1`
- **Use Case**: Internal tools, testing, emergency access
- **Best For**: Development and admin operations

## Features

### Dynamic Rate Limiting
- Rate limits are read from database in real-time
- No server restart needed for limit changes
- Per-API-key tracking (not per-IP)

### Account Management
```sql
-- Suspend an account
UPDATE client_api_access SET is_suspended = 1 WHERE api_key = 'problem-key';

-- Block automatically (system sets this)
UPDATE client_api_access SET is_auto_blocked = 1 WHERE api_key = 'abusive-key';

-- Grant temporary unlimited access
UPDATE client_api_access SET override_all_limits = 1 WHERE api_key = 'urgent-key';
```

### Usage Tracking
The system automatically updates:
- `total_requests_lifetime`: Running total of all requests
- `requests_today`: Daily request count (resets at midnight)
- `last_request_at`: Timestamp of most recent request

### Auto-Blocking
- Suspicious activity triggers `is_auto_blocked = 1`
- Configurable thresholds in security monitor
- Manual override available via database

## API Response Changes

### Rate Limit Headers
The API now returns enhanced rate limit information:
```json
{
  "error": "Rate limit exceeded", 
  "message": "Rate limit exceeded: 1 requests per minute",
  "tier": "basic",
  "limits": {
    "requests_per_minute": 1,
    "requests_per_hour": 60, 
    "requests_per_day": 1440
  }
}
```

### Usage Statistics Endpoint
Access current usage via the system:
```python
# In your code, you can get usage stats:
usage_stats = db_quota_manager.get_usage_stats(client_access)
```

Returns:
```json
{
  "client_id": 1,
  "access_tier": "basic",
  "current_usage": {
    "minute": 0,
    "hour": 5,
    "day": 127
  },
  "limits": {
    "requests_per_minute": 1,
    "requests_per_hour": 60,
    "requests_per_day": 1440
  },
  "database_stats": {
    "total_requests_lifetime": 15847,
    "requests_today": 127,
    "last_request_at": "2024-01-15T14:30:22"
  },
  "account_status": {
    "is_active": true,
    "is_suspended": false,
    "is_auto_blocked": false,
    "override_limits": false
  }
}
```

## Migration from Old System

Your API has been updated to use the new database system:

1. **Old quota_manager.py** → **New db_quota_manager.py**
2. **Hardcoded limits** → **Database-driven limits**
3. **IP-based tracking** → **API-key-based tracking**
4. **Static tiers** → **Flexible database tiers**

## Configuration

### Database Connection
The system uses your existing database configuration in `db_config.json`.

### Error Handling
- Database failures fall back to in-memory tracking
- Connection errors don't block API requests
- Graceful degradation when database is unavailable

## Monitoring

### Security Events
All rate limiting events are logged:
- Quota exceeded attempts
- Account suspensions
- Auto-blocking triggers
- Usage pattern analysis

### Performance
- Database queries are optimized with indexes
- In-memory caching for active rate limit windows
- Asynchronous usage statistics updates

## Administration

### Common Management Tasks

```sql
-- View all active API keys and usage
SELECT 
    api_key,
    access_tier,
    requests_per_minute,
    total_requests_lifetime,
    requests_today,
    last_request_at,
    is_active,
    is_suspended,
    is_auto_blocked
FROM client_api_access 
WHERE is_active = 1
ORDER BY last_request_at DESC;

-- Find high-usage accounts
SELECT 
    api_key,
    access_tier,
    requests_today,
    total_requests_lifetime
FROM client_api_access 
WHERE requests_today > 1000
ORDER BY requests_today DESC;

-- Reset daily usage (if needed manually)
UPDATE client_api_access SET requests_today = 0;
```

## Testing

Your API key protection is now database-driven. Test with:

```bash
# Basic request (should work within limits)
curl "http://localhost:8000/run?key=your-test-api-key&q=test"

# Rate limit test (make multiple requests quickly)
for i in {1..5}; do
    curl "http://localhost:8000/run?key=your-test-api-key&q=test"
    echo ""
done
```

The system will now reference your `client_api_access` table for all rate limiting decisions!

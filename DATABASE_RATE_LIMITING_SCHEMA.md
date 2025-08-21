# Database Schema for Dynamic API Rate Limiting

## 🗄️ **Recommended Client Table Fields**

### **Core Rate Limiting Fields:**

```sql
-- Add these columns to your existing client table:

-- Basic Rate Limits
ALTER TABLE clients ADD COLUMN requests_per_minute INT DEFAULT 2;
ALTER TABLE clients ADD COLUMN requests_per_hour INT DEFAULT 10;  
ALTER TABLE clients ADD COLUMN requests_per_day INT DEFAULT 100;

-- Tier Management
ALTER TABLE clients ADD COLUMN tier VARCHAR(20) DEFAULT 'free'; -- 'free', 'basic', 'premium', 'enterprise'
ALTER TABLE clients ADD COLUMN tier_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Account Status
ALTER TABLE clients ADD COLUMN is_active BIT DEFAULT 1; -- 0 = disabled, 1 = active
ALTER TABLE clients ADD COLUMN is_suspended BIT DEFAULT 0; -- 0 = normal, 1 = suspended
ALTER TABLE clients ADD COLUMN suspension_reason VARCHAR(255) NULL;
ALTER TABLE clients ADD COLUMN suspended_until DATETIME NULL; -- NULL = permanent, datetime = temporary

-- Usage Tracking & Analytics
ALTER TABLE clients ADD COLUMN total_requests_made BIGINT DEFAULT 0;
ALTER TABLE clients ADD COLUMN last_request_at DATETIME NULL;
ALTER TABLE clients ADD COLUMN first_request_at DATETIME NULL;

-- Advanced Limits
ALTER TABLE clients ADD COLUMN max_concurrent_requests INT DEFAULT 5;
ALTER TABLE clients ADD COLUMN allowed_endpoints TEXT NULL; -- JSON array of allowed endpoints
ALTER TABLE clients ADD COLUMN blocked_endpoints TEXT NULL; -- JSON array of blocked endpoints

-- Burst & Override Settings
ALTER TABLE clients ADD COLUMN burst_requests_allowed INT DEFAULT 0; -- Extra requests for short bursts
ALTER TABLE clients ADD COLUMN burst_window_minutes INT DEFAULT 1; -- Time window for burst
ALTER TABLE clients ADD COLUMN override_limits BIT DEFAULT 0; -- Admin override (no limits)

-- Security & Monitoring
ALTER TABLE clients ADD COLUMN failed_auth_attempts INT DEFAULT 0;
ALTER TABLE clients ADD COLUMN last_failed_auth_at DATETIME NULL;
ALTER TABLE clients ADD COLUMN auto_block_threshold INT DEFAULT 10; -- Failed attempts before auto-block
ALTER TABLE clients ADD COLUMN is_auto_blocked BIT DEFAULT 0;
ALTER TABLE clients ADD COLUMN auto_blocked_at DATETIME NULL;
ALTER TABLE clients ADD COLUMN auto_block_reason VARCHAR(255) NULL;

-- Metadata
ALTER TABLE clients ADD COLUMN rate_limits_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE clients ADD COLUMN notes TEXT NULL; -- Admin notes about the client
```

### **Example Client Records:**

```sql
-- Free Tier Client
INSERT INTO clients (client_id, api_key, tier, requests_per_minute, requests_per_hour, requests_per_day, is_active)
VALUES (1, 'FREE-KEY-12345', 'free', 2, 10, 100, 1);

-- Basic Tier Client  
INSERT INTO clients (client_id, api_key, tier, requests_per_minute, requests_per_hour, requests_per_day, is_active)
VALUES (2, 'BASIC-KEY-67890', 'basic', 3, 30, 200, 1);

-- Premium Tier Client
INSERT INTO clients (client_id, api_key, tier, requests_per_minute, requests_per_hour, requests_per_day, is_active, burst_requests_allowed)
VALUES (3, 'PREMIUM-KEY-11111', 'premium', 5, 100, 500, 1, 10);

-- Enterprise Client (No limits)
INSERT INTO clients (client_id, api_key, tier, override_limits, is_active)
VALUES (4, 'ENTERPRISE-KEY-22222', 'enterprise', 1, 1);

-- Suspended Client
INSERT INTO clients (client_id, api_key, tier, is_suspended, suspension_reason, suspended_until)
VALUES (5, 'SUSPENDED-KEY-33333', 'basic', 1, 'Payment overdue', '2025-08-25 00:00:00');
```

## 🔧 **Updated Service Code**

Here's how to modify your authentication service to use database-driven limits:

```python
# app/services/auth.py - Enhanced with DB rate limits

class ClientRateLimits:
    def __init__(self, client_data: dict):
        self.client_id = client_data.get('client_id')
        self.api_key = client_data.get('api_key')
        self.tier = client_data.get('tier', 'free')
        
        # Rate limits from database
        self.requests_per_minute = client_data.get('requests_per_minute', 2)
        self.requests_per_hour = client_data.get('requests_per_hour', 10)
        self.requests_per_day = client_data.get('requests_per_day', 100)
        
        # Account status
        self.is_active = bool(client_data.get('is_active', 1))
        self.is_suspended = bool(client_data.get('is_suspended', 0))
        self.suspension_reason = client_data.get('suspension_reason')
        self.suspended_until = client_data.get('suspended_until')
        
        # Advanced settings
        self.max_concurrent_requests = client_data.get('max_concurrent_requests', 5)
        self.burst_requests_allowed = client_data.get('burst_requests_allowed', 0)
        self.burst_window_minutes = client_data.get('burst_window_minutes', 1)
        self.override_limits = bool(client_data.get('override_limits', 0))
        
        # Security settings
        self.failed_auth_attempts = client_data.get('failed_auth_attempts', 0)
        self.auto_block_threshold = client_data.get('auto_block_threshold', 10)
        self.is_auto_blocked = bool(client_data.get('is_auto_blocked', 0))
        
        # Endpoint restrictions
        self.allowed_endpoints = self._parse_json_field(client_data.get('allowed_endpoints'))
        self.blocked_endpoints = self._parse_json_field(client_data.get('blocked_endpoints'))
    
    def _parse_json_field(self, field_value):
        if not field_value:
            return None
        try:
            return json.loads(field_value) if isinstance(field_value, str) else field_value
        except:
            return None
    
    def is_account_valid(self) -> tuple[bool, str]:
        """Check if account can make requests"""
        if not self.is_active:
            return False, "Account is deactivated"
        
        if self.is_auto_blocked:
            return False, "Account is auto-blocked due to suspicious activity"
        
        if self.is_suspended:
            if self.suspended_until:
                if datetime.now() < self.suspended_until:
                    return False, f"Account suspended until {self.suspended_until}"
                else:
                    # Suspension expired, could auto-unsuspend here
                    return True, ""
            else:
                return False, f"Account suspended: {self.suspension_reason}"
        
        return True, ""
    
    def can_access_endpoint(self, endpoint: str) -> bool:
        """Check if client can access specific endpoint"""
        if self.blocked_endpoints and endpoint in self.blocked_endpoints:
            return False
        
        if self.allowed_endpoints and endpoint not in self.allowed_endpoints:
            return False
        
        return True

async def get_client_limits_from_db(api_key: str) -> ClientRateLimits:
    """Get client rate limits from database"""
    engine = get_engine()
    
    query = """
        SELECT client_id, api_key, tier, 
               requests_per_minute, requests_per_hour, requests_per_day,
               is_active, is_suspended, suspension_reason, suspended_until,
               max_concurrent_requests, burst_requests_allowed, burst_window_minutes,
               override_limits, failed_auth_attempts, auto_block_threshold,
               is_auto_blocked, allowed_endpoints, blocked_endpoints
        FROM clients 
        WHERE api_key = ?
    """
    
    with engine.connect() as conn:
        result = conn.execute(query, (api_key,)).fetchone()
        
        if not result:
            raise ValueError("Invalid API key")
        
        # Convert row to dict
        client_data = dict(result._mapping)
        return ClientRateLimits(client_data)

# Usage in your quota manager:
async def resolve_client_with_db_limits(request: Request) -> ClientRateLimits:
    """Enhanced auth with database-driven limits"""
    api_key = request.query_params.get("key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        client_limits = await get_client_limits_from_db(api_key)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check account status
    is_valid, reason = client_limits.is_account_valid()
    if not is_valid:
        raise HTTPException(status_code=403, detail=reason)
    
    # Check endpoint access
    endpoint = request.url.path
    if not client_limits.can_access_endpoint(endpoint):
        raise HTTPException(status_code=403, detail=f"Access denied to endpoint: {endpoint}")
    
    return client_limits
```

## 📊 **Database Management Queries**

### **Real-time Limit Updates:**
```sql
-- Upgrade client to premium
UPDATE clients 
SET tier = 'premium', 
    requests_per_minute = 5,
    requests_per_hour = 100, 
    requests_per_day = 500,
    burst_requests_allowed = 10,
    rate_limits_updated_at = CURRENT_TIMESTAMP
WHERE client_id = 123;

-- Temporarily suspend client
UPDATE clients 
SET is_suspended = 1,
    suspension_reason = 'Payment overdue',
    suspended_until = '2025-08-25 00:00:00'
WHERE client_id = 456;

-- Block specific endpoints for client
UPDATE clients 
SET blocked_endpoints = '["POST /admin", "DELETE /data"]'
WHERE client_id = 789;

-- Reset failed authentication attempts
UPDATE clients 
SET failed_auth_attempts = 0,
    is_auto_blocked = 0,
    auto_blocked_at = NULL
WHERE client_id = 101;
```

### **Monitoring Queries:**
```sql
-- High usage clients
SELECT client_id, api_key, tier, total_requests_made, last_request_at
FROM clients 
WHERE total_requests_made > 1000
ORDER BY total_requests_made DESC;

-- Suspended/blocked clients
SELECT client_id, api_key, suspension_reason, suspended_until, auto_block_reason
FROM clients 
WHERE is_suspended = 1 OR is_auto_blocked = 1;

-- Usage by tier
SELECT tier, COUNT(*) as client_count, AVG(total_requests_made) as avg_requests
FROM clients 
GROUP BY tier;
```

## 🎯 **Benefits of Database-Driven Limits**

✅ **Real-time Updates** - Change limits without server restart
✅ **Granular Control** - Different limits per client
✅ **Account Management** - Suspend/activate accounts instantly
✅ **Endpoint Control** - Allow/block specific endpoints per client
✅ **Audit Trail** - Track when limits were changed
✅ **Burst Capacity** - Allow temporary spikes for premium clients
✅ **Auto-recovery** - Temporary suspensions that auto-expire

This approach gives you enterprise-level API management capabilities! 🚀

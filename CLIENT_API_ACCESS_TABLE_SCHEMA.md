# Separate API Access Control Table Schema

## 🎯 **Why a Separate Table is Better**

✅ **Better Normalization** - Client info separate from API control
✅ **Easier Maintenance** - Change API settings without touching client data
✅ **Version Control** - Track changes to API limits over time
✅ **Multiple Configurations** - Different API access profiles
✅ **Cleaner Queries** - Focused on API management only

---

## 📋 **Recommended Table Structure**

### **Main Table: `client_api_access`**

```sql
CREATE TABLE client_api_access (
    -- Primary Key
    access_id INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Foreign Key to Clients
    client_id INT NOT NULL,
    api_key NVARCHAR(255) NOT NULL UNIQUE, -- Could be FK or direct field
    
    -- Rate Limiting Configuration
    requests_per_minute INT DEFAULT 2,
    requests_per_hour INT DEFAULT 10,
    requests_per_day INT DEFAULT 100,
    requests_per_month INT DEFAULT NULL, -- Optional monthly limit
    
    -- Tier Management
    access_tier NVARCHAR(20) DEFAULT 'free', -- 'free', 'basic', 'premium', 'enterprise', 'custom'
    tier_effective_from DATETIME DEFAULT GETDATE(),
    tier_expires_at DATETIME NULL, -- NULL = permanent, date = temporary upgrade
    
    -- Account Status
    is_active BIT DEFAULT 1,
    is_suspended BIT DEFAULT 0,
    suspension_reason NVARCHAR(500) NULL,
    suspended_from DATETIME NULL,
    suspended_until DATETIME NULL, -- NULL = permanent, date = temporary
    
    -- Advanced Rate Limiting
    burst_requests_allowed INT DEFAULT 0, -- Extra requests for short bursts
    burst_window_minutes INT DEFAULT 1,
    max_concurrent_requests INT DEFAULT 5,
    request_timeout_seconds INT DEFAULT 30,
    
    -- Endpoint Access Control
    allowed_endpoints NVARCHAR(MAX) NULL, -- JSON array: ["GET /run", "GET /usage"]
    blocked_endpoints NVARCHAR(MAX) NULL, -- JSON array: ["POST /admin"]
    allowed_query_types NVARCHAR(MAX) NULL, -- JSON array: query IDs allowed
    blocked_query_types NVARCHAR(MAX) NULL, -- JSON array: query IDs blocked
    
    -- Security & Monitoring
    failed_auth_attempts INT DEFAULT 0,
    last_failed_auth_at DATETIME NULL,
    auto_block_threshold INT DEFAULT 10,
    is_auto_blocked BIT DEFAULT 0,
    auto_blocked_at DATETIME NULL,
    auto_block_reason NVARCHAR(500) NULL,
    
    -- Usage Statistics (Real-time counters)
    total_requests_lifetime BIGINT DEFAULT 0,
    requests_today INT DEFAULT 0,
    requests_this_hour INT DEFAULT 0,
    requests_this_minute INT DEFAULT 0,
    last_request_at DATETIME NULL,
    first_request_at DATETIME NULL,
    
    -- Admin Features
    override_all_limits BIT DEFAULT 0, -- Admin bypass
    internal_notes NVARCHAR(MAX) NULL, -- Admin notes
    priority_level INT DEFAULT 0, -- 0=normal, higher=priority processing
    
    -- Audit Trail
    created_at DATETIME DEFAULT GETDATE(),
    created_by NVARCHAR(100) NULL,
    updated_at DATETIME DEFAULT GETDATE(),
    updated_by NVARCHAR(100) NULL,
    
    -- Foreign Key Constraint
    FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
);

-- Indexes for Performance
CREATE INDEX IX_client_api_access_api_key ON client_api_access(api_key);
CREATE INDEX IX_client_api_access_client_id ON client_api_access(client_id);
CREATE INDEX IX_client_api_access_active ON client_api_access(is_active, is_suspended);
CREATE INDEX IX_client_api_access_tier ON client_api_access(access_tier);
```

### **Optional: API Access History Table**

```sql
CREATE TABLE client_api_access_history (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    access_id INT NOT NULL,
    client_id INT NOT NULL,
    api_key NVARCHAR(255) NOT NULL,
    
    -- What Changed
    change_type NVARCHAR(50) NOT NULL, -- 'TIER_UPGRADE', 'LIMIT_CHANGE', 'SUSPENSION', etc.
    old_values NVARCHAR(MAX) NULL, -- JSON of old settings
    new_values NVARCHAR(MAX) NULL, -- JSON of new settings
    change_reason NVARCHAR(500) NULL,
    
    -- When & Who
    changed_at DATETIME DEFAULT GETDATE(),
    changed_by NVARCHAR(100) NULL,
    
    FOREIGN KEY (access_id) REFERENCES client_api_access(access_id) ON DELETE CASCADE
);
```

### **Optional: Predefined Access Tiers Table**

```sql
CREATE TABLE api_access_tiers (
    tier_id INT IDENTITY(1,1) PRIMARY KEY,
    tier_name NVARCHAR(20) UNIQUE NOT NULL,
    display_name NVARCHAR(50) NOT NULL,
    
    -- Default Limits for this Tier
    default_requests_per_minute INT NOT NULL,
    default_requests_per_hour INT NOT NULL,
    default_requests_per_day INT NOT NULL,
    default_burst_requests INT DEFAULT 0,
    default_concurrent_requests INT DEFAULT 5,
    
    -- Features
    can_access_premium_queries BIT DEFAULT 0,
    can_export_data BIT DEFAULT 1,
    can_use_demo_mode BIT DEFAULT 1,
    
    -- Pricing (Optional)
    monthly_price DECIMAL(10,2) NULL,
    annual_price DECIMAL(10,2) NULL,
    
    -- Status
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE()
);

-- Insert Default Tiers
INSERT INTO api_access_tiers (tier_name, display_name, default_requests_per_minute, default_requests_per_hour, default_requests_per_day, monthly_price) VALUES
('free', 'Free Tier', 1, 10, 50, 0.00),
('basic', 'Basic Plan', 3, 30, 200, 19.99),
('premium', 'Premium Plan', 10, 100, 1000, 49.99),
('enterprise', 'Enterprise Plan', 50, 500, 5000, 199.99);
```

---

## 🔧 **Usage Examples**

### **Create API Access for New Client:**
```sql
-- When client registers, create their API access record
INSERT INTO client_api_access (client_id, api_key, access_tier, created_by)
VALUES (123, 'NEW-CLIENT-KEY-12345', 'free', 'system');
```

### **Upgrade Client to Premium:**
```sql
-- Upgrade with history tracking
INSERT INTO client_api_access_history (access_id, client_id, api_key, change_type, old_values, new_values, change_reason, changed_by)
SELECT access_id, client_id, api_key, 'TIER_UPGRADE', 
       JSON_OBJECT('tier', access_tier, 'limits', JSON_OBJECT('minute', requests_per_minute, 'hour', requests_per_hour, 'day', requests_per_day)),
       JSON_OBJECT('tier', 'premium', 'limits', JSON_OBJECT('minute', 10, 'hour', 100, 'day', 1000)),
       'Customer upgraded to premium plan', 'admin_user'
FROM client_api_access WHERE client_id = 123;

-- Apply the upgrade
UPDATE client_api_access 
SET access_tier = 'premium',
    requests_per_minute = 10,
    requests_per_hour = 100,
    requests_per_day = 1000,
    burst_requests_allowed = 20,
    tier_effective_from = GETDATE(),
    updated_at = GETDATE(),
    updated_by = 'admin_user'
WHERE client_id = 123;
```

### **Temporary Suspension:**
```sql
UPDATE client_api_access 
SET is_suspended = 1,
    suspension_reason = 'Payment overdue - invoice #12345',
    suspended_from = GETDATE(),
    suspended_until = DATEADD(DAY, 7, GETDATE()), -- 7 days from now
    updated_by = 'billing_system'
WHERE client_id = 456;
```

### **Block Specific Queries:**
```sql
UPDATE client_api_access 
SET blocked_query_types = '["admin-queries", "bulk-export"]',
    internal_notes = 'Client requested to block admin access',
    updated_by = 'support_agent'
WHERE client_id = 789;
```

---

## 🔍 **Query Examples for API Management**

### **Get Client Access Details:**
```sql
SELECT 
    caa.*,
    c.company_name,
    aat.display_name as tier_display_name,
    aat.monthly_price
FROM client_api_access caa
JOIN clients c ON caa.client_id = c.client_id
LEFT JOIN api_access_tiers aat ON caa.access_tier = aat.tier_name
WHERE caa.api_key = 'CLIENT-KEY-12345';
```

### **Find High Usage Clients:**
```sql
SELECT 
    caa.client_id,
    caa.api_key,
    caa.access_tier,
    caa.total_requests_lifetime,
    caa.requests_today,
    c.company_name
FROM client_api_access caa
JOIN clients c ON caa.client_id = c.client_id
WHERE caa.requests_today > (caa.requests_per_day * 0.8) -- 80% of daily limit
ORDER BY caa.requests_today DESC;
```

### **Suspended/Blocked Clients:**
```sql
SELECT 
    caa.client_id,
    caa.api_key,
    c.company_name,
    CASE 
        WHEN caa.is_suspended = 1 THEN 'Suspended: ' + caa.suspension_reason
        WHEN caa.is_auto_blocked = 1 THEN 'Auto-blocked: ' + caa.auto_block_reason
        ELSE 'Active'
    END as status,
    caa.suspended_until,
    caa.auto_blocked_at
FROM client_api_access caa
JOIN clients c ON caa.client_id = c.client_id
WHERE caa.is_suspended = 1 OR caa.is_auto_blocked = 1;
```

---

## 🎯 **Benefits of Separate Table**

✅ **Clean Separation** - Client data vs API access control
✅ **Flexible Limits** - Each client can have completely custom limits
✅ **History Tracking** - Full audit trail of changes
✅ **Tier Management** - Easy tier upgrades/downgrades
✅ **Security Features** - Comprehensive access control
✅ **Performance** - Optimized indexes for API lookups
✅ **Scalability** - Can handle millions of API clients
✅ **Admin Control** - Rich management interface possibilities

This approach gives you enterprise-grade API access management! 🚀

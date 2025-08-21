-- Security Event Database Schema
-- Tables for tracking rate limits, blocks, and brutal attacks

-- 1. Security Events Log (Main table for all security events)
CREATE TABLE app.security_events (
    event_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    event_type NVARCHAR(50) NOT NULL, -- 'RATE_LIMIT_EXCEEDED', 'BRUTAL_ATTACK', 'IP_BLOCKED', 'API_KEY_BLOCKED'
    event_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    -- Source identification
    source_ip NVARCHAR(45) NULL, -- IPv4/IPv6 support
    api_key NVARCHAR(255) NULL,
    client_id INT NULL,
    user_agent NVARCHAR(500) NULL,
    
    -- Event details
    event_severity NVARCHAR(20) NOT NULL DEFAULT 'MEDIUM', -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    event_description NVARCHAR(1000) NOT NULL,
    event_data NVARCHAR(MAX) NULL, -- JSON data for additional context
    
    -- Actions taken
    action_taken NVARCHAR(200) NULL, -- 'IP_BLOCKED', 'REQUEST_DENIED', 'KEY_SUSPENDED'
    auto_resolved BIT NOT NULL DEFAULT 0,
    resolved_at DATETIME2 NULL,
    
    -- Metadata
    endpoint NVARCHAR(200) NULL,
    request_method NVARCHAR(10) NULL,
    response_code INT NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    -- Indexes
    INDEX IX_security_events_timestamp (event_timestamp),
    INDEX IX_security_events_source_ip (source_ip),
    INDEX IX_security_events_api_key (api_key),
    INDEX IX_security_events_type (event_type),
    INDEX IX_security_events_severity (event_severity)
);

-- 2. Rate Limit Violations (Specific table for rate limit tracking)
CREATE TABLE app.rate_limit_violations (
    violation_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    api_key NVARCHAR(255) NOT NULL,
    client_id INT NOT NULL,
    source_ip NVARCHAR(45) NOT NULL,
    
    -- Violation details
    violation_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
    limit_type NVARCHAR(20) NOT NULL, -- 'MINUTE', 'HOUR', 'DAY'
    limit_value INT NOT NULL, -- The limit that was exceeded
    actual_requests INT NOT NULL, -- How many requests were made
    excess_requests INT NOT NULL, -- How many over the limit
    
    -- Rate limit configuration at time of violation
    access_tier NVARCHAR(50) NOT NULL,
    requests_per_minute INT NOT NULL,
    requests_per_hour INT NOT NULL,
    requests_per_day INT NOT NULL,
    
    -- Context
    endpoint NVARCHAR(200) NOT NULL,
    user_agent NVARCHAR(500) NULL,
    
    -- Foreign key to main security events
    security_event_id BIGINT NULL,
    
    FOREIGN KEY (security_event_id) REFERENCES app.security_events(event_id),
    INDEX IX_rate_limit_violations_api_key (api_key),
    INDEX IX_rate_limit_violations_timestamp (violation_timestamp),
    INDEX IX_rate_limit_violations_client_id (client_id)
);

-- 3. IP Blocking Events (Track IP blocks and unblocks)
CREATE TABLE app.ip_blocking_events (
    block_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    ip_address NVARCHAR(45) NOT NULL,
    
    -- Block details
    blocked_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    block_reason NVARCHAR(500) NOT NULL,
    block_type NVARCHAR(50) NOT NULL, -- 'AUTO_BRUTAL_ATTACK', 'MANUAL_ADMIN', 'SUSPICIOUS_ACTIVITY'
    
    -- Attack pattern info
    requests_in_period INT NULL, -- How many requests triggered the block
    time_period_minutes INT NULL, -- Time window for the requests
    
    -- Unblock info
    is_active BIT NOT NULL DEFAULT 1,
    unblocked_at DATETIME2 NULL,
    unblock_reason NVARCHAR(200) NULL,
    unblocked_by NVARCHAR(100) NULL, -- 'AUTO_EXPIRE', 'ADMIN_MANUAL', 'SYSTEM_RESET'
    
    -- Statistics before block
    total_requests_lifetime BIGINT NULL,
    first_seen_timestamp DATETIME2 NULL,
    
    -- Foreign key to main security events
    security_event_id BIGINT NULL,
    
    FOREIGN KEY (security_event_id) REFERENCES app.security_events(event_id),
    INDEX IX_ip_blocking_events_ip (ip_address),
    INDEX IX_ip_blocking_events_blocked_at (blocked_at),
    INDEX IX_ip_blocking_events_active (is_active)
);

-- 4. API Key Security Events (Track API key related security events)
CREATE TABLE app.api_key_security_events (
    event_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    api_key NVARCHAR(255) NOT NULL,
    client_id INT NOT NULL,
    
    -- Event details  
    event_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
    event_type NVARCHAR(50) NOT NULL, -- 'SUSPENDED', 'AUTO_BLOCKED', 'FAILED_AUTH', 'QUOTA_EXCEEDED'
    event_description NVARCHAR(500) NOT NULL,
    
    -- Context
    source_ip NVARCHAR(45) NULL,
    endpoint NVARCHAR(200) NULL,
    user_agent NVARCHAR(500) NULL,
    
    -- Previous state
    previous_status NVARCHAR(50) NULL,
    new_status NVARCHAR(50) NULL,
    
    -- Action details
    action_automatic BIT NOT NULL DEFAULT 1,
    action_by NVARCHAR(100) NULL, -- Admin user who took manual action
    
    INDEX IX_api_key_security_events_key (api_key),
    INDEX IX_api_key_security_events_timestamp (event_timestamp),
    INDEX IX_api_key_security_events_type (event_type),
    INDEX IX_api_key_security_events_client (client_id)
);

-- 5. Security Statistics Summary (For dashboard/reporting)
CREATE TABLE app.security_statistics_daily (
    stat_date DATE NOT NULL PRIMARY KEY,
    
    -- Request statistics
    total_requests BIGINT NOT NULL DEFAULT 0,
    blocked_requests BIGINT NOT NULL DEFAULT 0,
    rate_limited_requests BIGINT NOT NULL DEFAULT 0,
    
    -- IP statistics
    unique_ips INT NOT NULL DEFAULT 0,
    blocked_ips INT NOT NULL DEFAULT 0,
    new_blocked_ips INT NOT NULL DEFAULT 0,
    
    -- API Key statistics  
    active_api_keys INT NOT NULL DEFAULT 0,
    blocked_api_keys INT NOT NULL DEFAULT 0,
    suspended_api_keys INT NOT NULL DEFAULT 0,
    
    -- Attack statistics
    brutal_attacks INT NOT NULL DEFAULT 0,
    suspicious_activities INT NOT NULL DEFAULT 0,
    
    -- Performance metrics
    avg_response_time_ms DECIMAL(8,2) NULL,
    peak_requests_per_minute INT NOT NULL DEFAULT 0,
    
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    INDEX IX_security_statistics_date (stat_date)
);

-- Example queries for common security monitoring tasks:

-- 1. Recent brutal attacks
-- SELECT TOP 10 * FROM app.security_events 
-- WHERE event_type = 'BRUTAL_ATTACK' 
-- ORDER BY event_timestamp DESC;

-- 2. Most attacked IPs
-- SELECT source_ip, COUNT(*) as attack_count
-- FROM app.security_events 
-- WHERE event_type IN ('BRUTAL_ATTACK', 'RATE_LIMIT_EXCEEDED')
-- GROUP BY source_ip 
-- ORDER BY attack_count DESC;

-- 3. API keys with most violations
-- SELECT api_key, COUNT(*) as violation_count
-- FROM app.rate_limit_violations
-- WHERE violation_timestamp >= DATEADD(day, -7, GETDATE())
-- GROUP BY api_key
-- ORDER BY violation_count DESC;

-- 4. Daily security summary
-- SELECT * FROM app.security_statistics_daily 
-- WHERE stat_date >= DATEADD(day, -30, GETDATE())
-- ORDER BY stat_date DESC;

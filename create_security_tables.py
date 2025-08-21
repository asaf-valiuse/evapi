"""
Create Security Tables Script
Run this to create the security logging tables in your database
"""
from app.services.db import get_engine
from sqlalchemy import text

def create_security_tables():
    """Create all security logging tables"""
    
    security_tables_sql = """
    -- Main security events table
    CREATE TABLE app.security_events (
        event_id INT IDENTITY(1,1) PRIMARY KEY,
        event_type NVARCHAR(50) NOT NULL,
        event_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
        source_ip NVARCHAR(45),
        api_key NVARCHAR(100),
        client_id INT,
        event_severity NVARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
        event_description NVARCHAR(500) NOT NULL,
        event_data NVARCHAR(MAX),
        action_taken NVARCHAR(100),
        endpoint NVARCHAR(200),
        response_code INT,
        user_agent NVARCHAR(500)
    );

    -- Rate limit violations table
    CREATE TABLE app.rate_limit_violations (
        violation_id INT IDENTITY(1,1) PRIMARY KEY,
        api_key NVARCHAR(100) NOT NULL,
        client_id INT NOT NULL,
        source_ip NVARCHAR(45) NOT NULL,
        violation_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
        limit_type NVARCHAR(20) NOT NULL,
        limit_value INT NOT NULL,
        actual_requests INT NOT NULL,
        excess_requests INT NOT NULL,
        access_tier NVARCHAR(20),
        requests_per_minute INT,
        requests_per_hour INT,
        requests_per_day INT,
        endpoint NVARCHAR(200),
        user_agent NVARCHAR(500),
        security_event_id INT,
        FOREIGN KEY (security_event_id) REFERENCES app.security_events(event_id)
    );

    -- IP blocking events table
    CREATE TABLE app.ip_blocking_events (
        block_id INT IDENTITY(1,1) PRIMARY KEY,
        ip_address NVARCHAR(45) NOT NULL,
        block_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
        block_reason NVARCHAR(200) NOT NULL,
        block_type NVARCHAR(30) NOT NULL DEFAULT 'AUTO_BRUTAL_ATTACK',
        requests_in_period INT,
        time_period_minutes INT,
        total_requests_lifetime INT,
        first_seen_timestamp DATETIME2,
        unblock_timestamp DATETIME2 NULL,
        unblock_reason NVARCHAR(200) NULL,
        security_event_id INT,
        FOREIGN KEY (security_event_id) REFERENCES app.security_events(event_id)
    );

    -- API key security events table
    CREATE TABLE app.api_key_security_events (
        key_event_id INT IDENTITY(1,1) PRIMARY KEY,
        api_key NVARCHAR(100) NOT NULL,
        client_id INT NOT NULL,
        event_timestamp DATETIME2 NOT NULL DEFAULT GETDATE(),
        event_type NVARCHAR(50) NOT NULL,
        event_description NVARCHAR(300) NOT NULL,
        source_ip NVARCHAR(45),
        endpoint NVARCHAR(200),
        previous_status NVARCHAR(20),
        new_status NVARCHAR(20),
        action_automatic BIT NOT NULL DEFAULT 1,
        action_by NVARCHAR(100)
    );

    -- Daily security statistics table
    CREATE TABLE app.security_statistics_daily (
        stat_id INT IDENTITY(1,1) PRIMARY KEY,
        stat_date DATE NOT NULL UNIQUE,
        total_security_events INT NOT NULL DEFAULT 0,
        brutal_attacks INT NOT NULL DEFAULT 0,
        rate_limited_requests INT NOT NULL DEFAULT 0,
        new_blocked_ips INT NOT NULL DEFAULT 0,
        unique_ips INT NOT NULL DEFAULT 0,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
    );

    -- Indexes for performance
    CREATE INDEX IX_security_events_timestamp ON app.security_events(event_timestamp DESC);
    CREATE INDEX IX_security_events_type ON app.security_events(event_type);
    CREATE INDEX IX_security_events_source_ip ON app.security_events(source_ip);
    CREATE INDEX IX_security_events_api_key ON app.security_events(api_key);

    CREATE INDEX IX_rate_violations_timestamp ON app.rate_limit_violations(violation_timestamp DESC);
    CREATE INDEX IX_rate_violations_api_key ON app.rate_limit_violations(api_key);

    CREATE INDEX IX_ip_blocks_timestamp ON app.ip_blocking_events(block_timestamp DESC);
    CREATE INDEX IX_ip_blocks_ip ON app.ip_blocking_events(ip_address);

    CREATE INDEX IX_api_key_events_timestamp ON app.api_key_security_events(event_timestamp DESC);
    CREATE INDEX IX_api_key_events_key ON app.api_key_security_events(api_key);

    CREATE INDEX IX_daily_stats_date ON app.security_statistics_daily(stat_date DESC);
    """
    
    try:
        engine = get_engine()
        with engine.begin() as conn:
            # Split and execute each statement
            statements = [stmt.strip() for stmt in security_tables_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    print(f"Executing: {statement[:50]}...")
                    conn.execute(text(statement))
            
        print("✅ Security tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating security tables: {e}")
        return False

if __name__ == "__main__":
    create_security_tables()

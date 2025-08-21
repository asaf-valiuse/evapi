"""
Database setup script for client_api_access table
Run this to create sample data for testing
"""
import asyncio
import json
from datetime import datetime
from app.services.db import get_db_connection

async def create_sample_data():
    """Create sample client_api_access records for testing"""
    
    # Sample data for different tiers
    sample_records = [
        {
            "client_id": 1,
            "api_key": "basic-test-key-12345",
            "access_tier": "basic",
            "requests_per_minute": 1,
            "requests_per_hour": 60, 
            "requests_per_day": 1440,
            "is_active": True
        },
        {
            "client_id": 2,  
            "api_key": "premium-test-key-67890",
            "access_tier": "premium",
            "requests_per_minute": 10,
            "requests_per_hour": 600,
            "requests_per_day": 14400, 
            "is_active": True
        },
        {
            "client_id": 99,
            "api_key": "admin-unlimited-key-xyz",
            "access_tier": "admin", 
            "requests_per_minute": 1000,
            "requests_per_hour": 60000,
            "requests_per_day": 1440000,
            "override_all_limits": True,
            "is_active": True
        }
    ]
    
    connection = await get_db_connection()
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        cursor = connection.cursor()
        
        # Insert sample records
        for record in sample_records:
            # Check if record already exists
            cursor.execute(
                "SELECT COUNT(*) FROM client_api_access WHERE api_key = ?",
                (record["api_key"],)
            )
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                print(f"⚠️  Record with API key '{record['api_key']}' already exists, skipping...")
                continue
            
            # Insert new record
            insert_sql = """
                INSERT INTO client_api_access 
                (client_id, api_key, access_tier, requests_per_minute, requests_per_hour, requests_per_day, 
                 is_active, is_suspended, is_auto_blocked, override_all_limits, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, GETDATE(), GETDATE())
            """
            
            cursor.execute(insert_sql, (
                record["client_id"],
                record["api_key"], 
                record["access_tier"],
                record["requests_per_minute"],
                record["requests_per_hour"],
                record["requests_per_day"],
                1 if record["is_active"] else 0,
                1 if record.get("override_all_limits", False) else 0
            ))
            
            print(f"✅ Created {record['access_tier']} tier record: {record['api_key']}")
        
        # Commit changes
        connection.commit()
        
        # Display all records
        print("\n📊 All client_api_access records:")
        cursor.execute("""
            SELECT 
                client_id,
                api_key,
                access_tier, 
                requests_per_minute,
                requests_per_hour,
                requests_per_day,
                is_active,
                is_suspended,
                is_auto_blocked,
                override_all_limits,
                total_requests_lifetime,
                requests_today
            FROM client_api_access 
            ORDER BY client_id
        """)
        
        records = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        print(f"\n{'='*80}")
        for record in records:
            record_dict = dict(zip(columns, record))
            print(f"Client ID: {record_dict['client_id']}")
            print(f"API Key: {record_dict['api_key']}")
            print(f"Tier: {record_dict['access_tier']} | Limits: {record_dict['requests_per_minute']}/min, {record_dict['requests_per_hour']}/hr, {record_dict['requests_per_day']}/day")
            print(f"Status: Active={record_dict['is_active']}, Suspended={record_dict['is_suspended']}, Blocked={record_dict['is_auto_blocked']}, Unlimited={record_dict['override_all_limits']}")
            print(f"Usage: {record_dict['requests_today']} today, {record_dict['total_requests_lifetime']} lifetime")
            print("-" * 80)
            
        print(f"\n🎉 Database setup complete! You can now test with these API keys.")
        print(f"\n📝 Example test command:")
        print(f"curl \"http://localhost:8000/run?key=basic-test-key-12345&q=your-query\"")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        connection.rollback()
    finally:
        connection.close()

async def check_table_structure():
    """Check if client_api_access table exists and show its structure"""
    connection = await get_db_connection()
    
    if not connection:
        print("❌ Could not connect to database")
        return
    
    try:
        cursor = connection.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'client_api_access'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            print("❌ Table 'client_api_access' does not exist!")
            print("\n📋 Please create the table first using this SQL:")
            print("""
CREATE TABLE client_api_access (
    id INT IDENTITY(1,1) PRIMARY KEY,
    client_id INT NOT NULL,
    api_key NVARCHAR(255) NOT NULL,
    access_tier NVARCHAR(50) NOT NULL DEFAULT 'basic',
    requests_per_minute INT NOT NULL DEFAULT 1,
    requests_per_hour INT NOT NULL DEFAULT 60,
    requests_per_day INT NOT NULL DEFAULT 1440,
    is_active BIT NOT NULL DEFAULT 1,
    is_suspended BIT NOT NULL DEFAULT 0,
    is_auto_blocked BIT NOT NULL DEFAULT 0,
    override_all_limits BIT NOT NULL DEFAULT 0,
    total_requests_lifetime BIGINT NOT NULL DEFAULT 0,
    requests_today INT NOT NULL DEFAULT 0,
    last_request_at DATETIME2 NULL,
    created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    updated_at DATETIME2 NOT NULL DEFAULT GETDATE(),
    UNIQUE(api_key)
);
            """)
            return
        
        print("✅ Table 'client_api_access' exists!")
        
        # Show table structure
        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'client_api_access'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        print("\n📋 Table structure:")
        print("-" * 60)
        for col in columns:
            col_name, data_type, nullable, default = col
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f" DEFAULT {default}" if default else ""
            print(f"{col_name:<25} {data_type:<15} {nullable_str}{default_str}")
        
        # Show current record count
        cursor.execute("SELECT COUNT(*) FROM client_api_access")
        count = cursor.fetchone()[0]
        print(f"\n📊 Current records: {count}")
        
    except Exception as e:
        print(f"❌ Error checking table: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    print("🔧 Database Setup for API Access Control")
    print("=" * 50)
    
    # Check table structure first
    print("\n1. Checking table structure...")
    asyncio.run(check_table_structure())
    
    # Create sample data  
    print("\n2. Creating sample data...")
    asyncio.run(create_sample_data())

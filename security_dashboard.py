"""
Security Dashboard Script
View comprehensive security events and statistics from command line
"""
from app.services.db import get_engine
from sqlalchemy import text
from datetime import datetime

def show_security_dashboard():
    """Display comprehensive security dashboard"""
    
    engine = get_engine()
    
    print("🛡️  SECURITY DASHBOARD")
    print("=" * 50)
    
    try:
        # Get today's statistics
        with engine.connect() as conn:
            print("\n📊 TODAY'S SECURITY STATISTICS")
            print("-" * 30)
            
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN event_type = 'BRUTAL_ATTACK' THEN 1 END) as brutal_attacks,
                    COUNT(CASE WHEN event_type = 'IP_BLOCKED' THEN 1 END) as ip_blocks,
                    COUNT(CASE WHEN event_type = 'RATE_LIMIT_EXCEEDED' THEN 1 END) as rate_violations,
                    COUNT(DISTINCT source_ip) as unique_ips,
                    COUNT(DISTINCT api_key) as unique_api_keys
                FROM app.security_events 
                WHERE CAST(event_timestamp AS DATE) = CAST(GETDATE() AS DATE)
            """))
            
            stats = result.fetchone()
            print(f"Total Security Events: {stats.total_events}")
            print(f"Brutal Attack Blocks: {stats.brutal_attacks}")
            print(f"IP Blocks: {stats.ip_blocks}")
            print(f"Rate Limit Violations: {stats.rate_violations}")
            print(f"Unique IPs: {stats.unique_ips}")
            print(f"Unique API Keys: {stats.unique_api_keys}")
        
        # Get recent security events
        with engine.connect() as conn:
            print("\n🔍 RECENT SECURITY EVENTS")
            print("-" * 30)
            
            result = conn.execute(text("""
                SELECT TOP 10
                    event_type,
                    event_timestamp,
                    source_ip,
                    LEFT(api_key, 8) + '...' as api_key_masked,
                    event_severity,
                    event_description,
                    action_taken
                FROM app.security_events
                ORDER BY event_timestamp DESC
            """))
            
            events = result.fetchall()
            for event in events:
                timestamp = event.event_timestamp.strftime("%H:%M:%S")
                severity_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(event.event_severity, "⚪")
                
                print(f"{timestamp} {severity_icon} [{event.event_type}] {event.event_description}")
                if event.source_ip:
                    print(f"         IP: {event.source_ip} | API: {event.api_key_masked or 'N/A'} | Action: {event.action_taken or 'N/A'}")
                print()
        
        # Get rate limit violations
        with engine.connect() as conn:
            print("⏱️  RATE LIMIT VIOLATIONS")
            print("-" * 30)
            
            result = conn.execute(text("""
                SELECT TOP 5
                    LEFT(api_key, 8) + '...' as api_key_masked,
                    source_ip,
                    limit_type,
                    actual_requests,
                    limit_value,
                    access_tier,
                    violation_timestamp
                FROM app.rate_limit_violations
                ORDER BY violation_timestamp DESC
            """))
            
            violations = result.fetchall()
            if violations:
                for v in violations:
                    timestamp = v.violation_timestamp.strftime("%H:%M:%S")
                    print(f"{timestamp} - {v.api_key_masked} ({v.access_tier})")
                    print(f"         {v.actual_requests}/{v.limit_value} requests per {v.limit_type.lower()} from {v.source_ip}")
                    print()
            else:
                print("No rate limit violations recorded.")
        
        # Get IP blocks
        with engine.connect() as conn:
            print("🚫 IP BLOCKING EVENTS")
            print("-" * 30)
            
            result = conn.execute(text("""
                SELECT TOP 5
                    ip_address,
                    block_reason,
                    requests_in_period,
                    time_period_minutes,
                    block_timestamp
                FROM app.ip_blocking_events
                ORDER BY block_timestamp DESC
            """))
            
            blocks = result.fetchall()
            if blocks:
                for block in blocks:
                    timestamp = block.block_timestamp.strftime("%H:%M:%S")
                    print(f"{timestamp} - {block.ip_address}")
                    print(f"         {block.block_reason}")
                    if block.requests_in_period:
                        print(f"         {block.requests_in_period} requests in {block.time_period_minutes} minute(s)")
                    print()
            else:
                print("No IP blocking events recorded.")
                
    except Exception as e:
        print(f"❌ Error accessing security data: {e}")

if __name__ == "__main__":
    show_security_dashboard()

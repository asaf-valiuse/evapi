"""
Clear Cache and Reset Security System
Clears all in-memory caches, IP tracking, and blocked lists
"""
import os
import json

def clear_all_caches():
    """Clear all in-memory caches and reset security system"""
    
    print("🧹 CLEARING ALL CACHES AND SECURITY STATE")
    print("=" * 50)
    
    # 1. Clear blocked IPs file
    print("\n1. Clearing blocked IPs file...")
    blocked_ips_file = "blocked_ips.json"
    if os.path.exists(blocked_ips_file):
        try:
            # Reset to empty structure
            empty_blocked_data = {
                "ips": [],
                "api_keys": [],
                "ranges": []
            }
            with open(blocked_ips_file, 'w') as f:
                json.dump(empty_blocked_data, f, indent=2)
            print("✅ Blocked IPs file cleared")
        except Exception as e:
            print(f"❌ Error clearing blocked IPs file: {e}")
    else:
        print("ℹ️  Blocked IPs file doesn't exist")
    
    # 2. Clear any other cache files
    cache_files = [
        "cache_data.json",
        "rate_limit_cache.json", 
        "usage_tracking.json",
        "security_cache.json"
    ]
    
    print("\n2. Clearing other cache files...")
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                print(f"✅ Removed {cache_file}")
            except Exception as e:
                print(f"❌ Error removing {cache_file}: {e}")
    
    print("\n3. Cache clear instructions for running server:")
    print("-" * 40)
    print("To clear in-memory caches on the running server:")
    print("• Restart the FastAPI server (uvicorn)")
    print("• Or call the API endpoints to trigger cache refresh")
    print("• The rate limit cache will refresh automatically in 5 minutes")
    
    print("\n🎉 Cache clearing completed!")
    print("All persistent cache files have been cleared.")
    print("In-memory caches will be cleared on server restart.")

if __name__ == "__main__":
    clear_all_caches()

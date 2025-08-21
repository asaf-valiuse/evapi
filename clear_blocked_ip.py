#!/usr/bin/env python3
"""
Script to clear blocked IPs from the brutal attack tracker
"""
import sys
import os

# Add the current directory to Python path so we can import app modules
sys.path.insert(0, os.path.abspath('.'))

from app.services.ip_brutal_tracker import ip_brutal_tracker

def clear_blocked_ip(ip_address: str):
    """Clear a specific IP from being blocked"""
    print(f"Clearing blocked IP: {ip_address}")
    
    # Remove from tracking
    if ip_address in ip_brutal_tracker._ip_tracking:
        del ip_brutal_tracker._ip_tracking[ip_address]
        print(f"  ✓ Removed {ip_address} from tracking")
    else:
        print(f"  ℹ {ip_address} was not in tracking")
    
    # Clear any file-based blocks
    try:
        ip_brutal_tracker.save_blocked_ips_to_file()
        print(f"  ✓ Updated blocked IPs file")
    except Exception as e:
        print(f"  ⚠ Error updating file: {e}")
    
    print(f"IP {ip_address} has been cleared from blocking system.")

def clear_all_blocked_ips():
    """Clear all blocked IPs"""
    print("Clearing all blocked IPs...")
    
    # Clear all IP tracking
    ip_brutal_tracker._ip_tracking.clear()
    
    try:
        ip_brutal_tracker.save_blocked_ips_to_file()
        print("  ✓ All IPs cleared and file updated")
    except Exception as e:
        print(f"  ⚠ Error updating file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ip_to_clear = sys.argv[1]
        clear_blocked_ip(ip_to_clear)
    else:
        # Clear localhost IP specifically
        clear_blocked_ip("127.0.0.1")
        clear_all_blocked_ips()

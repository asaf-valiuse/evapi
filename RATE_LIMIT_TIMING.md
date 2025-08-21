# Rate Limit Release Timing - EnerVibe API

## ⏰ **When Rate Limits Are Released**

### **Current Configuration:**
```
- 3 requests per minute (60-second sliding window)
- 10 requests per hour (3600-second sliding window)  
- 200 requests per day (86400-second sliding window)
```

### **Release Timeline Examples:**

#### **Scenario 1: Minute Rate Limit (3 per minute)**
```
Time 12:00:00 - Request 1 ✅ (1/3 used)
Time 12:00:20 - Request 2 ✅ (2/3 used)  
Time 12:00:40 - Request 3 ✅ (3/3 used - LIMIT REACHED)
Time 12:00:50 - Request 4 ❌ (Rate limited)

⏰ Time 12:01:00 - Request 1 expires, can make 1 new request (2/3 used)
⏰ Time 12:01:20 - Request 2 expires, can make 1 new request (1/3 used)  
⏰ Time 12:01:40 - Request 3 expires, can make 1 new request (0/3 used)
```

#### **Scenario 2: API Key Abuse (10+ requests quickly)**
```
Time 12:00:00 - 10 rapid requests → API KEY AUTO-BLOCKED
Time 12:01:00 - Still blocked (not time-based, permanently blocked)
Time 12:02:00 - Still blocked (requires manual unblock or server restart)
```

### **Rate Limit Types:**

#### 1. **Temporary Rate Limits** (Automatic Release)
- **Minute limits**: Released after 60 seconds  
- **Hour limits**: Released after 3600 seconds
- **Day limits**: Released after 86400 seconds

#### 2. **Permanent Blocks** (Manual Release Required)
- **Auto-blocked API keys**: Requires manual removal from `blocked_ips.json`
- **Auto-blocked IPs**: Requires manual removal from `blocked_ips.json`

### **How to Check Current Status:**

```powershell
# Method 1: Check usage statistics
curl "http://localhost:8000/usage?key=YOUR_API_KEY"

# Method 2: Check blocked lists
$blocked = Get-Content "blocked_ips.json" | ConvertFrom-Json
Write-Host "Blocked IPs: $($blocked.ips)"
Write-Host "Blocked API Keys: $($blocked.api_keys)"

# Method 3: Test with a fresh API key
curl "http://localhost:8000/run?key=test-$(Get-Random)&q=test&demo=true"
```

### **Immediate Release Methods:**

#### **Option 1: Wait for Natural Expiration**
```
Minute limit: Wait 60 seconds from last request
Hour limit: Wait up to 1 hour  
Day limit: Wait up to 24 hours
```

#### **Option 2: Restart Server (Clears In-Memory Limits)**
```powershell
# Stop server (Ctrl+C)
# Start server
python -m uvicorn app.main:app --reload --port 8000

# Note: Permanent blocks in blocked_ips.json will persist
```

#### **Option 3: Manual Unblock (For Permanent Blocks)**
```json
// Edit blocked_ips.json - remove entries:
{
  "ips": [],           // Remove IPs from here
  "api_keys": [],      // Remove API keys from here  
  "ranges": [],
  "updated": "..."
}
```

### **Current Situation Analysis:**

Based on your testing session:

1. **API Key `test-key-12345`**: 
   - Made 3+ requests rapidly
   - Hit minute rate limit (3 per minute)
   - Should be released ~60 seconds after the first request

2. **IP `127.0.0.1`**:
   - I see it's in your blocked_ips.json
   - This is a **permanent block** - won't auto-release
   - Requires manual removal

### **To Immediately Test New Limits:**

```powershell
# Remove IP block manually:
$config = Get-Content "blocked_ips.json" | ConvertFrom-Json
$config.ips = @()  # Clear IP blocks
$config | ConvertTo-Json -Depth 10 | Set-Content "blocked_ips.json"

# Test with completely new API key:
curl "http://localhost:8000/run?key=brand-new-key-123&q=test&demo=true"
```

---

## **Summary:**
- **Rate limits** reset automatically based on sliding windows (60s, 1h, 24h)
- **Permanent blocks** (in blocked_ips.json) require manual intervention
- **Current issue**: Your localhost IP is permanently blocked, preventing all requests
- **Solution**: Remove 127.0.0.1 from blocked_ips.json or test from different IP

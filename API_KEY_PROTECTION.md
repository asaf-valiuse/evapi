# Enhanced API Key-Based Protection

## 🔑 **API Key is Now the PRIMARY Rate Limiting Factor**

Your protection system now prioritizes **API keys over IP addresses** for rate limiting and abuse detection.

### **Rate Limiting Priority:**

1. **🔑 API Key** - Primary rate limiting identifier
   - Each API key gets its own rate limit bucket
   - Users cannot bypass limits by changing IPs
   - More reliable for database access control

2. **🌐 IP Address** - Fallback only
   - Used only for endpoints without API keys (like `/healthz`)
   - Secondary protection layer

### **Protection Enhancements:**

#### ✅ **API Key Rate Limiting**
```bash
# Each API key has independent limits
API_KEY_A: 2/minute, 50/day (free tier)
API_KEY_B: 3/minute, 200/day (basic tier)

# Changing IP won't reset the API key limits
curl "api.com/run?key=API_KEY_A"  # Request 1/2 for this key
curl "api.com/run?key=API_KEY_A"  # Request 2/2 for this key
curl "api.com/run?key=API_KEY_A"  # BLOCKED - over limit
```

#### ✅ **API Key Abuse Detection**
- **>10 requests/minute** → Auto-block the API key
- **>3 failed auth attempts/minute** → Auto-block the API key  
- **>20 total failed attempts** → Auto-block the API key

#### ✅ **Persistent API Key Blocking**
- Blocked API keys saved to `blocked_ips.json`
- Survives server restarts
- Manual unblocking capability

### **File Structure Update:**

**`blocked_ips.json`** now includes:
```json
{
  "ips": ["192.168.1.100"],
  "api_keys": ["E1A77476-19DE-4E0C-AA54-53F7047EA56E"],
  "ranges": ["192.168.0.0/24"],
  "updated": "2025-08-21T10:30:00"
}
```

### **Security Headers Added:**
```http
X-Client-IP: 192.168.1.100
X-API-Key-Tracked: E1A77476...
```

### **Enhanced Error Responses:**

**API Key Blocked:**
```json
{
  "detail": "This API key has been blocked due to abuse"
}
```

**Rate Limited by API Key:**
```json
{
  "error": "Quota exceeded",
  "daily_limit": 200,
  "minute_limit": 3,
  "message": "You have exceeded your basic plan limits."
}
```

### **Testing API Key Protection:**

```powershell
# Test 1: Normal usage with valid key (should work)
curl "http://localhost:8000/run?key=VALID_KEY&q=test&demo=true"

# Test 2: Rapid requests with same key (should get blocked after tier limit)
for ($i=1; $i -le 10; $i++) {
    curl "http://localhost:8000/run?key=SAME_KEY&q=test&demo=true"
}

# Test 3: Same requests from different IP (should still be blocked - API key limit reached)
# Even if you change IP, the API key limit persists

# Test 4: Different API keys from same IP (should work independently)  
curl "http://localhost:8000/run?key=KEY_A&q=test&demo=true"  # Works
curl "http://localhost:8000/run?key=KEY_B&q=test&demo=true"  # Also works
```

### **Benefits:**

✅ **True Database Access Control** - Rate limiting follows the actual database access key
✅ **Bypass-Proof** - Users cannot circumvent limits by changing IPs, proxies, or VPNs
✅ **Granular Control** - Each API key has independent limits based on their tier
✅ **Abuse Tracking** - Failed authentication attempts tracked per API key
✅ **Persistent Protection** - Blocked API keys remain blocked across restarts

### **Monitoring Commands:**

```powershell
# Check blocked API keys
$blocked = Get-Content "blocked_ips.json" | ConvertFrom-Json
$blocked.api_keys

# Check usage for specific API key  
curl "http://localhost:8000/usage?key=YOUR_API_KEY"

# Check security logs for API key events
Get-Content "api_security.log" | Select-String "API_KEY"
```

### **Manual API Key Management:**

**Block an API key manually:**
```json
// Add to blocked_ips.json
{
  "api_keys": ["ABUSIVE_API_KEY_HERE"]
}
```

**Unblock an API key:**
```json  
// Remove from blocked_ips.json api_keys array
```

---

## 🎯 **Summary:**

Your API protection is now **API key-centric** rather than IP-centric, providing:
- **Stronger database access control** 
- **Bypass-proof rate limiting**
- **Better abuse tracking**
- **Persistent API key blocking**

**Each API key is now tracked independently, making your database truly secure from abuse regardless of where the requests come from!** 🔒

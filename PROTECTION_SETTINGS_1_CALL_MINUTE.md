# EnerVibe API - Protection Settings (Optimized for 1 call/minute usage)

## Updated Rate Limits (Active Now)

### Per-Minute Limits (Primary Protection)
```
Free Tier:     2 requests/minute  ✅ 100% tolerance for normal usage
Basic Tier:    3 requests/minute  ✅ 200% tolerance for normal usage  
Premium Tier:  5 requests/minute  ✅ 400% tolerance for normal usage
Enterprise:   10 requests/minute  ✅ 900% tolerance for normal usage
```

### Daily Limits (Secondary Protection)
```
Free Tier:     50 requests/day   ✅ ~50 minutes of usage
Basic Tier:   200 requests/day   ✅ ~3.3 hours of usage
Premium Tier: 500 requests/day   ✅ ~8.3 hours of usage
Enterprise:  1500 requests/day   ✅ ~25 hours of usage (full day + buffer)
```

### Auto-Ban Triggers (Suspicious Activity)
```
> 10 requests per minute from same IP  → Auto-block IP
> 5 failed authentication attempts     → Auto-block IP
Persistent abuse for 3+ minutes        → Auto-block IP
```

### Global Rate Limits (All IPs/Keys Combined)
```
Health endpoint: 10 requests/minute
Main API endpoints: 3 requests/minute (default)
Usage statistics: 10 requests/minute
```

## Protection Test Results ✅

**Normal Usage (1 call/minute):**
- ✅ Always allowed for all tiers
- ✅ Plenty of headroom for occasional burst requests

**Abuse Detection (10+ calls/minute):**
- ✅ Blocked after 10 requests within 1 minute
- ✅ Returns HTTP 429 (Too Many Requests)
- ✅ IP tracked for potential auto-ban

**Attack Scenarios:**
- ✅ API bombing: Blocked after 10 requests/minute
- ✅ Authentication attacks: Blocked after 5 failed attempts
- ✅ Distributed attacks: Each IP limited independently

## Client Guidance

### Normal Usage Pattern (1 call/minute)
```bash
# This will ALWAYS work for all client tiers
curl "https://your-api.com/run?key=YOUR_KEY&q=QUERY_ID"
# Wait 60 seconds
curl "https://your-api.com/run?key=YOUR_KEY&q=QUERY_ID"
```

### Burst Usage (Occasional)
```bash
# Free tier: Up to 2 calls in quick succession per minute
# Basic tier: Up to 3 calls in quick succession per minute  
# Premium tier: Up to 5 calls in quick succession per minute
# Enterprise: Up to 10 calls in quick succession per minute
```

### Error Responses
```json
// Rate limited
{
  "error": "Quota exceeded",
  "daily_limit": 200,
  "minute_limit": 3,
  "message": "You have exceeded your basic plan limits."
}

// IP blocked (after abuse)
{
  "detail": "Your IP address has been blocked due to suspicious activity"
}
```

## Monitoring Commands

```bash
# Check current usage
curl "http://localhost:8000/usage?key=YOUR_API_KEY"

# Check health (limited to 10/minute)
curl "http://localhost:8000/healthz"

# View security logs
Get-Content "api_security.log" -Tail 20

# View blocked IPs
Get-Content "blocked_ips.json" | ConvertFrom-Json
```

---

**Summary:** Your API is now optimally protected for 1 call/minute usage patterns while still allowing reasonable burst capacity and providing strong protection against abuse! 🔒

# API Protection & Security Guide

## Overview
This document describes the multi-layered protection system implemented to prevent API abuse, DDoS attacks, and unauthorized access to the EnerVibe API.

## Protection Layers

### 1. Rate Limiting 🚦
**Purpose**: Prevent API bombing and excessive requests

**Implementation**:
- Per API key limits (most granular)
- Per IP address limits (fallback)
- Different tiers: Free, Basic, Premium, Enterprise
- Both daily and per-minute limits

**Default Limits**:
```
Free Tier:     2 req/min,   100 req/day
Basic Tier:    10 req/min,  1,000 req/day
Premium Tier:  50 req/min,  10,000 req/day
Enterprise:    100 req/min, 50,000 req/day
```

**Configuration**: See `.env` file for customization

### 2. Request Protection 🛡️
**Purpose**: Prevent resource exhaustion

**Features**:
- Max request size (1MB default)
- Request timeout (30 seconds default)
- Concurrent request limiting (100 default)
- Automatic slow request detection

### 3. IP Blocking & Monitoring 🚫
**Purpose**: Block malicious IPs automatically

**Features**:
- Manual IP blocking via `blocked_ips.json`
- IP range blocking (CIDR notation)
- Automatic blocking based on suspicious activity:
  - Too many requests per minute (>60)
  - Too many authentication failures (>10)
  - Persistent abuse patterns

### 4. Authentication with Quotas 🔐
**Purpose**: Enhanced API key validation with usage tracking

**Features**:
- Real-time quota checking before processing
- Usage statistics per API key
- Graceful quota exceeded responses with upgrade suggestions

### 5. Security Logging & Monitoring 📊
**Purpose**: Track and alert on security events

**Features**:
- Structured security event logging
- API usage analytics
- Automatic alerting for high-severity events
- Log rotation and retention

## Configuration Files

### `.env` - Environment Variables
```bash
# Rate limiting
REDIS_URL=redis://localhost:6379
ENABLE_REDIS_RATE_LIMIT=false

# Request limits
MAX_REQUEST_SIZE=1048576
REQUEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=100

# CORS (restrict in production)
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### `blocked_ips.json` - IP Blocking Configuration
```json
{
  "ips": ["192.168.1.100", "10.0.0.50"],
  "ranges": ["192.168.0.0/24", "10.0.0.0/8"],
  "updated": "2025-08-21T10:00:00"
}
```

## Monitoring & Alerts

### Log Files
- `api_security.log` - Security events and API usage
- Standard application logs - General application events

### Security Events Logged
- Rate limit violations
- Authentication failures
- IP auto-blocking
- Suspicious activity patterns
- API usage statistics

### Sample Log Entry
```json
{
  "timestamp": "2025-08-21T10:30:00.000Z",
  "event_type": "RATE_LIMIT_EXCEEDED",
  "ip_address": "192.168.1.100",
  "severity": "MEDIUM",
  "details": {
    "api_key": "E1A77476...",
    "limit_type": "minute_limit",
    "action": "REQUEST_BLOCKED"
  }
}
```

## API Endpoints

### Protection Status
```
GET /usage?key=YOUR_API_KEY
```
Returns current usage statistics and limits for the API key.

**Response**:
```json
{
  "usage": {
    "daily_usage": 45,
    "total_requests": 12450,
    "last_request": "2025-08-21T10:30:00.000Z"
  },
  "limits": {
    "tier": "basic",
    "daily_limit": 1000,
    "minute_limit": 10
  }
}
```

## Response Codes & Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad request (invalid query, etc.)
- `401` - Invalid API key
- `403` - IP blocked
- `408` - Request timeout
- `413` - Request too large
- `429` - Rate limit exceeded

### Rate Limit Response
```json
{
  "error": "Quota exceeded",
  "daily_limit": 1000,
  "minute_limit": 10,
  "message": "You have exceeded your basic plan limits. Upgrade your plan for higher limits."
}
```

### IP Blocked Response
```json
{
  "detail": "Your IP address has been blocked due to suspicious activity"
}
```

## Production Deployment

### 1. Redis Setup (Recommended)
For production, use Redis for distributed rate limiting:

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Update .env
ENABLE_REDIS_RATE_LIMIT=true
REDIS_URL=redis://localhost:6379
```

### 2. Reverse Proxy Configuration
Configure your reverse proxy (nginx, Apache, etc.) to:
- Pass real IP addresses via `X-Forwarded-For` headers
- Set reasonable connection limits
- Add additional rate limiting at the proxy level

**Nginx Example**:
```nginx
server {
    listen 80;
    server_name your-api-domain.com;
    
    # Rate limiting at nginx level
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    limit_req zone=api burst=10 nodelay;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
    }
}
```

### 3. CORS Configuration
Restrict CORS to specific domains in production:

```python
# In .env
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 4. Security Headers
Consider adding security headers via your reverse proxy:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

## Testing the Protection

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Setup Script
```bash
# Linux/Mac
chmod +x setup_protection.sh
./setup_protection.sh

# Windows
setup_protection.bat
```

### 3. Start Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Test Rate Limiting
```powershell
# PowerShell - Rapid requests to test rate limiting
for ($i=1; $i -le 20; $i++) {
    Write-Host "Request $i"
    try {
        Invoke-RestMethod "http://localhost:8000/run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4&demo=true"
    } catch {
        Write-Host "Rate limited: $($_.Exception.Message)"
    }
    Start-Sleep -Milliseconds 100
}
```

## Maintenance

### Daily Tasks
- Monitor `api_security.log` for unusual activity
- Review auto-blocked IPs in `blocked_ips.json`
- Check API usage patterns via `/usage` endpoint

### Weekly Tasks
- Rotate log files if they become large
- Review and cleanup old blocked IPs
- Monitor server resource usage under load

### Monthly Tasks
- Review and update rate limits based on usage patterns
- Update blocked IP ranges based on new threat intelligence
- Assess need for additional protection layers

## Troubleshooting

### Common Issues

**Issue**: Rate limits too strict
**Solution**: Adjust limits in `.env` file and restart server

**Issue**: Legitimate users getting blocked
**Solution**: Remove IP from `blocked_ips.json` and restart server

**Issue**: Redis connection errors
**Solution**: Set `ENABLE_REDIS_RATE_LIMIT=false` to use in-memory limiting

**Issue**: High server load
**Solution**: Reduce `MAX_CONCURRENT_REQUESTS` and add more instances

### Debug Mode
Add debug logging by setting log level to DEBUG in production.

---

**Remember**: Security is an ongoing process. Regularly review logs, update configurations, and adapt to new threats.

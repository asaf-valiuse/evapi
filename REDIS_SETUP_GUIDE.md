# Production Setup: Redis-based Protection

## Quick Setup

### 1. Install Redis (Windows)
```powershell
# Using Chocolatey
choco install redis-64

# Or download from: https://github.com/microsoftarchive/redis/releases
```

### 2. Start Redis
```powershell
# Start Redis server
redis-server

# Test Redis connection
redis-cli ping
# Should return: PONG
```

### 3. Enable Redis in API
```bash
# Create/update .env file
ENABLE_REDIS_RATE_LIMIT=true
REDIS_URL=redis://localhost:6379
```

### 4. Restart API Server
```powershell
# Server will now use Redis for persistent protection
python -m uvicorn app.main:app --reload --port 8000
```

## Benefits After Redis Setup

✅ **Persistent Protection**
- Rate limits survive server restarts
- IP blocks persist across deployments
- Usage statistics maintained

✅ **Multi-Server Support**
- Works with load balancers
- Consistent protection across instances
- Shared state between servers

✅ **Better Performance**
- Faster lookups for large datasets
- Automatic cleanup of old data
- Memory efficient

## Test Redis Setup

```powershell
# Test rate limiting with Redis
for ($i=1; $i -le 15; $i++) {
    Write-Host "Request $i"
    try {
        Invoke-RestMethod "http://localhost:8000/healthz"
        Write-Host "✓ Success"
    } catch {
        Write-Host "✗ Rate Limited"
    }
}

# Restart server and test again - limits should persist!
```

## Azure Production Setup

For Azure deployment, use Azure Cache for Redis:

```bash
# Azure CLI setup
az redis create \
  --name your-api-cache \
  --resource-group your-rg \
  --location eastus \
  --sku Basic \
  --vm-size c0

# Get connection string
az redis list-keys --name your-api-cache --resource-group your-rg

# Update environment variables
ENABLE_REDIS_RATE_LIMIT=true
REDIS_URL=rediss://your-cache.redis.cache.windows.net:6380?ssl=true
```

## Current vs Redis Comparison

| Feature | In-Memory | Redis |
|---------|-----------|--------|
| Performance | Very Fast | Fast |
| Persistence | ❌ Lost on restart | ✅ Survives restarts |
| Multi-Server | ❌ Inconsistent | ✅ Shared state |
| Memory Usage | ❌ Grows over time | ✅ Auto cleanup |
| Setup Complexity | ✅ Simple | ⚠️ Requires Redis |
| Production Ready | ❌ For single server only | ✅ Full production |

## Recommendation

For your current single-server setup: **In-memory is fine for now**
For production/scaling: **Use Redis immediately**

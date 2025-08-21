# Azure App Service Deployment Guide (Linux)

## Prerequisites
1. Azure subscription
2. Azure App Service (Linux, Python 3.11)
3. Azure SQL Database (or accessible SQL Server)

## Deployment Steps

### 1. Create Azure App Service (Linux)
```bash
# Using Azure CLI
az webapp create \
  --resource-group your-resource-group \
  --plan your-app-service-plan \
  --name your-app-name \
  --runtime "PYTHON|3.11" \
  --os-type Linux
```

### 2. Configure App Settings in Azure Portal
Go to Azure Portal > App Service > Configuration > Application settings:

**Option A: Using Connection String (Recommended)**
```
api_db_conn=DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server.database.windows.net;DATABASE=your-database;UID=your-username;PWD=your-password
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

**Option B: Using Individual Settings**
```
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database-name
AZURE_SQL_USERNAME=your-username
AZURE_SQL_PASSWORD=your-password
AZURE_SQL_PORT=1433
SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

### 3. Configure Startup Command
In Azure Portal > App Service > Configuration > General settings:
- **Startup Command**: `bash startup.sh`

### 4. Deploy Code
```bash
# Deploy from Git
az webapp deployment source config \
  --name your-app-name \
  --resource-group your-resource-group \
  --repo-url https://github.com/yourusername/your-repo \
  --branch main \
  --manual-integration
```

### 5. Enable CORS (if needed)
In Azure Portal > App Service > CORS:
- Add allowed origins or use `*` for development

## Database Security
- Use Azure SQL Database with firewall rules
- Enable "Allow Azure services" in SQL Server firewall
- Consider using Managed Identity for database access

## Monitoring
- Enable Application Insights
- Monitor logs in Azure Portal > App Service > Log stream

## API Endpoints
- Health check: `https://your-app-name.azurewebsites.net/healthz`
- API endpoint: `https://your-app-name.azurewebsites.net/run?key=YOUR_KEY&q=QUERY_ID`

## Troubleshooting
- Check Azure logs: App Service > Log stream
- Verify environment variables in Configuration
- Test database connectivity from Azure

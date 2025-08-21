# EnerVibe API - Client Instructions

## Getting Started with EnerVibe API

Welcome! This guide will help you quickly start using the EnerVibe API to access your vehicle telemetry data.

### 🔑 What You Need
1. **API Key** - A unique key provided by your administrator
2. **Query ID** - The specific data query you want to run
3. **Internet connection** - To access the cloud-based API

### 🌐 API URL
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net
```

## 📞 Basic Usage

### Step 1: Test Connection
First, verify the API is working by testing the health endpoint:
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/healthz
```
**Expected Response:** `{"ok":true}`

### Step 2: Get Your Data
Use this URL format to get your data:
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=YOUR_QUERY_ID
```

**Replace:**
- `YOUR_API_KEY` - with your actual API key
- `YOUR_QUERY_ID` - with your query identifier

## � Available Data Types

### 1. Vehicle Weight Data
**Query ID:** `5EF690DC-092B-4176-A7B4-16408FAF0B9E`
- **What it shows:** Vehicle weight information from the last X minutes
- **Use it for:** Weight monitoring, load management
- **Parameters:**
  - `minutes` (optional) - How many minutes back to look (default: 15, min: 1, max: 500)

### 2. Wheel Telemetry Data  
**Query ID:** `8394F36D-2C9C-4871-AB8A-5489175E32E4`
- **What it shows:** Tire pressure (PSI), temperature (°C), and load (Kg) for all wheels
- **Use it for:** Tire monitoring, maintenance alerts
- **Parameters:**
  - `minutes` (optional) - How many minutes back to look (default: 15, min: 1, max: 500)

### 3. Active Alerts
**Query ID:** `47CE71C4-7406-4207-A0E9-ACBA0382CC18`
- **What it shows:** Current vehicle alerts including flat tires, distance exceeded, imbalanced weight, overload warnings
- **Use it for:** Real-time monitoring, safety alerts
- **Parameters:**
  - `hours` (optional) - How many hours back to check (default: 168, min: 1, max: 2200)
  - `include_closed` (optional) - Show resolved alerts too (0 = No, 1 = Yes, default: 0)

## 💡 Real Examples

### Get Recent Vehicle Weights (Last 30 Minutes)
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=5EF690DC-092B-4176-A7B4-16408FAF0B9E&minutes=30
```

### Get Current Tire Data (Last 15 Minutes) as CSV
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=8394F36D-2C9C-4871-AB8A-5489175E32E4&format=csv
```

### Get All Alerts from Last 24 Hours (Including Resolved)
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=47CE71C4-7406-4207-A0E9-ACBA0382CC18&hours=24&include_closed=1
```

## �💡 Examples

### Example 1: Vehicle Tire Data (JSON)
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4
```

### Example 2: Same Data as CSV File
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4&format=csv
```

### Example 3: Test with Demo Data
```
https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?key=YOUR_API_KEY&q=YOUR_QUERY_ID&demo=true
```

## 🎛️ Options You Can Use

### Response Format
Add `&format=csv` to get data as CSV instead of JSON:
- **JSON** (default): Easy to read, good for web applications
- **CSV**: Good for Excel, data analysis tools

### Demo Mode
Add `&demo=true` to get sample data for testing:
- Useful for testing your integration
- No risk of affecting real data
- Always returns the same sample results

## 🔧 How to Use in Different Tools

### 📊 Excel / Google Sheets
1. Open Excel or Google Sheets
2. Use "Get Data from Web" or "Import" function  
3. Paste your API URL with `&format=csv`
4. The data will import directly into your spreadsheet

### 🌐 Web Browser
Simply paste your API URL into any web browser address bar to see the data.

### 📱 Mobile Apps / Custom Software
Your developers can use the API URL in any programming language or tool that supports HTTP requests.

## ❗ Troubleshooting

### Common Issues

**Problem:** "Invalid API key" error  
**Solution:** Double-check your API key is correct and hasn't expired

**Problem:** "Query not found" error  
**Solution:** Verify your Query ID is correct and you have access to that data

**Problem:** "Service unavailable" error  
**Solution:** Try again in a few minutes. Contact support if it persists

**Problem:** No data returned  
**Solution:** Try with `&demo=true` to confirm the API works, then check your query parameters

### Getting Help
If you encounter issues:
1. Try the health check URL first
2. Test with demo mode (`&demo=true`)
3. Contact your system administrator with:
   - Your API key
   - The exact URL you're trying to use
   - Any error messages you see

## 🚀 Advanced Usage

### Custom Parameters
Some queries may accept additional parameters. Add them to your URL like this:
```
...&q=YOUR_QUERY_ID&vehicle_id=12345&start_date=2025-01-01
```

### Automation
You can use these URLs in:
- **Scheduled reports** - Set up automated data pulls
- **Dashboards** - Connect to business intelligence tools
- **Mobile apps** - Integrate real-time data
- **Excel macros** - Automate spreadsheet updates

## 📋 Quick Reference Card

| Purpose | URL Pattern |
|---------|-------------|
| Health Check | `/healthz` |
| Get JSON Data | `/run?key=KEY&q=QUERY` |
| Get CSV Data | `/run?key=KEY&q=QUERY&format=csv` |
| Test with Demo | `/run?key=KEY&q=QUERY&demo=true` |

## 📞 Support

**Need Help?**
- Technical issues: Contact your system administrator
- New API keys: Request through your account manager
- Query IDs: Check your account documentation

**Tips for Better Support:**
- Include the full URL you're trying to use
- Mention any error codes or messages
- Describe what you expected vs. what happened

---

## 🎉 You're Ready!

That's it! You now have everything you need to start using the EnerVibe API. Start with the health check, then try your data URL with demo mode to confirm everything works.

**Remember:** Keep your API key secure and don't share it with unauthorized users.

---
*Last Updated: August 21, 2025*  
*Need an API key? Contact your administrator*

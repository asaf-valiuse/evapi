# 🔐 API Authentication Update - HEADER-BASED SECURITY

## 🚨 **IMPORTANT SECURITY UPDATE**

Your API now supports **secure header-based authentication** instead of sending API keys in URLs!

---

## 🆕 **New Recommended Method (Secure)**

### **Using Authorization Header:**
```http
GET /run?q=YOUR_QUERY_ID&demo=true
Authorization: Bearer YOUR_API_KEY
```

### **Python Example:**
```python
import requests

# ✅ SECURE - API key in header
headers = {
    "Authorization": "Bearer E1A77476-19DE-4E0C-AA54-53F7047EA56E"
}
response = requests.get(
    "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run",
    params={"q": "5EF690DC-092B-4176-A7B4-16408FAF0B9E", "demo": "true"},
    headers=headers
)
```

### **cURL Example:**
```bash
# ✅ SECURE - API key in header
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?q=test&demo=true"
```

---

## 🔄 **Backward Compatibility (Deprecated)**

### **Old Method (Still Works, But Not Recommended):**
```http
GET /run?key=YOUR_API_KEY&q=YOUR_QUERY_ID&demo=true
```

⚠️ **Why this is less secure:**
- API keys appear in server logs
- Keys visible in browser history
- Keys may leak via referrer headers

---

## 💡 **Migration Guide for System Integration**

### **Before (Insecure):**
```python
# ❌ INSECURE - key in URL
params = {
    "key": "E1A77476-19DE-4E0C-AA54-53F7047EA56E",
    "q": "5EF690DC-092B-4176-A7B4-16408FAF0B9E",
    "demo": "true"
}
response = requests.get("https://api.enervibe.com/run", params=params)
```

### **After (Secure):**
```python
# ✅ SECURE - key in header
headers = {"Authorization": "Bearer E1A77476-19DE-4E0C-AA54-53F7047EA56E"}
params = {"q": "5EF690DC-092B-4176-A7B4-16408FAF0B9E", "demo": "true"}
response = requests.get("https://api.enervibe.com/run", params=params, headers=headers)
```

---

## 🔧 **Supported Header Formats**

Both formats are supported:

1. **Bearer Token Format (Recommended):**
   ```http
   Authorization: Bearer E1A77476-19DE-4E0C-AA54-53F7047EA56E
   ```

2. **Direct Token Format:**
   ```http
   Authorization: E1A77476-19DE-4E0C-AA54-53F7047EA56E
   ```

---

## 🚀 **System Integration Examples**

### **For Automated Systems (Python):**
```python
class EnerVibeAPI:
    def __init__(self, api_key: str):
        self.base_url = "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net"
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def get_vehicle_weight(self, minutes: int = 15):
        """Get vehicle weight data"""
        params = {
            "q": "5EF690DC-092B-4176-A7B4-16408FAF0B9E",
            "minutes": minutes
        }
        response = requests.get(f"{self.base_url}/run", params=params, headers=self.headers)
        return response.json()
    
    def get_wheel_telemetry(self, minutes: int = 15):
        """Get wheel telemetry data"""
        params = {
            "q": "8394F36D-2C9C-4871-AB8A-5489175E32E4", 
            "minutes": minutes
        }
        response = requests.get(f"{self.base_url}/run", params=params, headers=self.headers)
        return response.json()

# Usage
api = EnerVibeAPI("YOUR_API_KEY")
weight_data = api.get_vehicle_weight(30)
wheel_data = api.get_wheel_telemetry(30)
```

### **For JavaScript/Node.js:**
```javascript
const axios = require('axios');

class EnerVibeAPI {
    constructor(apiKey) {
        this.baseURL = 'https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net';
        this.headers = {
            'Authorization': `Bearer ${apiKey}`
        };
    }
    
    async getVehicleWeight(minutes = 15) {
        const params = {
            q: '5EF690DC-092B-4176-A7B4-16408FAF0B9E',
            minutes: minutes
        };
        const response = await axios.get(`${this.baseURL}/run`, { params, headers: this.headers });
        return response.data;
    }
}

// Usage
const api = new EnerVibeAPI('YOUR_API_KEY');
const weightData = await api.getVehicleWeight(30);
```

---

## 🎯 **Benefits of Header-Based Authentication**

✅ **Enhanced Security** - API keys not visible in URLs or logs  
✅ **Industry Standard** - Follows REST API best practices  
✅ **Better Integration** - Compatible with API gateways and proxies  
✅ **Audit Compliance** - Reduces credential exposure in logs  
✅ **Backward Compatible** - Existing integrations continue to work  

---

## ⚡ **Quick Test**

Test your integration with curl:
```bash
# Test with header (recommended)
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://enervibe-api-gfb6hpa4fvftabdj.israelcentral-01.azurewebsites.net/run?q=5EF690DC-092B-4176-A7B4-16408FAF0B9E&demo=true"
```

**Expected Response:**
```json
[
  {
    "vehicle_id": "V001", 
    "weight_kg": 1500.5,
    "timestamp": "2025-08-24T10:30:00"
  }
]
```

---

## 📞 **Support**

Need help updating your integration? Contact your administrator with:
- Your current integration code
- The programming language/framework you're using
- Any specific requirements for your system integration

# Token Pre-warming Implementation Guide

## 📋 **Overview**
The NSP MCP Connector includes intelligent token pre-warming to eliminate the 15-20 second NSP authentication delay that causes timeout issues in MCP tools and Copilot Studio.

## 🎯 **Problem Solved**
- **Without Pre-warming:** First MCP call takes 15-20 seconds (NSP authentication)
- **With Pre-warming:** All MCP calls take 2-3 seconds max (token always warm)

## 🏗️ **Architecture**

### **Smart Token Management**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐
│   Server Start  │───▶│ Initial NSP Auth │───▶│ Get Expiry  │
└─────────────────┘    └──────────────────┘    └─────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐
│ Schedule Refresh│◄───│ Parse Expiry     │◄───│"2025-08-19T │
│ (Expiry - 5min) │    │ Time & Buffer    │    │17:25:43.5Z" │
└─────────────────┘    └──────────────────┘    └─────────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────────┐
│ Auto Refresh    │───▶│ Schedule Next    │
│ Before Expiry   │    │ Refresh Cycle    │
└─────────────────┘    └──────────────────┘
```

### **Key Components**
1. **SmartTokenWarmer** - Main pre-warming class
2. **TokenSchedule** - Tracks expiry and refresh timing
3. **Background Threading** - Non-blocking token refresh
4. **Automatic Recovery** - Retry logic for failed refreshes

## ⚙️ **Configuration**

### **Environment Variables**
```bash
# In local-server/.env
PREWARMING_ENABLED=true                    # Enable/disable pre-warming
PREWARMING_REFRESH_BUFFER=5                # Refresh N minutes before expiry

# NSP credentials (required for pre-warming)
NSP_BASE_URL=http://your-nsp-server:1900/api/PublicApi/
NSP_USERNAME=yournspapiuser
NSP_PASSWORD=your_password
```

### **Default Behavior**
- **Enabled by default:** `PREWARMING_ENABLED=true`
- **Refresh buffer:** 5 minutes before token expiry
- **Auto-start:** Starts automatically when local server starts
- **Recovery:** Automatic retry on failed refreshes

## 🔄 **Operation Flow**

### **Server Startup Sequence**
1. **Local server starts** (`python local-server/app.py`)
2. **NSPClient initialized** with empty token
3. **SmartTokenWarmer created** and started
4. **Initial authentication** performed if no valid token
5. **Token expiry parsed** (e.g., "2025-08-19T17:25:43.555542Z")
6. **First refresh scheduled** (e.g., 17:20:43 = 5 min before expiry)

### **Automatic Refresh Cycle**
```
17:05:43 - Server starts, gets token expires 17:25:43
17:20:43 - Auto-refresh triggered (5 min buffer)
17:20:44 - New token obtained, expires 17:40:44
17:35:44 - Next refresh scheduled
... continues indefinitely
```

### **Error Recovery**
- **Failed refresh:** Retry in 5 minutes
- **Parse error:** Use 15-minute fallback
- **NSP unavailable:** Continue retrying until success

## 📊 **Performance Impact**

### **Before Pre-warming**
| Scenario | First Call | Subsequent Calls | After Token Expiry |
|----------|------------|------------------|-------------------|
| Cold Start | 15-20 seconds | 0.1 seconds | 15-20 seconds |
| Timeout Risk | High (>10s) | None | High (>10s) |

### **After Pre-warming**
| Scenario | Any Call | Cache Hit | Token Always Warm |
|----------|----------|-----------|-------------------|
| Response Time | 2-3 seconds | 0.1 seconds | 2-3 seconds |
| Timeout Risk | None | None | None |

## 🛠️ **API Endpoints**

### **1. Pre-warming Status**
```bash
GET /api/prewarming/status
```
**Response:**
```json
{
  "success": true,
  "data": {
    "prewarming_active": true,
    "refresh_buffer_minutes": 5,
    "token": {
      "has_token": true,
      "is_expired": false,
      "expires_at": "2025-08-19T17:25:43.555542Z",
      "username": "yournspapiuser"
    },
    "schedule": {
      "expires_at": "2025-08-19T17:25:43.555542Z",
      "refresh_at": "2025-08-19T17:20:43.555542Z",
      "next_refresh_in_minutes": 12.5
    }
  }
}
```

### **2. Manual Token Refresh**
```bash
POST /api/prewarming/refresh
```
**Response:**
```json
{
  "success": true,
  "message": "Token refresh initiated"
}
```

### **3. Start Pre-warming**
```bash
POST /api/prewarming/start
```
**Response:**
```json
{
  "success": true,
  "message": "Token pre-warming started successfully"
}
```

### **4. Stop Pre-warming**
```bash
POST /api/prewarming/stop
```
**Response:**
```json
{
  "success": true,
  "message": "Token pre-warming stopped"
}
```

### **5. Enhanced Health Check**
```bash
GET /health
```
**Response (includes pre-warming info):**
```json
{
  "status": "healthy",
  "service": "nsp-local-api",
  "authenticated": true,
  "prewarming": {
    "active": true,
    "next_refresh_in_minutes": 12.5
  }
}
```

## 📝 **Log Messages**

### **Startup**
```
INFO - SmartTokenWarmer initialized with 5min refresh buffer
INFO - 🚀 Starting intelligent token pre-warming...
INFO - No valid token found - performing initial authentication...
INFO - ✅ Initial token obtained successfully
INFO - 🕒 Token refresh scheduled:
INFO -    Expires at: 2025-08-19T17:25:43.555542Z
INFO -    Refresh at: 2025-08-19T17:20:43.555542Z (14.8 minutes)
INFO - 🔥 Token pre-warming system started successfully
```

### **Automatic Refresh**
```
INFO - 🔥 Pre-warming: Refreshing NSP token...
INFO - ✅ Token successfully refreshed via pre-warming
INFO -    New token expires: 2025-08-19T17:40:44.123456Z
INFO - 🕒 Token refresh scheduled:
INFO -    Expires at: 2025-08-19T17:40:44.123456Z
INFO -    Refresh at: 2025-08-19T17:35:44.123456Z (19.9 minutes)
```

### **Error Handling**
```
ERROR - ❌ Token refresh failed - scheduling retry
INFO - 🔄 Token refresh retry scheduled in 5.0 minutes
```

## 🧪 **Testing**

### **Automated Testing**
```bash
# Run comprehensive pre-warming tests
python tests/test_token_prewarming.py
```

### **Manual Testing**
```bash
# Check pre-warming status
curl http://localhost:5000/api/prewarming/status

# Force manual refresh
curl -X POST http://localhost:5000/api/prewarming/refresh

# Check health with pre-warming info
curl http://localhost:5000/health
```

### **Integration Testing**
```bash
# Test MCP tool response times (should be 2-3 seconds max)
curl -X POST http://localhost:5000/api/get_user_by_email \
  -H "Content-Type: application/json" \
  -d '{"email": "user@company.com"}'
```

## 🔍 **Monitoring**

### **Key Metrics to Watch**
- **Pre-warming active:** Should always be `true` in production
- **Next refresh time:** Should always be scheduled
- **Token expiry:** Should never be expired during operation
- **Refresh success rate:** Should be near 100%

### **Health Checks**
```bash
#!/bin/bash
# prewarming_health_check.sh

echo "Checking token pre-warming health..."

# Check if pre-warming is active
STATUS=$(curl -s http://localhost:5000/api/prewarming/status)
ACTIVE=$(echo $STATUS | jq -r '.data.prewarming_active')

if [ "$ACTIVE" = "true" ]; then
    echo "✅ Pre-warming active"
    
    # Check next refresh time
    NEXT_REFRESH=$(echo $STATUS | jq -r '.data.schedule.next_refresh_in_minutes')
    if [ "$NEXT_REFRESH" != "null" ] && [ $(echo "$NEXT_REFRESH > 0" | bc) -eq 1 ]; then
        echo "✅ Next refresh scheduled in $NEXT_REFRESH minutes"
    else
        echo "❌ No refresh scheduled"
    fi
else
    echo "❌ Pre-warming not active"
fi
```

## 🔧 **Troubleshooting**

### **Pre-warming Not Starting**
**Symptoms:**
- `prewarming_active: false`
- No scheduled refresh times
- Server logs show startup errors

**Solutions:**
```bash
# Check NSP credentials
curl -X POST http://localhost:5000/api/token/refresh

# Verify environment variables
echo $NSP_BASE_URL
echo $NSP_USERNAME
# (Don't echo password)

# Check NSP connectivity
ping your-nsp-server

# Manually start pre-warming
curl -X POST http://localhost:5000/api/prewarming/start
```

### **Tokens Still Expiring**
**Symptoms:**
- Occasional 15-20 second delays
- "Token expired" messages in logs
- Pre-warming shows as active but refreshes fail

**Solutions:**
```bash
# Check refresh buffer (increase if needed)
export PREWARMING_REFRESH_BUFFER=10  # 10 minutes instead of 5

# Force immediate refresh
curl -X POST http://localhost:5000/api/prewarming/refresh

# Check NSP server time synchronization
# (Token expiry is based on NSP server time)
```

### **High Refresh Failure Rate**
**Symptoms:**
- Frequent retry messages in logs
- Inconsistent token availability
- NSP authentication errors

**Solutions:**
```bash
# Check NSP server status
curl http://your-nsp-server:1900/api/PublicApi/

# Verify credentials haven't changed
# Update local-server/.env if needed

# Check network stability
# Pre-warming requires reliable NSP connectivity
```

## 🚀 **Advanced Configuration**

### **Custom Refresh Buffer**
```python
# For high-traffic environments, increase buffer
PREWARMING_REFRESH_BUFFER=10  # 10 minutes before expiry

# For testing environments, decrease buffer
PREWARMING_REFRESH_BUFFER=2   # 2 minutes before expiry
```

### **Disable Pre-warming (Not Recommended)**
```bash
# Only disable for debugging/testing
PREWARMING_ENABLED=false
```

### **Manual Token Management**
```python
# In code, you can control pre-warming programmatically
from token_prewarming import SmartTokenWarmer

warmer = SmartTokenWarmer(nsp_client)
warmer.start_prewarming()      # Start
warmer.force_refresh()         # Manual refresh
warmer.stop_prewarming()       # Stop
```

## 🔮 **Future Enhancements**

### **Planned Features**
1. **Metrics Dashboard** - Visual monitoring of refresh cycles
2. **Adaptive Buffer** - Adjust refresh timing based on usage patterns
3. **Multi-token Support** - Handle multiple NSP environments
4. **Refresh Prediction** - Predict optimal refresh times based on usage

### **Performance Optimizations**
1. **Connection Pooling** - Reuse HTTP connections for NSP
2. **Batch Operations** - Combine token refresh with other NSP calls
3. **Predictive Refresh** - Refresh before peak usage times

## 📚 **Related Documentation**
- [CACHE_IMPLEMENTATION.md](CACHE_IMPLEMENTATION.md) - User cache system
- [NSP_API_WORKAROUNDS.md](NSP_API_WORKAROUNDS.md) - NSP timeout issues
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting

---

*Token pre-warming eliminates the primary cause of MCP timeout issues and dramatically improves user experience in both MCP Inspector and Copilot Studio.*

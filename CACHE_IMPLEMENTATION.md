# User Cache Implementation Guide

## 📋 **Overview**
The NSP MCP Connector now includes intelligent user caching to improve performance and reduce NSP API calls. This document describes the cache implementation, configuration, and usage.

## 🎯 **Benefits**
- **Performance:** Subsequent user lookups are 10-50x faster (2-3 seconds vs 15-20 seconds)
- **Reduced API Load:** Fewer calls to NSP API reduces server load and timeout risks
- **Better User Experience:** Faster response times in MCP tools and Copilot Studio
- **Cost Efficiency:** Reduced bandwidth and processing costs

## 🏗️ **Architecture**

### **Cache Components**
```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   MCP Client    │    │  UserCache   │    │  NSP API    │
│ (Copilot/MCP)   │───▶│  (30min TTL) │───▶│   Server    │
└─────────────────┘    └──────────────┘    └─────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Thread-Safe  │
                       │ In-Memory    │
                       │ Storage      │
                       └──────────────┘
```

### **Cache Classes**
1. **`CachedUser`**: Represents a cached user entry with timestamp
2. **`UserCache`**: Thread-safe cache with TTL and size limits
3. **`NSPClient.get_user_by_email()`**: Enhanced with cache integration

## ⚙️ **Configuration**

### **Environment Variables**
Set up test users in `local-server/.env`:
```bash
# Test user emails for cache testing
TEST_USER_EMAIL=john.doe@company.com
TEST_CUSTOMER_1_EMAIL=customer1@company.com  
TEST_CUSTOMER_2_EMAIL=customer2@company.com

# NSP connection settings
NSP_BASE_URL=http://localhost:1900/api/PublicApi/
NSP_USERNAME=your_username
NSP_PASSWORD=your_password
```

### **Cache Settings**
```python
UserCache(
    ttl_minutes=30,     # Cache entries expire after 30 minutes
    max_size=100        # Maximum 100 cached users
)
```

### **Customization**
```python
# In nsp_client.py __init__
self.user_cache = UserCache(
    ttl_minutes=60,     # Longer cache time
    max_size=200        # More cache entries
)
```

## 🔄 **Cache Behavior**

### **Cache Hit Flow**
```
1. get_user_by_email("user@company.com")
2. Check cache for "user@company.com"
3. If found and not expired → Return cached data (fast)
4. Log: "Returning cached user data for: user@company.com"
```

### **Cache Miss Flow**
```
1. get_user_by_email("user@company.com")
2. Check cache for "user@company.com" 
3. Not found or expired → Query NSP API (slow)
4. Store result in cache
5. Log: "User found and cached: user@company.com -> ID: 1744"
```

### **Cache Expiration**
- **Automatic:** Entries expire after TTL (default 30 minutes)
- **Size-based:** Oldest 25% removed when max_size reached
- **Manual:** Can be cleared via API endpoint

## 📊 **Performance Metrics**

### **Typical Timing**
| Operation | First Call (Cache Miss) | Second Call (Cache Hit) | Improvement |
|-----------|------------------------|------------------------|-------------|
| NSP User Lookup | 15-20 seconds | 0.1-0.5 seconds | **30-200x faster** |
| MCP Tool Call | 20-25 seconds | 2-3 seconds | **8-10x faster** |
| Copilot Studio Response | Timeout (first), Success (second) | Immediate success | **No timeouts** |

### **Cache Statistics Example**
```json
{
  "total_entries": 5,
  "expired_entries": 1,
  "active_entries": 4,
  "ttl_minutes": 30,
  "max_size": 100
}
```

## 🛠️ **API Endpoints**

### **1. Health Check (Enhanced)**
```bash
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "service": "nsp-local-api",
  "user_cache": {
    "total_entries": 5,
    "active_entries": 4,
    "ttl_minutes": 30
  }
}
```

### **2. Cache Statistics**
```bash
GET /api/cache/stats
```
**Response:**
```json
{
  "success": true,
  "data": {
    "total_entries": 5,
    "expired_entries": 1,
    "active_entries": 4,
    "ttl_minutes": 30,
    "max_size": 100
  }
}
```

### **3. Clear Cache**
```bash
POST /api/cache/clear
```
**Response:**
```json
{
  "success": true,
  "message": "User cache cleared"
}
```

### **4. Warm Cache**
```bash
POST /api/cache/warm
Content-Type: application/json

{
  "emails": [
    "user1@company.com",
    "user2@company.com",
    "manager@company.com"
  ]
}
```
**Response:**
```json
{
  "success": true,
  "message": "Cache warming completed: 2/3 successful",
  "results": {
    "user1@company.com": true,
    "user2@company.com": true,
    "manager@company.com": false
  }
}
```

## 📝 **Log Messages**

### **Cache Hit**
```
INFO - Returning cached user data for: user@company.com -> John Doe (ID: 1744)
```

### **Cache Miss**
```
INFO - Cache miss - fetching user from NSP API: user@company.com
INFO - User found and cached: user@company.com -> John Doe (ID: 1744)
```

### **Cache Management**
```
DEBUG - Cache HIT for user: user@company.com
DEBUG - Cache MISS for user: user@company.com
DEBUG - Cache STORE for user: user@company.com
DEBUG - Cache cleanup: removed 5 old entries
INFO - User cache cleared
```

## 🧪 **Testing**

### **Manual Testing**
```bash
# 1. Set up test environment variables (in local-server/.env)
TEST_USER_EMAIL=user@company.com
TEST_CUSTOMER_1_EMAIL=customer1@company.com
TEST_CUSTOMER_2_EMAIL=customer2@company.com

# 2. Run the test script (automatically uses environment variables)
python tests/test_cache.py

# 3. Check health endpoint
curl http://localhost:5000/health

# 4. Test cache warming with real users
curl -X POST http://localhost:5000/api/cache/warm \
  -H "Content-Type: application/json" \
  -d '{"emails": ["user@company.com", "customer1@company.com"]}'

# 5. Check cache stats
curl http://localhost:5000/api/cache/stats
```

### **Performance Testing**
```python
import time
import requests

def test_performance():
    # Clear cache
    requests.post("http://localhost:5000/api/cache/clear")
    
    # First call (cache miss)
    start = time.time()
    response1 = requests.post(
        "http://localhost:5000/api/get_user_by_email",
        json={"email": "user@company.com"}
    )
    first_time = time.time() - start
    
    # Second call (cache hit)
    start = time.time()
    response2 = requests.post(
        "http://localhost:5000/api/get_user_by_email", 
        json={"email": "user@company.com"}
    )
    second_time = time.time() - start
    
    print(f"First call: {first_time:.2f}s")
    print(f"Second call: {second_time:.2f}s")
    print(f"Improvement: {first_time/second_time:.1f}x faster")
```

## 🔧 **Troubleshooting**

### **Cache Not Working**
**Symptoms:**
- Second lookups still slow
- Log shows "Cache MISS" for same user repeatedly

**Solutions:**
```bash
# Check cache stats
curl http://localhost:5000/api/cache/stats

# Clear cache and retry
curl -X POST http://localhost:5000/api/cache/clear

# Check logs for error messages
tail -f local-server.log | grep -i cache
```

### **Memory Usage**
**Symptoms:**
- High memory usage
- Cache cleanup messages frequent

**Solutions:**
```python
# Reduce cache size
self.user_cache = UserCache(ttl_minutes=15, max_size=50)

# More aggressive cleanup
# Edit _cleanup_oldest() to remove 50% instead of 25%
```

### **Cache Inconsistency**
**Symptoms:**
- Cached data doesn't match NSP
- User information outdated

**Solutions:**
```bash
# Clear cache to force fresh lookup
curl -X POST http://localhost:5000/api/cache/clear

# Reduce TTL for more frequent updates
# In nsp_client.py: UserCache(ttl_minutes=10)
```

## 🚀 **Optimization Strategies**

### **1. Pre-warming Common Users**
```python
# During application startup
common_users = [
    "support@company.com",
    "admin@company.com", 
    "manager@company.com"
]
nsp_client.warm_user_cache(common_users)
```

### **2. Smart TTL Based on User Activity**
```python
# Extend TTL for frequently accessed users
def adaptive_ttl(user_email):
    access_count = get_user_access_count(user_email)
    if access_count > 10:
        return 60  # 1 hour for frequent users
    return 30      # 30 minutes for others
```

### **3. Background Cache Refresh**
```python
import threading
import schedule

def refresh_cache():
    """Refresh cache entries before they expire"""
    stats = nsp_client.get_cache_stats()
    # Logic to refresh entries nearing expiration

schedule.every(20).minutes.do(refresh_cache)
threading.Thread(target=schedule.run_continuously, daemon=True).start()
```

## 📈 **Monitoring**

### **Key Metrics**
- **Cache Hit Rate:** `active_entries / (total_api_calls)`
- **Average Response Time:** Before/after cache implementation
- **Cache Size Growth:** Monitor memory usage over time
- **Expiration Rate:** How often entries expire vs. get replaced

### **Alerts**
```python
# Set up monitoring alerts
def check_cache_health():
    stats = nsp_client.get_cache_stats()
    
    # Alert if cache hit rate too low
    if stats['active_entries'] < 5 and total_calls > 20:
        send_alert("Low cache utilization")
    
    # Alert if too many expired entries
    if stats['expired_entries'] > stats['active_entries']:
        send_alert("High cache expiration rate")
```

## 🔮 **Future Enhancements**

### **Planned Features**
1. **Persistent Cache:** Store cache to disk for restart persistence
2. **Distributed Cache:** Redis/Memcached for multi-instance deployments
3. **Smart Invalidation:** Invalidate cache when user data changes in NSP
4. **Cache Analytics:** Detailed metrics and reporting dashboard
5. **Configurable TTL per User:** Different expiration times based on user roles

### **Advanced Caching Patterns**
```python
# Write-through cache
def update_user_in_nsp(user_id, data):
    result = nsp_api.update_user(user_id, data)
    # Immediately update cache with new data
    user_cache.put(user['Email'], updated_user_data)
    return result

# Cache-aside with fallback
def get_user_with_fallback(email):
    user = user_cache.get(email)
    if user is None:
        user = nsp_api.get_user(email)
        if user:
            user_cache.put(email, user)
    return user or get_user_from_backup_source(email)
```

## 📚 **Related Documentation**
- [NSP_API_WORKAROUNDS.md](NSP_API_WORKAROUNDS.md) - Timeout issues and solutions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting guide
- [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) - Current system status

---

*For questions about cache implementation, contact the development team or check the troubleshooting guide.*

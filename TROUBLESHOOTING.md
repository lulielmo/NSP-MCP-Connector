# NSP MCP Connector - Troubleshooting Guide

## 📋 **Overview**
This guide helps you diagnose and solve common problems with NSP MCP Connector integration.

## 🔍 **Quick Diagnostics**

### **Check System Status**
1. **Azure Function Health**
   ```bash
   curl "https://func-nsp-mcp-test-002.azurewebsites.net/api/health?code=YOUR_FUNCTION_KEY"
   ```
   Expected response: `{"status": "healthy", "service": "nsp-mcp-connector-v2"}`

2. **Local Server Health**
   ```bash
   curl "http://localhost:5000/health"  # or your server URL
   ```
   Expected response: `{"status": "healthy", "environment": "test"}`

3. **Hybrid Connection Status**
   - Go to Azure Portal → Function App → Networking → Hybrid connections
   - Check that status is "Connected" with "1 listener"

## ❌ **Common Problems and Solutions**

### **1. "No tools available" in Copilot Studio**

#### **Symptoms**
- Tools section shows "No tools available"
- "RequestFailure Connector request failed" in activity chart

#### **Causes**
- Connection Reference problem between Copilot Studio and Power Platform
- Custom Connector not properly configured
- Function Key issues

#### **Solution**
```
Step 1: Remove the tool
├── Go to Copilot Studio → Tools
├── Select your MCP tool
└── Delete

Step 2: Recreate the tool
├── Add "Custom Connector"
├── Select NSP MCP Custom Connector
├── Name: "NSP MCP Server - Main endpoint for MCP communication"
├── Code: YOUR_FUNCTION_KEY_HERE
└── Save

Step 3: Verify
├── Click "retry" icon
├── Check that no error messages appear
└── Test in chat window
```

#### **Prevention**
- Use consistent Function Keys
- Avoid changing Custom Connector after Copilot Studio tools are created

### **2. First Call Timeout**

#### **Symptoms**
- First MCP call always fails
- "Tool did not respond with success" in Copilot Studio
- Azure Function logs show 15-20 seconds execution time

#### **Cause**
NSP authentication takes 15-20 seconds, MCP timeout is 10 seconds

#### **Solution**
**For Users:**
```
1. First call will fail - this is normal
2. Say "try again" or ask the same question again
3. Second call will succeed in 2-3 seconds
```

**For Developers:**
```python
# Implement pre-warming (recommended)
def keep_token_warm():
    try:
        nsp_client.get_user_by_email("system.health@example.com")
    except:
        pass
        
schedule.every(30).minutes.do(keep_token_warm)
```

#### **Example**
```
First attempt:
User: "Can you retrieve my user information?"
Copilot: "Sorry, something went wrong. Error code: SystemError."

Second attempt:
User: "Try again"
Copilot: "Here is the retrieved user information for John Doe: ..."
```

### **3. Connection Reference Error**

#### **Symptoms**
```
Error: The operation id InvokeMCP of connection reference with name 
cr967_kundservicebotten-shared_nsp-2dmcp-2dconnector-2dtest-5f92f79c817c160019-...
was not found.
```

#### **Cause**
- Corrupt connection reference
- Custom Connector not synchronized with Power Platform
- Old connections that no longer work

#### **Solution**
```
Step 1: Open Connection Manager
├── In Copilot Studio chat, click "Open connection manager"
├── Check connection status
└── Green checkmark = OK, red X = problem

Step 2: If red X, create new connection
├── Click "New connection"
├── Select NSP MCP Custom Connector
├── Enter Function Key: YOUR_FUNCTION_KEY_HERE
└── Test connection

Step 3: Update tool
├── Go to Tools section
├── Select correct connection from dropdown
└── Save
```

### **4. MCP Inspector Timeout**

#### **Symptoms**
- "MCP error -32001: Request timed out" in MCP Inspector
- Red timeout indicator

#### **Cause**
Same as Copilot Studio - NSP authentication timeout

#### **Solution**
```
1. First call will show timeout - this is expected
2. Run the same call again immediately
3. Second call will succeed quickly
```

#### **For Development**
```bash
# Keep token warm by running this regularly:
curl -X POST "http://localhost:7071/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_my_info","arguments":{"user_email":"system.health@example.com"}}}'
```

### **5. "User not found" Error**

#### **Symptoms**
- MCP call succeeds technically but returns "User not found"
- 404 from NSP API

#### **Causes**
- Wrong email address (e.g., personal gmail instead of company email)
- User doesn't exist in NSP system
- NSP API connection problem

#### **Solution**
```
1. Check email address
   ✅ Correct: user.name@company.com
   ❌ Wrong:   user.name@gmail.com

2. Verify user exists in NSP
   - Log into NSP web interface
   - Search for user manually

3. Test with known user
   - Use your own work email
   - Or a colleague you know exists in the system
```

### **6. Hybrid Connection Problem**

#### **Symptoms**
- Azure Function can reach NSP but not via Hybrid Connection
- "Connection refused" or "Host not found" errors
- Local server works directly but not via Azure

#### **Diagnostics**
```bash
# 1. Check HCM status
hcm list
hcm show --namespace relay-shared-002 --name nsp-mcp-hc-test

# 2. Check local server
curl http://localhost:5000/health

# 3. Test Azure Function locally
curl http://localhost:7071/api/health
```

#### **Solution**
```
1. Restart Hybrid Connection Manager
   sudo systemctl restart hybridconnectionmanager

2. Verify endpoint configuration
   - Azure Portal → Hybrid Connection → User Metadata
   - Should be: {"key":"endpoint","value":"servername:5000"}

3. Check DNS resolution
   ping servername  # from same machine as HCM

4. Firewall check
   sudo ufw status
   # Port 5000 should be open
```

### **7. Custom Connector Import Problem**

#### **Symptoms**
- "The property 'example' is not valid" during OpenAPI import
- "Operation can have only one body parameter"
- "Cannot have multiple operations with the same operationId"

#### **Cause**
OpenAPI 2.0 syntax issues in schema file

#### **Solution**
```yaml
# Use nsp-mcp-schema-example.yaml (cleaned version)
# Remove all 'example' fields from parameters
# Use unique operationIds for all endpoints

Correct format:
parameters:
  - name: "code"
    in: "query"
    required: true
    type: "string"
    # NO 'example' here

Wrong format:
parameters:
  - name: "code"
    in: "query"
    required: true
    type: "string"
    example: "YOUR_FUNCTION_KEY_HERE"  # ❌ Invalid in OpenAPI 2.0
```

## 🔧 **Advanced Troubleshooting**

### **Azure Function Logs**

#### **Enable Detailed Logging**
```python
# In function_app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### **Important Log Messages**
```bash
✅ Success:
"Detected Copilot Studio client, using string ID: 1"
"HTTP Request: POST http://servername:5000/api/get_user_by_email \"HTTP/1.1 200 OK\""

❌ Problems:
"Detected MCP Inspector or other client" (wrong client detection)
"HTTP Request timeout" (NSP connection problem)
"Error calling local API: Client error '404 NOT FOUND'" (user not found)
```

### **Network Diagnostics**

#### **From Azure Function**
```bash
# Test Hybrid Connection
curl http://servername:5000/health

# Test direct NSP (if available)
curl https://nsp.example.com/api/health
```

#### **From Local Server**
```bash
# Test NSP connectivity
python -c "from nsp_client import NSPClient; client = NSPClient(); print(client.authenticate())"

# Test specific endpoint
curl -X POST "http://localhost:5000/api/get_user_by_email" \
  -H "Content-Type: application/json" \
  -d '{"email": "user.name@company.com"}'
```

### **Performance Diagnostics**

#### **Timing Analysis**
```python
import time

def timed_operation(func, *args):
    start = time.time()
    result = func(*args)
    end = time.time()
    print(f"{func.__name__} took {end-start:.2f} seconds")
    return result

# Use to measure NSP operations
result = timed_operation(nsp_client.get_user_by_email, "user.name@company.com")
```

#### **Memory and CPU**
```bash
# On local server
htop  # or top
ps aux | grep python

# Azure Function metrics
# Go to Azure Portal → Function App → Monitoring → Metrics
```

## 📊 **Monitoring and Alerts**

### **Health Checks**
```bash
#!/bin/bash
# health_check.sh

echo "Checking Azure Function..."
curl -f "https://func-nsp-mcp-test-002.azurewebsites.net/api/health?code=$FUNCTION_KEY" || echo "❌ Azure Function DOWN"

echo "Checking Local Server..."
curl -f "http://localhost:5000/health" || echo "❌ Local Server DOWN"

echo "Checking Hybrid Connection..."
hcm list | grep "Connected" || echo "❌ Hybrid Connection DOWN"
```

### **Automated Testing**
```python
# test_integration.py
import requests
import json

def test_mcp_integration():
    """Test complete MCP integration chain"""
    
    # Test 1: Health check
    health = requests.get(f"{AZURE_FUNCTION_URL}/api/health?code={FUNCTION_KEY}")
    assert health.status_code == 200
    
    # Test 2: MCP tools/list
    tools_list = requests.post(
        f"{AZURE_FUNCTION_URL}/api/mcp?code={FUNCTION_KEY}",
        json={"jsonrpc": "2.0", "id": "1", "method": "tools/list", "params": {}}
    )
    assert tools_list.status_code == 200
    
    # Test 3: MCP tools/call (may timeout first time)
    tools_call = requests.post(
        f"{AZURE_FUNCTION_URL}/api/mcp?code={FUNCTION_KEY}",
        json={
            "jsonrpc": "2.0", 
            "id": "2", 
            "method": "tools/call",
            "params": {
                "name": "get_my_info",
                "arguments": {"user_email": "user.name@company.com"}
            }
        }
    )
    # First call may timeout, second should succeed
    if tools_call.status_code != 200:
        # Retry once
        tools_call = requests.post(url, json=payload)
    
    assert tools_call.status_code == 200

if __name__ == "__main__":
    test_mcp_integration()
    print("✅ All tests passed!")
```

## 📞 **Support Contact**

### **Escalation**
1. **Level 1:** Check this troubleshooting guide
2. **Level 2:** Review [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for known issues
3. **Level 3:** Contact development team with:
   - Specific error messages
   - Azure Function logs
   - Steps to reproduce the problem

### **Information to Gather**
```
Problem Description:
- What were you trying to do?
- What did you expect to happen?
- What happened instead?

Environment:
- MCP Client: (Copilot Studio / MCP Inspector)
- Azure Function: func-nsp-mcp-test-002
- Local Server: (IP/hostname)
- Timestamp: (when the problem occurred)

Error Messages:
- Azure Function logs
- MCP Client error messages  
- Network/connectivity errors

Reproduction Steps:
1. Step 1...
2. Step 2...
3. Step 3...
```

## 📅 **Update History**
- **v1.0 (2025-08-19):** Initial troubleshooting guide
- **v1.1 (2025-08-19):** Added timeout-specific solutions
- **v1.2 (2025-08-19):** Copilot Studio connection reference problems

---

*For technical documentation, see [COPILOT_STUDIO_INTEGRATION.md](COPILOT_STUDIO_INTEGRATION.md) and [MCP_CLIENT_COMPATIBILITY.md](MCP_CLIENT_COMPATIBILITY.md)*
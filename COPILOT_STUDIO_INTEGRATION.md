# Copilot Studio MCP Integration Guide

## 📋 **Overview**
This guide describes how NSP MCP Connector integrates with Microsoft Copilot Studio via Custom Connectors and Model Context Protocol (MCP).

## 🎯 **Architecture**
```
Copilot Studio Agent → Power Apps Custom Connector → Azure Function → Hybrid Connection → Local Server → NSP API
```

## ✅ **Integration Status**
- **Status:** ✅ **FULLY FUNCTIONAL** (2025-08-19)
- **Test Results:** Complete user information retrieved from NSP
- **Compatibility:** Verified with both MCP Inspector and Copilot Studio

## 🚀 **Setup Guide**

### **Step 1: Azure Function Deployment**
See [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md) for complete Azure Function setup.

Important configurations:
- **Function App:** `func-nsp-mcp-test-002`
- **Runtime:** Python 3.11, Linux
- **Plan:** Standard (S1) - required for Hybrid Connections
- **Endpoint:** `https://func-nsp-mcp-test-002.azurewebsites.net/api/mcp`

### **Step 2: Power Apps Custom Connector**
1. **Import OpenAPI Schema**
   - Use `nsp-mcp-schema-example.yaml`
   - Update host to your Azure Function URL
   - Configure authentication (API Key)

2. **Configure Endpoints**
   - `GET /mcp` - List available tools
   - `POST /mcp` - Execute MCP calls
   - `GET /health` - Health check

3. **Test Connection**
   - Create test connection with Function Key
   - Verify all endpoints work

### **Step 3: Copilot Studio Configuration**
1. **Add Custom Connector**
   - Go to your Copilot Studio project
   - Add "Custom Connector"
   - Select your NSP MCP Custom Connector

2. **Configure Tool**
   - Name: "NSP MCP Server - Main endpoint for MCP communication"
   - Code: `YOUR_FUNCTION_KEY_HERE` (your Function Key)
   - Connection: Select your Custom Connector

3. **Activate and Test**
   - Activate the tool
   - Test in chat: "Can you retrieve my user information?"

## 🔧 **Client Detection Logic**

### **Technical Implementation**
Azure Function automatically detects whether the call comes from Copilot Studio or MCP Inspector:

```python
# Primary detection based on channelId
channel_id = client_info.get("channelId", "").lower()
is_copilot = (channel_id == "pva-studio" or 
             # fallback for backward compatibility
             "copilot" in client_name or "customerservice" in client_name)

if is_copilot:
    # Copilot Studio requires string IDs
    if isinstance(request_id, int):
        request_id = str(request_id)
    logger.info(f"Detected Copilot Studio client, using string ID: {request_id}")
else:
    # MCP Inspector uses original ID type (usually integer)
    logger.info(f"Detected MCP Inspector, using original ID type: {request_id}")
```

### **Client Signatures**

#### **Copilot Studio**
   ```json
   {
  "clientInfo": {
    "agentName": "CustomerServiceBot",
    "appId": "841bf9c7-874e-4d38-a5ac-94227fb459f6",
    "channelId": "pva-studio",
    "name": "mcs",
    "version": "1.0.0"
     }
   }
   ```

#### **MCP Inspector**
```json
{
  "clientInfo": {
    "name": "mcp-inspector",
    "version": "0.16.4"
  }
}
```

### **Why channelId is Better than agentName**
- **Generic:** `channelId: "pva-studio"` is consistent regardless of agent name
- **Robust:** Users can name their agent anything
- **Future-proof:** Based on technical platform, not user choice
- **Backward Compatible:** Fallback to old methods remains

## ⚠️ **Known Issues and Solutions**

### **1. First Call Timeout**
**Problem:** NSP authentication takes 15-20 seconds, MCP timeout is 10 seconds

**Symptoms:**
- First call always fails with timeout
- Copilot Studio shows "Tool did not respond with success"

**Solution:**
- **User Experience:** Tell user to try again
- **Second calls:** Always succeed (2-3 seconds with cached token)
- **Future:** Implement pre-warming or longer timeouts

**Example:**
```
First attempt:
User: "Can you retrieve my user information?"
Copilot: "Sorry, something went wrong. Error code: SystemError."

Second attempt:
User: "Try again"
Copilot: "Here is the retrieved user information for John Doe: ..."
```

### **2. "No tools available"**
**Problem:** Copilot Studio cannot load tools from Custom Connector

**Symptoms:**
- Tools section shows "No tools available"
- "RequestFailure Connector request failed"

**Solution:**
1. Remove tool from Copilot Studio
2. Recreate tool with same configuration
3. New connection reference is created automatically

### **3. RequestFailure Messages**
**Problem:** Intermittent connection issues between Copilot Studio and Power Platform

**Symptoms:**
- "RequestFailure Connector request failed"
- No calls reach Azure Function

**Solution:**
1. Click "Open connection manager" in Copilot Studio
2. Verify connection (green checkmark should appear)
3. Click "Retry" in chat window

### **4. Connection Reference Problem**
**Problem:** Long, cryptic connection reference names can become corrupted

**Symptoms:**
```
Error: The operation id InvokeMCP of connection reference with name 
cr967_kundservicebotten-shared_nsp-2dmcp-2dconnector-2dtest-5f92f79c817c160019-...
was not found.
```

**Solution:**
- Create new connection in Copilot Studio
- Use consistent Function Key (`YOUR_FUNCTION_KEY_HERE`)

## 🧪 **Test Scenarios**

### **Scenario 1: Basic User Information**
**User Question:** "Can you retrieve my user information?"

**Expected Result:**
```
Here is the retrieved user information for John Doe:
• Full Name: John Doe
• Email Address: user.name@company.com
• Job Title: IT Strategist
• Department: IT Department
• Company: Corp
• Office Location: Springfield
• Manager: manager.name@company.com
• Last Login Time: 2025-08-08T08:48:06Z
• Is Active: True
```

### **Scenario 2: Specific Email Address**
**User Question:** "Retrieve information for user.name@company.com"

**Expected Result:** Same as above

### **Scenario 3: First Call (Timeout)**
**User Question:** "Use the get_my_info tool"

**First Response:**
```
Sorry, something went wrong. Error code: SystemError.
It seems there was an error retrieving your user information. 
Let me escalate this issue to ensure it gets resolved.
```

**Second Response (after "try again"):** Successful (see Scenario 1)

## 📊 **Performance Metrics**

### **Timing**
- **First call:** 15-25 seconds (NSP authentication)
- **Subsequent calls:** 2-5 seconds (cached token)
- **MCP handshake:** <1 second (initialize + notifications/initialized)

### **Success Rates**
- **MCP Inspector:** 100% (no timeouts)
- **Copilot Studio first call:** ~10% (timeout)
- **Copilot Studio second call:** 100% (cached auth)

## 🔍 **Debugging Guide**

### **Azure Function Logs**
What to look for:
```
✅ Success:
Client detection - channelId: 'pva-studio'
Detected Copilot Studio client, using string ID: 1

❌ Problem:
Detected MCP Inspector or other client (wrong detection)
HTTP Request timeout (NSP auth problem)
```

### **Copilot Studio Activity**
What to look for in Activity Chart:
```
✅ Success:
get_my_info with user_email parameter
Tool Result: Success

❌ Problem:
Tool did not respond with success
RequestFailure Connector request failed
```

## 🚀 **Future Improvements**

### **1. Pre-warming**
- Implement background job to keep NSP token cached
- Reduce first-call timeout issues

### **2. Longer Timeouts**
- Investigate if MCP timeout can be configured
- Alternative: Asynchronous processing with polling

### **3. More Tools**
- `get_my_tickets` - Retrieve user's tickets
- `create_ticket` - Create new ticket
- `search_users` - Search for users

### **4. Error Handling**
- Better error messages for end users
- Automatic retry logic
- Graceful degradation on NSP issues

## 📅 **Version History**
- **v1.0 (2025-08-11):** Power Apps Custom Connector integration
- **v1.5 (2025-08-18):** MCP Inspector compatibility
- **v2.0 (2025-08-19):** Copilot Studio integration complete
- **v2.1 (2025-08-19):** Improved client detection with channelId

## 🤝 **Support**
For questions or issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or contact the development team.
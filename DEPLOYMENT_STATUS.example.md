# NSP MCP Connector - Deployment Status Template

## 📋 **Overview**
This document describes the current deployment status for NSP MCP Connector.

## 🎯 **Architecture**
```
Copilot Studio → Azure Function → Hybrid Connection → Local Server → NSP API
```

## 🏗️ **Azure Resources**

### **Resource Group**
- **Name:** `rg_nsp-mcp_{environment}_{sequence}`
- **Location:** Sweden Central
- **Subscription:** [SUBSCRIPTION_ID]

### **Storage Account**
- **Name:** `stnspmcp{environment}{sequence}`
- **Type:** Standard LRS
- **Location:** Sweden Central

### **App Service Plan**
- **Name:** `asp-nsp-mcp-{environment}-{sequence}`
- **SKU:** S1 (Standard)
- **OS:** Linux
- **Location:** Sweden Central

### **Function App**
- **Name:** `func-nsp-mcp-{environment}-{sequence}`
- **Runtime:** Python 3.11
- **OS:** Linux
- **Plan:** Standard (S1)
- **URL:** https://func-nsp-mcp-{environment}-{sequence}.azurewebsites.net

### **Hybrid Connection**
- **Namespace:** `relay-shared-{sequence}`
- **Name:** `nsp-mcp-hc-{environment}`
- **Resource Group:** `rg_nsp-mcp_{environment}_{sequence}`
- **Location:** Sweden Central
- **User Metadata:** `[{"key":"endpoint","value":"HOSTNAME:PORT"}]`
- **Status:** [Connected/Disconnected]

## 🔑 **Function Keys**

### **Health Endpoint**
- **URL:** https://func-nsp-mcp-{environment}-{sequence}.azurewebsites.net/api/health
- **Key:** [FUNCTION_KEY]
- **Full URL:** https://func-nsp-mcp-{environment}-{sequence}.azurewebsites.net/api/health?code=[FUNCTION_KEY]

### **MCP Endpoint**
- **URL:** https://func-nsp-mcp-{environment}-{sequence}.azurewebsites.net/api/mcp
- **Key:** [FUNCTION_KEY]
- **Full URL:** https://func-nsp-mcp-{environment}-{sequence}.azurewebsites.net/api/mcp?code=[FUNCTION_KEY]

## ⚙️ **Azure Function App Settings**

```json
{
  "LOCAL_API_BASE": "http://HOSTNAME:PORT"
}
```

## 🖥️ **Local Environment**

### **Local Server**
- **Status:** [Running/Stopped]
- **Port:** [PORT]
- **URL:** http://127.0.0.1:[PORT]
- **Network URL:** http://[IP]:[PORT]
- **Hostname:** [HOSTNAME]

### **Hybrid Connection Manager**
- **Status:** [Connected/Disconnected]
- **Listeners:** [NUMBER]
- **Installation:** [PATH]
- **Connection String:** [CONNECTION_STRING]

## 🧪 **Test Status**

### **✅ Working**
- [List working components]

### **❌ Issues**
- [List issues]

## 🔧 **Solutions**

### **Problem:**
[Problem description]

### **Solution:**
[Solution steps]

## 📝 **Recovery Commands**

### **Start Local Server**
```bash
cd local-server
python app.py
```

### **Start Hybrid Connection Manager**
```bash
[COMMAND_TO_START_HCM]
```

### **Check Hybrid Connection Status**
```bash
[COMMAND_TO_CHECK_STATUS]
```

### **Test Azure Function**
```bash
# Health endpoint
[HEALTH_TEST_COMMAND]

# MCP endpoint
[MCP_TEST_COMMAND]
```

## 📅 **Updated**
- **Date:** [YYYY-MM-DD]
- **Status:** [STATUS]
- **Version:** [VERSION]

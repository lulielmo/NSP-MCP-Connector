# Deployment Guide - NSP MCP Connector

This guide describes how to deploy the NSP MCP Connector with hybrid hosting.

## Architecture

```
Copilot Studio → Azure Function (MCP) → Hybrid Connection → On-premise (REST) → NSP API
```

## Prerequisites

- Azure subscription with access to Azure Functions
- Hybrid Connection Relay configured
- NSP instance available
- Python 3.9+ installed locally
- Azure Functions Core Tools installed

## Step 1: Configure Local REST API Server

### 1.1 Install dependencies
```bash
cd NSP-MCP-Connector/local-server
pip install -r requirements.txt
```

### 1.2 Configure environment variables
```bash
# Copy example file
cp env.example .env

# Edit .env with your NSP settings
NSP_BASE_URL=https://your-nsp-server:1901/api/
NSP_USERNAME=your_username
NSP_PASSWORD=your_password
```

### 1.3 Test local server
```bash
# Start the server
python app.py

# In another terminal, run tests
python ../test_local_server.py
```

### 1.4 Deploy as Docker container (optional)
```bash
# Build Docker image
docker build -t nsp-local-api .

# Run container
docker run -d \
  --name nsp-local-api \
  -p 5000:5000 \
  --env-file .env \
  nsp-local-api
```

## Step 2: Configure Azure Function

### 2.1 Install Azure Functions Core Tools
```bash
npm install -g azure-functions-core-tools@4 --unsafe-perm true
```

### 2.2 Configure local development
```bash
cd NSP-MCP-Connector/azure-function

# Copy settings
cp local.settings.json.example local.settings.json

# Edit local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "HYBRID_CONNECTION_ENDPOINT": "http://your-hybrid-connection-endpoint:5000",
    "HYBRID_CONNECTION_KEY": "your-hybrid-connection-key"
  }
}
```

### 2.3 Test locally
```bash
# Start Azure Function locally
func start

# Test health check
curl http://localhost:7071/api/health
```

## Step 3: Configure Hybrid Connection

### 3.1 Create Hybrid Connection in Azure
1. Go to Azure Portal
2. Create an App Service Plan
3. Create a Web App
4. Under "Networking" → "Hybrid connections"
5. Add new hybrid connection
6. Note endpoint and key

### 3.2 Configure local Hybrid Connection Manager
1. Download Hybrid Connection Manager
2. Install on local server
3. Configure with endpoint and key from Azure
4. Start Hybrid Connection Manager

## Step 4: Deploy Azure Function

### 4.1 Create Function App in Azure
```bash
# Login to Azure
az login

# Create resource group
az group create --name nsp-mcp-rg --location westeurope

# Create storage account
az storage account create \
  --name nspmcpsa \
  --resource-group nsp-mcp-rg \
  --location westeurope \
  --sku Standard_LRS

# Create Function App
az functionapp create \
  --name nsp-mcp-function \
  --resource-group nsp-mcp-rg \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.9 \
  --functions-version 4 \
  --storage-account nspmcpsa
```

### 4.2 Configure app settings
```bash
# Set environment variables
az functionapp config appsettings set \
  --name nsp-mcp-function \
  --resource-group nsp-mcp-rg \
  --settings \
    HYBRID_CONNECTION_ENDPOINT="http://your-hybrid-connection-endpoint:5000" \
    HYBRID_CONNECTION_KEY="your-hybrid-connection-key"
```

### 4.3 Deploy code
```bash
# From azure-function folder
func azure functionapp publish nsp-mcp-function
```

## Step 5: Configure Copilot Studio

### 5.1 Create MCP Server configuration
In Copilot Studio, add MCP server:

```json
{
  "mcpServers": {
    "nsp-connector": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://nsp-mcp-function.azurewebsites.net/api/mcp",
        "-H", "Content-Type: application/json",
        "-d", "{\"method\": \"tools/list\"}"
      ]
    }
  }
}
```

### 5.2 Test connection
1. Open Copilot Studio
2. Test calling NSP functions
3. Verify that data is retrieved correctly

## Step 6: Monitoring and Logging

### 6.1 Azure Application Insights
```bash
# Create Application Insights
az monitor app-insights component create \
  --app nsp-mcp-insights \
  --location westeurope \
  --resource-group nsp-mcp-rg

# Configure connection string
az functionapp config appsettings set \
  --name nsp-mcp-function \
  --resource-group nsp-mcp-rg \
  --settings \
    APPLICATIONINSIGHTS_CONNECTION_STRING="your-connection-string"
```

### 6.2 Logging
- Azure Function logs in Application Insights
- Local server logs in stdout/stderr
- Hybrid Connection logs in Azure Portal

## Troubleshooting

### Common issues

1. **Authentication fails**
   - Check NSP username/password
   - Verify NSP URL
   - Check network access

2. **Hybrid Connection doesn't work**
   - Verify endpoint and key
   - Check that Hybrid Connection Manager is running
   - Test network connectivity

3. **Azure Function can't reach local server**
   - Check Hybrid Connection configuration
   - Verify local server is running on correct port
   - Test with curl from Azure Function

### Test commands

```bash
# Test local server
curl http://localhost:5000/health

# Test Azure Function
curl https://nsp-mcp-function.azurewebsites.net/api/health

# Test MCP call
curl -X POST https://nsp-mcp-function.azurewebsites.net/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## Security

### Recommendations
- Use Azure Key Vault for sensitive data
- Enable Azure AD authentication
- Configure IP restrictions
- Use HTTPS for all communication
- Rotate credentials regularly

### Network security
- Hybrid Connection encrypts traffic automatically
- Local server exposed only via Hybrid Connection
- No direct internet connections to local server 
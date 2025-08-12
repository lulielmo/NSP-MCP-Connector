# Copilot Studio Integration Guide

## Overview

This guide provides step-by-step instructions for integrating the NSP MCP Connector with Microsoft Copilot Studio using Power Apps Custom Connectors.

## Prerequisites

- ✅ Azure Function deployed and working
- ✅ Hybrid Connection established and tested
- ✅ Local server running and accessible
- ✅ NSP API credentials configured
- ✅ Access to Microsoft Power Apps and Copilot Studio

## Step 1: Power Apps Custom Connector Setup

### 1.1 Create Custom Connector

1. **Navigate to Power Apps**
   - Go to [make.powerapps.com](https://make.powerapps.com)
   - Select your environment

2. **Create New Connector**
   - Click **"Data"** → **"Custom Connectors"**
   - Click **"+ New custom connector"**
   - Select **"Import an OpenAPI file"**

3. **Import Schema**
   - Upload `nsp-mcp-schema-example.yaml`
   - Review and confirm the import

### 1.2 Configure Connector

1. **General Settings**
   - **Name**: `NSP-MCP-Connector`
   - **Description**: `MCP Server for NSP IT support system`
   - **Icon**: Choose appropriate icon

2. **Security Settings**
   - **Authentication**: `API Key`
   - **Parameter name**: `code`
   - **Parameter location**: `Query`

3. **Definition**
   - Verify all endpoints are correctly mapped
   - Ensure operation IDs are unique
   - Check that schemas are properly defined

## Step 2: Test Custom Connector

### 2.1 Create Connection

1. **Go to Test Tab**
   - Click **"5. Test"** in the connector setup
   - Click **"+ New connection"**

2. **Configure Connection**
   - **Connection Name**: `NSP-MCP-[TEST/PROD]` (e.g., `NSP-MCP-TEST` for test environment)
   - **Function Key**: Use your Azure Function key
   - Click **"Create"**

### 2.2 Test Operations

1. **Test GetInvokeMCP**
   - Select **GetInvokeMCP** operation
   - Use your connection
   - Click **"Test operation"**
   - Expected: 200 OK with list of MCP tools

2. **Test InvokeMCP**
   - Select **InvokeMCP** operation
   - Use your connection
   - Enable **"Raw body"**
   - Test with:
   ```json
   {
     "method": "tools/call",
     "params": {
       "name": "get_my_info",
       "arguments": {
         "user_email": "test@example.com"
       }
     }
   }
   ```

3. **Test HealthCheck**
   - Select **HealthCheck** operation
   - Use your connection
   - Click **"Test operation"**
   - Expected: 200 OK with health status

## Step 3: Copilot Studio Integration

### 3.1 Add to Agent

1. **Navigate to Copilot Studio**
   - Go to [copilot.microsoft.com](https://copilot.microsoft.com)
   - Select your agent or create new one

2. **Add Custom Connector**
   - Go to **"Tools"** section
   - Click **"Add tools"**
   - Select **"Import from Power Apps"**
   - Choose your NSP-MCP-Connector

### 3.2 Configure Agent

1. **Set Up Prompts**
   - Configure system prompts to explain NSP capabilities
   - Add examples of how to use the connector
   - Set appropriate conversation starters

2. **Test Integration**
   - Ask agent to list available tools
   - Request ticket information
   - Test role-based access

## Step 4: User Experience Configuration

### 4.1 Conversation Starters

Add these conversation starters to your agent:

- **"Visa mina öppna ärenden"** - Shows user's open tickets
- **"Visa alla pågående tickets"** - Shows in-progress tickets
- **"Skapa nytt ärende"** - Helps create new ticket
- **"Sök bland ärenden"** - Advanced ticket search

### 4.2 System Prompts

Configure your agent with this system prompt:

```
You are an IT support assistant integrated with the NSP system. You can:

- Show users their tickets (as customer or agent)
- Display open/closed tickets
- Search tickets by status, type, or other criteria
- Create new tickets
- Provide ticket information

Always ask for user email when needed and explain what information you're showing.
Use appropriate role context (customer vs agent) based on the user's request.
```

## Step 5: Testing and Validation

### 5.1 Functional Testing

1. **Basic Operations**
   - List available tools
   - Get user information
   - Retrieve tickets

2. **Role-based Testing**
   - Test customer role access
   - Test agent role access
   - Verify permissions

3. **Error Handling**
   - Test with invalid email
   - Test with expired tokens
   - Verify error messages

### 5.2 User Experience Testing

1. **Natural Language**
   - Test conversational queries
   - Verify context understanding
   - Check response clarity

2. **Integration Flow**
   - End-to-end ticket retrieval
   - Multi-step operations
   - Context preservation

## Troubleshooting

### Common Issues

1. **Authentication Errors (401)**
   - Check Function Key in connection
   - Verify Azure Function is running
   - Check Hybrid Connection status

2. **Tool Discovery Issues**
   - Verify GetInvokeMCP works in Power Apps
   - Check Azure Function logs
   - Ensure `/tools/list` endpoint is accessible

3. **MCP Call Failures**
   - Verify InvokeMCP works in Power Apps
   - Check request format
   - Review Azure Function logs

### Debug Commands

Test endpoints directly:

```bash
# Test health endpoint
curl "https://your-function.azurewebsites.net/api/health?code=YOUR_KEY"

# Test tools list
curl "https://your-function.azurewebsites.net/api/tools/list?code=YOUR_KEY"

# Test MCP call
curl -X POST "https://your-function.azurewebsites.net/api/mcp?code=YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/list"}'
```

## Best Practices

### 1. **Security**
- Use dedicated Function Keys for production
- Regularly rotate credentials
- Monitor access logs

### 2. **Performance**
- Implement caching for user context
- Use pagination for large result sets
- Monitor response times

### 3. **User Experience**
- Provide clear error messages
- Use consistent terminology
- Offer helpful suggestions

### 4. **Monitoring**
- Set up Azure Application Insights
- Monitor Hybrid Connection status
- Track usage patterns

## Next Steps

After successful integration:

1. **User Training**
   - Create user guides
   - Provide examples
   - Offer support

2. **Advanced Features**
   - Implement ticket updates
   - Add comment functionality
   - Enable file attachments

3. **Analytics**
   - Track usage metrics
   - Monitor performance
   - Gather user feedback

## Support

For issues or questions:

1. **Check Azure Function logs**
2. **Verify Hybrid Connection status**
3. **Test endpoints directly**
4. **Review this documentation**
5. **Create GitHub issue** for bugs

---

**Note**: This integration enables AI-powered IT support through natural language conversations, making NSP more accessible and user-friendly.

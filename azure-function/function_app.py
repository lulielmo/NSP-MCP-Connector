"""
Azure Function MCP Server using MCP Python SDK
Test implementation with single tool
"""

import azure.functions as func
import logging
import json
import os
import httpx
import asyncio
from typing import Dict, Any, List
#from mcp import Server
from mcp.server.lowlevel import Server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
LOCAL_API_BASE = os.environ.get('LOCAL_API_BASE', 'http://localhost:5000')

# Create Azure Function app
app = func.FunctionApp()

# MCP Tool definition
MCP_TOOLS = [
    Tool(
        name="get_my_info",
        description="Get current user information and permissions",
        inputSchema={
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                }
            },
            "required": ["user_email"]
        }
    )
]

class NSPMCPConnector:
    """Simple MCP Connector for NSP"""
    
    def __init__(self):
        self.local_api_base = LOCAL_API_BASE.rstrip('/')
    
    async def _call_local_api(self, endpoint: str, method: str = 'POST', data: Dict = None) -> Dict[str, Any]:
        """Call local REST API"""
        url = f"{self.local_api_base}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == 'GET':
                    response = await client.get(url)
                else:
                    response = await client.post(url, json=data)
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error calling local API: {str(e)}")
            raise
    
    async def get_user_by_email(self, user_email: str) -> Dict[str, Any]:
        """Get user information by email address"""
        data = {"email": user_email}
        try:
            result = await self._call_local_api('/api/get_user_by_email', data=data)
            if result and result.get('success') and result.get('data'):
                return result['data']
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return None
        except Exception as e:
            logger.error(f"Error calling local API for user {user_email}: {str(e)}")
            return None

# Global MCP connector instance
nsp_connector = NSPMCPConnector()

@app.route(route="mcp", auth_level=func.AuthLevel.FUNCTION)
async def nsp_mcp_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Main handler for MCP calls using MCP Python SDK"""
    
    try:
        logger.info(f"MCP call received: {req.method} {req.url}")
        
        # Handle GET requests (list tools)
        if req.method == "GET":
            logger.info("GET request to /mcp - returning list of tools")
            return func.HttpResponse(
                json.dumps({
                    "tools": [tool.name for tool in MCP_TOOLS],
                    "result": [{"name": tool.name, "description": tool.description} for tool in MCP_TOOLS]
                }),
                mimetype="application/json"
            )
        
        # Handle POST requests (MCP calls)
        elif req.method == "POST":
            request_data = req.get_json()
            
            # Debug logging to see what Copilot Studio sends
            logger.info(f"Request body received: {json.dumps(request_data, indent=2) if request_data else 'None'}")
            
            if not request_data:
                logger.error("No request data received from Copilot Studio")
                return func.HttpResponse(
                    json.dumps({"error": "No request data"}),
                    status_code=400,
                    mimetype="application/json"
                )
            
            method = request_data.get("method")
            params = request_data.get("params", {})
            
            # Debug logging for method and params
            logger.info(f"Method: '{method}' (type: {type(method)}, length: {len(method) if method else 0}), Params: {json.dumps(params, indent=2) if params else 'None'}")
            
            if method == "initialize":
                # MCP initialization request - handle ID type based on caller
                request_id = request_data.get("id", "1")
                
                # Detect caller type based on clientInfo or user-agent
                client_info = params.get("clientInfo", {})
                client_name = client_info.get("name", "").lower()
                agent_name = client_info.get("agentName", "").lower()
                channel_id = client_info.get("channelId", "").lower()
                logger.info(f"Client detection - clientInfo: {client_info}, client_name: '{client_name}', agent_name: '{agent_name}', channel_id: '{channel_id}'")
                
                # Copilot Studio needs string IDs, MCP Inspector needs original type
                # Use channelId as primary detection method (more reliable than agent names)
                is_copilot = (channel_id == "pva-studio" or 
                             "copilot" in client_name or "customerservice" in client_name or "customerservicebot" in client_name or
                             "copilot" in agent_name or "customerservice" in agent_name or "customerservicebot" in agent_name)
                
                if is_copilot:
                    # Copilot Studio - convert to string
                    if isinstance(request_id, int):
                        request_id = str(request_id)
                    logger.info(f"Detected Copilot Studio client, using string ID: {request_id}")
                else:
                    # MCP Inspector or other - keep original type
                    logger.info(f"Detected MCP Inspector or other client, using original ID type: {request_id} ({type(request_id)})")
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "experimental": {}
                        },
                        "serverInfo": {
                            "name": "nsp-mcp-connector",
                            "version": "1.0.0"
                        },
                        # Include tools directly in initialize response
                        "tools": [{"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema} for tool in MCP_TOOLS]
                    }
                }
                return func.HttpResponse(
                    json.dumps(response),
                    mimetype="application/json"
                )
            
            elif method and method.startswith("notifications/"):
                # MCP notifications (including notifications/initialized)
                logger.info(f"Received MCP notification: {method}")
                # Notifications don't expect a JSON-RPC response, just HTTP 200
                return func.HttpResponse(
                    "",  # Empty response for notifications
                    status_code=200,
                    mimetype="text/plain"
                )
            
            elif method == "tools/list":
                # Get request ID and handle type based on caller
                request_id = request_data.get("id", "1")
                
                # Detect caller type - check if we have clientInfo from earlier
                # For tools/list, we don't get clientInfo, so we use a heuristic:
                # MCP Inspector typically uses integer IDs, Copilot Studio uses strings
                # Keep original type for MCP Inspector compatibility
                if isinstance(request_id, int):
                    # This is likely MCP Inspector - keep as integer
                    logger.info(f"tools/list with integer ID {request_id} - keeping as integer (likely MCP Inspector)")
                else:
                    # This is likely Copilot Studio or already a string
                    logger.info(f"tools/list with string ID {request_id} - keeping as string (likely Copilot Studio)")
                    if isinstance(request_id, int):
                        request_id = str(request_id)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [{"name": tool.name, "description": tool.description, "inputSchema": tool.inputSchema} for tool in MCP_TOOLS]
                    }
                }
                return func.HttpResponse(
                    json.dumps(response),
                    mimetype="application/json"
                )
            
            elif method == "tools/call":
                # Get request ID and handle type based on caller
                request_id = request_data.get("id", "1")
                
                # Same heuristic as tools/list - keep integer IDs as integers for MCP Inspector
                if isinstance(request_id, int):
                    logger.info(f"tools/call with integer ID {request_id} - keeping as integer (likely MCP Inspector)")
                else:
                    logger.info(f"tools/call with string ID {request_id} - keeping as string (likely Copilot Studio)")
                    if isinstance(request_id, int):
                        request_id = str(request_id)
                
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": "Tool name missing"}
                    }
                    return func.HttpResponse(
                        json.dumps(error_response),
                        status_code=400,
                        mimetype="application/json"
                    )
                
                if tool_name == "get_my_info":
                    user_email = arguments.get("user_email")
                    if not user_email:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32602, "message": "user_email required"}
                        }
                        return func.HttpResponse(
                            json.dumps(error_response),
                            status_code=400,
                            mimetype="application/json"
                        )
                    
                    result = await nsp_connector.get_user_by_email(user_email)
                    if result:
                        success_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [
                                    {
                                        "type": "text",
                                        "text": f"User information retrieved: {json.dumps(result, indent=2)}"
                                    }
                                ]
                            }
                        }
                        return func.HttpResponse(
                            json.dumps(success_response),
                            mimetype="application/json"
                        )
                    else:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32603, "message": "User not found"}
                        }
                        return func.HttpResponse(
                            json.dumps(error_response),
                            status_code=404,
                            mimetype="application/json"
                        )
                else:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    }
                    return func.HttpResponse(
                        json.dumps(error_response),
                        status_code=400,
                        mimetype="application/json"
                    )
            
            else:
                logger.error(f"Unknown method received: {method}")
            return func.HttpResponse(
                    json.dumps({"error": f"Unknown method: {method}"}),
                    status_code=400,
                mimetype="application/json"
            )
        
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Method {req.method} not allowed"}),
                status_code=405,
                mimetype="application/json"
            )
    
    except Exception as e:
        logger.error(f"Error in MCP handling: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

@app.route(route="health", auth_level=func.AuthLevel.FUNCTION)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "nsp-mcp-connector-v2",
            "local_api_base": LOCAL_API_BASE
        }),
        mimetype="application/json"
    ) 

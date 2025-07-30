"""
Azure Function MCP Server for NSP Connector
Exposes NSP functions via MCP for Copilot Studio
"""

import azure.functions as func
import logging
import json
import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Hybrid Connection configuration
HYBRID_CONNECTION_ENDPOINT = os.environ.get('HYBRID_CONNECTION_ENDPOINT', 'http://localhost:5000')

class NSPMCPConnector:
    """MCP Connector for NSP that communicates with local REST API"""
    
    def __init__(self):
        self.local_api_base = HYBRID_CONNECTION_ENDPOINT.rstrip('/')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _call_local_api(self, endpoint: str, method: str = 'POST', data: Dict = None) -> Dict[str, Any]:
        """Call local REST API via Hybrid Connection"""
        url = f"{self.local_api_base}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == 'GET':
                    response = await client.get(url)
                else:
                    response = await client.post(url, json=data or {})
                
                response.raise_for_status()
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"Error calling local API: {str(e)}")
            raise
    
    async def get_tickets(self, page: int = 1, page_size: int = 15, filters: Dict = None) -> Dict[str, Any]:
        """Get tickets from NSP"""
        data = {
            "page": page,
            "page_size": page_size
        }
        if filters:
            data["filters"] = filters
        
        return await self._call_local_api('/api/get_tickets', data=data)
    
    async def get_ticket_by_id(self, ticket_id: int) -> Dict[str, Any]:
        """Get specific ticket"""
        return await self._call_local_api(f'/api/get_ticket/{ticket_id}', method='GET')
    
    async def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new ticket"""
        return await self._call_local_api('/api/create_ticket', data=ticket_data)
    
    async def update_ticket(self, ticket_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update ticket"""
        return await self._call_local_api(f'/api/update_ticket/{ticket_id}', method='PUT', data=updates)
    
    async def search_entities(self, entity_type: str, query: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Search among entities"""
        data = {
            "entity_type": entity_type,
            "query": query,
            "page": page,
            "page_size": page_size
        }
        return await self._call_local_api('/api/search_entities', data=data)
    
    async def get_entity_types(self) -> Dict[str, Any]:
        """Get entity types"""
        return await self._call_local_api('/api/get_entity_types', method='GET')
    
    async def get_entity_metadata(self, entity_type: str) -> Dict[str, Any]:
        """Get metadata for entity type"""
        return await self._call_local_api(f'/api/get_entity_metadata/{entity_type}', method='GET')
    
    async def get_attachments(self, entity_type: str, entity_id: int) -> Dict[str, Any]:
        """Get attachments"""
        return await self._call_local_api(f'/api/get_attachments/{entity_type}/{entity_id}', method='GET')

# Global MCP connector instance
nsp_connector = NSPMCPConnector()

# MCP Tool definitions
MCP_TOOLS = [
    {
        "name": "get_tickets",
        "description": "Get tickets from NSP with pagination and filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page to fetch (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer", 
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                },
                "filters": {
                    "type": "object",
                    "description": "Filter criteria for tickets"
                }
            }
        }
    },
    {
        "name": "get_ticket_by_id",
        "description": "Get specific ticket by ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket to fetch"
                }
            },
            "required": ["ticket_id"]
        }
    },
    {
        "name": "create_ticket",
        "description": "Create new ticket in NSP",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the ticket"
                },
                "description": {
                    "type": "string", 
                    "description": "Description of the ticket"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority (Low, Medium, High, Critical)"
                },
                "category": {
                    "type": "string",
                    "description": "Category of the ticket"
                }
            },
            "required": ["title", "description"]
        }
    },
    {
        "name": "update_ticket",
        "description": "Update existing ticket",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "integer",
                    "description": "ID of the ticket to update"
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update"
                }
            },
            "required": ["ticket_id", "updates"]
        }
    },
    {
        "name": "search_entities",
        "description": "Search among entities in NSP",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Type of entity to search in (default: Ticket)",
                    "default": "Ticket"
                },
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "page": {
                    "type": "integer",
                    "description": "Page to fetch (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of results per page (default: 15)",
                    "default": 15
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_entity_types",
        "description": "Get available entity types from NSP",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_entity_metadata",
        "description": "Get metadata for specific entity type",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Entity type to get metadata for"
                }
            },
            "required": ["entity_type"]
        }
    },
    {
        "name": "get_attachments",
        "description": "Get attachments for specific entity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Type of entity"
                },
                "entity_id": {
                    "type": "integer",
                    "description": "ID of the entity"
                }
            },
            "required": ["entity_type", "entity_id"]
        }
    }
]

@app.route(route="mcp")
async def nsp_mcp_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Main handler for MCP calls from Copilot Studio"""
    
    try:
        # Log incoming call
        logger.info(f"MCP call received: {req.method} {req.url}")
        
        # Get request body
        request_data = req.get_json()
        
        if not request_data:
            return func.HttpResponse(
                json.dumps({"error": "No request data"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Handle different MCP operations
        method = request_data.get("method")
        params = request_data.get("params", {})
        
        if method == "tools/list":
            # Return list of available tools
            return func.HttpResponse(
                json.dumps({"result": MCP_TOOLS}),
                mimetype="application/json"
            )
        
        elif method == "tools/call":
            # Handle call to specific tool
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                return func.HttpResponse(
                    json.dumps({"error": "Tool name missing"}),
                    status_code=400,
                    mimetype="application/json"
                )
            
            # Call appropriate method based on tool name
            result = await call_tool(tool_name, arguments)
            
            return func.HttpResponse(
                json.dumps({"result": result}),
                mimetype="application/json"
            )
        
        else:
            return func.HttpResponse(
                json.dumps({"error": f"Unknown method: {method}"}),
                status_code=400,
                mimetype="application/json"
            )
    
    except Exception as e:
        logger.error(f"Error in MCP handling: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Call specific tool and return result"""
    
    try:
        if tool_name == "get_tickets":
            result = await nsp_connector.get_tickets(
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15),
                filters=arguments.get("filters")
            )
        
        elif tool_name == "get_ticket_by_id":
            result = await nsp_connector.get_ticket_by_id(
                ticket_id=arguments["ticket_id"]
            )
        
        elif tool_name == "create_ticket":
            result = await nsp_connector.create_ticket(
                ticket_data=arguments
            )
        
        elif tool_name == "update_ticket":
            result = await nsp_connector.update_ticket(
                ticket_id=arguments["ticket_id"],
                updates=arguments["updates"]
            )
        
        elif tool_name == "search_entities":
            result = await nsp_connector.search_entities(
                entity_type=arguments.get("entity_type", "Ticket"),
                query=arguments["query"],
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "get_entity_types":
            result = await nsp_connector.get_entity_types()
        
        elif tool_name == "get_entity_metadata":
            result = await nsp_connector.get_entity_metadata(
                entity_type=arguments["entity_type"]
            )
        
        elif tool_name == "get_attachments":
            result = await nsp_connector.get_attachments(
                entity_type=arguments["entity_type"],
                entity_id=arguments["entity_id"]
            )
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Format result for MCP
        if result.get("success"):
            return [{
                "type": "text",
                "text": json.dumps(result.get("data", result), indent=2, ensure_ascii=False)
            }]
        else:
            return [{
                "type": "text", 
                "text": f"Error: {result.get('error', 'Unknown error')}"
            }]
    
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {str(e)}")
        return [{
            "type": "text",
            "text": f"Error calling {tool_name}: {str(e)}"
        }]

@app.route(route="health")
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "nsp-mcp-connector",
            "hybrid_connection_endpoint": HYBRID_CONNECTION_ENDPOINT
        }),
        mimetype="application/json"
    ) 
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

# Add user context management
from collections import defaultdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API configuration
LOCAL_API_BASE = os.environ.get('LOCAL_API_BASE', 'http://localhost:5000')

# User context cache for session management
USER_CONTEXT_CACHE = {}
CACHE_EXPIRY_HOURS = 24  # Cache user context for 24 hours

class UserContext:
    """Represents user context with permissions and data"""
    def __init__(self, user_data: Dict[str, Any]):
        self.user_id = user_data.get('Id')
        self.user_type = user_data.get('UserTypeId')  # 'Agent' or 'End User'
        self.display_name = user_data.get('DisplayName')
        self.first_name = user_data.get('FirstName')
        self.email = user_data.get('Email')
        self.is_active = user_data.get('IsActive', False)
        self.department = user_data.get('Department')
        self.job_title = user_data.get('JobTitle')
        self.cached_at = time.time()
    
    def is_cache_valid(self) -> bool:
        """Check if user context cache is still valid"""
        return (time.time() - self.cached_at) < (CACHE_EXPIRY_HOURS * 3600)
    
    def is_agent(self) -> bool:
        """Check if user is an agent"""
        return self.user_type and 'Agent' in str(self.user_type)
    
    def is_customer(self) -> bool:
        """Check if user is a customer/end user"""
        return self.user_type and 'End User' in str(self.user_type)
    
    def can_list_own_tickets(self) -> bool:
        """Check if user can list their own tickets"""
        return self.is_active and (self.is_agent() or self.is_customer())
    
    def can_list_assigned_tickets(self) -> bool:
        """Check if user can list tickets assigned to them (agents only)"""
        return self.is_active and self.is_agent()
    
    def can_create_tickets(self) -> bool:
        """Check if user can create tickets"""
        return self.is_active and (self.is_agent() or self.is_customer())
    
    def can_update_tickets(self) -> bool:
        """Check if user can update tickets"""
        return self.is_active and self.is_agent()
    
    def get_personalized_greeting(self) -> str:
        """Get a personalized greeting for the user"""
        name = self.first_name or self.display_name or "Användare"
        role = "agent" if self.is_agent() else "kund"
        return f"Hej {name}! Du är inloggad som {role}."

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
    ),
    Tool(
        name="get_my_tickets",
        description="Get tickets based on user role - assigned tickets for agents, own tickets for customers",
        inputSchema={
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'agent' or 'customer'",
                    "enum": ["agent", "customer"]
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page",
                    "default": 15
                }
            },
            "required": ["user_email", "role"]
        }
    ),
    Tool(
        name="get_tickets_by_status",
        description="Get tickets filtered by status with role-based access control",
        inputSchema={
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'agent' or 'customer'",
                    "enum": ["agent", "customer"]
                },
                "status": {
                    "type": "string",
                    "description": "Ticket status to filter by (e.g., 'Registered', 'In progress', 'Resolved', 'Closed')"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page",
                    "default": 15
                }
            },
            "required": ["user_email", "role", "status"]
        }
    ),
    Tool(
        name="get_tickets_by_type",
        description="Get tickets filtered by type with role-based access control",
        inputSchema={
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'agent' or 'customer'",
                    "enum": ["agent", "customer"]
                },
                "ticket_type": {
                    "type": "string",
                    "description": "Ticket type to filter by (e.g., 'IT Request', 'Incident Management', 'ServiceOrderRequest')"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page",
                    "default": 15
                }
            },
            "required": ["user_email", "role", "ticket_type"]
        }
    ),
    Tool(
        name="search_my_tickets",
        description="Advanced search for tickets with combined filtering by role, type, and status",
        inputSchema={
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'agent' or 'customer'",
                    "enum": ["agent", "customer"]
                },
                "ticket_type": {
                    "type": "string",
                    "description": "Ticket type to filter by (optional, e.g., 'IT Request', 'Incident Management', 'ServiceOrderRequest')"
                },
                "status": {
                    "type": "string",
                    "description": "Ticket status to filter by (optional, e.g., 'Registered', 'In progress', 'Resolved', 'Closed')"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number for pagination",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page",
                    "default": 15
                }
            },
            "required": ["user_email", "role"]
        }
    ),
    Tool(
        name="create_ticket",
        description="Create a new IT Request ticket as a customer (user becomes the end user of the ticket)",
        inputSchema={
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address (user will become the end user/customer for this ticket)"
                },
                "title": {
                    "type": "string",
                    "description": "Ticket title/subject"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the IT issue or request"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level",
                    "enum": ["Low", "Medium", "High", "Critical"],
                    "default": "Medium"
                }
            },
            "required": ["user_email", "title", "description"]
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
    
    async def get_tickets_by_role(self, user_email: str, role: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets based on user role"""
        data = {
            "user_email": user_email,
            "role": role,
            "page": page,
            "page_size": page_size
        }
        try:
            result = await self._call_local_api('/api/get_tickets_by_role', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to get tickets"}
        except Exception as e:
            logger.error(f"Error calling local API for tickets (user: {user_email}, role: {role}): {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_tickets_by_status(self, status: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets filtered by status"""
        data = {
            "status": status,
            "page": page,
            "page_size": page_size
        }
        try:
            result = await self._call_local_api('/api/get_tickets_by_status', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to get tickets by status"}
        except Exception as e:
            logger.error(f"Error calling local API for tickets by status ({status}): {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_tickets_by_type(self, ticket_type: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets filtered by type"""
        data = {
            "ticket_type": ticket_type,
            "page": page,
            "page_size": page_size
        }
        try:
            result = await self._call_local_api('/api/get_tickets_by_type', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to get tickets by type"}
        except Exception as e:
            logger.error(f"Error calling local API for tickets by type ({ticket_type}): {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_tickets_by_role_and_status(self, user_email: str, role: str, status: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets filtered by both user role and status"""
        data = {
            "user_email": user_email,
            "role": role,
            "status": status,
            "page": page,
            "page_size": page_size
        }
        try:
            result = await self._call_local_api('/api/get_tickets_by_role_and_status', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to get tickets by role and status"}
        except Exception as e:
            logger.error(f"Error calling local API for tickets by role and status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_tickets_by_role_and_type(self, user_email: str, role: str, ticket_type: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets filtered by both user role and ticket type"""
        data = {
            "user_email": user_email,
            "role": role,
            "ticket_type": ticket_type,
            "page": page,
            "page_size": page_size
        }
        try:
            result = await self._call_local_api('/api/get_tickets_by_role_and_type', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to get tickets by role and type"}
        except Exception as e:
            logger.error(f"Error calling local API for tickets by role and type: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def search_tickets_advanced(self, user_email: str, role: str, ticket_type: str = None, status: str = None, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Advanced search for tickets with combined filtering"""
        data = {
            "user_email": user_email,
            "role": role,
            "page": page,
            "page_size": page_size
        }
        if ticket_type:
            data["ticket_type"] = ticket_type
        if status:
            data["status"] = status
            
        try:
            result = await self._call_local_api('/api/search_tickets_advanced', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to search tickets"}
        except Exception as e:
            logger.error(f"Error calling local API for advanced ticket search: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_customer_ticket(self, user_email: str, title: str, description: str, priority: str = "Medium") -> Dict[str, Any]:
        """Create a new IT Request ticket as a customer"""
        data = {
            "user_email": user_email,
            "title": title,
            "description": description,
            "priority": priority,
            "role": "customer"  # Always customer for ticket creation
        }
        try:
            result = await self._call_local_api('/api/create_customer_ticket', data=data)
            if result and result.get('success'):
                return result
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return {"success": False, "error": "Failed to create ticket"}
        except Exception as e:
            logger.error(f"Error calling local API for ticket creation: {str(e)}")
            return {"success": False, "error": str(e)}

# Global MCP connector instance
nsp_connector = NSPMCPConnector()

# User context management functions
async def get_user_context(user_email: str) -> UserContext:
    """Get or create user context with caching"""
    # Check if we have cached user context
    if user_email in USER_CONTEXT_CACHE:
        context = USER_CONTEXT_CACHE[user_email]
        if context.is_cache_valid():
            logger.info(f"Using cached user context for {user_email}")
            return context
        else:
            logger.info(f"User context cache expired for {user_email}")
            del USER_CONTEXT_CACHE[user_email]
    
    # Fetch fresh user data
    logger.info(f"Fetching fresh user data for {user_email}")
    user_data = await nsp_connector.get_user_by_email(user_email)
    
    if user_data:
        context = UserContext(user_data)
        USER_CONTEXT_CACHE[user_email] = context
        logger.info(f"Created and cached user context for {user_email} (type: {context.user_type})")
        return context
    else:
        logger.error(f"Failed to get user data for {user_email}")
        return None

async def call_tool(tool_name: str, arguments: Dict[str, Any], user_email: str = None) -> Dict[str, Any]:
    """Call a tool with user context validation"""
    logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
    
    # Get user context if user_email is provided
    user_context = None
    if user_email:
        user_context = await get_user_context(user_email)
        if not user_context:
            return {
                "success": False,
                "error": f"Kunde inte hitta användarinformation för {user_email}"
            }
    
    if tool_name == "get_my_info":
        if user_context:
            result = {
                "success": True,
                "data": {
                    "user_id": user_context.user_id,
                    "user_type": user_context.user_type,
                    "display_name": user_context.display_name,
                    "first_name": user_context.first_name,
                    "email": user_context.email,
                    "department": user_context.department,
                    "job_title": user_context.job_title,
                    "is_active": user_context.is_active,
                    "permissions": {
                        "can_list_own_tickets": user_context.can_list_own_tickets(),
                        "can_list_assigned_tickets": user_context.can_list_assigned_tickets(),
                        "can_create_tickets": user_context.can_create_tickets(),
                        "can_update_tickets": user_context.can_update_tickets(),
                    },
                    "greeting": user_context.get_personalized_greeting()
                }
            }
        else:
            result = {
                "success": False,
                "error": "Ingen användarkontext tillgänglig. Kontrollera att du är inloggad."
            }
    
    elif tool_name == "get_my_tickets":
        if not user_context:
            return {
                "success": False,
                "error": "Användarkontext krävs för att hämta ärenden"
            }
        
        role = arguments.get("role")
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 15)
        
        # Validate role permissions
        if role == "agent" and not user_context.can_list_assigned_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se tilldelade ärenden som agent"
            }
        elif role == "customer" and not user_context.can_list_own_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se dina egna ärenden"
            }
        
        # Call the local API
        api_result = await nsp_connector.get_tickets_by_role(
            user_email=user_email,
            role=role,
            page=page,
            page_size=page_size
        )
        
        if api_result.get("success"):
            # Transform the response to match expected format
            tickets_data = api_result.get("data", [])
            pagination = api_result.get("pagination", {})
            
            result = {
                "success": True,
                "data": {
                    "Result": tickets_data,
                    "TotalCount": pagination.get("total_count", 0),
                    "filter_description": f"Roll: {role}, Användare: {user_email}"
                }
            }
        else:
            result = api_result
    
    elif tool_name == "get_tickets_by_status":
        if not user_context:
            return {
                "success": False,
                "error": "Användarkontext krävs för att hämta ärenden"
            }
        
        role = arguments.get("role")
        status = arguments.get("status")
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 15)
        
        if not status:
            return {
                "success": False,
                "error": "Status krävs för att filtrera ärenden"
            }
        
        # Validate role permissions
        if role == "agent" and not user_context.can_list_assigned_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se tilldelade ärenden som agent"
            }
        elif role == "customer" and not user_context.can_list_own_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se dina egna ärenden"
            }
        
        # Call the local API with combined role and status filtering
        api_result = await nsp_connector.get_tickets_by_role_and_status(
            user_email=user_email,
            role=role,
            status=status,
            page=page,
            page_size=page_size
        )
        
        if api_result.get("success"):
            # Transform the response to match expected format
            tickets_data = api_result.get("data", [])
            pagination = api_result.get("pagination", {})
            
            result = {
                "success": True,
                "data": {
                    "Result": tickets_data,
                    "TotalCount": pagination.get("total_count", 0),
                    "filter_description": f"Roll: {role}, Status: {status}, Användare: {user_email}"
                }
            }
        else:
            result = api_result
    
    elif tool_name == "get_tickets_by_type":
        if not user_context:
            return {
                "success": False,
                "error": "Användarkontext krävs för att hämta ärenden"
            }
        
        role = arguments.get("role")
        ticket_type = arguments.get("ticket_type")
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 15)
        
        if not ticket_type:
            return {
                "success": False,
                "error": "Ärendetyp krävs för att filtrera ärenden"
            }
        
        # Validate role permissions
        if role == "agent" and not user_context.can_list_assigned_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se tilldelade ärenden som agent"
            }
        elif role == "customer" and not user_context.can_list_own_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se dina egna ärenden"
            }
        
        # Call the local API with combined role and type filtering
        api_result = await nsp_connector.get_tickets_by_role_and_type(
            user_email=user_email,
            role=role,
            ticket_type=ticket_type,
            page=page,
            page_size=page_size
        )
        
        if api_result.get("success"):
            # Transform the response to match expected format
            tickets_data = api_result.get("data", [])
            pagination = api_result.get("pagination", {})
            
            result = {
                "success": True,
                "data": {
                    "Result": tickets_data,
                    "TotalCount": pagination.get("total_count", 0),
                    "filter_description": f"Roll: {role}, Typ: {ticket_type}, Användare: {user_email}"
                }
            }
        else:
            result = api_result
    
    elif tool_name == "search_my_tickets":
        if not user_context:
            return {
                "success": False,
                "error": "Användarkontext krävs för att söka ärenden"
            }
        
        role = arguments.get("role")
        ticket_type = arguments.get("ticket_type")  # Optional
        status = arguments.get("status")  # Optional
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 15)
        
        # Validate role permissions
        if role == "agent" and not user_context.can_list_assigned_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se tilldelade ärenden som agent"
            }
        elif role == "customer" and not user_context.can_list_own_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att se dina egna ärenden"
            }
        
        # Call the local API with advanced search
        api_result = await nsp_connector.search_tickets_advanced(
            user_email=user_email,
            role=role,
            ticket_type=ticket_type,
            status=status,
            page=page,
            page_size=page_size
        )
        
        if api_result.get("success"):
            # Transform the response to match expected format
            tickets_data = api_result.get("data", [])
            pagination = api_result.get("pagination", {})
            
            # Build filter description
            filter_parts = [f"Roll: {role}", f"Användare: {user_email}"]
            if ticket_type:
                filter_parts.append(f"Typ: {ticket_type}")
            if status:
                filter_parts.append(f"Status: {status}")
            
            result = {
                "success": True,
                "data": {
                    "Result": tickets_data,
                    "TotalCount": pagination.get("total_count", 0),
                    "filter_description": ", ".join(filter_parts)
                }
            }
        else:
            result = api_result
    
    elif tool_name == "create_ticket":
        if not user_context:
            return {
                "success": False,
                "error": "Användarkontext krävs för att skapa ärenden"
            }
        
        # Note: Anyone can create tickets AS A CUSTOMER (even if they are agents in NSP)
        # IT staff can create tickets for their own issues by acting as customers
        
        # Validate that user has permission to create tickets
        if not user_context.can_create_tickets():
            return {
                "success": False,
                "error": "Du har inte behörighet att skapa ärenden"
            }
        
        title = arguments.get("title")
        description = arguments.get("description") 
        priority = arguments.get("priority", "Medium")
        
        if not title or not description:
            return {
                "success": False,
                "error": "Titel och beskrivning krävs för att skapa ärende"
            }
        
        # Call the local API to create customer ticket
        api_result = await nsp_connector.create_customer_ticket(
            user_email=user_email,
            title=title,
            description=description,
            priority=priority
        )
        
        if api_result.get("success"):
            ticket_data = api_result.get("data", {})
            ticket_id = ticket_data if isinstance(ticket_data, (int, str)) else ticket_data.get("Id", "Unknown")
            
            result = {
                "success": True,
                "data": {
                    "ticket_id": ticket_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "type": "IT Request",
                    "status": "Registered",
                    "created_by": user_email,
                    "message": f"Ärende #{ticket_id} har skapats framgångsrikt som IT Request"
                }
            }
        else:
            result = api_result
    
    else:
        result = {
            "success": False,
            "error": f"Okänt verktyg: {tool_name}"
        }
    
    return result

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
                
                # Handle all tool calls through the unified call_tool function
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
                
                # Call the tool with user context
                result = await call_tool(tool_name, arguments, user_email)
                
                if result.get("success"):
                    # Format successful response for MCP
                    if tool_name == "get_my_info":
                        text_content = f"Användarinformation:\n{json.dumps(result['data'], indent=2, ensure_ascii=False)}"
                    elif tool_name == "create_ticket":
                        ticket_info = result.get("data", {})
                        text_content = f"✅ Ärende skapat framgångsrikt!\n\n"
                        text_content += f"Ärende-ID: {ticket_info.get('ticket_id', 'N/A')}\n"
                        text_content += f"Titel: {ticket_info.get('title', 'N/A')}\n"
                        text_content += f"Beskrivning: {ticket_info.get('description', 'N/A')}\n"
                        text_content += f"Prioritet: {ticket_info.get('priority', 'N/A')}\n"
                        text_content += f"Typ: {ticket_info.get('type', 'N/A')}\n"
                        text_content += f"Status: {ticket_info.get('status', 'N/A')}\n"
                        text_content += f"Skapat av: {ticket_info.get('created_by', 'N/A')}\n\n"
                        text_content += f"💡 {ticket_info.get('message', 'Ärendet har skapats')}"
                    elif tool_name in ["get_my_tickets", "get_tickets_by_status", "get_tickets_by_type", "search_my_tickets"]:
                        tickets_data = result.get("data", {})
                        tickets = tickets_data.get("Result", [])
                        total_count = tickets_data.get("TotalCount", 0)
                        filter_desc = tickets_data.get("filter_description", "")
                        
                        text_content = f"Ärenden ({total_count} totalt):\n"
                        if filter_desc:
                            text_content += f"Filter: {filter_desc}\n\n"
                        
                        if tickets:
                            for ticket in tickets[:5]:  # Show first 5 tickets
                                text_content += f"ID: {ticket.get('Id', 'N/A')}\n"
                                text_content += f"Referens: {ticket.get('ReferenceNo', 'N/A')}\n"
                                text_content += f"Titel: {ticket.get('BaseHeader', 'N/A')}\n"
                                text_content += f"Beskrivning: {ticket.get('BaseDescription', 'N/A')[:100]}{'...' if len(ticket.get('BaseDescription', '')) > 100 else ''}\n"
                                text_content += f"Status: {ticket.get('BaseEntityStatus', 'N/A')}\n"
                                text_content += f"Typ: {ticket.get('Type', 'N/A')}\n"
                                text_content += f"Prioritet: {ticket.get('Priority', 'N/A')}\n"
                                text_content += f"Skapad: {ticket.get('CreatedDate', 'N/A')}\n"
                                text_content += f"Skapad av: {ticket.get('CreatedBy', 'N/A')}\n"
                                text_content += f"Tilldelad till: {ticket.get('BaseAgent', 'N/A')}\n"
                                text_content += f"Slutanvändare: {ticket.get('BaseEndUser', 'N/A')}\n"
                                text_content += "---\n"
                            
                            if total_count > 5:
                                text_content += f"\n... och {total_count - 5} fler ärenden"
                        else:
                            text_content += "Inga ärenden hittades."
                    else:
                        text_content = f"Resultat: {json.dumps(result['data'], indent=2, ensure_ascii=False)}"
                    
                    success_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": text_content
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
                        "error": {"code": -32603, "message": result.get("error", "Unknown error")}
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

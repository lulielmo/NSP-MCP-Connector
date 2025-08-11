"""
Azure Function MCP Server for NSP Connector
Exposes NSP functions via MCP for Copilot Studio
"""

import azure.functions as func
import logging
import json
import os
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, Any, List, Optional
from nsp_filtering_helpers import (
    create_simple_status_filter,
    create_simple_stage_filter,
    create_entity_type_filter,
    create_my_tickets_filter,
    create_open_tickets_filter,
    create_closed_tickets_filter,
    create_combined_filter,
    format_ticket_summary,
    get_filter_description
)

# Add user context management
from collections import defaultdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
    def is_agent(self) -> bool:
        """Check if user is an agent"""
        return self.user_type == 'Agent'
    
    def is_end_user(self) -> bool:
        """Check if user is an end user"""
        return self.user_type == 'End User'
    
    def can_list_own_tickets(self) -> bool:
        """Check if user can list their own tickets"""
        return self.is_active and (self.is_agent() or self.is_end_user())
    
    def can_list_assigned_tickets(self) -> bool:
        """Check if user can list tickets assigned to them (agents only)"""
        return self.is_active and self.is_agent()
    
    def can_create_tickets(self) -> bool:
        """Check if user can create tickets"""
        return self.is_active and (self.is_agent() or self.is_end_user())
    
    def can_update_tickets(self) -> bool:
        """Check if user can update tickets (agents only)"""
        return self.is_active and self.is_agent()
    
    def get_personalized_greeting(self) -> str:
        """Get personalized greeting for the user"""
        if self.first_name:
            return f"Hej {self.first_name}!"
        elif self.display_name:
            return f"Hej {self.display_name}!"
        else:
            return "Hej!"

async def get_user_context(user_email: str) -> Optional[UserContext]:
    """Get user context from cache or fetch from NSP"""
    if not user_email:
        return None
    
    # Check cache first
    if user_email in USER_CONTEXT_CACHE:
        context = USER_CONTEXT_CACHE[user_email]
        # Check if cache is still valid
        if time.time() - context.cached_at < (CACHE_EXPIRY_HOURS * 3600):
            logger.info(f"Using cached user context for {user_email}")
            return context
        else:
            # Remove expired cache entry
            del USER_CONTEXT_CACHE[user_email]
    
    # Fetch from NSP if not in cache
    try:
        logger.info(f"Fetching user context for {user_email}")
        # Use the existing NSP connector to get user data
        user_data = await nsp_connector.get_user_by_email(user_email)
        if user_data:
            context = UserContext(user_data)
            USER_CONTEXT_CACHE[user_email] = context
            logger.info(f"Cached user context for {user_email}: {context.user_type}")
            return context
        else:
            logger.warning(f"User not found in NSP or API error: {user_email}")
            return None
    except Exception as e:
        logger.error(f"Error fetching user context for {user_email}: {str(e)}")
        return None

def validate_user_permissions(user_context: UserContext, action: str, resource: str = None) -> bool:
    """Validate user permissions for specific actions"""
    if not user_context or not user_context.is_active:
        return False
    
    permission_map = {
        'list_own_tickets': user_context.can_list_own_tickets(),
        'list_assigned_tickets': user_context.can_list_assigned_tickets(),
        'create_ticket': user_context.can_create_tickets(),
        'update_ticket': user_context.can_update_tickets(),
        'get_user_info': True,  # Everyone can get their own info
    }
    
    return permission_map.get(action, False)

# API configuration - supports both local development and Azure deployment
LOCAL_API_BASE = os.environ.get('LOCAL_API_BASE', 'http://localhost:5000')

# Create Azure Function app
app = func.FunctionApp()

class NSPMCPConnector:
    """MCP Connector for NSP that communicates with local REST API"""
    
    def __init__(self):
        self.local_api_base = LOCAL_API_BASE.rstrip('/')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _call_local_api(self, endpoint: str, method: str = 'POST', data: Dict = None) -> Dict[str, Any]:
        """Call local REST API via Hybrid Connection or direct connection"""
        # Construct full URL using the configured base
        url = f"{self.local_api_base}{endpoint}"
        
        # Add detailed logging
        logger.info(f"Calling local API: {method} {url}")
        logger.info(f"Local API base: {self.local_api_base}")
        logger.info(f"Endpoint: {endpoint}")
        if data:
            logger.info(f"Request data: {json.dumps(data, indent=2)}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == 'GET':
                    logger.info(f"Making GET request to: {url}")
                    response = await client.get(url)
                else:
                    logger.info(f"Making POST request to: {url}")
                    response = await client.post(url, json=data)
                
                logger.info(f"Response status: {response.status_code}")
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error calling local API: {str(e)}")
            logger.error(f"URL attempted: {url}")
            logger.error(f"Local API base used: {self.local_api_base}")
            raise
    
    async def get_tickets(self, page: int = 1, page_size: int = 15, filters: Dict = None, 
                         sort_by: str = "CreatedDate", sort_direction: str = "desc", 
                         ticket_types: List[str] = None) -> Dict[str, Any]:
        """Get IT-related tickets from NSP with customizable sorting and type filtering"""
        data = {
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_direction": sort_direction
        }
        if filters:
            data["filters"] = filters
        if ticket_types:
            data["ticket_types"] = ticket_types
        
        return await self._call_local_api('/api/get_tickets', data=data)
    
    # User-friendly ticket functions
    
    async def get_my_tickets(self, user_email: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets assigned to the current user"""
        # First get user information to get their ID
        user_data = {"email": user_email}
        user_result = await self._call_local_api('/api/get_user_by_email', data=user_data)
        
        if not user_result.get('success') or not user_result.get('data'):
            return {"error": f"User not found: {user_email}"}
        
        user = user_result['data']
        user_id = user.get('Id')
        
        if not user_id:
            return {"error": f"User ID not found for: {user_email}"}
        
        # Create filter using user ID for BaseAgent
        filters = {
            "BaseAgent": user_id,
            "BaseEntityStatus": [1, 3, 6, 9]  # Not closed statuses
        }
        
        result = await self.get_tickets(page=page, page_size=page_size, filters=filters)
        
        # Format response for user-friendly display
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = get_filter_description(filters)
        
        return result
    
    async def get_open_tickets(self, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get all open tickets (not closed)"""
        filters = create_open_tickets_filter()
        result = await self.get_tickets(page=page, page_size=page_size, filters=filters)
        
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = get_filter_description(filters)
        
        return result
    
    async def get_closed_tickets(self, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get all closed tickets"""
        filters = create_closed_tickets_filter()
        result = await self.get_tickets(page=page, page_size=page_size, filters=filters)
        
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = get_filter_description(filters)
        
        return result
    
    async def get_tickets_by_status(self, status: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets by status (New, Open, Assigned, In progress, Closed, etc.)"""
        filters = create_simple_status_filter(status)
        if not filters:
            return {"error": f"Invalid status: {status}. Valid statuses: New, Registered, Assigned, In progress, Pending, Resolved, Closed"}
        
        result = await self.get_tickets(page=page, page_size=page_size, filters=filters)
        
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = get_filter_description(filters)
        
        return result
    
    async def get_tickets_by_type(self, entity_type: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets by type (Ticket, ServiceOrderRequest, Incident)"""
        # Map entity type names to ticket type names for filtering
        entity_type_to_ticket_type = {
            "Ticket": "IT Request",
            "ServiceOrderRequest": "ServiceOrderRequest", 
            "Incident": "Incident Management"
        }
        
        ticket_type = entity_type_to_ticket_type.get(entity_type, "IT Request")
        result = await self.get_tickets(page=page, page_size=page_size, ticket_types=[ticket_type])
        
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = f"Typ: {entity_type}"
        
        return result
    
    async def get_tickets_by_stage(self, entity_type: str, stage: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Get tickets by stage (New, Open, Resolved, Closed) for specific entity type"""
        # Map entity type names to ticket type names for filtering
        entity_type_to_ticket_type = {
            "Ticket": "IT Request",
            "ServiceOrderRequest": "ServiceOrderRequest", 
            "Incident": "Incident Management"
        }
        
        ticket_type = entity_type_to_ticket_type.get(entity_type, "IT Request")
        stage_filter = create_simple_stage_filter(stage, entity_type)
        
        if not stage_filter:
            return {"error": f"Invalid stage: {stage} for type: {entity_type}"}
        
        result = await self.get_tickets(page=page, page_size=page_size, filters=stage_filter, ticket_types=[ticket_type])
        
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = f"Typ: {entity_type}, Fas: {stage}"
        
        return result
    
    async def search_tickets(self, 
                           status: Optional[str] = None,
                           entity_type: Optional[str] = None,
                           stage: Optional[str] = None,
                           user_email: Optional[str] = None,
                           page: int = 1, 
                           page_size: int = 15) -> Dict[str, Any]:
        """Advanced search with multiple criteria"""
        # Build filters and ticket types
        filters = {}
        ticket_types = None
        
        # Handle status filter
        if status:
            status_filter = create_simple_status_filter(status)
            filters.update(status_filter)
        
        # Handle stage filter
        if stage and entity_type:
            stage_filter = create_simple_stage_filter(stage, entity_type)
            filters.update(stage_filter)
        
        # Handle user filter
        if user_email:
            user_filter = create_my_tickets_filter(user_email)
            filters.update(user_filter)
        
        # Handle entity type (map to ticket types)
        if entity_type:
            entity_type_to_ticket_type = {
                "Ticket": "IT Request",
                "ServiceOrderRequest": "ServiceOrderRequest", 
                "Incident": "Incident Management"
            }
            ticket_type = entity_type_to_ticket_type.get(entity_type, "IT Request")
            ticket_types = [ticket_type]
        
        result = await self.get_tickets(page=page, page_size=page_size, filters=filters, ticket_types=ticket_types)
        
        if 'Result' in result and result['Result']:
            result['Result'] = [format_ticket_summary(ticket) for ticket in result['Result']]
            result['filter_description'] = get_filter_description(filters)
        
        return result
    
    async def get_ticket_by_id(self, ticket_id: int) -> Dict[str, Any]:
        """Get specific ticket"""
        return await self._call_local_api(f'/api/get_ticket/{ticket_id}', method='GET')
    
    async def create_ticket(self, ticket_data: Dict[str, Any], user_email: str = None) -> Dict[str, Any]:
        """Create new ticket with user context"""
        # Use create_ticket_with_role with customer role for consistency
        data = {
            "ticket_data": ticket_data,
            "user_email": user_email,
            "role": "customer"  # Always customer when creating tickets
        }
        return await self._call_local_api('/api/create_ticket_with_role', data=data)
    
    async def update_ticket(self, ticket_id: int, updates: Dict[str, Any], user_email: str = None) -> Dict[str, Any]:
        """Update ticket with user context"""
        # Use update_ticket_with_role with agent role for consistency
        data = {
            "updates": updates,
            "user_email": user_email,
            "role": "agent"  # Default to agent role for updates
        }
        return await self._call_local_api(f'/api/update_ticket_with_role/{ticket_id}', method='PUT', data=data)
    
    async def search_entities(self, entity_type: str, query: str, page: int = 1, page_size: int = 15,
                            sort_by: str = "CreatedDate", sort_direction: str = "Descending") -> Dict[str, Any]:
        """Search among entities with customizable sorting"""
        data = {
            "entity_type": entity_type,
            "query": query,
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_direction": sort_direction
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
    
    async def get_user_by_email(self, user_email: str) -> Dict[str, Any]:
        """Get user information by email address"""
        data = {"email": user_email}
        try:
            result = await self._call_local_api('/api/get_user_by_email', data=data)
            # Check if we got a successful response with data
            if result and result.get('success') and result.get('data'):
                return result['data']
            else:
                logger.error(f"Local API returned unsuccessful response: {result}")
                return None
        except Exception as e:
            logger.error(f"Error calling local API for user {user_email}: {str(e)}")
            return None
    
    async def get_tickets_by_role(self, user_email: str, role: str = "customer", page: int = 1, page_size: int = 15,
                                sort_by: str = "CreatedDate", sort_direction: str = "desc", 
                                ticket_types: List[str] = None) -> Dict[str, Any]:
        """Get IT-related tickets filtered by user role (customer or agent) with customizable sorting and type filtering"""
        data = {
            "user_email": user_email,
            "role": role,
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_direction": sort_direction
        }
        if ticket_types:
            data["ticket_types"] = ticket_types
        return await self._call_local_api('/api/get_tickets_by_role', data=data)
    
    async def create_ticket_with_role(self, ticket_data: Dict[str, Any], user_email: str, role: str = "customer") -> Dict[str, Any]:
        """Create ticket with proper user context based on role"""
        data = {
            "ticket_data": ticket_data,
            "user_email": user_email,
            "role": role
        }
        return await self._call_local_api('/api/create_ticket_with_role', data=data)
    
    async def update_ticket_with_role(self, ticket_id: int, updates: Dict[str, Any], user_email: str, role: str = "agent") -> Dict[str, Any]:
        """Update ticket with proper user context based on role"""
        data = {
            "updates": updates,
            "user_email": user_email,
            "role": role
        }
        return await self._call_local_api(f'/api/update_ticket_with_role/{ticket_id}', method='PUT', data=data)
    
    async def get_tickets_by_status(self, status: str = "open", page: int = 1, page_size: int = 15,
                                  sort_by: str = "CreatedDate", sort_direction: str = "desc",
                                  ticket_types: List[str] = None) -> Dict[str, Any]:
        """Get IT-related tickets filtered by status (open or closed) with customizable sorting and type filtering"""
        data = {
            "status": status,
            "page": page,
            "page_size": page_size,
            "sort_by": sort_by,
            "sort_direction": sort_direction
        }
        if ticket_types:
            data["ticket_types"] = ticket_types
        return await self._call_local_api('/api/get_tickets_by_status', data=data)

# Global MCP connector instance
nsp_connector = NSPMCPConnector()

# MCP Tool definitions
MCP_TOOLS = [
    {
        "name": "get_my_tickets",
        "description": "Get tickets assigned to the current user",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            },
            "required": ["user_email"]
        }
    },
    {
        "name": "get_open_tickets",
        "description": "Get all open tickets (not closed)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            }
        }
    },
    {
        "name": "get_closed_tickets",
        "description": "Get all closed tickets",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            }
        }
    },
    {
        "name": "get_tickets_by_status",
        "description": "Get tickets by status (New, Open, Assigned, In progress, Closed, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status: New, Registered, Assigned, In progress, Pending, Resolved, Closed"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            },
            "required": ["status"]
        }
    },
    {
        "name": "get_tickets_by_type",
        "description": "Get tickets by type (Ticket, ServiceOrderRequest, Incident)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Entity type: Ticket, ServiceOrderRequest, Incident"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            },
            "required": ["entity_type"]
        }
    },
    {
        "name": "get_tickets_by_stage",
        "description": "Get tickets by stage (New, Open, Resolved, Closed) for specific entity type",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "description": "Entity type: Ticket, ServiceOrderRequest, Incident"
                },
                "stage": {
                    "type": "string",
                    "description": "Stage: New, Open, Resolved, Closed"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            },
            "required": ["entity_type", "stage"]
        }
    },
    {
        "name": "search_tickets",
        "description": "Advanced search with multiple criteria (status, type, stage, user)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status filter (optional)"
                },
                "entity_type": {
                    "type": "string",
                    "description": "Entity type filter (optional)"
                },
                "stage": {
                    "type": "string",
                    "description": "Stage filter (optional)"
                },
                "user_email": {
                    "type": "string",
                    "description": "User email filter (optional)"
                },
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of tickets per page (default: 15)",
                    "default": 15
                }
            }
        }
    },
    {
        "name": "get_tickets",
        "description": "Get IT-related tickets from NSP with pagination, filtering, customizable sorting, and type filtering",
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
                },
                "sort_by": {
                    "type": "string",
                    "description": "Field to sort by (default: 'CreatedDate')",
                    "default": "CreatedDate"
                },
                "sort_direction": {
                    "type": "string",
                    "description": "Sort direction: 'asc' or 'desc' (default: 'desc' for newest first)",
                    "enum": ["asc", "desc"],
                    "default": "desc"
                },
                "ticket_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["Ticket", "ServiceOrderRequest", "Incident"]
                    },
                    "description": "Specific IT ticket types to include. If not specified, includes all IT types"
                }
            }
        }
    },
    {
        "name": "get_tickets_by_role",
        "description": "Get IT-related tickets filtered by user role (customer or agent) with customizable sorting and type filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "Email address of the user"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'customer' or 'agent'",
                    "enum": ["customer", "agent"],
                    "default": "customer"
                },
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
                "sort_by": {
                    "type": "string",
                    "description": "Field to sort by (default: 'CreatedDate')",
                    "default": "CreatedDate"
                },
                "sort_direction": {
                    "type": "string",
                    "description": "Sort direction: 'asc' or 'desc' (default: 'desc' for newest first)",
                    "enum": ["asc", "desc"],
                    "default": "desc"
                },
                "ticket_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["Ticket", "ServiceOrderRequest", "Incident"]
                    },
                    "description": "Specific IT ticket types to include. If not specified, includes all IT types"
                }
            },
            "required": ["user_email"]
        }
    },
    {
        "name": "get_tickets_by_status",
        "description": "Get IT-related tickets filtered by status (open or closed) with customizable sorting and type filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Ticket status: 'open' for non-closed tickets or 'closed' for closed tickets",
                    "enum": ["open", "closed"],
                    "default": "open"
                },
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
                "sort_by": {
                    "type": "string",
                    "description": "Field to sort by (default: 'CreatedDate')",
                    "default": "CreatedDate"
                },
                "sort_direction": {
                    "type": "string",
                    "description": "Sort direction: 'asc' or 'desc' (default: 'desc' for newest first)",
                    "enum": ["asc", "desc"],
                    "default": "desc"
                },
                "ticket_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["Ticket", "ServiceOrderRequest", "Incident"]
                    },
                    "description": "Specific IT ticket types to include. If not specified, includes all IT types"
                }
            }
        }
    },
    {
        "name": "get_user_by_email",
        "description": "Get user information by email address",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "Email address to look up"
                }
            },
            "required": ["user_email"]
        }
    },
    {
        "name": "get_my_info",
        "description": "Get current user information and permissions",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
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
                },
                "user_email": {
                    "type": "string",
                    "description": "Email of the user creating the ticket (optional, will use API account if not provided)"
                }
            },
            "required": ["title", "description"]
        }
    },
    {
        "name": "create_ticket_with_role",
        "description": "Create new ticket with proper user context based on role",
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
                },
                "user_email": {
                    "type": "string",
                    "description": "Email of the user creating the ticket"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'customer' or 'agent'",
                    "enum": ["customer", "agent"],
                    "default": "customer"
                }
            },
            "required": ["title", "description", "user_email"]
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
                },
                "user_email": {
                    "type": "string",
                    "description": "Email of the user updating the ticket (optional, will use API account if not provided)"
                }
            },
            "required": ["ticket_id", "updates"]
        }
    },
    {
        "name": "update_ticket_with_role",
        "description": "Update existing ticket with proper user context based on role",
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
                },
                "user_email": {
                    "type": "string",
                    "description": "Email of the user updating the ticket"
                },
                "role": {
                    "type": "string",
                    "description": "User role: 'customer' or 'agent'",
                    "enum": ["customer", "agent"],
                    "default": "agent"
                }
            },
            "required": ["ticket_id", "updates", "user_email"]
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
        "description": "Get available entity types in NSP",
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
                    "description": "Type of entity to get metadata for"
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
                    "description": "Type of entity (e.g., Ticket)"
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

@app.route(route="mcp", auth_level=func.AuthLevel.FUNCTION)
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
            
            # Extract user information from Copilot context if available
            # This might come from headers, context, or other sources depending on Copilot setup
            user_email = None
            
            # Try to get user email from various possible sources
            # 1. From request headers (if Copilot sets them)
            user_email = req.headers.get('X-User-Email') or req.headers.get('User-Email')
            
            # 2. From arguments if explicitly provided
            if not user_email and 'user_email' in arguments:
                user_email = arguments.pop('user_email')
            
            # 3. From context if available in request data
            if not user_email and 'context' in request_data:
                context = request_data.get('context', {})
                user_email = context.get('user_email') or context.get('user', {}).get('email')
            
            logger.info(f"Tool call: {tool_name}, User: {user_email or 'API account'}")
            
            # Get user context for permission validation
            user_context = None
            if user_email:
                user_context = await get_user_context(user_email)
                if user_context:
                    logger.info(f"User context: {user_context.user_type} - {user_context.display_name}")
                else:
                    logger.warning(f"Could not get user context for {user_email}")
            
            # Call appropriate method based on tool name
            result = await call_tool(tool_name, arguments, user_email, user_context)
            
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

async def call_tool(tool_name: str, arguments: Dict[str, Any], user_email: str = None, user_context: UserContext = None) -> List[Dict[str, Any]]:
    """Call specific tool and return result"""
    
    try:
        # Permission validation based on tool and user context
        if user_context:
            # Define permission requirements for each tool
            permission_requirements = {
                'get_my_tickets': 'list_own_tickets',
                'get_tickets_by_role': 'list_own_tickets',
                'create_ticket': 'create_ticket',
                'create_ticket_with_role': 'create_ticket',
                'update_ticket': 'update_ticket',
                'update_ticket_with_role': 'update_ticket',
                'get_user_by_email': 'get_user_info',
            }
            
            required_permission = permission_requirements.get(tool_name)
            if required_permission and not validate_user_permissions(user_context, required_permission):
                return [{
                    "type": "error",
                    "message": f"Du har inte behörighet att använda {tool_name}. Kontakta IT-support om du behöver hjälp."
                }]
            
            # Add personalized greeting for user-friendly tools
            if tool_name in ['get_my_tickets', 'get_tickets_by_role']:
                greeting = user_context.get_personalized_greeting()
                logger.info(f"User {user_context.email} ({user_context.user_type}) accessing {tool_name}")
        
        # Continue with tool execution
        # User-friendly functions
        if tool_name == "get_my_tickets":
            # Determine role based on user context
            role = "customer"  # Default
            if user_context:
                if user_context.is_agent():
                    # Ask user which role they want to use
                    role = arguments.get("role", "customer")  # Default to customer view for agents
                else:
                    role = "customer"  # End users can only see their own tickets
            
            result = await nsp_connector.get_tickets_by_role(
                user_email=user_email,
                role=role,
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "get_open_tickets":
            result = await nsp_connector.get_open_tickets(
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "get_closed_tickets":
            result = await nsp_connector.get_closed_tickets(
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "get_tickets_by_status":
            result = await nsp_connector.get_tickets_by_status(
                status=arguments["status"],
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "get_tickets_by_type":
            result = await nsp_connector.get_tickets_by_type(
                entity_type=arguments["entity_type"],
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "get_tickets_by_stage":
            result = await nsp_connector.get_tickets_by_stage(
                entity_type=arguments["entity_type"],
                stage=arguments["stage"],
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        elif tool_name == "search_tickets":
            result = await nsp_connector.search_tickets(
                status=arguments.get("status"),
                entity_type=arguments.get("entity_type"),
                stage=arguments.get("stage"),
                user_email=user_email,
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15)
            )
        
        # Advanced functions
        elif tool_name == "get_tickets":
            result = await nsp_connector.get_tickets(
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15),
                filters=arguments.get("filters"),
                sort_by=arguments.get("sort_by", "CreatedDate"),
                sort_direction=arguments.get("sort_direction", "desc"),
                ticket_types=arguments.get("ticket_types")
            )
        
        elif tool_name == "get_tickets_by_role":
            result = await nsp_connector.get_tickets_by_role(
                user_email=user_email,
                role=arguments.get("role", "customer"),
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15),
                sort_by=arguments.get("sort_by", "CreatedDate"),
                sort_direction=arguments.get("sort_direction", "desc"),
                ticket_types=arguments.get("ticket_types")
            )
        
        elif tool_name == "get_tickets_by_status_advanced":
            result = await nsp_connector.get_tickets_by_status(
                status=arguments.get("status", "open"),
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15),
                sort_by=arguments.get("sort_by", "CreatedDate"),
                sort_direction=arguments.get("sort_direction", "desc"),
                ticket_types=arguments.get("ticket_types")
            )
        
        elif tool_name == "get_user_by_email":
            result = await nsp_connector.get_user_by_email(
                user_email=user_email
            )
        
        elif tool_name == "get_my_info":
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
        
        elif tool_name == "get_ticket_by_id":
            result = await nsp_connector.get_ticket_by_id(
                ticket_id=int(arguments["ticket_id"])
            )
        
        elif tool_name == "create_ticket":
            result = await nsp_connector.create_ticket(
                ticket_data=arguments,
                user_email=user_email
            )
        
        elif tool_name == "create_ticket_with_role":
            result = await nsp_connector.create_ticket_with_role(
                ticket_data=arguments,
                user_email=user_email,
                role=arguments.get("role", "customer")
            )
        
        elif tool_name == "update_ticket":
            result = await nsp_connector.update_ticket(
                ticket_id=int(arguments["ticket_id"]),
                updates=arguments["updates"],
                user_email=user_email
            )
        
        elif tool_name == "update_ticket_with_role":
            result = await nsp_connector.update_ticket_with_role(
                ticket_id=int(arguments["ticket_id"]),
                updates=arguments["updates"],
                user_email=user_email,
                role=arguments.get("role", "agent")
            )
        
        elif tool_name == "search_entities":
            result = await nsp_connector.search_entities(
                entity_type=arguments.get("entity_type", "Ticket"),
                query=arguments["query"],
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 15),
                sort_by=arguments.get("sort_by", "CreatedDate"),
                sort_direction=arguments.get("sort_direction", "Descending")
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
            data = result.get("data", result)
            # Handle case where data is an integer (like ticket ID)
            if isinstance(data, int):
                return [{
                    "type": "text",
                    "text": str(data)
                }]
            else:
                return [{
                    "type": "text",
                    "text": json.dumps(data, indent=2, ensure_ascii=False)
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

@app.route(route="health", auth_level=func.AuthLevel.FUNCTION)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "service": "nsp-mcp-connector",
            "local_api_base": LOCAL_API_BASE
        }),
        mimetype="application/json"
    ) 
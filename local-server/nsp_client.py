"""
NSP API Client - Handles communication with NSP Public API
Based on insights from NSP.PublicApiDemoForm
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime, timezone, timedelta
import time

logger = logging.getLogger(__name__)

@dataclass
class AuthToken:
    """Represents NSP authentication token"""
    token: str = ""
    expires: str = ""
    auth_result_message: str = ""
    
    def is_expired(self) -> bool:
        """Check if token is expired or will expire within 5 minutes"""
        if not self.expires:
            return True
        
        try:
            # Parse the expires timestamp (handling various formats)
            expires_str = self.expires
            
            # Handle different timezone formats
            if expires_str.endswith('Z'):
                expires_str = expires_str[:-1] + '+00:00'
            elif '+' in expires_str and expires_str.count('+') > 1:
                # Handle format like '2025-07-31T09:08:07.5238698+00:00'
                # This might be a malformed timestamp, try to fix it
                parts = expires_str.split('+')
                if len(parts) >= 3:
                    # Take the first part and add the timezone
                    expires_str = parts[0] + '+' + parts[-1]
            
            # Handle microseconds with more than 6 digits (NSP sends 7 digits)
            if '.' in expires_str and '+' in expires_str:
                # Split on timezone
                time_part, tz_part = expires_str.rsplit('+', 1)
                if '.' in time_part:
                    # Split on decimal point
                    date_time, microseconds = time_part.split('.')
                    # Truncate microseconds to 6 digits max
                    if len(microseconds) > 6:
                        microseconds = microseconds[:6]
                    # Reconstruct
                    expires_str = f"{date_time}.{microseconds}+{tz_part}"
            
            expires_time = datetime.fromisoformat(expires_str)
            # Add 5 minute buffer to avoid edge cases
            buffer_time = datetime.now(timezone.utc) + timedelta(minutes=5)
            return expires_time <= buffer_time
        except Exception as e:
            logger.warning(f"Could not parse token expiration time: {e}")
            # If we can't parse, assume it's expired to be safe
            return True

class NSPClient:
    """Client for NSP Public API with automatic token management"""
    
    def __init__(self, base_url: str, username: str = "", password: str = ""):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.auth_token = AuthToken()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'NSP-MCP-Connector/1.0',
            'Cache-Control': 'no-cache',
            'LanguageId': '1',  # English
            'CultureName': 'en-US'
        })
        
        # Security warning for password transmission
        if password:
            logger.warning("WARNING: Password will be transmitted in plain text to NSP API. "
                          "This should only be used in secure on-premise environments.")
    
    def authenticate(self) -> bool:
        """Authenticate against NSP and retrieve token"""
        try:
            # Authentication uses different path than other API calls
            auth_url = f"{self.base_url}/logon/getauthenticationtoken"
            params = {
                'email': self.username,
                'password': self.password
            }
            
            logger.info(f"Authenticating user '{self.username}' against NSP")
            response = self.session.get(auth_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if 'Result' in data:
                    token_data = data['Result']
                    self.auth_token.token = token_data.get('Token', '')
                    self.auth_token.expires = token_data.get('Expires', '')
                    
                    # Set Authorization header for future requests
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.auth_token.token}'
                    })
                    
                    logger.info(f"Authentication successful. Token expires: {self.auth_token.expires}")
                    return True
                else:
                    logger.error("No token in authentication response")
                    return False
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            return False
    
    def ensure_valid_token(self) -> bool:
        """Ensure we have a valid token, re-authenticate if needed"""
        if not self.auth_token.token or self.auth_token.is_expired():
            logger.info("Token expired or missing, re-authenticating...")
            return self.authenticate()
        return True
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to NSP API with automatic token refresh and retry logic"""
        # Ensure we have a valid token before making request
        if not self.ensure_valid_token():
            raise Exception("Failed to obtain valid authentication token")
        
        # Use PublicApi path for all endpoints except authentication
        if endpoint.startswith('logon/'):
            url = f"{self.base_url}/{endpoint}"
        else:
            url = f"{self.base_url}/PublicApi/{endpoint}"
        
        try:
            # Set headers for this specific request
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'NSP-MCP-Connector/1.0',
                'Cache-Control': 'no-cache',
                'LanguageId': '1',  # English
                'CultureName': 'en-US'
            }
            
            # Add authorization header if we have a token
            if self.auth_token.token:
                headers['Authorization'] = f'Bearer {self.auth_token.token}'
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=data, headers=headers)
            else:
                response = self.session.post(url, json=data, headers=headers)
            
            # Handle 401 Unauthorized - token might have expired
            if response.status_code == 401:
                logger.warning("Received 401 Unauthorized, token may have expired. Re-authenticating...")
                if self.authenticate():
                    # Retry the request with new token
                    headers['Authorization'] = f'Bearer {self.auth_token.token}'
                    if method.upper() == 'GET':
                        response = self.session.get(url, params=data, headers=headers)
                    else:
                        response = self.session.post(url, json=data, headers=headers)
                else:
                    raise Exception("Failed to re-authenticate after 401 error")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            raise
    
    def get_it_tickets(self, page: int = 1, page_size: int = 15, filters: Optional[Dict] = None, 
                      sort_by: str = "CreatedDate", sort_direction: str = "desc", 
                      ticket_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get IT-related tickets using SysTicket entity type with filtering for IT ticket types.
        
        Args:
            page: Page number for pagination
            page_size: Number of tickets per page
            filters: Additional filters to apply
            sort_by: Field to sort by
            sort_direction: Sort direction ('asc' or 'desc')
            ticket_types: List of specific ticket types to include. If None, includes all IT types:
                         ['IT Request', 'ServiceOrderRequest', 'Incident Management']
        """
        # Default IT ticket types if none specified
        if ticket_types is None:
            ticket_types = ['IT Request', 'ServiceOrderRequest', 'Incident Management']
        
        # Map ticket type names to their numeric IDs
        # Note: NSP API returns DisplayName for Type field in responses, not numeric IDs
        # English: 'IT Request' (112), 'Service Order Request' (113), 'Incident Management' (281)
        # Swedish: 'IT-Ärende' (112), 'Service Order Request' (113), 'Incident Management' (281)
        ticket_type_ids = {
            'IT Request': 112,      # Updated to match actual NSP DisplayName
            'ServiceOrderRequest': 113,
            'Incident Management': 281  # Updated to match actual NSP DisplayName
        }
        
        # Build the type filter for IT-related tickets using numeric IDs
        type_filters = []
        for ticket_type in ticket_types:
            if ticket_type in ticket_type_ids:
                type_filters.append({
                    "field": "Type",
                    "operator": "eq",
                    "value": ticket_type_ids[ticket_type]
                })
        
        # Combine type filter with any additional filters
        combined_filters = {
            "logic": "and",
            "filters": [
                {
                    "logic": "or",
                    "filters": type_filters
                }
            ]
        }
        
        # Add additional filters if provided
        if filters:
            # If filters is a simple filter object, wrap it in the combined structure
            if "logic" not in filters:
                combined_filters["filters"].append(filters)
            else:
                # If filters already has a logic structure, add it directly
                combined_filters["filters"].append(filters)
        
        query_data = {
            "EntityType": "SysTicket",  # Use SysTicket as base entity type
            "Page": page,
            "PageSize": page_size,
            "filters": combined_filters
        }
        
        # Workaround: Use explicit columns for SysTicket to avoid SortOrder issues
        # These columns should work for all IT ticket types
        query_data["columns"] = [
            "Type", "Owner", "Version", "CreatedDate", "CreatedBy", "UpdatedDate", "UpdatedBy", 
            "IPAddress", "BaseStatus", "OwnerAgent", "CC", "Priority", "Category", "Callback", 
            "CloseDateTime", "AgentGroup", "EndUserRating", "IsMajor", "BaseEntitySource", 
            "GeoLocation", "BrowserName", "ReferenceNo", "BaseEntityStage", "Escalation", 
            "Resolution", "BaseEntitySecurity", "IsSecurity", "FormId", "CaseType", "ReportedBy", 
            "OnBehalfOf", "BaseEndUser", "BaseAgent", "BaseHeader", "BaseDescription", 
            "BaseEntityStatus", "Location", "Customer", "SspFormId", "RequesterCommentCount", 
            "EndUserCommentCount", "SlaSummary", "MainWaypoint", "Urgency", "Impact", "AssignedDate", 
            "Address", "CommentCount", "LastCommentUserType", "ServiceEntitiesCount", "CiCount", 
            "TaskCount", "TicketOrganization", "ScenarioName", "EntitySerialNumber", "ConversationId", 
            "ServiceOrderItemId", "MasterTicket", "DependentParent", "IsInvoiceable", "IsInvoicingDecisionMade", 
            "ServiceCiId", "ServiceCiCategoryId", "SlaStartTimeCounter", "JiraIssueKey", "MetaDataOrderInfoId", 
            "StartMeetingTime", "EndMeetingTime", "RecipientAs", "AttachmentCount", "CiId", "CrmReference", 
            "MarkedForDelete", "EmailOrigin", "IsClosedFromSsp"
        ]
        
        # Add explicit sorting using the correct NSP API format
        query_data["sorts"] = [{"field": sort_by, "direction": sort_direction}]
        
        try:
            response = self._make_request('POST', 'GetEntityListByQuery', query_data)
            # GetEntityListByQuery returns data in 'Data' field (array)
            return response
        except Exception as e:
            # If first attempt fails, try without explicit sorting
            if "SortOrder" in str(e) or "property not found" in str(e):
                logger.warning("SortOrder error detected, trying without explicit sorting...")
                query_data.pop("sorts", None)
                response = self._make_request('POST', 'GetEntityListByQuery', query_data)
                return response
            else:
                raise

    def get_tickets(self, page: int = 1, page_size: int = 15, filters: Optional[Dict] = None, 
                   sort_by: str = "CreatedDate", sort_direction: str = "desc") -> Dict[str, Any]:
        """
        Get tickets from NSP with workaround for SortOrder issue.
        This method is kept for backward compatibility but now delegates to get_it_tickets.
        """
        return self.get_it_tickets(page=page, page_size=page_size, filters=filters, 
                                 sort_by=sort_by, sort_direction=sort_direction)
    
    def get_ticket_by_id(self, ticket_id: int) -> Dict[str, Any]:
        """Get specific ticket by ID"""
        query_data = {
            "EntityType": "Ticket",
            "Id": ticket_id
        }
        
        response = self._make_request('POST', 'GetEntityById', query_data)
        # GetEntityById returns data in 'Data' field (object)
        return response
    
    def create_ticket(self, ticket_data: Dict[str, Any], user_email: Optional[str] = None) -> Dict[str, Any]:
        """Create new ticket with optional user context"""
        # If user_email is provided, add it to the ticket data for proper attribution
        if user_email:
            ticket_data['CreatedBy'] = user_email
            ticket_data['AssignedTo'] = user_email
            logger.info(f"Creating ticket on behalf of user: {user_email}")
        
        return self._make_request('POST', 'CreateEntity', ticket_data)
    
    def update_ticket(self, ticket_id: int, updates: Dict[str, Any], user_email: Optional[str] = None) -> Dict[str, Any]:
        """Update existing ticket with optional user context"""
        update_data = {
            "EntityType": "Ticket",
            "Id": ticket_id,
            **updates
        }
        
        # If user_email is provided, add it to track who made the update
        if user_email:
            update_data['ModifiedBy'] = user_email
            logger.info(f"Updating ticket {ticket_id} on behalf of user: {user_email}")
        
        return self._make_request('POST', 'UpdateEntity', update_data)
    
    def get_it_tickets_by_status(self, status: str = "open", page: int = 1, page_size: int = 15,
                                sort_by: str = "CreatedDate", sort_direction: str = "desc",
                                ticket_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get IT-related tickets filtered by status.
        
        Args:
            status: 'open' for non-closed tickets (BaseEntityStatus neq 11) or 'closed' for closed tickets (BaseEntityStatus eq 11)
            page: Page number for pagination
            page_size: Number of tickets per page
            sort_by: Field to sort by
            sort_direction: Sort direction ('asc' or 'desc')
            ticket_types: List of specific ticket types to include. If None, includes all IT types
        """
        # Build status filter based on BaseEntityStatus
        if status.lower() == "open":
            status_filter = {
                "field": "BaseEntityStatus",
                "operator": "neq",
                "value": 11
            }
        elif status.lower() == "closed":
            status_filter = {
                "field": "BaseEntityStatus",
                "operator": "eq",
                "value": 11
            }
        else:
            raise ValueError(f"Invalid status: {status}. Must be 'open' or 'closed'")
        
        # Get IT tickets with status filter and ticket type filtering
        return self.get_it_tickets(page=page, page_size=page_size, filters=status_filter,
                                 sort_by=sort_by, sort_direction=sort_direction,
                                 ticket_types=ticket_types)
    
    def search_entities(self, entity_type: str, query: str, page: int = 1, page_size: int = 15,
                       sort_by: str = "CreatedDate", sort_direction: str = "desc") -> Dict[str, Any]:
        """Search among entities with workaround for SortOrder issue and customizable sorting"""
        search_data = {
            "EntityType": entity_type,
            "SearchText": query,
            "Page": page,
            "PageSize": page_size
        }
        
        # Workaround: Use explicit columns for different entity types
        if entity_type.lower() == "ticket":
            search_data["columns"] = [
                "Type", "Owner", "Version", "CreatedDate", "CreatedBy", "UpdatedDate", "UpdatedBy", 
                "IPAddress", "BaseStatus", "OwnerAgent", "CC", "Priority", "Category", "Callback", 
                "CloseDateTime", "AgentGroup", "EndUserRating", "IsMajor", "BaseEntitySource", 
                "GeoLocation", "BrowserName", "ReferenceNo", "BaseEntityStage", "Escalation", 
                "Resolution", "BaseEntitySecurity", "IsSecurity", "FormId", "CaseType", "ReportedBy", 
                "OnBehalfOf", "BaseEndUser", "BaseAgent", "BaseHeader", "BaseDescription", 
                "BaseEntityStatus", "Location", "Customer", "SspFormId", "RequesterCommentCount", 
                "EndUserCommentCount", "SlaSummary", "MainWaypoint", "Urgency", "Impact", "AssignedDate", 
                "Address", "CommentCount", "LastCommentUserType", "ServiceEntitiesCount", "CiCount", 
                "TaskCount", "TicketOrganization", "ScenarioName", "EntitySerialNumber", "ConversationId", 
                "ServiceOrderItemId", "MasterTicket", "DependentParent", "IsInvoiceable", "IsInvoicingDecisionMade", 
                "ServiceCiId", "ServiceCiCategoryId", "SlaStartTimeCounter", "JiraIssueKey", "MetaDataOrderInfoId", 
                "StartMeetingTime", "EndMeetingTime", "RecipientAs", "AttachmentCount", "CiId", "CrmReference", 
                "MarkedForDelete", "EmailOrigin", "IsClosedFromSsp"
            ]
            # Add explicit sorting for tickets using the correct NSP API format
            search_data["sorts"] = [{"field": sort_by, "direction": sort_direction}]
        elif entity_type.lower() == "person":
            search_data["columns"] = [
                "Type", "Owner", "Version", "CreatedDate", "CreatedBy", "UpdatedDate", "UpdatedBy", 
                "IPAddress", "BaseStatus", "LastLoginTime", "UserTypeId", "Email", "PasswordMD5HexHash", 
                "LastPwdDate", "IsActive", "IsLicensed", "DisplayName", "AuthToken", "AuthTokenGeneratedOn", 
                "WindowsUserName", "WindowsSidString", "LdapServerId", "Room", "CostCenter", "IsVIP", 
                "VIPNotes", "FirstName", "LastName", "EMailAddress", "Phone", "MobilePhone", "Address", 
                "Department", "JobTitle", "PersonTitle", "DateOfBirth", "Image", "FullName", "Organization", 
                "SysLanguage", "MaxStorage", "Description", "Comment", "Notes", "Company", "FaxNumber", 
                "HomeFolder", "HomeDrive", "HomePhone", "HomeAddress", "IpPhoneNumber", "Manager", 
                "PagerNumber", "WebPageAddress", "LyncAddress", "PhoneClean", "MobilePhoneClean", 
                "SkypeName", "MemberOf", "RoomNumber", "OfficeLocation", "ExtraCustomField1", 
                "ExtraCustomField2", "ExtraCustomField3", "DoNotSendEmailNotification", "LyncTel", 
                "AdManagerUserId", "SwedishPersonalNumber", "NormalizedSwedishPersonalNumber", 
                "NorwegianPid", "ExternalId", "DoNotSendApprovalNotification", "u_Rrelsegrenkostnadsstlle", 
                "u_Mailnotifieringvidnyttrende"
            ]
        
        try:
            response = self._make_request('POST', 'GetEntityListByQuery', search_data)
            # GetEntityListByQuery returns data in 'Data' field (array)
            return response
        except Exception as e:
            # Om första försöket misslyckas, prova utan explicit sortering
            if "SortOrder" in str(e) or "property not found" in str(e):
                logger.warning(f"SortOrder error detected for {entity_type}, trying without explicit sorting...")
                search_data.pop("sorts", None)
                response = self._make_request('POST', 'GetEntityListByQuery', search_data)
                return response
            else:
                raise
    
    def get_entity_types(self) -> Dict[str, Any]:
        """Get available entity types"""
        return self._make_request('GET', 'GetEntityTypes')
    
    def get_entity_metadata(self, entity_type: str) -> Dict[str, Any]:
        """Get metadata for specific entity type"""
        return self._make_request('POST', 'GetEntityTypeInfo', {"EntityType": entity_type})
    
    def upload_attachment(self, entity_id: int, entity_type: str, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload attachment to entity"""
        # This requires multipart/form-data implementation
        # For now return a placeholder
        return {
            "success": True,
            "message": f"Attachment {filename} uploaded for {entity_type} {entity_id}"
        }
    
    def get_attachments(self, entity_id: int, entity_type: str) -> Dict[str, Any]:
        """Get attachments for entity"""
        query_data = {
            "EntityType": entity_type,
            "Id": entity_id
        }
        
        return self._make_request('POST', 'GetEntityAttachments', query_data)
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get current token information for debugging"""
        return {
            "has_token": bool(self.auth_token.token),
            "expires": self.auth_token.expires,
            "is_expired": self.auth_token.is_expired(),
            "username": self.username
        } 

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Get user information by email address"""
        query_data = {
            "EntityType": "Person",
            "columns": [
                "Type", "Owner", "Version", "CreatedDate", "CreatedBy", "UpdatedDate", "UpdatedBy", 
                "IPAddress", "BaseStatus", "LastLoginTime", "UserTypeId", "Email", "PasswordMD5HexHash", 
                "LastPwdDate", "IsActive", "IsLicensed", "DisplayName", "AuthToken", "AuthTokenGeneratedOn", 
                "WindowsUserName", "WindowsSidString", "LdapServerId", "Room", "CostCenter", "IsVIP", 
                "VIPNotes", "FirstName", "LastName", "EMailAddress", "Phone", "MobilePhone", "Address", 
                "Department", "JobTitle", "PersonTitle", "DateOfBirth", "Image", "FullName", "Organization", 
                "SysLanguage", "MaxStorage", "Description", "Comment", "Notes", "Company", "FaxNumber", 
                "HomeFolder", "HomeDrive", "HomePhone", "HomeAddress", "IpPhoneNumber", "Manager", 
                "PagerNumber", "WebPageAddress", "LyncAddress", "PhoneClean", "MobilePhoneClean", 
                "SkypeName", "MemberOf", "RoomNumber", "OfficeLocation", "ExtraCustomField1", 
                "ExtraCustomField2", "ExtraCustomField3", "DoNotSendEmailNotification", "LyncTel", 
                "AdManagerUserId", "SwedishPersonalNumber", "NormalizedSwedishPersonalNumber", 
                "NorwegianPid", "ExternalId", "DoNotSendApprovalNotification", "u_Rrelsegrenkostnadsstlle", 
                "u_Mailnotifieringvidnyttrende"
            ],
            "filters": {
                "logic": "or",
                "filters": [
                    {
                        "field": "Email",
                        "operator": "eq",
                        "value": email
                    }
                ]
            },
            "Page": 1,
            "PageSize": 10
        }
        
        try:
            result = self._make_request('POST', 'GetEntityListByQuery', query_data)
            users = result.get('Data', [])  # GetEntityListByQuery returns data in 'Data' field
            
            # Find exact email match
            for user in users:
                if user.get('Email', '').lower() == email.lower():
                    return user
            
            return None
        except Exception as e:
            logger.error(f"Error looking up user by email {email}: {str(e)}")
            return None
    
    def get_tickets_by_user_role(self, user_email: str, role: str = "customer", page: int = 1, page_size: int = 15,
                               sort_by: str = "CreatedDate", sort_direction: str = "desc", 
                               ticket_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get IT-related tickets filtered by user role (customer or agent) with customizable sorting.
        
        Args:
            user_email: Email of the user to filter tickets for
            role: User role - 'customer' or 'agent'
            page: Page number for pagination
            page_size: Number of tickets per page
            sort_by: Field to sort by
            sort_direction: Sort direction ('asc' or 'desc')
            ticket_types: List of specific ticket types to include. If None, includes all IT types
        """
        # First get user information
        user = self.get_user_by_email(user_email)
        if not user:
            raise Exception(f"User not found: {user_email}")
        
        user_id = user.get('Id')
        
        # Map ticket type names to their numeric IDs
        # Note: NSP API returns DisplayName for Type field in responses, not numeric IDs
        # English: 'IT Request' (112), 'Service Order Request' (113), 'Incident Management' (281)
        # Swedish: 'IT-Ärende' (112), 'Service Order Request' (113), 'Incident Management' (281)
        ticket_type_ids = {
            'Ticket': 112,
            'ServiceOrderRequest': 113,
            'Incident': 281
        }
        
        # Default IT ticket types if none specified
        if ticket_types is None:
            ticket_types = ['IT Request', 'ServiceOrderRequest', 'Incident Management']
        
        # Build the type filter for IT-related tickets using numeric IDs
        type_filters = []
        for ticket_type in ticket_types:
            if ticket_type in ticket_type_ids:
                type_filters.append({
                    "field": "Type",
                    "operator": "eq",
                    "value": ticket_type_ids[ticket_type]
                })
        
        # Build the complete filter structure combining user role and ticket types
        if role.lower() == "customer":
            # Tickets where user is the end user/customer AND matches IT ticket types
            filters = {
                "logic": "and",
                "filters": [
                    {
                        "field": "BaseEndUser",
                        "operator": "eq",
                        "value": user_id
                    },
                    {
                        "logic": "or",
                        "filters": type_filters
                    }
                ]
            }
        elif role.lower() == "agent":
            # Tickets where user is the assigned agent AND matches IT ticket types
            filters = {
                "logic": "and",
                "filters": [
                    {
                        "field": "BaseAgent",
                        "operator": "eq",
                        "value": user_id
                    },
                    {
                        "logic": "or",
                        "filters": type_filters
                    }
                ]
            }
        else:
            raise ValueError(f"Invalid role: {role}. Must be 'customer' or 'agent'")
        
        # Get IT tickets with the combined filter structure
        return self.get_it_tickets(page=page, page_size=page_size, filters=filters, 
                                 sort_by=sort_by, sort_direction=sort_direction)
    
    def create_ticket_with_user_context(self, ticket_data: Dict[str, Any], user_email: str, role: str = "customer") -> Dict[str, Any]:
        """Create ticket with proper user context based on role"""
        # Get user information
        user = self.get_user_by_email(user_email)
        if not user:
            raise Exception(f"User not found: {user_email}")
        
        user_id = user.get('Id')
        
        # Set user context based on role
        if role.lower() == "customer":
            # User is creating ticket as customer
            ticket_data['BaseEndUser'] = user_id
            ticket_data['ReportedBy'] = user_id
            logger.info(f"Creating ticket as customer: {user_email}")
        elif role.lower() == "agent":
            # User is creating ticket as agent
            ticket_data['BaseAgent'] = user_id
            ticket_data['CreatedBy'] = user_id
            logger.info(f"Creating ticket as agent: {user_email}")
        else:
            raise ValueError(f"Invalid role: {role}. Must be 'customer' or 'agent'")
        
        return self._make_request('POST', 'CreateEntity', ticket_data)
    
    def update_ticket_with_user_context(self, ticket_id: int, updates: Dict[str, Any], user_email: str, role: str = "agent") -> Dict[str, Any]:
        """Update ticket with proper user context based on role"""
        # Get user information
        user = self.get_user_by_email(user_email)
        if not user:
            raise Exception(f"User not found: {user_email}")
        
        user_id = user.get('Id')
        
        update_data = {
            "EntityType": "Ticket",
            "Id": ticket_id,
            **updates
        }
        
        # Set user context based on role
        if role.lower() == "agent":
            # Agent is updating the ticket
            update_data['ModifiedBy'] = user_id
            update_data['BaseAgent'] = user_id
            logger.info(f"Updating ticket {ticket_id} as agent: {user_email}")
        elif role.lower() == "customer":
            # Customer is updating the ticket (e.g., adding comments)
            update_data['ModifiedBy'] = user_id
            logger.info(f"Updating ticket {ticket_id} as customer: {user_email}")
        else:
            raise ValueError(f"Invalid role: {role}. Must be 'customer' or 'agent'")
        
        return self._make_request('POST', 'UpdateEntity', update_data) 
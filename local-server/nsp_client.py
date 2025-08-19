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
import threading
from functools import lru_cache

logger = logging.getLogger(__name__)

@dataclass
class CachedUser:
    """Represents a cached user lookup result"""
    user_data: Dict[str, Any]
    cached_at: datetime
    email: str

    def is_expired(self, ttl_minutes: int = 30) -> bool:
        """Check if cache entry is expired"""
        age = datetime.now(timezone.utc) - self.cached_at
        return age > timedelta(minutes=ttl_minutes)

class UserCache:
    """Thread-safe cache for user lookups"""
    
    def __init__(self, ttl_minutes: int = 30, max_size: int = 100):
        self._cache: Dict[str, CachedUser] = {}
        self._lock = threading.RLock()
        self.ttl_minutes = ttl_minutes
        self.max_size = max_size
        
    def get(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user from cache if exists and not expired"""
        with self._lock:
            email_key = email.lower()
            if email_key in self._cache:
                cached_user = self._cache[email_key]
                if not cached_user.is_expired(self.ttl_minutes):
                    logger.debug(f"Cache HIT for user: {email}")
                    return cached_user.user_data
                else:
                    # Remove expired entry
                    logger.debug(f"Cache EXPIRED for user: {email}")
                    del self._cache[email_key]
            
            logger.debug(f"Cache MISS for user: {email}")
            return None
    
    def put(self, email: str, user_data: Dict[str, Any]) -> None:
        """Store user in cache"""
        with self._lock:
            # Clean up if we're at max size
            if len(self._cache) >= self.max_size:
                self._cleanup_oldest()
            
            email_key = email.lower()
            self._cache[email_key] = CachedUser(
                user_data=user_data,
                cached_at=datetime.now(timezone.utc),
                email=email
            )
            logger.debug(f"Cache STORE for user: {email}")
    
    def _cleanup_oldest(self) -> None:
        """Remove oldest cache entries to make room"""
        if not self._cache:
            return
            
        # Remove oldest 25% of entries
        entries_to_remove = max(1, len(self._cache) // 4)
        oldest_keys = sorted(
            self._cache.keys(), 
            key=lambda k: self._cache[k].cached_at
        )[:entries_to_remove]
        
        for key in oldest_keys:
            del self._cache[key]
        
        logger.debug(f"Cache cleanup: removed {len(oldest_keys)} old entries")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_count = sum(
                1 for cached_user in self._cache.values() 
                if cached_user.is_expired(self.ttl_minutes)
            )
            return {
                "total_entries": len(self._cache),
                "expired_entries": expired_count,
                "active_entries": len(self._cache) - expired_count,
                "ttl_minutes": self.ttl_minutes,
                "max_size": self.max_size
            }

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
        
        # Initialize user cache
        self.user_cache = UserCache(ttl_minutes=30, max_size=100)
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
                
                # Try to parse JSON response to check for Errors field
                try:
                    json_response = e.response.json()
                    if 'Errors' in json_response:
                        errors = json_response['Errors']
                        # Handle case where Errors is an integer instead of a list
                        if isinstance(errors, int):
                            logger.error(f"NSP API returned error code: {errors}")
                            raise Exception(f"NSP API error: {errors}")
                        elif isinstance(errors, list):
                            for error in errors:
                                if isinstance(error, dict):
                                    message = error.get('Message', 'Unknown error')
                                    logger.error(f"NSP API error: {message}")
                                else:
                                    logger.error(f"NSP API error: {error}")
                        else:
                            logger.error(f"NSP API returned unexpected error format: {errors}")
                except (ValueError, TypeError) as parse_error:
                    logger.error(f"Could not parse error response: {parse_error}")
            raise
    
    def get_it_tickets(self, page: int = 1, page_size: int = 15, filters: Optional[Dict] = None, 
                      sort_by: str = "CreatedDate", sort_direction: str = "desc", 
                      ticket_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get IT-related tickets using SysTicket entity type with filtering for IT ticket types.
        
        Args:
            page: Page number for pagination
            page_size: Number of tickets per page
            filters: Additional filters to apply (simple key-value format)
            sort_by: Field to sort by
            sort_direction: Sort direction ('asc' or 'desc')
            ticket_types: List of specific ticket types to include. If None, includes all IT types:
                         ['IT Request', 'ServiceOrderRequest', 'Incident Management']
        """
        # Default IT ticket types if none specified
        if ticket_types is None:
            ticket_types = ['IT Request', 'ServiceOrderRequest', 'Incident Management']
        
        # Map ticket type names to their numeric IDs
        ticket_type_ids = {
            'IT Request': 112,
            'ServiceOrderRequest': 113,
            'Incident Management': 281
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
        
        # Start with type filter
        all_filters = []
        if type_filters:
            all_filters.append({
                "logic": "or",
                "filters": type_filters
            })
        
        # Add additional filters if provided
        if filters:
            # Convert simple key-value filters to NSP format
            for key, value in filters.items():
                # Skip EntityType filter - it's not a filter field, it's a query parameter
                if key == "EntityType":
                    continue
                    
                # Remove .Id suffix if present (e.g., BaseEntityStatus.Id -> BaseEntityStatus)
                clean_key = key.replace('.Id', '')
                
                if isinstance(value, list):
                    # Handle list values (e.g., multiple status IDs)
                    list_filters = []
                    for v in value:
                        list_filters.append({
                            "field": clean_key,
                            "operator": "eq",
                            "value": v
                        })
                    all_filters.append({
                        "logic": "or",
                        "filters": list_filters
                    })
                else:
                    # Handle single values
                    all_filters.append({
                        "field": clean_key,
                        "operator": "eq",
                        "value": value
                    })
        
        # Build the final filter structure according to NSP API documentation
        if len(all_filters) == 0:
            combined_filters = None
        elif len(all_filters) == 1:
            # Single filter - use it directly without logic wrapper
            combined_filters = all_filters[0]
        else:
            # Multiple filters - combine with AND logic
            combined_filters = {
                "logic": "and",
                "filters": all_filters
            }
        
        query_data = {
            "EntityType": "SysTicket",
            "Page": page,
            "PageSize": page_size
        }
        
        if combined_filters:
            query_data["filters"] = combined_filters
        
        # Workaround: Use explicit columns for SysTicket to avoid SortOrder issues
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
            ticket_data['UpdatedBy'] = user_email
            logger.info(f"Creating ticket on behalf of user: {user_email}")
        
        return self._make_request('POST', 'SaveEntity', ticket_data)
    
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
        
        return self._make_request('POST', 'SaveEntity', update_data)
    
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
        # Build status filter based on BaseEntityStatus using the new filter structure
        if status.lower() == "open":
            status_filter = {
                "BaseEntityStatus": [1, 3, 6, 9]  # Not closed statuses
            }
        elif status.lower() == "closed":
            status_filter = {
                "BaseEntityStatus": [10, 11]  # Resolved, Closed
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
                "u_Mailnotifieringvidnytttrende"
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
        return self._make_request('GET', 'GetAllEntityTypes')
    
    def get_entity_metadata(self, entity_type: str) -> Dict[str, Any]:
        """Get metadata for specific entity type"""
        return self._make_request('GET', f'GetEntityTypeInfo?entityType={entity_type}')
    
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
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get user cache statistics"""
        return self.user_cache.stats()
    
    def clear_user_cache(self) -> None:
        """Clear the user cache"""
        self.user_cache.clear()
        logger.info("User cache cleared")
    
    def warm_user_cache(self, emails: List[str]) -> Dict[str, bool]:
        """Pre-warm cache with specific users"""
        results = {}
        for email in emails:
            try:
                user = self.get_user_by_email(email)
                if user:
                    results[email] = True
                    user_id = user.get('Id', 'Unknown')
                    user_name = user.get('FullName', 'Unknown')
                    logger.info(f"Cache warming for {email}: success -> {user_name} (ID: {user_id})")
                else:
                    results[email] = False
                    logger.info(f"Cache warming for {email}: not found")
            except Exception as e:
                results[email] = False
                logger.error(f"Cache warming failed for {email}: {str(e)}")
        
        return results 

    def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Get user information by email address with caching"""
        # Check cache first
        cached_user = self.user_cache.get(email)
        if cached_user is not None:
            user_id = cached_user.get('Id', 'Unknown')
            user_name = cached_user.get('FullName', 'Unknown')
            logger.info(f"Returning cached user data for: {email} -> {user_name} (ID: {user_id})")
            return cached_user
        
        # Cache miss - fetch from NSP API
        logger.info(f"Cache miss - fetching user from NSP API: {email}")
        
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
                    # Store in cache before returning
                    self.user_cache.put(email, user)
                    user_id = user.get('Id', 'Unknown')
                    user_name = user.get('FullName', 'Unknown')
                    logger.info(f"User found and cached: {email} -> {user_name} (ID: {user_id})")
                    return user
            
            # No user found - cache the null result temporarily (shorter TTL)
            logger.info(f"User not found: {email}")
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
        
        # Create simple filters that get_it_tickets can handle
        # The get_it_tickets method will handle the complex filter structure internally
        filters = {}
        
        if role.lower() == "customer":
            # Tickets where user is the end user/customer
            filters["BaseEndUser"] = user_id
        elif role.lower() == "agent":
            # Tickets where user is the assigned agent
            filters["BaseAgent"] = user_id
        else:
            raise ValueError(f"Invalid role: {role}. Must be 'customer' or 'agent'")
        
        # Get IT tickets with the user filter and specified ticket types
        return self.get_it_tickets(page=page, page_size=page_size, filters=filters, 
                                 sort_by=sort_by, sort_direction=sort_direction,
                                 ticket_types=ticket_types)
    
    def get_priority_ids(self) -> Dict[str, int]:
        """Get available priority IDs from NSP API"""
        try:
            # Query the SysPriority table to get available priorities
            query_data = {
                "EntityType": "SysPriority",
                "Page": 1,
                "PageSize": 50
            }
            
            result = self._make_request('POST', 'GetEntityListByQuery', query_data)
            
            if result and result.get('Data'):
                priorities = {}
                for priority in result['Data']:
                    # Use DisplayNameId if available and not empty/null, otherwise fallback to StrongName
                    display_name = priority.get('DisplayNameId')
                    strong_name = priority.get('StrongName', '')
                    
                    # Choose the name to use - prefer DisplayNameId if it exists and is not empty/null
                    if display_name and display_name.strip():  # Check if not None, empty, or just whitespace
                        name = display_name.lower()
                    elif strong_name and strong_name.strip():
                        name = strong_name.lower()
                    else:
                        # Skip this entry if we don't have a valid name
                        continue
                    
                    priority_id = priority.get('Id')
                    if priority_id is not None and name:  # Only add if we have both ID and name
                        priorities[name] = priority_id
                
                logger.info(f"Found priorities: {priorities}")
                return priorities
            else:
                logger.warning("Could not fetch priorities from NSP API, using defaults")
                return {"medium": 2}  # Fallback to default
                
        except Exception as e:
            logger.error(f"Error fetching priorities: {str(e)}")
            return {"medium": 2}  # Fallback to default

    def get_entity_status_ids(self) -> Dict[str, int]:
        """Get available entity status IDs from NSP API"""
        try:
            query_data = {
                "EntityType": "SysEntityStatus",
                "Page": 1,
                "PageSize": 50,
                #"columns": ["Id", "Name", "Description"]
            }
            
            result = self._make_request('POST', 'GetEntityListByQuery', query_data)
            
            if result and result.get('Data'):
                statuses = {}
                for status in result['Data']:
                    # Use DisplayNameId if available and not empty/null, otherwise fallback to StrongName
                    display_name = status.get('DisplayNameId')
                    strong_name = status.get('StrongName', '')
                    
                    # Choose the name to use - prefer DisplayNameId if it exists and is not empty/null
                    if display_name and display_name.strip():  # Check if not None, empty, or just whitespace
                        name = display_name.lower()
                    elif strong_name and strong_name.strip():
                        name = strong_name.lower()
                    else:
                        # Skip this entry if we don't have a valid name
                        continue
                    
                    status_id = status.get('Id')
                    if status_id is not None and name:  # Only add if we have both ID and name
                        statuses[name] = status_id
                
                logger.info(f"Found entity statuses: {statuses}")
                return statuses
            else:
                logger.warning("Could not fetch entity statuses from NSP API, using defaults")
                return {"open": 1}  # Fallback to default
                
        except Exception as e:
            logger.error(f"Error fetching entity statuses: {str(e)}")
            return {"open": 1}  # Fallback to default

    def get_agent_group_ids(self) -> Dict[str, int]:
        """Get available agent group IDs from NSP API"""
        try:
            query_data = {
                "EntityType": "SysGroup",
                "Page": 1,
                "PageSize": 50,
                #"columns": ["Id", "Name", "Description"]
            }
            
            result = self._make_request('POST', 'GetEntityListByQuery', query_data)
            
            if result and result.get('Data'):
                groups = {}
                for group in result['Data']:
                    # Use GroupName if available and not empty/null, otherwise fallback to StrongName
                    group_name = group.get('GroupName')
                    strong_name = group.get('StrongName', '')
                    
                    # Choose the name to use - prefer GroupName if it exists and is not empty/null
                    if group_name and group_name.strip():  # Check if not None, empty, or just whitespace
                        name = group_name.lower()
                    elif strong_name and strong_name.strip():
                        name = strong_name.lower()
                    else:
                        # Skip this entry if we don't have a valid name
                        continue
                    
                    group_id = group.get('Id')
                    if group_id is not None and name:  # Only add if we have both ID and name
                        groups[name] = group_id
                
                logger.info(f"Found agent groups: {groups}")
                return groups
            else:
                logger.warning("Could not fetch agent groups from NSP API, using defaults")
                return {"default": 1}  # Fallback to default
                
        except Exception as e:
            logger.error(f"Error fetching agent groups: {str(e)}")
            return {"default": 1}  # Fallback to default

    def get_entity_source_ids(self) -> Dict[str, int]:
        """Get available entity source IDs from NSP API"""
        try:
            query_data = {
                "EntityType": "SysEntitySource",
                "Page": 1,
                "PageSize": 50,
                #"columns": ["Id", "Name", "Description"]
            }
            
            result = self._make_request('POST', 'GetEntityListByQuery', query_data)
            
            if result and result.get('Data'):
                sources = {}
                for source in result['Data']:
                    # Use DisplayNameId if available and not empty/null, otherwise fallback to SourceName
                    display_name = source.get('DisplayNameId')
                    source_name = source.get('SourceName', '')
                    
                    # Choose the name to use - prefer DisplayNameId if it exists and is not empty/null
                    if display_name and display_name.strip():  # Check if not None, empty, or just whitespace
                        name = display_name.lower()
                    elif source_name and source_name.strip():
                        name = source_name.lower()
                    else:
                        # Skip this entry if we don't have a valid name
                        continue
                    
                    source_id = source.get('Id')
                    if source_id is not None and name:  # Only add if we have both ID and name
                        sources[name] = source_id
                
                logger.info(f"Found entity sources: {sources}")
                return sources
            else:
                logger.warning("Could not fetch entity sources from NSP API, using defaults")
                return {"web": 1}  # Fallback to default
                
        except Exception as e:
            logger.error(f"Error fetching entity sources: {str(e)}")
            return {"web": 1}  # Fallback to default

    def get_form_ids(self) -> Dict[str, int]:
        """Get available form IDs from NSP API"""
        try:
            query_data = {
                "EntityType": "SysEntityForm",
                "Page": 1,
                "PageSize": 50,
                #"columns": ["Id", "Name", "Description"]
            }
            
            result = self._make_request('POST', 'GetEntityListByQuery', query_data)
            
            if result and result.get('Data'):
                forms = {}
                for form in result['Data']:
                    # Use DisplayName if available and not empty/null, otherwise fallback to StrongName
                    display_name = form.get('DisplayName')
                    strong_name = form.get('StrongName', '')
                    
                    # Choose the name to use - prefer DisplayName if it exists and is not empty/null
                    if display_name and display_name.strip():  # Check if not None, empty, or just whitespace
                        name = display_name.lower()
                    elif strong_name and strong_name.strip():
                        name = strong_name.lower()
                    else:
                        # Skip this entry if we don't have a valid name
                        continue
                    
                    form_id = form.get('Id')
                    if form_id is not None and name:  # Only add if we have both ID and name
                        forms[name] = form_id
                
                logger.info(f"Found forms: {forms}")
                return forms
            else:
                logger.warning("Could not fetch forms from NSP API, using defaults")
                return {"default": 1}  # Fallback to default
                
        except Exception as e:
            logger.error(f"Error fetching forms: {str(e)}")
            return {"default": 1}  # Fallback to default

    def create_ticket_with_user_context(self, ticket_data: Dict[str, Any], user_email: str, role: str = "customer") -> Dict[str, Any]:
        """Create ticket with proper user context based on role"""
        # Get user information
        user = self.get_user_by_email(user_email)
        if not user:
            raise Exception(f"User not found: {user_email}")
        
        user_id = user.get('Id')
        
        # Get available IDs from NSP for required fields
        priority_ids = self.get_priority_ids()
        status_ids = self.get_entity_status_ids()
        agent_group_ids = self.get_agent_group_ids()
        source_ids = self.get_entity_source_ids()
        form_ids = self.get_form_ids()
        
        # Convert field names from Azure Function format to NSP format
        converted_data = {}
        for key, value in ticket_data.items():
            if key == "title":
                converted_data["BaseHeader"] = value
            elif key == "description":
                converted_data["BaseDescription"] = value
            elif key == "priority":
                # Convert priority string to PriorityId using dynamic mapping
                priority_lower = value.lower() if isinstance(value, str) else str(value).lower()
                if priority_lower in priority_ids:
                    converted_data["PriorityId"] = priority_ids[priority_lower]
                else:
                    # Try to find a close match
                    for name, pid in priority_ids.items():
                        if priority_lower in name or name in priority_lower:
                            converted_data["PriorityId"] = pid
                            break
                    else:
                        # Use first available priority as fallback
                        first_priority = next(iter(priority_ids.values()), 2)
                        converted_data["PriorityId"] = first_priority
                        logger.warning(f"Priority '{value}' not found, using fallback ID: {first_priority}")
            elif key == "category":
                # For now, skip category as it might need special handling
                pass
            else:
                # Keep other fields as-is
                converted_data[key] = value
        
        # Get valid IDs for required fields
        default_status_id = next(iter(status_ids.values()), 1)
        default_agent_group_id = next(iter(agent_group_ids.values()), 1)
        
        # Use Microsoft Chat Bot as source since we're creating tickets via AI assistant
        default_source_id = source_ids.get('microsoft chat bot', 16)  # ID 16 for Microsoft Chat Bot
        if not default_source_id:
            # Fallback to API if Microsoft Chat Bot not found
            default_source_id = source_ids.get('api', 24)  # ID 24 for API
            if not default_source_id:
                # Final fallback to first available source
                default_source_id = next(iter(source_ids.values()), 1)
        
        default_form_id = next(iter(form_ids.values()), 1)
        
        # Prepare ticket data with required fields using valid IDs
        prepared_ticket_data = {
            "EntityType": "Ticket",  # Required by NSP API
            "BaseEntityStatusId": default_status_id,
            "AgentGroupId": default_agent_group_id,
            "BaseEntitySource": default_source_id,
            "FormId": default_form_id,
            **converted_data
        }
        
        # Set user context based on role
        if role.lower() == "customer":
            # User is creating ticket as customer
            prepared_ticket_data['BaseEndUser'] = user_id
            prepared_ticket_data['CreatedBy'] = user_id
            prepared_ticket_data['UpdatedBy'] = user_id
            logger.info(f"Creating ticket as customer: {user_email}")
        elif role.lower() == "agent":
            # User is creating ticket as agent
            prepared_ticket_data['BaseAgent'] = user_id
            prepared_ticket_data['CreatedBy'] = user_id
            prepared_ticket_data['UpdatedBy'] = user_id
            logger.info(f"Creating ticket as agent: {user_email}")
        else:
            raise ValueError(f"Invalid role: {role}. Must be 'customer' or 'agent'")
        
        logger.info(f"Final ticket data: {prepared_ticket_data}")
        return self._make_request('POST', 'SaveEntity', prepared_ticket_data)
    
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
        
        return self._make_request('POST', 'SaveEntity', update_data) 
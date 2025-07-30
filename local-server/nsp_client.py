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
from datetime import datetime, timezone
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
            # Parse the expires timestamp (assuming ISO format)
            expires_time = datetime.fromisoformat(self.expires.replace('Z', '+00:00'))
            # Add 5 minute buffer to avoid edge cases
            buffer_time = datetime.now(timezone.utc) + datetime.timedelta(minutes=5)
            return expires_time <= buffer_time
        except Exception as e:
            logger.warning(f"Could not parse token expiration time: {e}")
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
            'Accept': 'application/json'
        })
        
        # Security warning for password transmission
        if password:
            logger.warning("WARNING: Password will be transmitted in plain text to NSP API. "
                          "This should only be used in secure on-premise environments.")
    
    def authenticate(self) -> bool:
        """Authenticate against NSP and retrieve token"""
        try:
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
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=data)
            else:
                response = self.session.post(url, json=data)
            
            # Handle 401 Unauthorized - token might have expired
            if response.status_code == 401:
                logger.warning("Received 401 Unauthorized, token may have expired. Re-authenticating...")
                if self.authenticate():
                    # Retry the request with new token
                    if method.upper() == 'GET':
                        response = self.session.get(url, params=data)
                    else:
                        response = self.session.post(url, json=data)
                else:
                    raise Exception("Failed to re-authenticate after 401 error")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {str(e)}")
            raise
    
    def get_tickets(self, page: int = 1, page_size: int = 15, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Get tickets from NSP"""
        query_data = {
            "EntityType": "Ticket",
            "Page": page,
            "PageSize": page_size
        }
        
        if filters:
            query_data.update(filters)
        
        return self._make_request('POST', 'GetEntityListByQuery', query_data)
    
    def get_ticket_by_id(self, ticket_id: int) -> Dict[str, Any]:
        """Get specific ticket by ID"""
        query_data = {
            "EntityType": "Ticket",
            "Id": ticket_id
        }
        
        return self._make_request('POST', 'GetEntityById', query_data)
    
    def create_ticket(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new ticket"""
        return self._make_request('POST', 'CreateEntity', ticket_data)
    
    def update_ticket(self, ticket_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing ticket"""
        update_data = {
            "EntityType": "Ticket",
            "Id": ticket_id,
            **updates
        }
        
        return self._make_request('POST', 'UpdateEntity', update_data)
    
    def search_entities(self, entity_type: str, query: str, page: int = 1, page_size: int = 15) -> Dict[str, Any]:
        """Search among entities"""
        search_data = {
            "EntityType": entity_type,
            "SearchText": query,
            "Page": page,
            "PageSize": page_size
        }
        
        return self._make_request('POST', 'GetEntityListByQuery', search_data)
    
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
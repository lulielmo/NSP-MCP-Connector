#!/usr/bin/env python3
"""
Consolidated test script for direct NSP API testing
Combines: test_simple.py, test_nsp_client_direct.py, test_numeric_ids.py, test_it_filtering.py
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

# Add local-server to path
sys.path.append('../local-server')

# Load environment variables
load_dotenv('../local-server/.env')

# Configuration from environment variables
NSP_BASE_URL = os.getenv('NSP_BASE_URL')
NSP_USERNAME = os.getenv('NSP_USERNAME')
NSP_PASSWORD = os.getenv('NSP_PASSWORD')
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL')

# Global NSP client instance
nsp_client = None

def test_environment():
    """Test that environment variables are loaded"""
    print("🔧 Testing environment configuration...")
    
    required_vars = ['NSP_BASE_URL', 'NSP_USERNAME', 'NSP_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * len(value)} (configured)")
    
    if missing_vars:
        print(f"❌ Missing or default values for: {', '.join(missing_vars)}")
        print("Please update your .env file with real values")
        return False
    
    print("✅ Environment configuration looks good!")
    return True

def test_nsp_connectivity():
    """Test basic connectivity to NSP API"""
    print("\n🌐 Testing NSP API connectivity...")
    
    try:
        from nsp_client import NSPClient
        
        # Create client
        client = NSPClient(base_url=NSP_BASE_URL, username=NSP_USERNAME, password=NSP_PASSWORD)
        
        # Test authentication
        print("   Testing authentication...")
        auth_result = client.authenticate()
        
        if auth_result:
            print("✅ Authentication successful!")
            
            # Test a simple API call
            print("   Testing basic API call...")
            test_data = {
                "EntityType": "Ticket",
                "Page": 1,
                "PageSize": 5,
                "columns": [
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
            }
            result = client._make_request('POST', 'GetEntityListByQuery', test_data)
            
            if result and result.get('Data') is not None:
                print(f"✅ API call successful! Found {len(result.get('Data', []))} tickets")
                
                # Store client globally for other tests
                global nsp_client
                nsp_client = client
                return True
            else:
                print("❌ API call failed or returned no data")
                return False
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing NSP connectivity: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_get_entity_metadata():
    """Test getting entity metadata to understand required fields"""
    print("\n🧪 Testing entity metadata retrieval...")
    
    try:
        # Get metadata for Ticket entity
        metadata = nsp_client.get_entity_metadata("Ticket")
        
        print(f"✅ Retrieved Ticket metadata")
        print(f"Metadata keys: {list(metadata.keys())}")
        
        # Look for field information
        if 'Data' in metadata:
            data = metadata['Data']
            print(f"Data keys: {list(data.keys())}")
            
            # Look for fields/properties (now 'Columns' in the response)
            if 'Columns' in data:
                properties = data['Columns']
                print(f"Found {len(properties)} columns")
                
                # Show first few properties
                for i, prop in enumerate(properties[:10]):
                    name = prop.get('Name', 'Unknown')
                    # Determine the type: use ReferenceType for reference types, DataType for others
                    if prop.get('IsReference', False):
                        prop_type = prop.get('ReferenceType', 'Unknown')
                    else:
                        prop_type = prop.get('DataType', 'Unknown')
                    print(f"   {i+1}. {name}: {prop_type}")
                
                if len(properties) > 10:
                    print(f"   ... and {len(properties) - 10} more properties")
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata retrieval failed: {e}")
        return False

def test_get_available_ids():
    """Test the new ID fetching functions"""
    print("\n🧪 Testing ID fetching functions...")
    
    try:
        # Test priority IDs
        print("   Testing priority IDs...")
        priority_ids = nsp_client.get_priority_ids()
        print(f"   Found {len(priority_ids)} priorities: {priority_ids}")
        
        # Test status IDs
        print("   Testing status IDs...")
        status_ids = nsp_client.get_entity_status_ids()
        print(f"   Found {len(status_ids)} statuses: {status_ids}")
        
        # Test agent group IDs
        print("   Testing agent group IDs...")
        agent_group_ids = nsp_client.get_agent_group_ids()
        print(f"   Found {len(agent_group_ids)} agent groups: {agent_group_ids}")
        
        # Test source IDs
        print("   Testing source IDs...")
        source_ids = nsp_client.get_entity_source_ids()
        print(f"   Found {len(source_ids)} sources: {source_ids}")
        
        # Test form IDs
        print("   Testing form IDs...")
        form_ids = nsp_client.get_form_ids()
        print(f"   Found {len(form_ids)} forms: {form_ids}")
        
        return True
        
    except Exception as e:
        print(f"❌ ID fetching failed: {e}")
        return False

def test_create_ticket_direct():
    """Test creating a ticket directly via NSP API"""
    print("\n🧪 Testing direct ticket creation via NSP API...")
    
    try:
        # Test ticket data - using minimal required fields
        ticket_data = {
            "EntityType": "Ticket",
            "BaseHeader": "Direct API Test Ticket",
            "BaseDescription": "This ticket was created directly via NSP API for testing",
            "BaseEntityStatusId": 1,  # New status
            "PriorityId": 7,  # Medium priority
            "AgentGroupId": 1,
            "BaseEntitySource": 1,
            "FormId": 1
        }
        
        print(f"📝 Attempting to create ticket with data:")
        for key, value in ticket_data.items():
            print(f"   {key}: {value}")
        
        # Try to create the ticket
        response = nsp_client._make_request('POST', 'SaveEntity', ticket_data)
        
        print(f"✅ Ticket creation successful!")
        print(f"Response: {response}")
        
        # Extract ticket ID if available
        if 'Data' in response and response['Data']:
            ticket_id = response['Data']  # Data contains the ticket ID directly
            if ticket_id:
                print(f"📋 Created ticket ID: {ticket_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ticket creation failed: {e}")
        
        # Try to get more detailed error information
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Status code: {e.response.status_code}")
            print(f"   Response text: {e.response.text}")
            
            # Try to parse JSON error response
            try:
                error_data = e.response.json()
                print(f"   Error data: {error_data}")
            except:
                pass
        
        return False

def test_create_ticket_with_user_context():
    """Test creating a ticket with user context"""
    print("\n🧪 Testing ticket creation with user context...")
    
    try:
        # Test ticket data
        ticket_data = {
            "title": "User Context Test Ticket",
            "description": "This ticket tests user context handling",
            "priority": "Medium"
        }
        
        print(f"📝 Attempting to create ticket with user context:")
        print(f"   User email: {TEST_USER_EMAIL}")
        print(f"   Ticket data: {ticket_data}")
        
        # Try to create the ticket with user context
        result = nsp_client.create_ticket_with_user_context(ticket_data, TEST_USER_EMAIL, "customer")
        
        print(f"✅ Ticket creation with user context successful!")
        print(f"Result: {result}")
        
        # Extract ticket ID if available
        if result.get('Data'):
            ticket_id = result['Data']
            print(f"📋 Created ticket ID: {ticket_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ticket creation with user context failed: {e}")
        return False

def test_numeric_id_filtering():
    """Test the numeric ID filtering implementation"""
    print("\n🧪 Testing numeric ID filtering...")
    
    # Test 1: Get all IT tickets (should use numeric IDs internally)
    print("\n📋 Test 1: Getting all IT tickets...")
    try:
        result = nsp_client.get_it_tickets(page=1, page_size=5)
        if result and result.get('Data'):
            print(f"✅ Successfully retrieved {len(result['Data'])} IT tickets")
            print(f"   Total available: {result.get('Total', 'Unknown')}")
            
            # Show ticket types found
            types_found = set()
            for ticket in result['Data']:
                if 'Type' in ticket:
                    types_found.add(ticket['Type'])
            print(f"   Ticket types found: {types_found}")
        else:
            print("❌ No data returned or unexpected response structure")
            print(f"   Response: {result}")
    except Exception as e:
        print(f"❌ Error getting IT tickets: {e}")
        return False
    
    # Test 2: Get specific ticket types
    print("\n📋 Test 2: Getting specific ticket types...")
    try:
        result = nsp_client.get_it_tickets(page=1, page_size=20, ticket_types=['IT Request', 'Incident Management'])
        if result and result.get('Data'):
            print(f"✅ Successfully retrieved {len(result['Data'])} tickets (Ticket + Incident only, page_size=20)")
            
            # Verify only requested types are returned
            types_found = set()
            for ticket in result['Data']:
                if 'Type' in ticket:
                    types_found.add(ticket['Type'])
            print(f"   Ticket types found: {types_found}")
        else:
            print("❌ No data returned for specific ticket types")
    except Exception as e:
        print(f"❌ Error getting specific ticket types: {e}")
        return False
    
    return True

def test_it_tickets_filtering():
    """Test the new IT tickets filtering functionality"""
    print("\n🧪 Testing IT Tickets Filtering")
    print("=" * 50)
    
    try:
        # Test 1: Get all IT tickets (default behavior)
        print("\n📋 Test 1: Get all IT tickets (default)")
        print("-" * 30)
        result = nsp_client.get_it_tickets(page=1, page_size=5)
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} IT tickets")
        
        # Show ticket types found
        types_found = set(ticket.get('Type') for ticket in tickets)
        print(f"📊 Ticket types found: {types_found}")
        
        # Test 2: Get only IT Requests
        print("\n📋 Test 2: Get only IT Requests")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=5, 
            ticket_types=['Ticket']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} IT Request tickets")
        
        # Test 3: Get only Service Orders
        print("\n📋 Test 3: Get only Service Orders")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=5, 
            ticket_types=['ServiceOrderRequest']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} Service Order tickets")
        
        # Test 4: Get only Incidents
        print("\n📋 Test 4: Get only Incidents")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=5, 
            ticket_types=['Incident']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} Incident tickets")
        
        # Test 5: Get open tickets only
        print("\n📋 Test 5: Get open IT tickets only")
        print("-" * 30)
        result = nsp_client.get_it_tickets_by_status(
            status="open",
            page=1, 
            page_size=5
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} open IT tickets")
        
        # Test 6: Get closed tickets only
        print("\n📋 Test 6: Get closed IT tickets only")
        print("-" * 30)
        result = nsp_client.get_it_tickets_by_status(
            status="closed",
            page=1, 
            page_size=5
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} closed IT tickets")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in IT tickets filtering: {e}")
        return False

def main():
    """Run all direct NSP API tests"""
    print("🚀 NSP Direct API Tests")
    print("=" * 60)
    
    tests = [
        ("Environment Configuration", test_environment),
        ("NSP Connectivity", test_nsp_connectivity),
        ("Entity Metadata", test_get_entity_metadata),
        ("Available IDs", test_get_available_ids),
        ("Direct Ticket Creation", test_create_ticket_direct),
        ("Ticket Creation with User Context", test_create_ticket_with_user_context),
        ("Numeric ID Filtering", test_numeric_id_filtering),
        ("IT Tickets Filtering", test_it_tickets_filtering)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
        
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print(f"{'='*60}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    exit(main()) 
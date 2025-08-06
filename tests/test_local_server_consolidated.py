#!/usr/bin/env python3
"""
Consolidated test script for local server testing
Combines: test_local_server.py, test_local_server_direct.py, test_ticket_creation.py
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../local-server/.env')

# Configuration
LOCAL_SERVER_URL = "http://localhost:5000"

# Get test user emails from environment variables
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL')
TEST_CUSTOMER_1_EMAIL = os.getenv('TEST_CUSTOMER_1_EMAIL')
TEST_CUSTOMER_2_EMAIL = os.getenv('TEST_CUSTOMER_2_EMAIL')

def test_health_check():
    """Test health check endpoint"""
    print("🧪 Testing health check...")
    
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/health")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Service: {result.get('service')}")
            print(f"Authenticated: {result.get('authenticated')}")
            if 'token_info' in result:
                token_info = result['token_info']
                print(f"Token status: has_token={token_info.get('has_token')}, is_expired={token_info.get('is_expired')}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_token_status():
    """Test token status endpoint"""
    print("\n🧪 Testing token status...")
    
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/api/token/status")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                token_info = result.get('data', {})
                print(f"Token info: {token_info}")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_token_refresh():
    """Test manual token refresh"""
    print("\n🧪 Testing token refresh...")
    
    try:
        response = requests.post(f"{LOCAL_SERVER_URL}/api/token/refresh")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("✅ Token refreshed successfully")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_tickets():
    """Test fetching tickets"""
    print("\n🧪 Testing get_tickets...")
    
    try:
        data = {
            "page": 1,
            "page_size": 5
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/get_tickets",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                tickets = result.get('data', [])
                print(f"✅ Successfully retrieved {len(tickets)} tickets")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_tickets_with_different_filters():
    """Test get_tickets with different filter formats"""
    print("\n🔍 Testing get_tickets with Different Filters")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "No filters",
            "data": {
                "page": 1,
                "page_size": 5
            }
        },
        {
            "name": "Simple status filter",
            "data": {
                "page": 1,
                "page_size": 5,
                "filters": {"BaseEntityStatus": 3}
            }
        },
        {
            "name": "Stage filter",
            "data": {
                "page": 1,
                "page_size": 5,
                "filters": {"BaseEntityStage": 2}
            }
        },
        {
            "name": "Combined filters",
            "data": {
                "page": 1,
                "page_size": 5,
                "filters": {
                    "BaseEntityStatus": 3,
                    "BaseEntityStage": 2
                }
            }
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Data: {json.dumps(test_case['data'], indent=2)}")
        
        try:
            response = requests.post(
                f"{LOCAL_SERVER_URL}/api/get_tickets",
                json=test_case['data'],
                headers={"Content-Type": "application/json"},
                timeout=15.0
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success!")
                print(f"   Has Data: {'data' in result}")
                if 'data' in result:
                    print(f"   Data count: {len(result['data'])}")
            else:
                print(f"   ❌ Error: {response.text}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            all_passed = False
    
    return all_passed

def test_get_entity_types():
    """Test getting entity types"""
    print("\n🧪 Testing get_entity_types...")
    
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/api/get_entity_types")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                entity_types = result.get('data', [])
                print(f"✅ Successfully retrieved {len(entity_types)} entity types")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_search_entities():
    """Test searching entities"""
    print("\n🧪 Testing search_entities...")
    
    try:
        data = {
            "entity_type": "Ticket",
            "query": "test",
            "page": 1,
            "page_size": 5
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/search_entities",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                entities = result.get('data', [])
                print(f"✅ Successfully found {len(entities)} entities")
                if len(entities) == 0:
                    print("   Note: Search functionality may not be fully implemented yet")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_ticket_with_user():
    """Test creating ticket with user context"""
    print("\n🧪 Testing create_ticket with user context...")
    
    try:
        data = {
            "ticket_data": {
                "EntityType": "Ticket",
                "BaseHeader": "Test ticket with user handling",
                "BaseDescription": "This is a test to verify that tickets are created in the correct user's name",
                "PriorityId": 7,  # Medium priority
                "BaseEntityStatusId": 1,
                "AgentGroupId": 1,
                "BaseEntitySource": 1,
                "FormId": 1
            },
            "user_email": TEST_USER_EMAIL,
            "role": "customer"  # Always customer when creating tickets
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/create_ticket_with_role",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Ticket created successfully")
                print(f"Created for user: {result.get('user_email')}")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_ticket_with_role():
    """Test creating ticket with user role"""
    print("\n🧪 Testing create_ticket_with_role...")
    
    try:
        data = {
            "ticket_data": {
                "EntityType": "Ticket",
                "BaseHeader": "Test ticket with role",
                "BaseDescription": "This ticket is created with specific user role",
                "PriorityId": 7,  # Medium priority
                "BaseEntityStatusId": 1,
                "AgentGroupId": 1,
                "BaseEntitySource": 1,
                "FormId": 1
            },
            "user_email": TEST_CUSTOMER_1_EMAIL,
            "role": "customer"
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/create_ticket_with_role",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Ticket created successfully")
                print(f"Created for user: {result.get('user_email')}")
                print(f"User role: {result.get('user_role')}")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_update_ticket_with_user():
    """Test updating ticket with user context"""
    print("\n🧪 Testing update_ticket with user context...")
    
    # First create a ticket to update
    print("   Creating ticket for update test...")
    create_data = {
        "ticket_data": {
            "EntityType": "Ticket",
            "BaseHeader": "Ticket for update test",
            "BaseDescription": "This ticket will be updated",
            "PriorityId": 7,
            "BaseEntityStatusId": 1,
            "AgentGroupId": 1,
            "BaseEntitySource": 1,
            "FormId": 1
        },
        "user_email": TEST_USER_EMAIL,
        "role": "customer"
    }
    
    try:
        create_response = requests.post(
            f"{LOCAL_SERVER_URL}/api/create_ticket_with_role",
            json=create_data,
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code != 200:
            print(f"❌ Failed to create ticket for update test: {create_response.text}")
            return False
        
        create_result = create_response.json()
        if not create_result.get('success'):
            print(f"❌ Failed to create ticket for update test: {create_result.get('error')}")
            return False
        
        ticket_id = create_result.get('data')
        if not ticket_id:
            print("❌ Could not extract ticket ID from created ticket")
            return False
        
        print(f"   Created ticket ID: {ticket_id}")
        
        # Now update the ticket
        update_data = {
            "updates": {
                "BaseHeader": "Updated ticket header",
                "BaseDescription": "This ticket has been updated"
            },
            "user_email": TEST_USER_EMAIL,
            "role": "agent"
        }
        
        update_response = requests.put(
            f"{LOCAL_SERVER_URL}/api/update_ticket_with_role/{ticket_id}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Update Status: {update_response.status_code}")
        
        if update_response.status_code == 200:
            update_result = update_response.json()
            if update_result.get('success'):
                print(f"✅ Ticket updated successfully")
                return True
            else:
                print(f"❌ Error: {update_result.get('error')}")
                return False
        else:
            print(f"❌ Error: {update_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_user_by_email():
    """Test getting user by email"""
    print("\n🧪 Testing get_user_by_email...")
    
    try:
        data = {"email": TEST_USER_EMAIL}
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/get_user_by_email",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                user_data = result.get('data', {})
                print(f"✅ Successfully retrieved user data")
                print(f"User ID: {user_data.get('Id')}")
                print(f"User email: {user_data.get('Email')}")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_tickets_by_role():
    """Test getting tickets by user role"""
    print("\n🧪 Testing get_tickets_by_role...")
    
    try:
        data = {
            "user_email": TEST_USER_EMAIL,
            "role": "customer",
            "page": 1,
            "page_size": 5
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/get_tickets_by_role",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                tickets = result.get('data', [])
                print(f"✅ Successfully retrieved {len(tickets)} tickets for user role")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_and_update_ticket():
    """Test creating and then updating a ticket"""
    print("\n🧪 Testing create and update ticket workflow...")
    
    try:
        # Create ticket
        create_data = {
            "ticket_data": {
                "EntityType": "Ticket",
                "BaseHeader": "Create and Update Test Ticket",
                "BaseDescription": "This ticket will be created and then updated",
                "PriorityId": 7,
                "BaseEntityStatusId": 1,
                "AgentGroupId": 1,
                "BaseEntitySource": 1,
                "FormId": 1
            },
            "user_email": TEST_CUSTOMER_2_EMAIL,
            "role": "customer"
        }
        
        create_response = requests.post(
            f"{LOCAL_SERVER_URL}/api/create_ticket_with_role",
            json=create_data,
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code != 200:
            print(f"❌ Failed to create ticket: {create_response.text}")
            return False
        
        create_result = create_response.json()
        if not create_result.get('success'):
            print(f"❌ Failed to create ticket: {create_result.get('error')}")
            return False
        
        ticket_id = create_result.get('data')
        print(f"✅ Created ticket ID: {ticket_id}")
        
        # Wait a moment before updating
        time.sleep(1)
        
        # Update ticket
        update_data = {
            "updates": {
                "BaseHeader": "Updated Create and Update Test Ticket",
                "BaseDescription": "This ticket has been successfully updated"
            },
            "user_email": TEST_USER_EMAIL,
            "role": "agent"
        }
        
        update_response = requests.put(
            f"{LOCAL_SERVER_URL}/api/update_ticket_with_role/{ticket_id}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        if update_response.status_code == 200:
            update_result = update_response.json()
            if update_result.get('success'):
                print(f"✅ Ticket updated successfully")
                return True
            else:
                print(f"❌ Error updating ticket: {update_result.get('error')}")
                return False
        else:
            print(f"❌ Error updating ticket: {update_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all local server tests"""
    print("🚀 Local Server Tests")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health_check),
        ("Token Status", test_token_status),
        ("Token Refresh", test_token_refresh),
        ("Get Tickets", test_get_tickets),
        ("Get Tickets with Filters", test_get_tickets_with_different_filters),
        ("Get Entity Types", test_get_entity_types),
        ("Search Entities", test_search_entities),
        ("Create Ticket with User", test_create_ticket_with_user),
        ("Create Ticket with Role", test_create_ticket_with_role),
        ("Update Ticket with User", test_update_ticket_with_user),
        ("Get User by Email", test_get_user_by_email),
        ("Get Tickets by Role", test_get_tickets_by_role),
        ("Create and Update Ticket", test_create_and_update_ticket)
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
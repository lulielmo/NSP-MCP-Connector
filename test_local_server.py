"""
Test script for local NSP API server
"""

import requests
import json
import time

# Configuration
LOCAL_SERVER_URL = "http://localhost:5000"

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
                print(f"Number of tickets: {len(result.get('data', []))}")
                print(f"Pagination: {result.get('pagination', {})}")
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

def test_get_entity_types():
    """Test fetching entity types"""
    print("\n🧪 Testing get_entity_types...")
    
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/api/get_entity_types")
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"Entity types: {result.get('data', [])}")
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
    """Test search functionality"""
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
                print(f"Search results: {len(result.get('data', []))} hits")
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
                "title": "Test ticket with user handling",
                "description": "This is a test to verify that tickets are created in the correct user's name",
                "priority": "Medium",
                "category": "Test"
            },
            "user_email": "test.user@example.com"
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/create_ticket",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Ticket created successfully")
                print(f"Created for user: {result.get('created_for_user')}")
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
    
    try:
        # First create a ticket to update
        create_data = {
            "ticket_data": {
                "title": "Ticket for updating",
                "description": "This ticket will be updated",
                "priority": "Low",
                "category": "Test"
            },
            "user_email": "creator@example.com"
        }
        
        create_response = requests.post(
            f"{LOCAL_SERVER_URL}/api/create_ticket",
            json=create_data,
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code != 200:
            print("❌ Could not create ticket for update test")
            return False
        
        # Get the created ticket ID (this is a simplified test)
        # In a real scenario, you'd extract the ID from the response
        ticket_id = 1  # Placeholder - you'd need to extract this from create response
        
        # Now update the ticket
        update_data = {
            "updates": {
                "description": "Updated ticket description",
                "priority": "High"
            },
            "user_email": "updater@example.com"
        }
        
        response = requests.put(
            f"{LOCAL_SERVER_URL}/api/update_ticket/{ticket_id}",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"✅ Ticket updated successfully")
                print(f"Updated by user: {result.get('updated_by_user')}")
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

def test_get_user_by_email():
    """Test getting user by email"""
    print("\n🧪 Testing get_user_by_email...")
    
    try:
        data = {
            "email": "test.user@example.com"
        }
        
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
                print(f"✅ User found: {user_data.get('Email', 'N/A')}")
                print(f"   User ID: {user_data.get('Id', 'N/A')}")
                return True
            else:
                print(f"❌ Error: {result.get('error')}")
                return False
        elif response.status_code == 404:
            print("⚠️  User not found (expected for test)")
            return True
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
        # Test as customer
        customer_data = {
            "user_email": "test.user@example.com",
            "role": "customer",
            "page": 1,
            "page_size": 5
        }
        
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/get_tickets_by_role",
            json=customer_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status (customer): {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                tickets = result.get('data', [])
                print(f"✅ Customer tickets: {len(tickets)} found")
                print(f"   Role: {result.get('user_role')}")
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
            "title": "Test ticket with role",
            "description": "This ticket is created with specific user role",
            "priority": "Medium",
            "category": "Test",
            "user_email": "test.user@example.com",
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
                print(f"   User: {result.get('user_email')}")
                print(f"   Role: {result.get('user_role')}")
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

def main():
    """Run all tests"""
    print("🚀 Starting tests for local NSP API server...")
    print("=" * 50)
    
    tests = [
        test_health_check,
        test_token_status,
        test_token_refresh,
        test_get_tickets,
        test_get_entity_types,
        test_search_entities,
        test_create_ticket_with_user,
        test_update_ticket_with_user,
        test_get_user_by_email,
        test_get_tickets_by_role,
        test_create_ticket_with_role
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
            print("✅ Test passed")
        else:
            print("❌ Test failed")
        time.sleep(1)  # Short pause between tests
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check configuration.")

if __name__ == "__main__":
    main() 
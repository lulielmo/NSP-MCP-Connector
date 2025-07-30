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
        test_search_entities
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
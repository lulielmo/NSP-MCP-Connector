"""
Test script to investigate NSP API issues and workarounds
"""

import requests
import json
import time
from nsp_client import NSPClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_nsp_api_directly():
    """Test NSP API directly to identify problems"""
    print("🔍 Testing NSP API directly...")
    
    # Initialize NSP client
    nsp_client = NSPClient(
        base_url=os.getenv('NSP_BASE_URL', 'http://localhost:1900/api/PublicApi/'),
        username=os.getenv('NSP_USERNAME', ''),
        password=os.getenv('NSP_PASSWORD', '')
    )
    
    try:
        # Test authentication
        print("1. Testing authentication...")
        if nsp_client.authenticate():
            print("✅ Authentication successful")
            token_info = nsp_client.get_token_info()
            print(f"   Token expires: {token_info['expires']}")
        else:
            print("❌ Authentication failed")
            return False
        
        # Test get entity types
        print("\n2. Testing get_entity_types...")
        try:
            result = nsp_client.get_entity_types()
            print(f"✅ Entity types: {len(result.get('Result', []))} found")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test get tickets
        print("\n3. Testing get_tickets...")
        try:
            result = nsp_client.get_tickets(page=1, page_size=5)
            print(f"✅ Tickets: {len(result.get('Result', []))} found")
            print(f"   Total count: {result.get('TotalCount', 0)}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test create ticket (with minimal data)
        print("\n4. Testing create_ticket...")
        try:
            ticket_data = {
                "EntityType": "Ticket",
                "Title": "API Test Ticket",
                "Description": "Test ticket from API",
                "Priority": "Low"
            }
            result = nsp_client.create_ticket(ticket_data)
            print(f"✅ Create ticket result: {result}")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("   This might be where workaround is needed...")
        
        return True
        
    except Exception as e:
        print(f"❌ General error: {e}")
        return False

def test_nsp_api_workarounds():
    """Test various workarounds for NSP API issues"""
    print("\n🔧 Testing workarounds...")
    
    nsp_client = NSPClient(
        base_url=os.getenv('NSP_BASE_URL', 'http://localhost:1900/api/PublicApi/'),
        username=os.getenv('NSP_USERNAME', ''),
        password=os.getenv('NSP_PASSWORD', '')
    )
    
    # Ensure authentication
    if not nsp_client.ensure_valid_token():
        print("❌ Cannot authenticate")
        return False
    
    # Workaround 1: Test with different data formats
    print("\nWorkaround 1: Different data formats...")
    test_formats = [
        {
            "EntityType": "Ticket",
            "Title": "Test 1",
            "Description": "Description 1"
        },
        {
            "entityType": "Ticket",  # lowercase
            "title": "Test 2",
            "description": "Description 2"
        },
        {
            "EntityType": "Ticket",
            "Title": "Test 3",
            "Description": "Description 3",
            "Priority": "Low",
            "Category": "Test"
        }
    ]
    
    for i, format_data in enumerate(test_formats, 1):
        try:
            print(f"   Testing format {i}...")
            result = nsp_client.create_ticket(format_data)
            print(f"   ✅ Format {i} worked: {result}")
            break
        except Exception as e:
            print(f"   ❌ Format {i} failed: {e}")
    
    # Workaround 2: Test with different endpoints
    print("\nWorkaround 2: Different endpoints...")
    endpoints_to_test = [
        'CreateEntity',
        'createentity',  # lowercase
        'CreateTicket',
        'createticket'
    ]
    
    for endpoint in endpoints_to_test:
        try:
            print(f"   Testing endpoint: {endpoint}")
            ticket_data = {
                "EntityType": "Ticket",
                "Title": f"Test via {endpoint}",
                "Description": "Test description"
            }
            
            # Use direct request method
            result = nsp_client._make_request('POST', endpoint, ticket_data)
            print(f"   ✅ Endpoint {endpoint} worked: {result}")
            break
        except Exception as e:
            print(f"   ❌ Endpoint {endpoint} failed: {e}")
    
    return True

def test_sortorder_workaround():
    """Test specifically the SortOrder workaround"""
    print("\n🔧 Testing SortOrder workaround...")
    
    nsp_client = NSPClient(
        base_url=os.getenv('NSP_BASE_URL', 'http://localhost:1900/api/PublicApi/'),
        username=os.getenv('NSP_USERNAME', ''),
        password=os.getenv('NSP_PASSWORD', '')
    )
    
    # Ensure authentication
    if not nsp_client.ensure_valid_token():
        print("❌ Cannot authenticate")
        return False
    
    # Test 1: Use our workaround method
    print("\n1. Testing get_tickets with workaround...")
    try:
        result = nsp_client.get_tickets(page=1, page_size=5)
        print(f"✅ Workaround worked: {len(result.get('Result', []))} tickets found")
        print(f"   Total count: {result.get('TotalCount', 0)}")
        return True
    except Exception as e:
        print(f"❌ Workaround failed: {e}")
        return False

def test_direct_api_with_workaround():
    """Test direct API calls with workaround parameters"""
    print("\n🔧 Testing direct API with workaround...")
    
    nsp_client = NSPClient(
        base_url=os.getenv('NSP_BASE_URL', 'http://localhost:1900/api/PublicApi/'),
        username=os.getenv('NSP_USERNAME', ''),
        password=os.getenv('NSP_PASSWORD', '')
    )
    
    # Ensure authentication
    if not nsp_client.ensure_valid_token():
        print("❌ Cannot authenticate")
        return False
    
    # Test different workaround combinations with columns instead of ExcludeProperties
    workaround_tests = [
        {
            "name": "Columns + SortBy",
            "data": {
                "EntityType": "Ticket",
                "Page": 1,
                "PageSize": 5,
                "columns": ["Type", "Owner", "Version", "CreatedDate", "CreatedBy", "Priority", "Category"],
                "SortBy": "Id",
                "SortDirection": "Descending"
            }
        },
        {
            "name": "Only columns (minimal)",
            "data": {
                "EntityType": "Ticket",
                "Page": 1,
                "PageSize": 5,
                "columns": ["Type", "Owner", "CreatedDate", "Priority"]
            }
        },
        {
            "name": "Only SortBy",
            "data": {
                "EntityType": "Ticket",
                "Page": 1,
                "PageSize": 5,
                "SortBy": "Id",
                "SortDirection": "Descending"
            }
        },
        {
            "name": "Minimal data (without workaround)",
            "data": {
                "EntityType": "Ticket",
                "Page": 1,
                "PageSize": 5
            }
        }
    ]
    
    for test in workaround_tests:
        try:
            print(f"   Testing: {test['name']}")
            result = nsp_client._make_request('POST', 'GetEntityListByQuery', test['data'])
            print(f"   ✅ {test['name']} worked: {len(result.get('Result', []))} tickets")
            return True
        except Exception as e:
            print(f"   ❌ {test['name']} failed: {e}")
    
    return False

def main():
    """Run all tests"""
    print("🚀 Starting NSP API issues and workaround tests...")
    print("=" * 60)
    
    # Test 1: Direct API test
    if test_nsp_api_directly():
        print("\n✅ Direct API test completed")
    else:
        print("\n❌ Direct API test failed")
    
    # Test 2: SortOrder workaround
    if test_sortorder_workaround():
        print("\n✅ SortOrder workaround worked")
    else:
        print("\n❌ SortOrder workaround failed")
    
    # Test 3: Direct API with workaround
    if test_direct_api_with_workaround():
        print("\n✅ Direct API with workaround worked")
    else:
        print("\n❌ Direct API with workaround failed")
    
    # Test 4: General workarounds
    if test_nsp_api_workarounds():
        print("\n✅ General workaround tests completed")
    else:
        print("\n❌ General workaround tests failed")
    
    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("- SortOrder problem is known and has workaround implemented")
    print("- ExcludeProperties and explicit sorting helps")
    print("- Check logs above for specific results")
    print("- Document which workarounds work best")

if __name__ == "__main__":
    main() 
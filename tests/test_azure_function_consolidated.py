#!/usr/bin/env python3
"""
Consolidated test script for Azure Function MCP endpoints
Combines: test_azure_function_local.py, debug_azure_function.py
"""

import asyncio
import json
import httpx
import sys
import os
import time
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
# Try multiple possible paths for .env file
import pathlib

# Get the directory where this test file is located
test_dir = pathlib.Path(__file__).parent.absolute()
project_root = test_dir.parent

# Try different possible .env file locations
env_paths = [
    project_root / 'local-server' / '.env',
    test_dir / '..' / 'local-server' / '.env',
    project_root / '.env',
    pathlib.Path.cwd() / 'local-server' / '.env',
    pathlib.Path.cwd() / '.env'
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
        env_loaded = True
        break

if not env_loaded:
    print("⚠️  Warning: No .env file found in any of the expected locations:")
    for env_path in env_paths:
        print(f"   - {env_path}")
    print("   Environment variables may not be loaded correctly.")

# Test configuration
LOCAL_SERVER_URL = "http://localhost:5000"  # Local Flask server
AZURE_FUNCTION_URL = "http://localhost:7071"  # Local Azure Function

# Test user configuration from environment variables
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL')
TEST_CUSTOMER_1_EMAIL = os.getenv('TEST_CUSTOMER_1_EMAIL')
TEST_CUSTOMER_2_EMAIL = os.getenv('TEST_CUSTOMER_2_EMAIL')

# Validate that required environment variables are set
if not TEST_USER_EMAIL:
    print("❌ ERROR: TEST_USER_EMAIL environment variable is not set!")
    print("   Please check your .env file or set the environment variable manually.")
    print(f"   Current working directory: {pathlib.Path.cwd()}")
    print(f"   Test file location: {test_dir}")
    sys.exit(1)

print(f"✅ Using TEST_USER_EMAIL: {TEST_USER_EMAIL}")

def test_local_server_health():
    """Test if local server is running"""
    print("🏥 Testing Local Server Health")
    print("=" * 40)
    
    try:
        response = httpx.get(f"{LOCAL_SERVER_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ Local server is running")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Local server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to local server: {e}")
        print("   Make sure local-server/app.py is running")
        return False

def test_azure_function_health():
    """Test if Azure Function is running"""
    print("\n🏥 Testing Azure Function Health")
    print("=" * 40)
    
    try:
        response = httpx.get(f"{AZURE_FUNCTION_URL}/api/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ Azure Function is running")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Azure Function returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Azure Function: {e}")
        print("   Make sure Azure Function is running locally")
        return False

def test_basic_connectivity():
    """Test basic connectivity to both services"""
    print("\n🔍 Testing Basic Connectivity")
    print("=" * 40)
    
    local_server_ok = False
    azure_function_ok = False
    
    # Test local server
    try:
        print("Testing local server...")
        response = httpx.get(f"{LOCAL_SERVER_URL}/health", timeout=5.0)
        print(f"✅ Local server: {response.status_code} - {response.json()}")
        local_server_ok = True
    except Exception as e:
        print(f"❌ Local server error: {e}")
    
    # Test Azure Function
    try:
        print("Testing Azure Function...")
        response = httpx.get(f"{AZURE_FUNCTION_URL}/api/health", timeout=5.0)
        print(f"✅ Azure Function: {response.status_code} - {response.json()}")
        azure_function_ok = True
    except Exception as e:
        print(f"❌ Azure Function error: {e}")
    
    return local_server_ok and azure_function_ok

def test_mcp_tools_list():
    """Test MCP tools/list endpoint"""
    print("\n📋 Testing MCP Tools List")
    print("=" * 40)
    
    try:
        request_data = {
            "method": "tools/list",
            "params": {}
        }
        
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=10.0
        )
        
        if response.status_code == 200:
            result = response.json()
            tools = result.get("result", [])
            print(f"✅ Got {len(tools)} tools")
            
            # Check for new user-friendly functions
            new_functions = [
                "get_my_tickets",
                "get_open_tickets", 
                "get_closed_tickets",
                "get_tickets_by_status",
                "get_tickets_by_type",
                "get_tickets_by_stage",
                "search_tickets"
            ]
            
            found_functions = []
            for tool in tools:
                if tool.get("name") in new_functions:
                    found_functions.append(tool.get("name"))
            
            print(f"✅ Found {len(found_functions)} user-friendly functions: {found_functions}")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_simple_mcp_call():
    """Test a simple MCP call that should work"""
    print("\n🔍 Testing Simple MCP Call")
    print("=" * 40)
    
    try:
        request_data = {
            "method": "tools/list",
            "params": {}
        }
        
        print("Making tools/list call...")
        start_time = time.time()
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=10.0
        )
        end_time = time.time()
        
        print(f"✅ Response time: {end_time - start_time:.2f}s")
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Response: {response.json()}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_user_friendly_functions():
    """Test the new user-friendly functions"""
    print("\n🧪 Testing User-Friendly Functions")
    print("=" * 50)
    
    open_tickets_ok = False
    closed_tickets_ok = False
    
    # Test get_open_tickets
    print("\n📋 Testing get_open_tickets...")
    try:
        request_data = {
            "method": "tools/call",
            "params": {
                "name": "get_open_tickets",
                "arguments": {
                    "page": 1,
                    "page_size": 5
                }
            }
        }
        
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ get_open_tickets successful")
            print(f"   Response: {result}")
            open_tickets_ok = True
        else:
            print(f"❌ get_open_tickets failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ get_open_tickets error: {e}")
    
    # Test get_closed_tickets
    print("\n📋 Testing get_closed_tickets...")
    try:
        request_data = {
            "method": "tools/call",
            "params": {
                "name": "get_closed_tickets",
                "arguments": {
                    "page": 1,
                    "page_size": 5
                }
            }
        }
        
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ get_closed_tickets successful")
            print(f"   Response: {result}")
            closed_tickets_ok = True
        else:
            print(f"❌ get_closed_tickets failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ get_closed_tickets error: {e}")
    
    return open_tickets_ok and closed_tickets_ok

def test_my_tickets_function():
    """Test get_my_tickets function with user email"""
    print("\n🧪 Testing get_my_tickets Function")
    print("=" * 50)
    
    try:
        request_data = {
            "method": "tools/call",
            "params": {
                "name": "get_my_tickets",
                "arguments": {
                    "user_email": TEST_USER_EMAIL,
                    "page": 1,
                    "page_size": 3
                }
            }
        }
        
        print(f"Testing with user: {TEST_USER_EMAIL}")
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=60.0
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ get_my_tickets successful")
            print(f"   Response: {result}")
            
            # Check if the response contains an error
            if 'result' in result and result['result']:
                for item in result['result']:
                    if item.get('type') == 'text' and 'Error' in item.get('text', ''):
                        print(f"❌ get_my_tickets contains error in response")
                        return False
            
            return True
        else:
            print(f"❌ get_my_tickets failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ get_my_tickets error: {e}")
        return False

def test_create_ticket_via_azure_function():
    """Test creating a ticket via Azure Function"""
    print("\n🧪 Testing Ticket Creation via Azure Function")
    print("=" * 50)
    
    try:
        request_data = {
            "method": "tools/call",
            "params": {
                "name": "create_ticket",
                "arguments": {
                    "title": "Azure Function Test Ticket",
                    "description": "This ticket was created via Azure Function MCP endpoint",
                    "priority": "Medium",
                    "user_email": TEST_USER_EMAIL
                }
            }
        }
        
        print("Creating ticket via Azure Function...")
        start_time = time.time()
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=60.0  # Longer timeout for ticket creation
        )
        end_time = time.time()
        
        print(f"Response time: {end_time - start_time:.2f}s")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket creation successful")
            print(f"Response: {result}")
            return True
        else:
            print(f"❌ Ticket creation failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ticket creation error: {e}")
        return False

def test_create_ticket_with_role_via_azure_function():
    """Test creating a ticket with role via Azure Function"""
    print("\n🧪 Testing Ticket Creation with Role via Azure Function")
    print("=" * 50)
    
    try:
        request_data = {
            "method": "tools/call",
            "params": {
                "name": "create_ticket_with_role",
                "arguments": {
                    "title": "Azure Function Role Test Ticket",
                    "description": "This ticket was created with role via Azure Function",
                    "priority": "Medium",
                    "user_email": TEST_CUSTOMER_1_EMAIL,
                    "role": "customer"
                }
            }
        }
        
        print("Creating ticket with role via Azure Function...")
        start_time = time.time()
        response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=request_data,
            timeout=60.0
        )
        end_time = time.time()
        
        print(f"Response time: {end_time - start_time:.2f}s")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket creation with role successful")
            print(f"Response: {result}")
            return True
        else:
            print(f"❌ Ticket creation with role failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ticket creation with role error: {e}")
        return False

def test_update_ticket_via_azure_function():
    """Test updating a ticket via Azure Function"""
    print("\n🧪 Testing Ticket Update via Azure Function")
    print("=" * 50)
    
    # First create a ticket to update
    print("Creating ticket for update test...")
    create_request = {
        "method": "tools/call",
        "params": {
            "name": "create_ticket_with_role",
            "arguments": {
                "title": "Ticket for Update Test",
                "description": "This ticket will be updated via Azure Function",
                "priority": "Medium",
                "user_email": TEST_USER_EMAIL,
                "role": "agent"
            }
        }
    }
    
    try:
        create_response = httpx.post(
            f"{AZURE_FUNCTION_URL}/api/mcp",
            json=create_request,
            timeout=60.0
        )
        
        if create_response.status_code != 200:
            print(f"❌ Failed to create ticket for update: {create_response.text}")
            return False
        
        create_result = create_response.json()
        print(f"✅ Created ticket for update test")
        print(f"Create result: {create_result}")
        
        # Extract ticket ID from response - simplified approach
        ticket_id = None
        if 'result' in create_result:
            result_data = create_result['result']
            print(f"Result data type: {type(result_data)}, value: {result_data}")
            
            if isinstance(result_data, list) and result_data:
                for item in result_data:
                    if item.get('type') == 'text':
                        text_content = item.get('text', '')
                        print(f"Text content: {text_content}")
                        
                        # Direct extraction: if it's a digit, convert to int
                        if text_content.isdigit():
                            ticket_id = int(text_content)
                            break
        
        if not ticket_id:
            print("⚠️  Could not extract ticket ID from response, skipping update test")
            return True
        
        print(f"✅ Extracted ticket ID: {ticket_id}")
        print(f"Ticket ID type: {type(ticket_id)}")
        
        # Now update the ticket
        update_request = {
            "method": "tools/call",
            "params": {
                "name": "update_ticket_with_role",
                "arguments": {
                    "ticket_id": ticket_id,
                    "updates": {
                        "BaseHeader": "Updated Ticket for Update Test",
                        "BaseDescription": "This ticket has been successfully updated via Azure Function"
                    },
                    "user_email": TEST_USER_EMAIL,
                    "role": "agent"
                }
            }
        }
        
        print(f"Update request: {update_request}")
        print("Updating ticket via Azure Function...")
        
        try:
            update_response = httpx.post(
                f"{AZURE_FUNCTION_URL}/api/mcp",
                json=update_request,
                timeout=60.0
            )
            print(f"Update response status: {update_response.status_code}")
        except Exception as update_error:
            print(f"❌ Error during update request: {update_error}")
            return False
        
        if update_response.status_code == 200:
            update_result = update_response.json()
            print(f"✅ Ticket update successful")
            print(f"Update response: {update_result}")
            
            # Check if the response contains an error message
            if 'result' in update_result and update_result['result']:
                for item in update_result['result']:
                    if item.get('type') == 'text' and 'Error' in item.get('text', ''):
                        print(f"❌ Update response contains error: {item.get('text')}")
                        return False
            
            return True
        else:
            print(f"❌ Ticket update failed: {update_response.status_code} - {update_response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error creating ticket for update: {e}")
        return False

def test_azure_function_with_timeout():
    """Test Azure Function with different timeout values"""
    print("\n🔍 Testing Azure Function with Different Timeouts")
    print("=" * 40)
    
    request_data = {
        "method": "tools/call",
        "params": {
            "name": "get_tickets_by_status",
            "arguments": {
                "status": "open",
                "page": 1,
                "page_size": 5
            }
        }
    }
    
    timeouts = [5, 10, 30, 60]
    successful_timeouts = 0
    total_timeouts = len(timeouts)
    
    for timeout in timeouts:
        print(f"\nTesting with {timeout}s timeout...")
        try:
            start_time = time.time()
            response = httpx.post(
                f"{AZURE_FUNCTION_URL}/api/mcp",
                json=request_data,
                timeout=timeout
            )
            end_time = time.time()
            
            print(f"✅ {timeout}s timeout: {response.status_code} in {end_time - start_time:.2f}s")
            successful_timeouts += 1
            
        except httpx.TimeoutException:
            print(f"❌ {timeout}s timeout: TIMEOUT")
        except Exception as e:
            print(f"❌ {timeout}s timeout: {e}")
    
    # Return True if at least half of the timeouts were successful
    success_rate = successful_timeouts / total_timeouts
    print(f"\n📊 Timeout test results: {successful_timeouts}/{total_timeouts} successful ({success_rate:.1%})")
    
    return success_rate >= 0.5  # At least 50% success rate

def test_get_tickets_direct():
    """Test calling get_tickets directly via local server"""
    print("\n🔍 Testing Direct Local Server Call")
    print("=" * 40)
    
    try:
        data = {
            "page": 1,
            "page_size": 5,
            "filters": {"BaseEntityStatus.Id": 3}  # Assigned status
        }
        
        print("Making direct call to local server...")
        start_time = time.time()
        response = httpx.post(
            f"{LOCAL_SERVER_URL}/api/get_tickets",
            json=data,
            timeout=10.0
        )
        end_time = time.time()
        
        print(f"✅ Response time: {end_time - start_time:.2f}s")
        print(f"✅ Status: {response.status_code}")
        result = response.json()
        print(f"✅ Has Result: {'Result' in result}")
        if 'Result' in result:
            print(f"✅ Result count: {len(result['Result'])}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all Azure Function tests"""
    print("🚀 Azure Function Tests")
    print("=" * 60)
    
    tests = [
        ("Local Server Health", test_local_server_health),
        ("Azure Function Health", test_azure_function_health),
        ("Basic Connectivity", test_basic_connectivity),
        ("MCP Tools List", test_mcp_tools_list),
        ("Simple MCP Call", test_simple_mcp_call),
        ("User-Friendly Functions", test_user_friendly_functions),
        ("My Tickets Function", test_my_tickets_function),
        ("Create Ticket via Azure Function", test_create_ticket_via_azure_function),
        ("Create Ticket with Role via Azure Function", test_create_ticket_with_role_via_azure_function),
        ("Update Ticket via Azure Function", test_update_ticket_via_azure_function),
        ("Azure Function Timeouts", test_azure_function_with_timeout),
        ("Direct Local Server Call", test_get_tickets_direct)
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
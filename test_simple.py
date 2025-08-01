#!/usr/bin/env python3
"""
Simple test script to verify basic NSP connectivity
Run this before running the full test suite
"""

import os
import sys
import requests
import time
from dotenv import load_dotenv

# Add local-server to path
sys.path.append('local-server')

# Load environment variables
load_dotenv('local-server/.env')

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
        
        # Get environment variables
        base_url = os.getenv('NSP_BASE_URL')
        username = os.getenv('NSP_USERNAME')
        password = os.getenv('NSP_PASSWORD')
        
        # Create client
        client = NSPClient(base_url=base_url, username=username, password=password)
        
        # Test authentication
        print("   Testing authentication...")
        auth_result = client.authenticate()
        
        if auth_result:
            print("✅ Authentication successful!")
            
            # Test a simple API call
            print("   Testing basic API call...")
            # Test with GetEntityListByQuery instead of GetEntityTypes
            # Include columns to avoid SortOrder issues
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
            
            # Debug: Print the actual response structure
            #print(f"   Debug: Response keys: {list(result.keys()) if result else 'None'}")
            #print(f"   Debug: Response type: {type(result)}")
            #if result:
            #    print(f"   Debug: Response preview: {str(result)[:200]}...")
            
            if result and result.get('Data') is not None:
                print(f"✅ API call successful! Found {len(result.get('Data', []))} tickets")
                return True
            else:
                print("❌ API call failed or returned no data")
                return False
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing NSP connectivity: {e}")
        return False

def test_server_startup():
    """Test that the Flask server can start"""
    print("\n🚀 Testing server startup...")
    
    try:
        import subprocess
        
        # Start server in background
        server_process = subprocess.Popen([
            sys.executable, 'local-server/app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait longer for server to start and try multiple times
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(2)  # Wait 2 seconds between attempts
            
            try:
                response = requests.get('http://localhost:5000/health', timeout=3)
                if response.status_code == 200:
                    print("✅ Server started and responding!")
                    server_process.terminate()
                    return True
                else:
                    print(f"   Attempt {attempt + 1}: Server responded with status {response.status_code}")
            except requests.exceptions.RequestException:
                print(f"   Attempt {attempt + 1}: Server not responding yet...")
        
        print("❌ Server failed to start after multiple attempts")
        server_process.terminate()
        return False
            
    except Exception as e:
        print(f"❌ Error testing server startup: {e}")
        return False

def main():
    """Run all simple tests"""
    print("🧪 NSP MCP Connector - Simple Connectivity Tests")
    print("=" * 50)
    
    tests = [
        ("Environment Configuration", test_environment),
        ("NSP API Connectivity", test_nsp_connectivity),
        ("Server Startup", test_server_startup)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! You're ready to run the full test suite.")
        print("\nNext steps:")
        print("1. Run: python test_local_server.py")
        print("2. Or start the server manually: python local-server/app.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues before proceeding.")
    
    return passed == len(results)

if __name__ == "__main__":
    main() 
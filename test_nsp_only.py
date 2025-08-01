#!/usr/bin/env python3
"""
Simple NSP connectivity test only
"""

import os
import sys
from dotenv import load_dotenv

# Add local-server to path
sys.path.append('local-server')

# Load environment variables
load_dotenv('local-server/.env')

def test_nsp_connectivity():
    """Test basic connectivity to NSP API"""
    print("🌐 Testing NSP API connectivity...")
    
    try:
        from nsp_client import NSPClient
        
        # Get environment variables
        base_url = os.getenv('NSP_BASE_URL')
        username = os.getenv('NSP_USERNAME')
        password = os.getenv('NSP_PASSWORD')
        
        print(f"   Base URL: {base_url}")
        print(f"   Username: {username}")
        print(f"   Password: {'*' * len(password) if password else 'None'}")
        
        # Create client
        client = NSPClient(base_url=base_url, username=username, password=password)
        
        # Test authentication
        print("\n   Testing authentication...")
        auth_result = client.authenticate()
        
        if auth_result:
            print("✅ Authentication successful!")
            
            # Test a simple API call
            print("\n   Testing basic API call...")
            result = client.get_entity_types()
            
            if result and result.get('Result'):
                print(f"✅ API call successful! Found {len(result['Result'])} entity types")
                print(f"   Entity types: {result['Result']}")
                return True
            else:
                print("❌ API call failed or returned no data")
                print(f"   Response: {result}")
                return False
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing NSP connectivity: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 NSP Connectivity Test Only")
    print("=" * 40)
    
    success = test_nsp_connectivity()
    
    if success:
        print("\n🎉 NSP connectivity test passed!")
    else:
        print("\n⚠️  NSP connectivity test failed!") 
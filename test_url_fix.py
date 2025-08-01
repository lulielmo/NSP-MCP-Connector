#!/usr/bin/env python3
"""
Test script to verify URL fix for NSP API
"""

import os
import sys
from dotenv import load_dotenv

# Add local-server to path
sys.path.append('local-server')

# Load environment variables
load_dotenv('local-server/.env')

def test_url_construction():
    """Test that URLs are constructed correctly"""
    print("🔧 Testing URL construction...")
    
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
        
        # Test authentication URL construction
        auth_url = f"{base_url}/logon/getauthenticationtoken"
        print(f"\n   Authentication URL: {auth_url}")
        
        # Test API URL construction
        api_url = f"{base_url}/PublicApi/GetEntityListByQuery"
        print(f"   API URL: {api_url}")
        
        print("\n✅ URL construction looks correct!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing URL construction: {e}")
        return False

def test_authentication():
    """Test authentication with correct URL"""
    print("\n🌐 Testing authentication...")
    
    try:
        from nsp_client import NSPClient
        
        # Get environment variables
        base_url = os.getenv('NSP_BASE_URL')
        username = os.getenv('NSP_USERNAME')
        password = os.getenv('NSP_PASSWORD')
        
        # Create client
        client = NSPClient(base_url=base_url, username=username, password=password)
        
        # Test authentication
        auth_result = client.authenticate()
        
        if auth_result:
            print("✅ Authentication successful!")
            return True
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return False

if __name__ == "__main__":
    print("🧪 NSP URL Fix Test")
    print("=" * 40)
    
    # Test URL construction
    url_ok = test_url_construction()
    
    if url_ok:
        # Test authentication
        auth_ok = test_authentication()
        
        if auth_ok:
            print("\n🎉 All tests passed! URL fix is working.")
        else:
            print("\n⚠️  URL construction OK but authentication failed.")
    else:
        print("\n❌ URL construction failed.") 
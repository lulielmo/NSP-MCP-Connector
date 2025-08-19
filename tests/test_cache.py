#!/usr/bin/env python3
"""
Test script for user cache functionality
Run this to verify that the cache is working correctly
"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables from local-server directory
load_dotenv('../local-server/.env')

# Configuration
LOCAL_SERVER_URL = "http://localhost:5000"

# Get test user emails from environment variables
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL')
TEST_CUSTOMER_1_EMAIL = os.getenv('TEST_CUSTOMER_1_EMAIL')
TEST_CUSTOMER_2_EMAIL = os.getenv('TEST_CUSTOMER_2_EMAIL')

# Use first available test email
TEST_EMAIL = TEST_USER_EMAIL or TEST_CUSTOMER_1_EMAIL or "user.name@company.com"

def check_environment_config():
    """Check and display environment configuration"""
    print("\n🔧 Environment Configuration Check")
    print("-" * 30)
    
    env_vars = {
        'TEST_USER_EMAIL': TEST_USER_EMAIL,
        'TEST_CUSTOMER_1_EMAIL': TEST_CUSTOMER_1_EMAIL, 
        'TEST_CUSTOMER_2_EMAIL': TEST_CUSTOMER_2_EMAIL
    }
    
    configured_count = sum(1 for v in env_vars.values() if v)
    print(f"Configured test emails: {configured_count}/3")
    
    for var_name, var_value in env_vars.items():
        status = "✅" if var_value else "❌"
        value_display = var_value if var_value else "Not set"
        print(f"  {status} {var_name}: {value_display}")
    
    if configured_count == 0:
        print("\n⚠️  No test emails configured!")
        print("💡 Add these to local-server/.env:")
        print("   TEST_USER_EMAIL=your.email@company.com")
        print("   TEST_CUSTOMER_1_EMAIL=customer1@company.com")
        print("   TEST_CUSTOMER_2_EMAIL=customer2@company.com")
    
    return configured_count > 0

def diagnose_nsp_connection():
    """Provide diagnostic information for NSP connection issues"""
    print("\n🔍 NSP Connection Diagnostic")
    print("-" * 30)
    
    # Check required NSP environment variables
    nsp_vars = {
        'NSP_BASE_URL': os.getenv('NSP_BASE_URL'),
        'NSP_USERNAME': os.getenv('NSP_USERNAME'),
        'NSP_PASSWORD': '***' if os.getenv('NSP_PASSWORD') else None
    }
    
    print("NSP Configuration:")
    for var_name, var_value in nsp_vars.items():
        status = "✅" if var_value else "❌"
        value_display = var_value if var_value else "Not set"
        print(f"  {status} {var_name}: {value_display}")
    
    missing_vars = [k for k, v in nsp_vars.items() if not v]
    if missing_vars:
        print(f"\n⚠️  Missing NSP configuration: {', '.join(missing_vars)}")
        print("💡 Add these to local-server/.env:")
        print("   NSP_BASE_URL=http://your-nsp-server:1900/api/PublicApi/")
        print("   NSP_USERNAME=your_nsp_username")
        print("   NSP_PASSWORD=your_nsp_password")
        return False
    
    print("\n✅ NSP configuration appears complete")
    print("💡 If authentication still fails, check:")
    print("   - NSP server is running and accessible")
    print("   - Username/password are correct")
    print("   - Network connectivity to NSP server")
    return True

def test_cache_functionality():
    """Test the user cache functionality"""
    print("🧪 Testing User Cache Functionality")
    print("=" * 50)
    
    # Check environment configuration first
    env_ok = check_environment_config()
    
    # Test 1: Check health endpoint includes cache stats
    print("\n1. Testing health endpoint with cache stats...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/health")
        if response.status_code == 200:
            data = response.json()
            if "user_cache" in data:
                print("✅ Health endpoint includes cache stats")
                print(f"   Cache stats: {data['user_cache']}")
                print(f"   NSP Authentication: {data.get('authenticated', 'Unknown')}")
            else:
                print("❌ Health endpoint missing cache stats")
        elif response.status_code == 401:
            print("❌ Health endpoint failed: 401 Unauthorized")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'NSP Authentication failed')}")
            except:
                print("   Error: NSP Authentication failed")
            print("   💡 Check NSP credentials in local-server/.env:")
            print("      NSP_BASE_URL, NSP_USERNAME, NSP_PASSWORD")
            print("   💡 Make sure NSP is accessible and credentials are correct")
            print("   ⚠️  Continuing with remaining tests (may also fail)...")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Raw response: {response.text}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        print("   💡 Make sure local server is running: python local-server/app.py")
    
    # Test 2: Get initial cache stats
    print("\n2. Getting initial cache stats...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/api/cache/stats")
        if response.status_code == 200:
            initial_stats = response.json()["data"]
            print("✅ Cache stats retrieved")
            print(f"   Initial stats: {initial_stats}")
        elif response.status_code == 401:
            print("❌ Cache stats failed: 401 Unauthorized (NSP Authentication failed)")
            print("   ⚠️  Cannot continue with cache tests without NSP authentication")
            return
        else:
            print(f"❌ Cache stats failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Raw response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Cache stats error: {e}")
        return
    
    # Test 3: Clear cache
    print("\n3. Clearing cache...")
    try:
        response = requests.post(f"{LOCAL_SERVER_URL}/api/cache/clear")
        if response.status_code == 200:
            print("✅ Cache cleared successfully")
        else:
            print(f"❌ Cache clear failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cache clear error: {e}")
    
    # Test 4: First user lookup (should be cache miss)
    print(f"\n4. First user lookup (cache miss): {TEST_EMAIL}")
    start_time = time.time()
    try:
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/get_user_by_email",
            json={"email": TEST_EMAIL}
        )
        first_lookup_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                user_data = result['data']
                user_name = user_data.get('FullName', 'Unknown')
                user_id = user_data.get('Id', 'Unknown')
                user_email = user_data.get('Email', TEST_EMAIL)
                print(f"✅ First lookup successful ({first_lookup_time:.2f}s)")
                print(f"   User found: {user_name} (ID: {user_id}) <{user_email}>")
            else:
                print(f"⚠️  First lookup returned no user: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ First lookup failed: {response.status_code}")
    except Exception as e:
        print(f"❌ First lookup error: {e}")
        return
    
    # Test 5: Second user lookup (should be cache hit)
    print(f"\n5. Second user lookup (cache hit): {TEST_EMAIL}")
    start_time = time.time()
    try:
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/get_user_by_email",
            json={"email": TEST_EMAIL}
        )
        second_lookup_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                user_data = result['data']
                user_name = user_data.get('FullName', 'Unknown')
                user_id = user_data.get('Id', 'Unknown')
                user_email = user_data.get('Email', TEST_EMAIL)
                print(f"✅ Second lookup successful ({second_lookup_time:.2f}s)")
                print(f"   User found: {user_name} (ID: {user_id}) <{user_email}>")
                
                # Compare timing
                if second_lookup_time < first_lookup_time * 0.5:
                    print(f"🚀 Cache hit detected! Second lookup {first_lookup_time/second_lookup_time:.1f}x faster")
                else:
                    print("⚠️  Second lookup not significantly faster - cache might not be working")
            else:
                print(f"⚠️  Second lookup returned no user: {result.get('error', 'Unknown error')}")
        else:
            print(f"❌ Second lookup failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Second lookup error: {e}")
    
    # Test 6: Check cache stats after lookups
    print("\n6. Checking cache stats after lookups...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/api/cache/stats")
        if response.status_code == 200:
            final_stats = response.json()["data"]
            print("✅ Final cache stats retrieved")
            print(f"   Final stats: {final_stats}")
            
            if final_stats["active_entries"] > initial_stats["active_entries"]:
                print("🎯 Cache entries increased - caching is working!")
            else:
                print("⚠️  Cache entries didn't increase - check implementation")
        else:
            print(f"❌ Final cache stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Final cache stats error: {e}")
    
    # Test 7: Cache warming
    print(f"\n7. Testing cache warming...")
    try:
        # Use available test emails from environment
        warm_emails = [email for email in [TEST_USER_EMAIL, TEST_CUSTOMER_1_EMAIL, TEST_CUSTOMER_2_EMAIL] if email]
        if not warm_emails:
            warm_emails = [TEST_EMAIL]  # Fallback to default
        
        # Add a likely non-existent email to test failure handling
        warm_emails.append("system.health@example.com")
        response = requests.post(
            f"{LOCAL_SERVER_URL}/api/cache/warm",
            json={"emails": warm_emails}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Cache warming completed")
            print(f"   Message: {result['message']}")
            print("   Results:")
            for email, success in result['results'].items():
                status = "✅ Found" if success else "❌ Not found"
                print(f"     {status}: {email}")
        else:
            print(f"❌ Cache warming failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cache warming error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Cache functionality test completed!")
    print("\nNext steps:")
    print("- Check the local server logs for cache HIT/MISS messages")
    print("- Monitor performance improvements in your MCP calls")
    print("- Consider implementing cache pre-warming for common users")

if __name__ == "__main__":
    print("NSP MCP Connector - Cache Test")
    print("Make sure the local server is running on localhost:5000")
    print("\nTest Configuration:")
    print(f"  Primary test email: {TEST_EMAIL}")
    if TEST_USER_EMAIL:
        print(f"  TEST_USER_EMAIL: {TEST_USER_EMAIL}")
    if TEST_CUSTOMER_1_EMAIL:
        print(f"  TEST_CUSTOMER_1_EMAIL: {TEST_CUSTOMER_1_EMAIL}")
    if TEST_CUSTOMER_2_EMAIL:
        print(f"  TEST_CUSTOMER_2_EMAIL: {TEST_CUSTOMER_2_EMAIL}")
    
    if not any([TEST_USER_EMAIL, TEST_CUSTOMER_1_EMAIL, TEST_CUSTOMER_2_EMAIL]):
        print("  ⚠️  No environment variables found - using fallback email")
        print("  💡 Set TEST_USER_EMAIL, TEST_CUSTOMER_1_EMAIL, or TEST_CUSTOMER_2_EMAIL in local-server/.env")
    
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    test_cache_functionality()

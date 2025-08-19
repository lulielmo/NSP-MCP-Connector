#!/usr/bin/env python3
"""
Test script for token pre-warming functionality
Run this to verify that the token pre-warming system is working correctly
"""

import requests
import json
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

# Load environment variables from local-server directory
load_dotenv('../local-server/.env')

# Configuration
LOCAL_SERVER_URL = "http://localhost:5000"

def check_prewarming_config():
    """Check and display pre-warming configuration"""
    print("\n🔧 Pre-warming Configuration Check")
    print("-" * 35)
    
    prewarming_enabled = os.getenv('PREWARMING_ENABLED', 'true').lower() == 'true'
    refresh_buffer = os.getenv('PREWARMING_REFRESH_BUFFER', '5')
    
    print(f"PREWARMING_ENABLED: {'✅ Enabled' if prewarming_enabled else '❌ Disabled'}")
    print(f"PREWARMING_REFRESH_BUFFER: {refresh_buffer} minutes")
    
    if not prewarming_enabled:
        print("\n⚠️  Pre-warming is disabled!")
        print("💡 Set PREWARMING_ENABLED=true in local-server/.env to enable")
        return False
    
    return True

def test_prewarming_status():
    """Test pre-warming status endpoint"""
    print("\n1. Testing pre-warming status...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/api/prewarming/status")
        
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                status = data["data"]
                print("✅ Pre-warming status retrieved")
                print(f"   Active: {'🟢 Yes' if status['prewarming_active'] else '🔴 No'}")
                print(f"   Refresh buffer: {status['refresh_buffer_minutes']} minutes")
                
                token_info = status["token"]
                print(f"   Token status: {'✅ Valid' if token_info['has_token'] and not token_info['is_expired'] else '❌ Invalid'}")
                print(f"   Token expires: {token_info['expires_at']}")
                print(f"   Username: {token_info['username']}")
                
                schedule = status["schedule"]
                if schedule["next_refresh_in_minutes"] is not None:
                    print(f"   Next refresh in: {schedule['next_refresh_in_minutes']:.1f} minutes")
                    print(f"   Refresh scheduled: {schedule['refresh_at']}")
                else:
                    print("   Next refresh: Not scheduled")
                
                return status
            else:
                print(f"❌ Status request failed: {data.get('error', 'Unknown error')}")
        elif response.status_code == 401:
            print("❌ Pre-warming status failed: 401 Unauthorized (NSP Authentication failed)")
            print("   💡 Check NSP credentials and ensure NSP is accessible")
        else:
            print(f"❌ Pre-warming status failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Raw response: {response.text}")
    except Exception as e:
        print(f"❌ Pre-warming status error: {e}")
        print("   💡 Make sure local server is running: python local-server/app.py")
    
    return None

def test_health_with_prewarming():
    """Test health endpoint includes pre-warming info"""
    print("\n2. Testing health endpoint with pre-warming info...")
    try:
        response = requests.get(f"{LOCAL_SERVER_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            if "prewarming" in data:
                prewarming = data["prewarming"]
                print("✅ Health endpoint includes pre-warming info")
                print(f"   Pre-warming active: {'🟢 Yes' if prewarming['active'] else '🔴 No'}")
                
                if prewarming["next_refresh_in_minutes"] is not None:
                    print(f"   Next refresh in: {prewarming['next_refresh_in_minutes']:.1f} minutes")
                else:
                    print("   Next refresh: Not scheduled")
            else:
                print("❌ Health endpoint missing pre-warming info")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")

def test_force_refresh():
    """Test manual token refresh"""
    print("\n3. Testing manual token refresh...")
    try:
        print("   Triggering manual refresh...")
        response = requests.post(f"{LOCAL_SERVER_URL}/api/prewarming/refresh")
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                print("✅ Manual token refresh initiated successfully")
                print(f"   Message: {result['message']}")
                
                # Wait a moment for refresh to complete
                print("   Waiting 3 seconds for refresh to complete...")
                time.sleep(3)
                
                # Check status after refresh
                print("   Checking status after refresh...")
                status_response = requests.get(f"{LOCAL_SERVER_URL}/api/prewarming/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data["success"]:
                        token_info = status_data["data"]["token"]
                        print(f"   Token after refresh: {'✅ Valid' if token_info['has_token'] and not token_info['is_expired'] else '❌ Invalid'}")
                        print(f"   New expiry: {token_info['expires_at']}")
                    else:
                        print("   ⚠️  Could not verify refresh result")
                else:
                    print("   ⚠️  Could not check status after refresh")
            else:
                print(f"❌ Manual refresh failed: {result.get('error', 'Unknown error')}")
        elif response.status_code == 400:
            error_data = response.json()
            print(f"❌ Manual refresh failed: {error_data.get('error', 'Bad request')}")
        else:
            print(f"❌ Manual refresh failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Manual refresh error: {e}")

def test_prewarming_control():
    """Test starting and stopping pre-warming"""
    print("\n4. Testing pre-warming start/stop control...")
    
    try:
        # Test stop
        print("   Testing stop...")
        response = requests.post(f"{LOCAL_SERVER_URL}/api/prewarming/stop")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Stop: {result['message']}")
        else:
            print(f"   ❌ Stop failed: {response.status_code}")
        
        # Brief pause
        time.sleep(1)
        
        # Test start
        print("   Testing start...")
        response = requests.post(f"{LOCAL_SERVER_URL}/api/prewarming/start")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Start: {result['message']}")
        else:
            print(f"   ❌ Start failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Pre-warming control error: {e}")

def test_token_persistence():
    """Test that token remains valid across multiple calls"""
    print("\n5. Testing token persistence across multiple calls...")
    
    call_times = []
    
    for i in range(3):
        print(f"   Call {i+1}/3...")
        start_time = time.time()
        
        try:
            # Make a simple API call that requires authentication
            response = requests.get(f"{LOCAL_SERVER_URL}/api/cache/stats")
            call_time = time.time() - start_time
            call_times.append(call_time)
            
            if response.status_code == 200:
                print(f"     ✅ Success in {call_time:.2f}s")
            else:
                print(f"     ❌ Failed: {response.status_code}")
                
        except Exception as e:
            call_time = time.time() - start_time
            call_times.append(call_time)
            print(f"     ❌ Error in {call_time:.2f}s: {e}")
        
        # Small delay between calls
        if i < 2:
            time.sleep(1)
    
    # Analyze timing
    if len(call_times) >= 2:
        avg_time = sum(call_times) / len(call_times)
        print(f"   📊 Average call time: {avg_time:.2f}s")
        
        if avg_time < 5:  # Should be fast with pre-warming
            print("   🚀 Excellent! All calls were fast (token pre-warming working)")
        elif avg_time < 10:
            print("   ⚠️  Moderate timing - pre-warming may be partially working")
        else:
            print("   ❌ Slow calls detected - pre-warming may not be working properly")

def test_prewarming_functionality():
    """Main test function for token pre-warming"""
    print("🔥 Testing Token Pre-warming Functionality")
    print("=" * 50)
    
    # Check configuration
    config_ok = check_prewarming_config()
    if not config_ok:
        print("\n⚠️  Pre-warming configuration issues detected")
        print("   Tests may not work as expected")
    
    # Test status endpoint
    initial_status = test_prewarming_status()
    
    # Test health endpoint
    test_health_with_prewarming()
    
    # Test manual refresh (if pre-warming is active)
    if initial_status and initial_status.get('prewarming_active'):
        test_force_refresh()
        
        # Test control functions
        test_prewarming_control()
        
        # Test token persistence
        test_token_persistence()
    else:
        print("\n⚠️  Pre-warming not active - skipping advanced tests")
        print("   Check NSP connection and configuration")
    
    print("\n" + "=" * 50)
    print("🏁 Token pre-warming test completed!")
    print("\nKey benefits of pre-warming:")
    print("- Eliminates 15-20 second NSP authentication delays")
    print("- Keeps tokens fresh automatically") 
    print("- Improves MCP tool response times dramatically")
    print("- Reduces timeout issues in Copilot Studio")
    print("\nNext steps:")
    print("- Monitor local server logs for pre-warming activity")
    print("- Test MCP tools for improved response times")
    print("- Check that tokens refresh automatically before expiry")

if __name__ == "__main__":
    print("NSP MCP Connector - Token Pre-warming Test")
    print("Make sure the local server is running on localhost:5000")
    
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    test_prewarming_functionality()

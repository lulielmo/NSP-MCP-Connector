#!/usr/bin/env python3
"""
Test User Scenario - Simulates real user interactions with NSP
Tests the complete chain: authentication -> user lookup -> ticket listing
"""

import os
import sys
import requests
import json
import time
from typing import Dict, Any, Optional

# Add local-server to path for imports
sys.path.append('local-server')

from nsp_client import NSPClient

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")

def print_step(step: str, status: str = "⏳"):
    """Print a formatted step"""
    print(f"{status} {step}")

def print_success(message: str):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message: str):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message: str):
    """Print info message"""
    print(f"ℹ️  {message}")

def load_environment():
    """Load environment variables from env file"""
    env_file = 'local-server/.env'  # Use .env file
    
    if not os.path.exists(env_file):
        print_error(f"Environment file not found: {env_file}")
        print_info("Please create env.test file with your NSP configuration")
        return None
    
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    return env_vars

def test_user_scenario():
    """Test complete user scenario: auth -> user lookup -> ticket listing"""
    print_header("NSP User Scenario Test")
    print_info("Simulating: User wants to see their open tickets as end user")
    
    # Load environment
    print_step("Loading environment configuration...")
    env = load_environment()
    if not env:
        return False
    
    # Check required environment variables
    required_vars = ['NSP_BASE_URL', 'NSP_USERNAME', 'NSP_PASSWORD', 'TEST_USER_EMAIL']
    for var in required_vars:
        if var not in env or not env[var]:
            print_error(f"Missing required environment variable: {var}")
            return False
    
    print_success("Environment configuration loaded")
    
    # Initialize NSP client
    print_step("Initializing NSP client...")
    try:
        client = NSPClient(
            base_url=env['NSP_BASE_URL'],
            username=env['NSP_USERNAME'],
            password=env['NSP_PASSWORD']
        )
        print_success("NSP client initialized")
    except Exception as e:
        print_error(f"Failed to initialize NSP client: {e}")
        return False
    
    # Step 1: Authenticate
    print_step("Step 1: Authenticating with NSP API...")
    try:
        if client.authenticate():
            print_success("Authentication successful")
            token_info = client.get_token_info()
            print_info(f"Token expires: {token_info['expires']}")
        else:
            print_error("Authentication failed")
            return False
    except Exception as e:
        print_error(f"Authentication error: {e}")
        return False
    
    # Step 2: Look up test user
    test_user_email = env['TEST_USER_EMAIL']
    print_step(f"Step 2: Looking up test user: {test_user_email}")
    try:
        user = client.get_user_by_email(test_user_email)
        if user:
            print_success(f"User found: {user.get('DisplayName', 'Unknown')} (ID: {user.get('Id')})")
            print_info(f"User details: {json.dumps(user, indent=2, default=str)}")
        else:
            print_error(f"User not found: {test_user_email}")
            print_info("Please check TEST_USER_EMAIL in .env file")
            return False
    except Exception as e:
        print_error(f"User lookup error: {e}")
        return False
    
    # Step 3: Get user's tickets as customer (end user)
    print_step("Step 3: Getting user's tickets as customer (end user)...")
    try:
        tickets_result = client.get_tickets_by_user_role(
            user_email=test_user_email,
            role="customer",
            page=1,
            page_size=10
        )
        
        if tickets_result and 'Data' in tickets_result:
            tickets = tickets_result['Data']
            total_tickets = tickets_result.get('Total', 0)
            print_success(f"Found {len(tickets)} tickets (total: {total_tickets})")
            
            if tickets:
                print_info("Sample tickets:")
                for i, ticket in enumerate(tickets[:3], 1):  # Show first 3 tickets
                    print(f"  {i}. Ticket #{ticket.get('Id')}: {ticket.get('BaseHeader', 'No title')}")
                    print(f"     Status: {ticket.get('BaseStatus', 'Unknown')}")
                    print(f"     Created: {ticket.get('CreatedDate', 'Unknown')}")
                    print(f"     Type: {ticket.get('Type', 'Unknown')}")
                    print()
            else:
                print_info("No tickets found for this user as customer")
        else:
            print_error("Failed to retrieve tickets")
            return False
            
    except Exception as e:
        print_error(f"Ticket retrieval error: {e}")
        return False
    
    # Step 4: Get user's tickets as agent (optional)
    print_step("Step 4: Getting user's tickets as agent (optional)...")
    try:
        agent_tickets_result = client.get_tickets_by_user_role(
            user_email=test_user_email,
            role="agent",
            page=1,
            page_size=10
        )
        
        if agent_tickets_result and 'Data' in agent_tickets_result:
            agent_tickets = agent_tickets_result['Data']
            total_agent_tickets = agent_tickets_result.get('Total', 0)
            print_success(f"Found {len(agent_tickets)} tickets as agent (total: {total_agent_tickets})")
            
            if agent_tickets:
                print_info("Sample agent tickets:")
                for i, ticket in enumerate(agent_tickets[:3], 1):  # Show first 3 tickets
                    print(f"  {i}. Ticket #{ticket.get('Id')}: {ticket.get('BaseHeader', 'No title')}")
                    print(f"     Status: {ticket.get('BaseStatus', 'Unknown')}")
                    print(f"     Created: {ticket.get('CreatedDate', 'Unknown')}")
                    print(f"     Type: {ticket.get('Type', 'Unknown')}")
                    print()
            else:
                print_info("No tickets found for this user as agent")
        else:
            print_error("Failed to retrieve agent tickets")
            return False
            
    except Exception as e:
        print_error(f"Agent ticket retrieval error: {e}")
        return False
    
    # Step 5: Test local server endpoints (if server is running)
    print_step("Step 5: Testing local server endpoints...")
    try:
        server_url = "http://localhost:5000"
        
        # Test server health
        health_response = requests.get(f"{server_url}/health", timeout=5)
        if health_response.status_code == 200:
            print_success("Local server is running")
            
            # Test user lookup endpoint
            user_response = requests.post(
                f"{server_url}/api/get_user_by_email",
                json={"email": test_user_email},
                timeout=10
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                print_success("User lookup via local server successful")
                print_info(f"User ID: {user_data.get('data', {}).get('Id')}")
            else:
                print_error(f"User lookup via local server failed: {user_response.status_code}")
            
            # Test ticket listing endpoint
            tickets_response = requests.post(
                f"{server_url}/api/get_tickets_by_role",
                json={
                    "user_email": test_user_email,
                    "role": "customer",
                    "page": 1,
                    "page_size": 5
                },
                timeout=10
            )
            
            if tickets_response.status_code == 200:
                tickets_data = tickets_response.json()
                print_success("Ticket listing via local server successful")
                print_info(f"Found {len(tickets_data.get('data', []))} tickets")
            else:
                print_error(f"Ticket listing via local server failed: {tickets_response.status_code}")
                
        else:
            print_info("Local server not running - skipping server tests")
            
    except requests.exceptions.ConnectionError:
        print_info("Local server not running - skipping server tests")
    except Exception as e:
        print_error(f"Server test error: {e}")
    
    print_header("Test Summary")
    print_success("User scenario test completed successfully!")
    print_info("The complete chain works: Authentication -> User Lookup -> Ticket Listing")
    print_info("Ready for Copilot integration testing")
    
    return True

def main():
    """Main function"""
    try:
        success = test_user_scenario()
        if success:
            print("\n🎉 All tests passed! Ready for next steps.")
            print("\nNext steps:")
            print("1. Start local server: python local-server/app.py")
            print("2. Test with Copilot Studio")
            print("3. Deploy to Azure Functions")
        else:
            print("\n❌ Some tests failed. Please check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
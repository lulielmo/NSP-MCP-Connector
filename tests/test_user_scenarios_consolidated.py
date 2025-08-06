#!/usr/bin/env python3
"""
Consolidated test script for user scenarios and user-friendly functions
Combines: test_user_scenario.py, test_user_friendly_functions.py
"""

import os
import sys
import requests
import json
import time
from typing import Dict, Any, Optional

# Add local-server to path for imports
sys.path.append('../local-server')

from nsp_client import NSPClient

# Import the filtering helpers from azure-function directory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../azure-function'))
from nsp_filtering_helpers import (
    create_simple_status_filter,
    create_simple_stage_filter,
    create_entity_type_filter,
    create_my_tickets_filter,
    create_open_tickets_filter,
    create_closed_tickets_filter,
    create_combined_filter,
    format_ticket_summary,
    get_filter_description,
    get_entity_type_id,
    get_entity_type_name,
    get_status_name,
    get_stage_name
)

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
    env_file = '../local-server/.env'  # Use .env file
    
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
    
    # Step 2: Look up user by email
    print_step("Step 2: Looking up user by email...")
    try:
        user_email = env['TEST_USER_EMAIL']
        print_info(f"Looking up user: {user_email}")
        
        # Search for user in Person entity
        search_data = {
            "EntityType": "Person",
            "Page": 1,
            "PageSize": 10,
            "columns": ["Id", "Email", "FirstName", "LastName"],
            "filters": {
                "field": "Email",
                "operator": "eq",
                "value": user_email
            }
        }
        
        result = client._make_request('POST', 'GetEntityListByQuery', search_data)
        
        if result and result.get('Data'):
            users = result['Data']
            if users:
                user = users[0]  # Take first match
                user_id = user.get('Id')
                print_success(f"Found user: {user.get('FirstName')} {user.get('LastName')} (ID: {user_id})")
            else:
                print_error(f"User not found: {user_email}")
                return False
        else:
            print_error("User lookup failed")
            return False
    except Exception as e:
        print_error(f"User lookup error: {e}")
        return False
    
    # Step 3: Get user's tickets
    print_step("Step 3: Getting user's tickets...")
    try:
        # Use the user-friendly filter for "my tickets" with the user ID we found
        my_tickets_filter = create_my_tickets_filter(user_email, user_id)
        print_info(f"Using filter: {my_tickets_filter}")
        
        # Use the get_it_tickets method which properly converts filters to NSP API format
        result = client.get_it_tickets(page=1, page_size=10, filters=my_tickets_filter)
        
        if result and result.get('Data'):
            tickets = result['Data']
            print_success(f"Found {len(tickets)} tickets for user")
            
            # Display ticket summaries
            for i, ticket in enumerate(tickets[:5]):  # Show first 5
                formatted = format_ticket_summary(ticket)
                print_info(f"Ticket {i+1}: {formatted.get('title', 'No title')} - {formatted.get('status', 'Unknown status')}")
            
            if len(tickets) > 5:
                print_info(f"... and {len(tickets) - 5} more tickets")
        else:
            print_info("No tickets found for user")
    except Exception as e:
        print_error(f"Ticket retrieval error: {e}")
        return False
    
    print_success("User scenario completed successfully!")
    return True

def test_filtering_helpers():
    """Test the filtering helper functions"""
    print_header("Testing Filtering Helper Functions")
    print("=" * 50)
    
    # Test 1: Status filter
    print("\n1. Testing status filter:")
    status_filter = create_simple_status_filter("Assigned")
    print(f"   'Assigned' -> {status_filter}")
    
    # Test 2: Stage filter
    print("\n2. Testing stage filter:")
    stage_filter = create_simple_stage_filter("Open", "Ticket")
    print(f"   'Open' for 'Ticket' -> {stage_filter}")
    
    # Test 3: Entity type filter
    print("\n3. Testing entity type filter:")
    entity_filter = create_entity_type_filter("Incident")
    print(f"   'Incident' -> {entity_filter}")
    
    # Test 4: My tickets filter
    print("\n4. Testing my tickets filter:")
    my_filter = create_my_tickets_filter("test@example.com")
    print(f"   'test@example.com' -> {my_filter}")
    
    # Test 5: Open tickets filter
    print("\n5. Testing open tickets filter:")
    open_filter = create_open_tickets_filter()
    print(f"   Open tickets -> {open_filter}")
    
    # Test 6: Closed tickets filter
    print("\n6. Testing closed tickets filter:")
    closed_filter = create_closed_tickets_filter()
    print(f"   Closed tickets -> {closed_filter}")
    
    # Test 7: Combined filter
    print("\n7. Testing combined filter:")
    combined_filter = create_combined_filter(
        status="Assigned",
        entity_type="Ticket",
        stage="Open",
        user_email="test@example.com"
    )
    print(f"   Combined -> {combined_filter}")
    
    # Test 8: Name lookups
    print("\n8. Testing name lookups:")
    print(f"   Entity type 112 -> {get_entity_type_name(112)}")
    print(f"   Status 3 -> {get_status_name(3)}")
    print(f"   Stage 2 for Ticket -> {get_stage_name(2, 'Ticket')}")
    
    # Test 9: Filter description
    print("\n9. Testing filter description:")
    description = get_filter_description(combined_filter)
    print(f"   Description: {description}")
    
    return True

def test_ticket_formatting():
    """Test ticket formatting with sample data"""
    print_header("Testing Ticket Formatting")
    print("=" * 50)
    
    # Sample ticket data (similar to what NSP returns)
    sample_ticket = {
        "Id": 12345,
        "BaseHeader": "Test ärende - Skrivare fungerar inte",
        "BaseDescription": "Skrivaren i rum 301 fungerar inte. När man försöker skriva ut så får man felmeddelande 'Printer not found'. Detta är en ganska lång beskrivning som ska trunkeras om den är för lång.",
        "EntityType.Id": 112,
        "BaseEntityStatus.Id": 3,
        "BaseEntityStage.Id": 2,
        "BaseAgent": "support@example.com",
        "CreatedDate": "2024-01-15T10:30:00Z",
        "Priority": "Medium"
    }
    
    print("\nOriginal ticket data:")
    print(json.dumps(sample_ticket, indent=2, ensure_ascii=False))
    
    print("\nFormatted ticket:")
    formatted = format_ticket_summary(sample_ticket)
    print(json.dumps(formatted, indent=2, ensure_ascii=False))
    
    return True

def test_error_handling():
    """Test error handling for invalid inputs"""
    print_header("Testing Error Handling")
    print("=" * 50)
    
    # Test invalid status
    print("\n1. Invalid status:")
    invalid_status = create_simple_status_filter("InvalidStatus")
    print(f"   'InvalidStatus' -> {invalid_status}")
    
    # Test invalid stage
    print("\n2. Invalid stage:")
    invalid_stage = create_simple_stage_filter("InvalidStage", "Ticket")
    print(f"   'InvalidStage' for 'Ticket' -> {invalid_stage}")
    
    # Test invalid entity type
    print("\n3. Invalid entity type:")
    invalid_entity = create_entity_type_filter("InvalidType")
    print(f"   'InvalidType' -> {invalid_entity}")
    
    # Test case insensitive matching
    print("\n4. Case insensitive matching:")
    status_lower = create_simple_status_filter("assigned")
    print(f"   'assigned' -> {status_lower}")
    
    stage_upper = create_simple_stage_filter("OPEN", "Ticket")
    print(f"   'OPEN' for 'Ticket' -> {stage_upper}")
    
    return True

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    print_header("Testing Edge Cases")
    print("=" * 50)
    
    # Test empty/None inputs
    print("\n1. Empty/None inputs:")
    empty_combined = create_combined_filter()
    print(f"   No parameters -> {empty_combined}")
    
    # Test with only some parameters
    partial_combined = create_combined_filter(status="New", entity_type="Ticket")
    print(f"   Only status and type -> {partial_combined}")
    
    # Test stage without entity type
    stage_only = create_combined_filter(stage="Open")
    print(f"   Only stage -> {stage_only}")
    
    # Test unknown IDs
    print("\n2. Unknown IDs:")
    print(f"   Unknown entity type 999 -> {get_entity_type_name(999)}")
    print(f"   Unknown status 999 -> {get_status_name(999)}")
    print(f"   Unknown stage 999 -> {get_stage_name(999, 'Ticket')}")
    
    return True

def test_real_world_scenario():
    """Test a real-world scenario with actual NSP data"""
    print_header("Real-World Scenario Test")
    print("=" * 50)
    
    # Load environment
    env = load_environment()
    if not env:
        return False
    
    try:
        # Initialize NSP client
        client = NSPClient(
            base_url=env['NSP_BASE_URL'],
            username=env['NSP_USERNAME'],
            password=env['NSP_PASSWORD']
        )
        
        # Authenticate
        if not client.authenticate():
            print_error("Authentication failed")
            return False
        
        print_success("Connected to NSP")
        
        # Test 1: Get open tickets
        print_step("Getting open tickets...")
        open_filter = create_open_tickets_filter()
        result = client.get_it_tickets(page=1, page_size=5, filters=open_filter)
        
        if result and result.get('Data'):
            tickets = result['Data']
            print_success(f"Found {len(tickets)} open tickets")
            
            # Format and display first ticket
            if tickets:
                formatted = format_ticket_summary(tickets[0])
                print_info(f"Sample ticket: {formatted}")
        else:
            print_info("No open tickets found")
        
        # Test 2: Get tickets by status
        print_step("Getting tickets by status...")
        status_filter = create_simple_status_filter("Assigned")
        result = client.get_it_tickets(page=1, page_size=5, filters=status_filter)
        
        if result and result.get('Data'):
            tickets = result['Data']
            print_success(f"Found {len(tickets)} assigned tickets")
        else:
            print_info("No assigned tickets found")
        
        # Test 3: Search for specific user's tickets
        print_step("Searching for user's tickets...")
        user_email = env.get('TEST_USER_EMAIL')
        if user_email:
            # First get the user ID
            user_result = client.get_user_by_email(user_email)
            if user_result:
                user_id = user_result.get('Id')
                if user_id:
                    my_filter = create_my_tickets_filter(user_email, user_id)
                    result = client.get_it_tickets(page=1, page_size=5, filters=my_filter)
                else:
                    print_error(f"Could not get user ID for {user_email}")
                    return False
            else:
                print_error(f"User not found: {user_email}")
                return False
            
            if result and result.get('Data'):
                tickets = result['Data']
                print_success(f"Found {len(tickets)} tickets for {user_email}")
            else:
                print_info(f"No tickets found for {user_email}")
        
        return True
        
    except Exception as e:
        print_error(f"Real-world scenario error: {e}")
        return False

def main():
    """Run all user scenario and user-friendly function tests"""
    print("🚀 User Scenarios and User-Friendly Functions Tests")
    print("=" * 60)
    
    tests = [
        ("User Scenario", test_user_scenario),
        ("Filtering Helpers", test_filtering_helpers),
        ("Ticket Formatting", test_ticket_formatting),
        ("Error Handling", test_error_handling),
        ("Edge Cases", test_edge_cases),
        ("Real-World Scenario", test_real_world_scenario)
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
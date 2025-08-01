#!/usr/bin/env python3
"""
Test script to verify numeric ID filtering for IT tickets.
This script tests the updated implementation that uses numeric IDs instead of string names.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add the local-server directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'local-server'))

from nsp_client import NSPClient

def test_numeric_id_filtering():
    """Test the numeric ID filtering implementation"""
    
    # Load environment variables
    load_dotenv('local-server/.env')
    
    # Initialize NSP client
    base_url = os.getenv('NSP_BASE_URL')
    username = os.getenv('NSP_USERNAME')
    password = os.getenv('NSP_PASSWORD')
    
    if not all([base_url, username, password]):
        print("❌ Missing required environment variables. Please check your .env file.")
        return False
    
    client = NSPClient(base_url, username, password)
    
    # Test authentication
    print("🔐 Testing authentication...")
    if not client.authenticate():
        print("❌ Authentication failed")
        return False
    print("✅ Authentication successful")
    
    # Test 1: Get all IT tickets (should use numeric IDs internally)
    print("\n📋 Test 1: Getting all IT tickets...")
    try:
        result = client.get_it_tickets(page=1, page_size=5)
        if result and result.get('Data'):
            print(f"✅ Successfully retrieved {len(result['Data'])} IT tickets")
            print(f"   Total available: {result.get('Total', 'Unknown')}")
            
            # Show ticket types found
            types_found = set()
            for ticket in result['Data']:
                if 'Type' in ticket:
                    types_found.add(ticket['Type'])
            print(f"   Ticket types found: {types_found}")
        else:
            print("❌ No data returned or unexpected response structure")
            print(f"   Response: {result}")
    except Exception as e:
        print(f"❌ Error getting IT tickets: {e}")
        return False
    
    # Test 2: Get specific ticket types
    print("\n📋 Test 2: Getting specific ticket types...")
    try:
        result = client.get_it_tickets(page=1, page_size=20, ticket_types=['IT Request', 'Incident Management'])
        if result and result.get('Data'):
            print(f"✅ Successfully retrieved {len(result['Data'])} tickets (Ticket + Incident only, page_size=20)")
            
            # Verify only requested types are returned
            types_found = set()
            for ticket in result['Data']:
                if 'Type' in ticket:
                    types_found.add(ticket['Type'])
            print(f"   Ticket types found: {types_found}")
            
            # Check if only expected ticket types are returned (handling both numeric IDs and DisplayNames)
            expected_numeric_ids = {112, 281}
            expected_display_names = {
                # English DisplayNames
                'IT Request', 'Incident Management',
                # Swedish DisplayNames  
                'IT-Ärende', 'Incident Management'
            }
            
            # Check if all found types are either expected numeric IDs or expected DisplayNames
            all_expected = expected_numeric_ids.union(expected_display_names)
            unexpected_types = types_found - all_expected
            
            if not unexpected_types:
                print("✅ Only expected ticket types returned")
                print(f"   Found types: {types_found}")
            else:
                print(f"⚠️  Unexpected ticket types found: {unexpected_types}")
                print(f"   Expected: {all_expected}")
                print(f"   Found: {types_found}")
        else:
            print("❌ No data returned for specific ticket types")
    except Exception as e:
        print(f"❌ Error getting specific ticket types: {e}")
        return False
    
    # Test 2b: Get only Incident tickets
    print("\n📋 Test 2b: Getting only Incident tickets...")
    try:
        result = client.get_it_tickets(page=1, page_size=50, ticket_types=['Incident Management'])
        if result and result.get('Data'):
            print(f"✅ Successfully retrieved {len(result['Data'])} Incident tickets (page_size=50)")
            
            # Show ticket types found
            types_found = set()
            for ticket in result['Data']:
                if 'Type' in ticket:
                    types_found.add(ticket['Type'])
            print(f"   Ticket types found: {types_found}")
            
            # Check if we found any Incident tickets
            expected_incident_names = {'Incident Management', 'IT-Ärende'}  # Both English and Swedish
            if types_found.intersection(expected_incident_names):
                print("✅ Found Incident tickets")
            else:
                print("⚠️  No Incident tickets found in the system")
        else:
            print("❌ No data returned for Incident tickets")
    except Exception as e:
        print(f"❌ Error getting Incident tickets: {e}")
        return False
    
    # Test 3: Get tickets by status
    print("\n📋 Test 3: Getting open IT tickets...")
    try:
        result = client.get_it_tickets_by_status(status="open", page=1, page_size=5)
        if result and result.get('Data'):
            print(f"✅ Successfully retrieved {len(result['Data'])} open IT tickets")
            
            # Check that all tickets have non-closed status
            closed_count = 0
            for ticket in result['Data']:
                if ticket.get('BaseEntityStatus') == 11:  # 11 = closed
                    closed_count += 1
            
            if closed_count == 0:
                print("✅ All returned tickets are open (BaseEntityStatus != 11)")
            else:
                print(f"⚠️  Found {closed_count} closed tickets in open results")
        else:
            print("❌ No data returned for open tickets")
    except Exception as e:
        print(f"❌ Error getting open tickets: {e}")
        return False
    
    # Test 4: Get tickets by user role (if test user is available)
    test_user_email = os.getenv('TEST_USER_EMAIL')
    if test_user_email:
        print(f"\n📋 Test 4: Getting tickets for user {test_user_email} as customer...")
        try:
            result = client.get_tickets_by_user_role(
                user_email=test_user_email, 
                role="customer", 
                page=1, 
                page_size=5
            )
            if result and result.get('Data'):
                print(f"✅ Successfully retrieved {len(result['Data'])} tickets for user as customer")
                
                # Check that all tickets have the correct user as BaseEndUser
                user = client.get_user_by_email(test_user_email)
                if user:
                    user_id = user.get('Id')
                    user_display_name = user.get('DisplayName')
                    correct_user_count = 0
                    
                    print(f"   User ID: {user_id}, DisplayName: '{user_display_name}'")
                    
                    for ticket in result['Data']:
                        base_end_user = ticket.get('BaseEndUser')
                        # NSP API returns DisplayName in BaseEndUser field, not ID
                        if base_end_user == user_display_name:
                            correct_user_count += 1
                        else:
                            print(f"     Ticket {ticket.get('Id', 'Unknown')}: BaseEndUser = '{base_end_user}' (expected '{user_display_name}')")
                    
                    print(f"   {correct_user_count}/{len(result['Data'])} tickets have correct user as BaseEndUser")
            else:
                print("❌ No data returned for user tickets")
        except Exception as e:
            print(f"❌ Error getting user tickets: {e}")
            return False
    else:
        print("\n📋 Test 4: Skipped (TEST_USER_EMAIL not set)")
    
    print("\n🎉 All tests completed!")
    return True

if __name__ == "__main__":
    success = test_numeric_id_filtering()
    sys.exit(0 if success else 1) 
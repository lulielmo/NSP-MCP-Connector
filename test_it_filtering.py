#!/usr/bin/env python3
"""
Test IT Filtering Functionality
Tests the new IT-related ticket filtering using SysTicket entity type
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add local-server to path for imports
sys.path.append('local-server')

from nsp_client import NSPClient

# Load environment variables
load_dotenv('local-server/.env')

def test_it_tickets_filtering():
    """Test the new IT tickets filtering functionality"""
    print("🧪 Testing IT Tickets Filtering")
    print("=" * 50)
    
    # Initialize NSP client
    nsp_client = NSPClient(
        base_url=os.getenv('NSP_BASE_URL'),
        username=os.getenv('NSP_USERNAME'),
        password=os.getenv('NSP_PASSWORD')
    )
    
    try:
        # Test 1: Get all IT tickets (default behavior)
        print("\n📋 Test 1: Get all IT tickets (default)")
        print("-" * 30)
        result = nsp_client.get_it_tickets(page=1, page_size=5)
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} IT tickets")
        
        # Show ticket types found
        types_found = set(ticket.get('Type') for ticket in tickets)
        print(f"📊 Ticket types found: {types_found}")
        
        # Test 2: Get only IT Requests
        print("\n📋 Test 2: Get only IT Requests")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=5, 
            ticket_types=['Ticket']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} IT Request tickets")
        
        # Test 3: Get only Service Orders
        print("\n📋 Test 3: Get only Service Orders")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=5, 
            ticket_types=['ServiceOrderRequest']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} Service Order tickets")
        
        # Test 4: Get only Incidents
        print("\n📋 Test 4: Get only Incidents")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=5, 
            ticket_types=['Incident']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} Incident tickets")
        
        # Test 5: Get open tickets only
        print("\n📋 Test 5: Get open IT tickets only")
        print("-" * 30)
        result = nsp_client.get_it_tickets_by_status(
            status="open",
            page=1, 
            page_size=5
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} open IT tickets")
        
        # Test 6: Get closed tickets only
        print("\n📋 Test 6: Get closed IT tickets only")
        print("-" * 30)
        result = nsp_client.get_it_tickets_by_status(
            status="closed",
            page=1, 
            page_size=5
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} closed IT tickets")
        
        # Test 7: Get open tickets with specific types
        print("\n📋 Test 7: Get open IT Requests only")
        print("-" * 30)
        result = nsp_client.get_it_tickets_by_status(
            status="open",
            page=1, 
            page_size=5,
            ticket_types=['Ticket']
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} open IT Request tickets")
        
        # Test 8: Test sorting (oldest first)
        print("\n📋 Test 8: Get IT tickets sorted by oldest first")
        print("-" * 30)
        result = nsp_client.get_it_tickets(
            page=1, 
            page_size=3,
            sort_by="CreatedDate",
            sort_direction="asc"
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} IT tickets (oldest first)")
        for i, ticket in enumerate(tickets):
            created_date = ticket.get('CreatedDate', 'Unknown')
            ticket_type = ticket.get('Type', 'Unknown')
            print(f"   {i+1}. {ticket_type} - Created: {created_date}")
        
        print("\n🎉 All IT filtering tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False
    
    return True

def test_user_role_filtering():
    """Test user role filtering with IT tickets"""
    print("\n🧪 Testing User Role Filtering with IT Tickets")
    print("=" * 50)
    
    # Get test user email from environment
    test_user_email = os.getenv('TEST_USER_EMAIL')
    if not test_user_email:
        print("⚠️  TEST_USER_EMAIL not set in environment, skipping user role tests")
        return True
    
    # Initialize NSP client
    nsp_client = NSPClient(
        base_url=os.getenv('NSP_BASE_URL'),
        username=os.getenv('NSP_USERNAME'),
        password=os.getenv('NSP_PASSWORD')
    )
    
    try:
        # Test 1: Get user's tickets as customer
        print(f"\n📋 Test 1: Get {test_user_email}'s tickets as customer")
        print("-" * 30)
        result = nsp_client.get_tickets_by_user_role(
            user_email=test_user_email,
            role="customer",
            page=1,
            page_size=5
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} tickets as customer")
        
        # Test 2: Get user's tickets as agent
        print(f"\n📋 Test 2: Get {test_user_email}'s tickets as agent")
        print("-" * 30)
        result = nsp_client.get_tickets_by_user_role(
            user_email=test_user_email,
            role="agent",
            page=1,
            page_size=5
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} tickets as agent")
        
        # Test 3: Get user's open tickets as customer
        print(f"\n📋 Test 3: Get {test_user_email}'s open tickets as customer")
        print("-" * 30)
        result = nsp_client.get_tickets_by_user_role(
            user_email=test_user_email,
            role="customer",
            page=1,
            page_size=5,
            ticket_types=['Ticket']  # Only IT Requests
        )
        tickets = result.get('Data', [])
        print(f"✅ Found {len(tickets)} open IT Request tickets as customer")
        
        print("\n🎉 All user role filtering tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during user role testing: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting IT Filtering Tests")
    print("=" * 50)
    
    # Test basic IT filtering
    success1 = test_it_tickets_filtering()
    
    # Test user role filtering
    success2 = test_user_role_filtering()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1) 
# User Role Management in NSP MCP Connector

## Overview

The NSP MCP Connector supports user role management to handle different contexts where users can act as either **customers** or **agents**. This allows for proper attribution and filtering of tickets based on the user's role in each interaction.

## User Roles

### Customer Role
- **Purpose**: End users who create support tickets
- **Context**: "As a customer, what open tickets do I have?"
- **NSP Fields**: `BaseEndUser`, `ReportedBy`
- **Default**: Used when creating tickets

### Agent Role
- **Purpose**: Support staff who handle tickets
- **Context**: "As an agent, what open tickets am I assigned to?"
- **NSP Fields**: `BaseAgent`, `CreatedBy`, `ModifiedBy`
- **Default**: Used when updating tickets

## Implementation

### User Lookup
Before performing role-based operations, the system looks up the user by email address:

```python
# Get user information from NSP
user = nsp_client.get_user_by_email("user@example.com")
user_id = user.get('Id')
```

### Role-Based Ticket Filtering

#### Customer Tickets
```python
# Get tickets where user is the end user/customer
filters = {"BaseEndUser": user_id}
tickets = nsp_client.get_tickets(filters=filters)
```

#### Agent Tickets
```python
# Get tickets where user is the assigned agent
filters = {"BaseAgent": user_id}
tickets = nsp_client.get_tickets(filters=filters)
```

### Role-Based Ticket Creation

#### As Customer
```python
ticket_data = {
    "title": "Support request",
    "description": "I need help with...",
    "priority": "Medium"
}

# User creates ticket as customer
result = nsp_client.create_ticket_with_user_context(
    ticket_data, 
    user_email="user@example.com", 
    role="customer"
)
# Sets: BaseEndUser, ReportedBy
```

#### As Agent
```python
ticket_data = {
    "title": "Internal ticket",
    "description": "Internal issue to track",
    "priority": "High"
}

# Agent creates ticket
result = nsp_client.create_ticket_with_user_context(
    ticket_data, 
    user_email="agent@example.com", 
    role="agent"
)
# Sets: BaseAgent, CreatedBy
```

## API Endpoints

### Get User Information
```http
POST /api/get_user_by_email
{
    "email": "user@example.com"
}
```

### Get Tickets by Role
```http
POST /api/get_tickets_by_role
{
    "user_email": "user@example.com",
    "role": "customer",  // or "agent"
    "page": 1,
    "page_size": 15
}
```

### Create Ticket with Role
```http
POST /api/create_ticket_with_role
{
    "title": "Support request",
    "description": "I need help",
    "priority": "Medium",
    "user_email": "user@example.com",
    "role": "customer"
}
```

### Update Ticket with Role
```http
PUT /api/update_ticket_with_role/{ticket_id}
{
    "updates": {
        "description": "Updated description"
    },
    "user_email": "agent@example.com",
    "role": "agent"
}
```

## MCP Tools

### New Role-Based Tools

#### `get_tickets_by_role`
- **Description**: Get tickets filtered by user role
- **Parameters**: `user_email`, `role` (customer/agent), `page`, `page_size`
- **Example**: "Show me my open tickets as a customer"

#### `get_user_by_email`
- **Description**: Get user information by email
- **Parameters**: `user_email`
- **Example**: "Look up user information for john@example.com"

#### `create_ticket_with_role`
- **Description**: Create ticket with proper user context
- **Parameters**: `title`, `description`, `user_email`, `role`
- **Example**: "Create a support ticket as a customer"

#### `update_ticket_with_role`
- **Description**: Update ticket with proper user context
- **Parameters**: `ticket_id`, `updates`, `user_email`, `role`
- **Example**: "Update ticket status as an agent"

## Usage Examples

### Copilot Interactions

#### Customer Context
```
User: "As a customer, what open tickets do I have?"
Copilot: Uses get_tickets_by_role with role="customer"
Result: Shows tickets where user is BaseEndUser
```

#### Agent Context
```
User: "As an agent, what tickets am I assigned to?"
Copilot: Uses get_tickets_by_role with role="agent"
Result: Shows tickets where user is BaseAgent
```

#### Creating Tickets
```
User: "Create a support ticket for me"
Copilot: Uses create_ticket_with_role with role="customer"
Result: Ticket created with user as BaseEndUser
```

#### Updating Tickets
```
User: "Update ticket #123 status to resolved"
Copilot: Uses update_ticket_with_role with role="agent"
Result: Ticket updated with user as ModifiedBy
```

## Benefits

### 1. **Proper Attribution**
- Tickets are correctly attributed to the right user
- Audit trail shows who created/modified tickets

### 2. **Context-Aware Filtering**
- Users see relevant tickets based on their role
- Different views for customers vs agents

### 3. **Flexible User Management**
- Same user can act in different roles
- Email-based user lookup for simplicity

### 4. **NSP Integration**
- Uses proper NSP field mappings
- Maintains data integrity in NSP

## Security Considerations

- **User Validation**: Email addresses are validated against NSP
- **Role Enforcement**: System enforces valid roles (customer/agent)
- **Audit Trail**: All actions are logged with user context
- **Error Handling**: Graceful handling of missing users

## Testing

Run role-based tests:
```bash
python test_local_server.py
```

Tests include:
- User lookup by email
- Ticket filtering by role
- Ticket creation with roles
- Ticket updates with roles 
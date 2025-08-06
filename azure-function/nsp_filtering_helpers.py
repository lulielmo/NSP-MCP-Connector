# NSP Filtering Helper Functions - User-Friendly Version

from typing import Dict, List, Optional

def get_entity_type_id(entity_type_name: str) -> int:
    """Get entity type ID from name"""
    entity_types = {
        "Ticket": 112,
        "ServiceOrderRequest": 113, 
        "Incident": 281
    }
    return entity_types.get(entity_type_name, 112)

def get_entity_type_name(entity_type_id: int) -> str:
    """Get entity type name from ID"""
    entity_types = {
        112: "Ticket",
        113: "ServiceOrderRequest", 
        281: "Incident"
    }
    return entity_types.get(entity_type_id, "Ticket")

def get_common_status_ids() -> Dict[str, int]:
    """Get common status IDs (BaseEntityStatus)"""
    return {
        "New": 12,
        "Registered": 1,
        "Assigned": 3,
        "In progress": 6,
        "Pending": 9,
        "Resolved": 10,
        "Closed": 11
    }

def get_status_name(status_id: int) -> str:
    """Get status name from ID"""
    status_ids = get_common_status_ids()
    for name, id_val in status_ids.items():
        if id_val == status_id:
            return name
    return f"Status {status_id}"

def get_common_stage_ids(entity_type: str = "Ticket") -> Dict[str, int]:
    """Get common stage IDs for entity type (BaseEntityStage)"""
    if entity_type == "Ticket":
        return {
            "New": 1,
            "Open": 2,
            "Resolved": 3,
            "Closed": 4
        }
    elif entity_type == "ServiceOrderRequest":
        return {
            "New": 39,
            "Open": 40,
            "Resolved": 41,
            "Closed": 42
        }
    elif entity_type == "Incident":
        return {
            "New": 5,
            "Open": 6,
            "Resolved": 7,
            "Closed": 8
        }
    return {}

def get_stage_name(stage_id: int, entity_type: str = "Ticket") -> str:
    """Get stage name from ID"""
    stage_ids = get_common_stage_ids(entity_type)
    for name, id_val in stage_ids.items():
        if id_val == stage_id:
            return name
    return f"Stage {stage_id}"

# User-friendly filter functions for MCP connector

def create_simple_status_filter(status: str) -> Dict:
    """Create filter for simple status (BaseEntityStatus)"""
    status_ids = get_common_status_ids()
    if status.lower() in [s.lower() for s in status_ids.keys()]:
        # Find the correct case
        for status_name, status_id in status_ids.items():
            if status_name.lower() == status.lower():
                return {"BaseEntityStatus": status_id}
    return {}

def create_simple_stage_filter(stage: str, entity_type: str = "Ticket") -> Dict:
    """Create filter for simple stage (BaseEntityStage)"""
    stage_ids = get_common_stage_ids(entity_type)
    if stage.lower() in [s.lower() for s in stage_ids.keys()]:
        # Find the correct case
        for stage_name, stage_id in stage_ids.items():
            if stage_name.lower() == stage.lower():
                return {"BaseEntityStage": stage_id}
    return {}

def create_entity_type_filter(entity_type: str) -> Dict:
    """Create filter for entity type"""
    # Note: EntityType is not a filter field, it's handled separately in the API call
    # This function is kept for compatibility but returns empty dict
    return {}

def create_my_tickets_filter(user_email: str, user_id: int = None) -> Dict:
    """Create filter for user's own tickets"""
    # If user_id is provided, use it directly with BaseAgent
    # Otherwise, return a filter that needs user_id to be resolved later
    if user_id is not None:
        return {
            "BaseAgent": user_id,  # Use the user's BaseAgent ID
            "BaseEntityStatus": [1, 3, 6, 9]  # Not closed statuses
        }
    else:
        # Return a filter that indicates we need to resolve user_id from email
        return {
            "BaseAgent": user_email,  # This will be replaced with user_id when resolved
            "BaseEntityStatus": [1, 3, 6, 9]  # Not closed statuses
        }

def create_open_tickets_filter() -> Dict:
    """Create filter for all open tickets (simple)"""
    return {
        "BaseEntityStatus": [1, 3, 6, 9]  # Not closed statuses
    }

def create_closed_tickets_filter() -> Dict:
    """Create filter for all closed tickets"""
    return {
        "BaseEntityStatus": [10, 11]  # Resolved, Closed
    }

def create_combined_filter(
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    stage: Optional[str] = None,
    user_email: Optional[str] = None
) -> Dict:
    """Create combined filter with multiple criteria"""
    filters = {}
    
    if status:
        status_filter = create_simple_status_filter(status)
        filters.update(status_filter)
    
    if entity_type:
        entity_filter = create_entity_type_filter(entity_type)
        filters.update(entity_filter)
    
    if stage and entity_type:
        stage_filter = create_simple_stage_filter(stage, entity_type)
        filters.update(stage_filter)
    
    if user_email:
        # Note: create_my_tickets_filter now requires user_id to be resolved separately
        # This function will need to be updated to handle user_id resolution
        user_filter = create_my_tickets_filter(user_email)
        filters.update(user_filter)
    
    return filters

# Helper functions for MCP responses

def format_ticket_summary(ticket: Dict) -> Dict:
    """Format ticket for user-friendly display"""
    entity_type = get_entity_type_name(ticket.get('EntityType.Id', 112))
    status = get_status_name(ticket.get('BaseEntityStatus.Id', 0))
    stage = get_stage_name(ticket.get('BaseEntityStage.Id', 0), entity_type)
    
    return {
        "id": ticket.get('Id', ''),
        "title": ticket.get('BaseHeader', ''),
        "type": entity_type,
        "status": status,
        "stage": stage,
        "assigned_to": ticket.get('BaseAgent', ''),
        "created_date": ticket.get('CreatedDate', ''),
        "priority": ticket.get('Priority', ''),
        "description": ticket.get('BaseDescription', '')[:200] + "..." if len(ticket.get('BaseDescription', '')) > 200 else ticket.get('BaseDescription', '')
    }

def get_filter_description(filters: Dict) -> str:
    """Get human-readable description of applied filters"""
    descriptions = []
    
    if 'BaseEntityStatus' in filters:
        status_id = filters['BaseEntityStatus']
        if isinstance(status_id, list):
            # Handle list of status IDs (e.g., for open/closed filters)
            if status_id == [1, 3, 6, 9]:
                descriptions.append("Status: Öppna ärenden")
            elif status_id == [10, 11]:
                descriptions.append("Status: Stängda ärenden")
            else:
                status_names = [get_status_name(sid) for sid in status_id]
                descriptions.append(f"Status: {', '.join(status_names)}")
        else:
            status_name = get_status_name(status_id)
            descriptions.append(f"Status: {status_name}")
    
    # Note: EntityType is not a filter field, so we don't include it in descriptions
    
    if 'BaseEntityStage' in filters:
        stage_id = filters['BaseEntityStage']
        entity_type = get_entity_type_name(filters.get('EntityType', 112))
        stage_name = get_stage_name(stage_id, entity_type)
        descriptions.append(f"Fas: {stage_name}")
    
    if 'BaseAgent' in filters:
        descriptions.append("Tilldelade till dig")
    
    return ", ".join(descriptions) if descriptions else "Inga filter" 
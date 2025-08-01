# NSP API Workarounds

## SortOrder Property Problem

### Problem
The NSP API has a known issue with the `SortOrder` property on the Ticket entity that causes NHibernate mapping errors:

```
"Internal error has occurred: 'property not found: SortOrder on entity Ticket'."
```

### Implemented Workaround

#### 1. Explicit Columns
Use `columns` to specify exactly which properties should be returned (automatically excludes SortOrder):

```json
{
    "EntityType": "Ticket",
    "Page": 1,
    "PageSize": 20,
    "columns": ["Type", "Owner", "Version", "CreatedDate", "CreatedBy", "UpdatedDate", "UpdatedBy", "IPAddress", "BaseStatus", "OwnerAgent", "CC", "Priority", "Category", "Callback", "CloseDateTime", "AgentGroup", "EndUserRating", "IsMajor", "BaseEntitySource", "GeoLocation", "BrowserName", "ReferenceNo", "BaseEntityStage", "Escalation", "Resolution", "BaseEntitySecurity", "IsSecurity", "FormId", "CaseType", "ReportedBy", "OnBehalfOf", "BaseEndUser", "BaseAgent", "BaseHeader", "BaseDescription", "BaseEntityStatus", "Location", "Customer", "SspFormId", "RequesterCommentCount", "EndUserCommentCount"]
}
```

#### 2. Explicit Sorting
Use explicit sorting instead of default:
```json
{
    "EntityType": "Ticket",
    "Page": 1,
    "PageSize": 20,
    "SortBy": "Id",
    "SortDirection": "Descending"
}
```

#### 3. Combined Workaround
Combine both for best results:
```json
{
    "EntityType": "Ticket",
    "Page": 1,
    "PageSize": 20,
    "columns": ["Type", "Owner", "Version", "CreatedDate", "CreatedBy", "Priority", "Category"],
    "SortBy": "Id",
    "SortDirection": "Descending"
}
```

### Implementation in Code

#### NSPClient.get_tickets()
```python
def get_tickets(self, page: int = 1, page_size: int = 15, filters: Optional[Dict] = None) -> Dict[str, Any]:
    query_data = {
        "EntityType": "Ticket",
        "Page": page,
        "PageSize": page_size
    }
    
    # Workaround: Use explicit columns instead of ExcludeProperties
    # NSP API doesn't support ExcludeProperties but uses columns to specify which fields should be returned
    query_data["columns"] = [
        "Type", "Owner", "Version", "CreatedDate", "CreatedBy", "UpdatedDate", "UpdatedBy", 
        "IPAddress", "BaseStatus", "OwnerAgent", "CC", "Priority", "Category", "Callback", 
        "CloseDateTime", "AgentGroup", "EndUserRating", "IsMajor", "BaseEntitySource", 
        "GeoLocation", "BrowserName", "ReferenceNo", "BaseEntityStage", "Escalation", 
        "Resolution", "BaseEntitySecurity", "IsSecurity", "FormId", "CaseType", "ReportedBy", 
        "OnBehalfOf", "BaseEndUser", "BaseAgent", "BaseHeader", "BaseDescription", 
        "BaseEntityStatus", "Location", "Customer", "SspFormId", "RequesterCommentCount", 
        "EndUserCommentCount"
    ]
    
    # Add explicit sorting
    query_data["SortBy"] = "Id"
    query_data["SortDirection"] = "Descending"
    
    try:
        return self._make_request('POST', 'GetEntityListByQuery', query_data)
    except Exception as e:
        # Fallback: try without explicit sorting
        if "SortOrder" in str(e) or "property not found" in str(e):
            query_data.pop("SortBy", None)
            query_data.pop("SortDirection", None)
            return self._make_request('POST', 'GetEntityListByQuery', query_data)
        else:
            raise
```

### Why Columns instead of ExcludeProperties?

- **ExcludeProperties** is ignored by the NSP API
- **Columns** provides explicit control over which fields are returned
- **Columns** is more efficient as only requested fields are fetched
- **Columns** automatically avoids problematic properties like SortOrder

### Testing

Run the workaround tests:
```bash
python test_nsp_api_issues.py
```

### Affected Endpoints

- `GetEntityListByQuery` - for both `get_tickets` and `search_entities`
- Affects all queries that return Ticket entities

### Status

✅ **Workaround implemented** - Uses columns to avoid SortOrder problem  
✅ **Fallback logic** - If first attempt fails, try without explicit sorting  
✅ **Logging** - Warnings when workaround is used  
✅ **Tests** - Dedicated tests for the workaround  
✅ **Verified** - Tested and working in Postman  

### Future Improvements

1. **Configurable columns** - Make the columns list configurable via environment variables
2. **Caching** - Cache which columns work for specific NSP instances
3. **Monitoring** - Track how often workarounds are used
4. **Dynamic column discovery** - Automatically find available columns via metadata

---

## Other Known Issues

### 1. Authentication
- Tokens can expire unexpectedly
- 401 errors are handled automatically with re-authentication

### 2. Data Format
- Some properties may require specific formats
- Test different property names (uppercase/lowercase)

### 3. Endpoint Variations
- Some endpoints may have different names on different NSP versions
- Implemented fallback to alternative endpoint names 
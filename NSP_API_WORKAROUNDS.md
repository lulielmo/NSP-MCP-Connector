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

## ⏱️ Authentication Timeout i MCP Context

### Problem
NSP authentication tar betydligt längre tid än vad MCP-protokollet tolererar:

- **NSP Authentication:** 15-20 sekunder (första gången)
- **MCP Client Timeout:** 10 sekunder (standard)
- **Resultat:** Första MCP-anrop misslyckas alltid med timeout

### Tekniska Detaljer

#### Timing Breakdown
```
Första anrop (cold start):
├── MCP Client skickar tools/call     (t=0s)
├── Azure Function mottar anrop       (t=0.1s)
├── NSP authentication startar        (t=0.2s)
├── MCP Client timeout                (t=10s) ❌
└── NSP authentication slutförd       (t=17s)

Andra anrop (warm cache):
├── MCP Client skickar tools/call     (t=0s)
├── Azure Function mottar anrop       (t=0.1s)
├── Använder cached NSP token         (t=0.2s)
├── NSP API-anrop                     (t=1s)
└── Respons till MCP Client           (t=2s) ✅
```

#### Affected Clients
| MCP Client | Timeout | Första Anrop | Andra Anrop |
|------------|---------|--------------|-------------|
| MCP Inspector | 10s | ❌ Timeout | ✅ Framgång |
| Copilot Studio | 10s | ❌ Timeout | ✅ Framgång |

### Implemented Workarounds

#### 1. User Experience Strategy
**Copilot Studio Behavior:**
```
Första försök:
"Sorry, something went wrong. Error code: SystemError.
It seems there was an error retrieving your user information. 
Let me escalate this issue to ensure it gets resolved."

Andra försök (användaren säger "försök igen"):
"Here is the retrieved user information for John Doe:
• Full Name: John Doe
• Email Address: john.doe@company.com
• [... komplett användarinformation]"
```

#### 2. Token Caching
NSP-token cachas automatiskt efter första autentiseringen:
```python
# I nsp_client.py
def _authenticate(self):
    if self.token and not self._is_token_expired():
        return  # Använd cached token
    
    # Endast första gången - långsam autentisering
    self.token = self._get_new_token()  # 15-20 sekunder
```

#### 3. Graceful Error Handling
```python
# I Azure Function
try:
    result = await nsp_connector.get_user_by_email(user_email)
    if result:
        return success_response(result)
    else:
        return error_response("User not found")
except Exception as e:
    logger.error(f"Error: {str(e)}")
    # MCP Client kommer få timeout, men det är förväntat
    return error_response(str(e))
```

### User Impact

#### Copilot Studio
- **Första interaktion:** Användaren måste säga "försök igen"
- **Efterföljande anrop:** Fungerar normalt (2-3 sekunder)
- **User Education:** Dokumentera att första anrop kan kräva retry

#### MCP Inspector
- **Första anrop:** Röd timeout-indikator
- **Andra anrop:** Grön framgång-indikator
- **Development Impact:** Minimal - utvecklare förstår timeout-konceptet

### Future Solutions

#### 1. Pre-warming (Rekommenderad)
```python
# Background job som håller token aktiv
import schedule
import time

def keep_token_warm():
    """Kör var 30:e minut för att hålla NSP-token cached"""
    try:
        nsp_client.get_user_by_email("system.health@example.com")
    except:
        pass  # Ignore errors, bara för att hålla token warm

schedule.every(30).minutes.do(keep_token_warm)
```

#### 2. Asynkron Processing
```python
# Returnera omedelbart, processa i bakgrunden
@app.route(route="mcp_async", auth_level=func.AuthLevel.FUNCTION)
async def nsp_mcp_async_handler(req: func.HttpRequest):
    request_id = generate_request_id()
    
    # Starta bakgrundsprocessing
    asyncio.create_task(process_nsp_request(request_id, req_data))
    
    # Returnera omedelbart med polling-URL
    return {
        "status": "processing",
        "request_id": request_id,
        "poll_url": f"/api/mcp_status/{request_id}"
    }
```

#### 3. Längre MCP Timeouts
Undersök om MCP-klienter kan konfigureras med längre timeouts:
- MCP Inspector: Konfigurationsfil?
- Copilot Studio: Azure Function timeout-settings?

#### 4. Connection Pooling
```python
# Håll NSP-anslutning aktiv
class NSPConnectionPool:
    def __init__(self):
        self.connections = {}
        self.last_used = {}
    
    def get_connection(self, user_context):
        # Återanvänd befintliga anslutningar
        # Automatisk cleanup av gamla anslutningar
```

### Testing

#### Reproducera Problemet
```bash
# Första anrop (kommer timeout)
curl -X POST "https://func-nsp-mcp-test-002.azurewebsites.net/api/mcp" \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/call","params":{"name":"get_my_info","arguments":{"user_email":"john.doe@company.com"}}}'

# Andra anrop (kommer lyckas)
# Kör samma kommando igen inom 1 timme
```

#### Verifiera Caching
```bash
# Kolla Azure Function logs för:
"Token expired or missing, re-authenticating..."  # Första anrop
"Looking up user by email: john.doe@company.com"  # Andra anrop (ingen re-auth)
```

### Monitoring

#### Metrics att spåra
- **First Call Success Rate:** Borde vara ~0%
- **Second Call Success Rate:** Borde vara ~100%
- **Average Response Time First Call:** 15-25 sekunder
- **Average Response Time Subsequent Calls:** 2-5 sekunder

#### Alerts
```yaml
# Azure Monitor Alert
- name: "NSP MCP High Failure Rate"
  condition: "First call success rate < 20% over 5 minutes"
  action: "Investigate pre-warming solution"

- name: "NSP MCP Slow Response"
  condition: "Average response time > 30 seconds"
  action: "Check NSP API health"
```

### Status

✅ **Problem identifierat** - NSP auth timeout vs MCP timeout mismatch  
✅ **Workaround implementerat** - Token caching fungerar  
✅ **User experience dokumenterat** - "Försök igen" pattern  
⏳ **Pre-warming solution** - Planerad förbättring  
⏳ **Monitoring** - Metrics och alerts planerade  

---

## Other Known Issues

### 1. Authentication
- Tokens can expire unexpectedly
- 401 errors are handled automatically with re-authentication
- **New:** First-time authentication takes 15-20 seconds (see timeout section above)

### 2. Data Format
- Some properties may require specific formats
- Test different property names (uppercase/lowercase)

### 3. Endpoint Variations
- Some endpoints may have different names on different NSP versions
- Implemented fallback to alternative endpoint names 
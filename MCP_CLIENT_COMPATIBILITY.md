# MCP Client Compatibility Guide

## 📋 **Overview**
This guide describes how NSP MCP Connector handles different MCP clients and ensures compatibility between various implementations of the Model Context Protocol.

## 🎯 **Supported Clients**

### ✅ **Verified Clients**
| Client | Status | ID Type | Detection Method | Tested Version |
|--------|--------|---------|------------------|----------------|
| MCP Inspector | ✅ Works | Integer | `clientInfo.name: "mcp-inspector"` | v0.16.4 |
| Copilot Studio | ✅ Works | String | `channelId: "pva-studio"` | 2025-08-19 |

### 🔄 **Future Clients**
The solution is designed to easily support new MCP clients through:
- Generic client detection logic
- Configurable ID type handling
- Extensible client signature matching

## 🔍 **Client Detection Logic**

### **Current Implementation**
```python
def detect_client_type(client_info):
    """
    Detects MCP client type based on clientInfo
    Returns: 'copilot_studio', 'mcp_inspector', or 'unknown'
    """
    client_name = client_info.get("name", "").lower()
    agent_name = client_info.get("agentName", "").lower()
    channel_id = client_info.get("channelId", "").lower()
    
    # Primary detection: channelId (most reliable)
    if channel_id == "pva-studio":
        return 'copilot_studio'
    
    # Secondary detection: specific client names
    if client_name == "mcp-inspector":
        return 'mcp_inspector'
    
    # Fallback detection: keywords in names
    copilot_keywords = ["copilot", "customerservice", "customerservicebot"]
    if any(keyword in client_name for keyword in copilot_keywords) or \
       any(keyword in agent_name for keyword in copilot_keywords):
        return 'copilot_studio'
    
    return 'unknown'
```

### **Client Signatures**

#### **Copilot Studio Signature**
```json
{
  "jsonrpc": "2.0",
  "id": "1",  // String ID
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "agentName": "CustomerServiceBot",      // Användardefinierat
      "appId": "841bf9c7-874e-4d38-a5ac-94227fb459f6",
      "channelId": "pva-studio",             // Pålitlig indikator
      "name": "mcs",                         // Tekniskt namn
      "version": "1.0.0"
    }
  }
}
```

#### **MCP Inspector Signature**
```json
{
  "jsonrpc": "2.0",
  "id": 0,    // Integer ID
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {
      "sampling": {},
      "elicitation": {},
      "roots": {"listChanged": true}
    },
    "clientInfo": {
      "name": "mcp-inspector",               // Pålitlig indikator
      "version": "0.16.4"
    }
  }
}
```

## 🔧 **ID Type Handling**

### **The Problem**
Different MCP clients use different data types for JSON-RPC IDs:
- **MCP Inspector:** Uses integers (`0`, `1`, `2`)
- **Copilot Studio:** Expects strings (`"0"`, `"1"`, `"2"`)

### **The Solution**
Automatic ID type conversion based on client type:

```python
def handle_request_id(request_id, client_type):
    """
    Converts request ID to correct type based on client
    """
    if client_type == 'copilot_studio':
        # Copilot Studio kräver string IDs
        if isinstance(request_id, int):
            return str(request_id)
        return request_id
    
    elif client_type == 'mcp_inspector':
        # MCP Inspector använder original typ (vanligtvis integer)
        return request_id
    
    else:
        # Unknown clients: behåll original typ
        return request_id
```

### **Exempel på Konvertering**
```python
# Copilot Studio input
request_id = 1  # integer från JSON parsing
client_type = 'copilot_studio'
# Output: "1" (string)

# MCP Inspector input  
request_id = 1  # integer från JSON parsing
client_type = 'mcp_inspector'
# Output: 1 (integer, oförändrad)
```

## 📊 **Detection Method Evolution**

### **Version 1.0: agentName-baserad (Specifik)**
```python
# Problem: Endast fungerar för specifika agentnamn
if "customerservicebot" in agent_name.lower():
    return 'copilot_studio'
```

**Begränsningar:**
- Fungerar bara om agenten heter "CustomerServiceBot"
- Användare kan döpa sin agent till vad som helst
- Inte skalbar för framtida användare

### **Version 2.0: channelId-baserad (Generell)**
```python
# Lösning: Baserad på teknisk plattformsinformation
if channel_id == "pva-studio":
    return 'copilot_studio'
```

**Fördelar:**
- Fungerar oavsett agentens namn
- Baserat på teknisk plattform, inte användarval
- Framtidssäker och skalbar
- Behåller backward compatibility

### **Version 2.1: Hybrid Approach (Robust)**
```python
# Bästa av båda världar
is_copilot = (channel_id == "pva-studio" or 
             "copilot" in client_name or 
             "customerservice" in client_name or 
             "customerservicebot" in client_name or
             "copilot" in agent_name or 
             "customerservice" in agent_name or 
             "customerservicebot" in agent_name)
```

## 🚀 **Lägga till Nya Klienter**

### **Steg 1: Identifiera Client Signature**
Samla in exempel på initialize-anrop från den nya klienten:
```bash
# Aktivera debug-logging i Azure Function
logger.info(f"Client detection - clientInfo: {client_info}")
```

### **Steg 2: Analysera Patterns**
Leta efter unika identifierare:
- `clientInfo.name` - Klientens tekniska namn
- `clientInfo.channelId` - Plattformsspecifik kanal
- `clientInfo.version` - Versionsinfo
- `protocolVersion` - MCP protokollversion

### **Steg 3: Uppdatera Detection Logic**
```python
def detect_client_type(client_info):
    # ... existing logic ...
    
    # Lägg till ny klient
    if client_name == "new-mcp-client":
        return 'new_client'
    
    # Eller baserat på andra attribut
    if client_info.get("platformId") == "custom-platform":
        return 'custom_client'
```

### **Steg 4: Konfigurera ID Handling**
```python
def handle_request_id(request_id, client_type):
    # ... existing logic ...
    
    elif client_type == 'new_client':
        # Definiera ID-typ för ny klient
        return str(request_id)  # eller keep as integer
```

### **Steg 5: Testa och Validera**
- Testa initialize-handshake
- Verifiera tools/list funktionalitet
- Validera tools/call med verkliga anrop

## 🧪 **Test Matrix**

### **Initialize Handshake**
| Klient | ID Input | ID Output | Status |
|--------|----------|-----------|---------|
| MCP Inspector | `0` (int) | `0` (int) | ✅ |
| Copilot Studio | `"1"` (str) | `"1"` (str) | ✅ |
| Copilot Studio | `1` (int) | `"1"` (str) | ✅ |

### **Tools/List**
| Klient | ID Input | ID Output | Response Time |
|--------|----------|-----------|---------------|
| MCP Inspector | `1` (int) | `1` (int) | <100ms |
| Copilot Studio | `"1"` (str) | `"1"` (str) | <200ms |

### **Tools/Call**
| Klient | ID Input | ID Output | Success Rate |
|--------|----------|-----------|--------------|
| MCP Inspector | `2` (int) | `2` (int) | 100% |
| Copilot Studio (1st) | `"2"` (str) | `"2"` (str) | ~10% (timeout) |
| Copilot Studio (2nd) | `"3"` (str) | `"3"` (str) | 100% (cached) |

## ⚠️ **Common Pitfalls**

### **1. Hårdkodade Klientnamn**
❌ **Fel:**
```python
if client_name == "customerservicebot":
    return 'copilot_studio'
```

✅ **Rätt:**
```python
if channel_id == "pva-studio":
    return 'copilot_studio'
```

### **2. Ignorera ID-typ Konvertering**
❌ **Fel:**
```python
# Returnera samma ID-typ till alla klienter
return request_id
```

✅ **Rätt:**
```python
# Anpassa ID-typ baserat på klient
if client_type == 'copilot_studio':
    return str(request_id)
```

### **3. Otillräcklig Fallback Logic**
❌ **Fel:**
```python
# Endast en detection-metod
if channel_id == "pva-studio":
    return 'copilot_studio'
else:
    return 'unknown'
```

✅ **Rätt:**
```python
# Flera detection-metoder med fallbacks
if channel_id == "pva-studio":
    return 'copilot_studio'
elif client_name == "mcp-inspector":
    return 'mcp_inspector'
elif "copilot" in client_name:
    return 'copilot_studio'  # fallback
else:
    return 'unknown'
```

## 📈 **Performance Considerations**

### **Detection Performance**
- **String Operations:** `O(n)` för keyword matching
- **Dictionary Lookups:** `O(1)` för exact matches
- **Recommendation:** Använd exact matches när möjligt

### **ID Conversion Performance**
- **Type Check:** `isinstance()` är snabb
- **String Conversion:** `str()` är minimal overhead
- **Impact:** Försumbar på totala response time

## 🔮 **Framtida Förbättringar**

### **1. Configuration-driven Detection**
```json
{
  "client_patterns": {
    "copilot_studio": {
      "channelId": ["pva-studio"],
      "name_patterns": ["copilot", "customerservice"],
      "id_type": "string"
    },
    "mcp_inspector": {
      "name": ["mcp-inspector"],
      "id_type": "integer"
    }
  }
}
```

### **2. Plugin Architecture**
- Modulär client detection
- Runtime registration av nya klienter
- Separata handlers per klienttyp

### **3. Telemetry och Analytics**
- Spåra klienttyper och användning
- Performance metrics per klient
- Automatisk detection av nya klienttyper

## 📅 **Versionshistorik**
- **v1.0:** Grundläggande MCP Inspector support
- **v1.5:** Copilot Studio support med agentName detection
- **v2.0:** channelId-baserad detection för Copilot Studio
- **v2.1:** Hybrid detection med fallback logic

## 🤝 **Bidrag**
För att lägga till support för nya MCP-klienter:
1. Samla client signatures från nya klienten
2. Uppdatera detection logic i `function_app.py`
3. Lägg till test cases
4. Uppdatera denna dokumentation

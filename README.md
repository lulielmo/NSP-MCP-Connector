# NSP MCP Connector

An MCP (Model Context Protocol) connector for NSP (Nilex Service Platform) Public API that enables AI integration via Copilot Studio.

## Architecture

```
Copilot Studio → Azure Function (MCP) → Hybrid Connection → On-premise (REST) → NSP API
```

## 🤖 Copilot Studio Integration (KOMPLETT)

✅ **Fullt funktionell MCP integration med Microsoft Copilot Studio** (2025-08-19)

### **Verifierade Klienter**
- **MCP Inspector** ✅ - Utveckling och testning
- **Microsoft Copilot Studio** ✅ - Produktionsanvändning via Custom Connectors

### **Tekniska Funktioner**
- **Azure Function MCP Server** - Hanterar MCP-protokoll kommunikation
- **Smart Client Detection** - Automatisk kompatibilitet mellan olika MCP-klienter
- **ID Type Handling** - Konverterar ID-typer baserat på klient (integer ↔ string)
- **Hybrid Connection** - Säker anslutning till on-premise system
- **Role-based Access Control** - Dynamiska behörigheter baserat på användarkontext
- **Timeout Workarounds** - Hanterar NSP authentication delay med token caching

### **Dokumentation**
- **[COPILOT_STUDIO_INTEGRATION.md](COPILOT_STUDIO_INTEGRATION.md)** - Komplett setup guide för Copilot Studio
- **[MCP_CLIENT_COMPATIBILITY.md](MCP_CLIENT_COMPATIBILITY.md)** - Client detection och kompatibilitet
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Felsökning och vanliga problem
- **[NSP_API_WORKAROUNDS.md](NSP_API_WORKAROUNDS.md)** - Timeout workarounds och NSP-specifika lösningar
- **[DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)** - Aktuell deployment status och konfiguration

### MCP Endpoints
- `GET /api/mcp` - List available MCP tools
- `POST /api/mcp` - Execute MCP tool calls
- `GET /api/health` - Health check with connection status

### MCP Tools Available
- **User Management**: `get_my_info`, `get_user_by_email`
- **Ticket Management**: `get_my_tickets`, `get_open_tickets`, `get_closed_tickets`
- **Advanced Search**: `search_tickets`, `get_tickets_by_status`, `get_tickets_by_type`
- **Ticket Operations**: `create_ticket`, `update_ticket`
- **Role-based Access**: Support for both customer and agent roles

## Project Structure

```
NSP-MCP-Connector/
├── azure-function/          # Azure Function MCP Server
├── local-server/           # Local REST API Server
├── shared/                 # Shared code between Azure and local
├── tests/                  # Tests
├── docs/                   # Documentation
├── nsp-mcp-schema-example.yaml  # Example OpenAPI schema for Power Apps
└── .gitignore              # Git ignore rules
```

## Setup

### Prerequisites
- Python 3.9+
- Azure Functions Core Tools
- NSP instance available
- Hybrid Connection Relay configured

### Installation

1. **Clone the project**
```bash
git clone <repository-url>
cd NSP-MCP-Connector
```

2. **Install dependencies**
```bash
# Azure Function
cd azure-function
pip install -r requirements.txt

# Local server
cd ../local-server
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Azure Function
cp azure-function/local.settings.json.example azure-function/local.settings.json
# Edit local.settings.json with your settings

# Local server
cp local-server/env.example local-server/.env
# Edit .env with your NSP settings
```

## Development

### Start local server
```bash
cd local-server
python app.py
```

### Start Azure Function locally
```bash
cd azure-function
func start
```

### Test MCP connection
```bash
# Test local REST API
curl -X POST http://localhost:5000/api/get_tickets \
  -H "Content-Type: application/json" \
  -d '{"page": 1, "page_size": 10}'
```

## Deployment

### Azure Function
```bash
cd azure-function
func azure functionapp publish <function-app-name>
```

### Local server
Deploy as Docker container or Windows Service.

## Features

- **Ticket Management**: Get, create, update tickets
- **File Management**: Upload and download attachments
- **Search**: Advanced search and filtering
- **Authentication**: Secure authentication against NSP with automatic token management

## Security Features

### Authentication Management
- **Automatic token refresh**: Tokens are automatically refreshed when expired
- **Token expiration monitoring**: Built-in expiration time tracking with 5-minute buffer
- **401 handling**: Automatic re-authentication on 401 responses
- **Token status monitoring**: Debug endpoints for token information

### Security Considerations
⚠️ **Important**: This connector transmits passwords in plain text to the NSP API. This should only be used in secure on-premise environments.

**Security recommendations:**
- Use dedicated API accounts with minimal required permissions
- Ensure network security between connector and NSP server
- Regularly rotate API account passwords
- Monitor authentication logs
- Use HTTPS for all communications

### Token Management Endpoints
- `GET /health` - Health check with token status
- `GET /api/token/status` - Get current token information
- `POST /api/token/refresh` - Manually refresh authentication token

## API Endpoints

### Authentication
- `GET /health` - Health check with authentication status
- `GET /api/token/status` - Get token information
- `POST /api/token/refresh` - Refresh authentication token

### Tickets
- `POST /api/get_tickets` - Get tickets with pagination and filtering
- `GET /api/get_ticket/<id>` - Get specific ticket by ID
- `POST /api/create_ticket` - Create new ticket
- `PUT /api/update_ticket/<id>` - Update existing ticket

### Search & Metadata
- `POST /api/search_entities` - Search among entities
- `GET /api/get_entity_types` - Get available entity types
- `GET /api/get_entity_metadata/<type>` - Get metadata for entity type

### Attachments
- `GET /api/get_attachments/<type>/<id>` - Get attachments for entity

### Cache Management
- `GET /api/cache/stats` - Get user cache statistics
- `POST /api/cache/clear` - Clear user cache
- `POST /api/cache/warm` - Pre-warm cache with specific users

### Token Pre-warming
- `GET /api/prewarming/status` - Get token pre-warming status
- `POST /api/prewarming/start` - Start token pre-warming
- `POST /api/prewarming/stop` - Stop token pre-warming
- `POST /api/prewarming/refresh` - Force immediate token refresh

## 🧪 Testing

The project includes comprehensive test suites:

### Test Files
- `tests/test_cache.py` - User cache functionality tests
- `tests/test_token_prewarming.py` - Token pre-warming system tests
- `tests/test_local_server_consolidated.py` - Local server API tests
- `tests/test_user_scenarios_consolidated.py` - End-to-end user scenarios
- `tests/test_azure_function_consolidated.py` - Azure Function MCP tests
- `tests/test_nsp_direct.py` - Direct NSP API tests

### Running Tests
```bash
# Test user cache functionality
python tests/test_cache.py

# Test token pre-warming system
python tests/test_token_prewarming.py

# Test local server endpoints
python tests/test_local_server_consolidated.py

# Test user scenarios
python tests/test_user_scenarios_consolidated.py
```

### Test Configuration
Set up test users and pre-warming in `local-server/.env`:
```bash
# Test users
TEST_USER_EMAIL=user@company.com
TEST_CUSTOMER_1_EMAIL=customer1@company.com
TEST_CUSTOMER_2_EMAIL=customer2@company.com

# Token pre-warming
PREWARMING_ENABLED=true
PREWARMING_REFRESH_BUFFER=5
``` 
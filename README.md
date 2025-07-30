# NSP MCP Connector

An MCP (Model Context Protocol) connector for NSP (Nilex Service Platform) Public API that enables AI integration via Copilot Studio.

## Architecture

```
Copilot Studio → Azure Function (MCP) → Hybrid Connection → On-premise (REST) → NSP API
```

## Project Structure

```
NSP-MCP-Connector/
├── azure-function/          # Azure Function MCP Server
├── local-server/           # Local REST API Server
├── shared/                 # Shared code between Azure and local
├── tests/                  # Tests
└── docs/                   # Documentation
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
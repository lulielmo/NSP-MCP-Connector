# Environment Configuration for NSP MCP Connector

## Overview

The project supports two NSP environments:
- **Test Environment**: `http://your-test-nsp-server:1900` (for development)
- **Production Environment**: `https://your-production-nsp-server:1901` (for production)

## Quick Start for Development

### 1. Configure Local Server

```bash
cd local-server

# Copy test environment file
cp env.test .env

# Edit .env with your test credentials
# NSP_USERNAME=your_test_username
# NSP_PASSWORD=your_test_password
```

### 2. Start Local Server

```bash
python app.py
```

### 3. Test Connection

```bash
# In another terminal
python test_local_server.py
python test_nsp_api_issues.py
```

## Environment Files

### Local Server

| File | Purpose | NSP URL |
|------|---------|---------|
| `env.example` | Template with comments | - |
| `env.test` | Test environment (development) | `http://your-test-nsp-server:1900` |
| `env.production` | Production environment | `https://your-production-nsp-server:1901` |
| `.env` | Your active configuration | Choose based on environment |

### Azure Function

| File | Purpose |
|------|---------|
| `local.settings.json.example` | Template for local development |
| `local.settings.json` | Your local Azure Function configuration |

## Configuration Variables

### NSP API
```bash
NSP_BASE_URL=http://your-test-nsp-server:1900/api/
NSP_USERNAME=your_username
NSP_PASSWORD=your_password
```

### Server
```bash
FLASK_ENV=development  # or production
FLASK_DEBUG=True       # or False for production
PORT=5000
LOG_LEVEL=INFO         # or WARNING for production
```

### Azure Function
```json
{
  "HYBRID_CONNECTION_ENDPOINT": "http://your-hybrid-connection-endpoint:5000",
  "HYBRID_CONNECTION_KEY": "your-hybrid-connection-key",
  "NSP_BASE_URL": "https://your-test-nsp-server:1901/api/",
  "NSP_USERNAME": "your_username",
  "NSP_PASSWORD": "your_password"
}
```

## Security

### ✅ Recommended
- Use HTTPS for production NSP calls (HTTP for test environment)
- Use dedicated API accounts with minimal permissions
- Rotate passwords regularly
- Monitor authentication logs

### ⚠️ Warnings
- Passwords are transmitted in plain text to NSP API
- Only for on-premise use
- Use secure networks

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check username/password
   - Verify API account has proper permissions

2. **SSL/TLS Errors**
   - Check that HTTPS works
   - Verify certificates

3. **SortOrder Errors**
   - Workaround implemented automatically
   - Check logs for fallback usage

### Test Connection

```bash
# Test directly against NSP
curl -X GET "http://your-test-nsp-server:1900/api/PublicApi/GetEntityTypes" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test local server
curl http://localhost:5000/health
```

## Deployment

### Test Environment → Production Environment

1. **Update NSP URL:**
   ```bash
   # From test environment
   NSP_BASE_URL=http://your-test-nsp-server:1900/api/
   
   # To production environment
   NSP_BASE_URL=https://your-production-nsp-server:1901/api/
   ```

2. **Update Credentials:**
   - Use production API account
   - Verify permissions

3. **Update Server Settings:**
   ```bash
   FLASK_ENV=production
   FLASK_DEBUG=False
   LOG_LEVEL=WARNING
   ```

4. **Test Production:**
   ```bash
   python test_local_server.py
   ``` 
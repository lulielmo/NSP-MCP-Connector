# NSP Local Server

## 📁 **Folder Structure**

```
local-server/
├── docker/
│   ├── test/
│   │   ├── docker-compose.test.yml
│   │   ├── start-test.sh
│   │   └── stop-all.sh
│   └── prod/
│       ├── docker-compose.prod.yml
│       ├── start-prod.sh
│       └── stop-all.sh
├── env/
│   ├── env.example          # Template (utan test-användare)
│   ├── env.development      # Lokal utveckling (med test-användare)
│   ├── env.test            # Ubuntu test-miljö (utan test-användare)
│   └── env.production      # Ubuntu prod-miljö (utan test-användare)
├── app.py                  # Main Flask application
├── nsp_client.py           # NSP API client
├── Dockerfile              # Docker image definition
├── requirements.txt        # Python dependencies
└── .dockerignore          # Files to exclude from Docker build
```

## 🚀 **Deployment to Ubuntu**

### **Quick Setup:**
```bash
# Clone repository
git clone https://github.com/lulielmo/NSP-MCP-Connector.git temp
cd temp/local-server

# Copy Docker configurations
cp -r docker/* /opt/nsp-mcp/

# Copy environment templates
cp -r env/* /opt/nsp-mcp/

# Configure credentials
cd /opt/nsp-mcp/test
cp env.test .env
# Edit .env with your NSP credentials

cd /opt/nsp-mcp/prod
cp env.production .env
# Edit .env with your NSP credentials

# Start environments
cd /opt/nsp-mcp/test
docker compose -f docker-compose.test.yml up -d

cd /opt/nsp-mcp/prod
docker compose -f docker-compose.prod.yml up -d
```

### **Ports:**
- **Test Environment:** Port 5000
- **Production Environment:** Port 5002
- **HCM Service:** Port 5001

## 🔧 **Development**

### **Local Development:**
```bash
# Copy development environment
cp env/env.development .env
# Edit .env with your credentials

# Run locally
python app.py
```

### **Docker Development:**
```bash
# Build image
docker build -t nsp-local-server:latest .

# Run test environment
cd docker/test
docker compose -f docker-compose.test.yml up -d
```

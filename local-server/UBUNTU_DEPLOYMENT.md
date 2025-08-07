# NSP Local Server - Ubuntu Deployment Guide

## 🎯 **Overview**

This guide describes how to set up NSP Local Server on Ubuntu Linux with Docker and Hybrid Connection Manager for both test and production environments.

## 🏗️ **Architecture**

```
Azure Function → Hybrid Connection → Ubuntu HCM → Docker Containers
├── Test: relay-shared-002 → ubuntu-hostname:5000 → Test Container
└── Prod: relay-shared-001 → ubuntu-hostname:5001 → Prod Container
```

## 📋 **Prerequisites**

- Ubuntu 22.04 LTS or later
- Docker installed
- NSP API access
- Azure Hybrid Connection Manager

## 🚀 **Installation**

### **1. Install Docker (if not already done)**
```bash
sudo apt update
sudo apt install apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### **2. Install Docker Compose**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### **3. Install Hybrid Connection Manager**
```bash
sudo wget "https://download.microsoft.com/download/HybridConnectionManager-Linux.tar.gz"
sudo tar -xf HybridConnectionManager-Linux.tar.gz
cd HybridConnectionManager/
sudo chmod 755 setup.sh
sudo ./setup.sh
```

## 🔧 **Configuration**

### **1. Create project structure**
```bash
sudo mkdir -p /opt/nsp-mcp/{test,prod}
cd /opt/nsp-mcp
```

### **2. Configure test environment**
```bash
cd /opt/nsp-mcp/test

# Copy files from repository
# (You need to copy the local-server folder here)

# Create .env file
cp env.example .env
nano .env
# Configure NSP credentials for test environment
```

### **3. Configure production environment**
```bash
cd /opt/nsp-mcp/prod

# Copy the same files
# Create .env file
cp env.example .env
nano .env
# Configure NSP credentials for production environment
```

## 🐳 **Docker Setup**

### **1. Get Docker image**
```bash
# Pull from Docker Hub (when image is published)
docker pull yourusername/nsp-local-server:latest

# Or build locally
docker build -t nsp-local-server:latest .
```

### **2. Test image locally**
```bash
# Test test environment
cd /opt/nsp-mcp/test
chmod +x scripts/start-test.sh
./scripts/start-test.sh

# Test production environment
cd /opt/nsp-mcp/prod
chmod +x scripts/start-prod.sh
./scripts/start-prod.sh
```

## 🔗 **Hybrid Connection Setup**

### **1. Configure test environment**
```bash
# Add test Hybrid Connection
hcm add --namespace relay-shared-002 --name nsp-mcp-hc-test --endpoint ubuntu-hostname:5000
```

### **2. Configure production environment**
```bash
# Add production Hybrid Connection
hcm add --namespace relay-shared-001 --name nsp-mcp-hc-prod --endpoint ubuntu-hostname:5001
```

### **3. Verify connections**
```bash
hcm list
# Should show both connections as "Connected"
```

## 🚀 **Start environments**

### **Test environment**
```bash
cd /opt/nsp-mcp/test
./scripts/start-test.sh
```

### **Production environment**
```bash
cd /opt/nsp-mcp/prod
./scripts/start-prod.sh
```

### **Stop all environments**
```bash
cd /opt/nsp-mcp/test
./scripts/stop-all.sh
```

## 🔍 **Monitoring and troubleshooting**

### **Check container status**
```bash
docker ps --filter "name=nsp-local-server"
```

### **View logs**
```bash
# Test environment
docker logs nsp-local-server-test

# Production environment
docker logs nsp-local-server-prod
```

### **Health checks**
```bash
# Test environment
curl http://localhost:5000/health

# Production environment
curl http://localhost:5001/health
```

### **Hybrid Connection status**
```bash
hcm list
hcm show nsp-mcp-hc-test
hcm show nsp-mcp-hc-prod
```

## 🔒 **Security**

### **Environment variables**
- ✅ `.env` files exist only locally on Ubuntu
- ✅ No secrets in Docker images
- ✅ No secrets in Git repository
- ✅ Runtime injection of credentials

### **Network security**
- ✅ Isolated Docker networks
- ✅ Different ports for test/prod
- ✅ Hybrid Connection encryption

## 📝 **Maintenance**

### **Update Docker image**
```bash
# Pull latest version
docker pull yourusername/nsp-local-server:latest

# Restart containers
cd /opt/nsp-mcp/test && ./scripts/start-test.sh
cd /opt/nsp-mcp/prod && ./scripts/start-prod.sh
```

### **Backup .env files**
```bash
# Backup credentials
sudo cp /opt/nsp-mcp/test/.env /opt/nsp-mcp/test/.env.backup
sudo cp /opt/nsp-mcp/prod/.env /opt/nsp-mcp/prod/.env.backup
```

## 🆘 **Troubleshooting**

### **Container won't start**
```bash
# Check .env file
cat .env

# Check Docker logs
docker logs nsp-local-server-test

# Check disk space
df -h
```

### **Hybrid Connection doesn't work**
```bash
# Check HCM status
hcm list

# Check network connection
curl -f http://localhost:5000/health

# Restart HCM
sudo systemctl restart hcm
```

### **NSP API connection doesn't work**
```bash
# Test from container
docker exec nsp-local-server-test curl -f http://localhost:5000/api/token/status

# Check NSP credentials
docker exec nsp-local-server-test env | grep NSP
```

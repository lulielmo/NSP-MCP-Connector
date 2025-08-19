#!/bin/bash

# Start NSP Local Server - Production Environment
echo "🚀 Starting NSP Local Server - Production Environment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy env.example to .env and configure your NSP credentials"
    exit 1
fi

# Build image if it doesn't exist
if [[ "$(docker images -q nsp-local-server:latest 2> /dev/null)" == "" ]]; then
    echo "📦 Building Docker image..."
    docker build -t nsp-local-server:latest .
fi

# Start production environment
echo "🐳 Starting production container..."
docker compose -f docker-compose.prod.yml up -d

# Check status
echo "📊 Checking container status..."
docker ps --filter "name=nsp-local-server-prod"

echo "✅ Production environment started!"
echo "🌐 Health check: http://localhost:5001/health"
echo "📝 Logs: docker logs nsp-local-server-prod"

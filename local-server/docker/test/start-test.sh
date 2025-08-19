#!/bin/bash

# Start NSP Local Server - Test Environment
echo "🚀 Starting NSP Local Server - Test Environment..."

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

# Start test environment
echo "🐳 Starting test container..."
docker compose -f docker-compose.test.yml up -d

# Check status
echo "📊 Checking container status..."
docker ps --filter "name=nsp-local-server-test"

echo "✅ Test environment started!"
echo "🌐 Health check: http://localhost:5000/health"
echo "📝 Logs: docker logs nsp-local-server-test"

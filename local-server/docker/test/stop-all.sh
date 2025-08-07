#!/bin/bash

# Stop all NSP Local Server environments
echo "🛑 Stopping all NSP Local Server environments..."

# Stop test environment
echo "🐳 Stopping test environment..."
docker-compose -f docker-compose.test.yml down

# Stop production environment
echo "🐳 Stopping production environment..."
docker-compose -f docker-compose.prod.yml down

# Check if any containers are still running
echo "📊 Checking for remaining containers..."
docker ps --filter "name=nsp-local-server"

echo "✅ All environments stopped!"

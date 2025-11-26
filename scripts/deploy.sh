#!/bin/bash
# Zapply Production Deployment Script for Synology NAS
# This script pulls the latest Docker images and restarts the services

set -e

echo "🚀 Starting Zapply deployment..."

# Configuration
DEPLOY_DIR="/volume1/docker/zapply"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GITHUB_REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-vpetreski}"

cd "$DEPLOY_DIR" || exit 1

echo "📁 Working directory: $(pwd)"

# Load environment variables
if [ -f .env.production ]; then
    echo "✅ Loading environment variables from .env.production"
    set -a
    source .env.production
    set +a
else
    echo "❌ Error: .env.production not found"
    exit 1
fi

# Pull latest images
echo "📥 Pulling latest Docker images..."
export GITHUB_REPOSITORY_OWNER="$GITHUB_REPO_OWNER"
export IMAGE_TAG="$IMAGE_TAG"

docker-compose -f docker-compose.prod.yml pull

# Stop and remove old containers
echo "🛑 Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

# Start new containers
echo "▶️  Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.prod.yml ps

# Show logs
echo "📋 Recent logs:"
docker-compose -f docker-compose.prod.yml logs --tail=20

echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your application at:"
echo "   Frontend: http://192.168.0.188:3000"
echo "   or via QuickConnect: https://192-168-0-188.vpetreski.direct.quickconnect.to:3000"
echo ""
echo "📊 View logs with:"
echo "   docker-compose -f $DEPLOY_DIR/docker-compose.prod.yml logs -f [service]"

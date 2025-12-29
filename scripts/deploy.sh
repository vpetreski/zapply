#!/bin/bash
# Zapply Production Deployment Script
# This script pulls the latest Docker images and restarts the services

set -e

echo "🚀 Starting Zapply deployment..."

# Configuration
DEPLOY_DIR="${DEPLOY_DIR:-/volume1/docker/zapply}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GITHUB_REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-your_github_username}"

# Use sudo docker when running as GitHub Actions, otherwise use docker directly
if [ -n "$GITHUB_ACTIONS" ]; then
  DOCKER="sudo docker"
else
  DOCKER="docker"
fi

cd "$DEPLOY_DIR" || exit 1

echo "📁 Working directory: $(pwd)"

# Load environment variables
if [ -f .env.production ]; then
    echo "✅ Loading environment variables from .env.production"
    set -a
    source .env.production
    set +a
    # Strip quotes from ADMIN_PASSWORD if present (bcrypt hashes fail with quotes)
    ADMIN_PASSWORD=$(echo "$ADMIN_PASSWORD" | sed "s/^'\\(.*\\)'\$/\\1/")
else
    echo "❌ Error: .env.production not found"
    exit 1
fi

# Pull latest images
echo "📥 Pulling latest Docker images..."
export GITHUB_REPOSITORY_OWNER="$GITHUB_REPO_OWNER"
export IMAGE_TAG="$IMAGE_TAG"

$DOCKER pull ghcr.io/$GITHUB_REPO_OWNER/zapply-backend:$IMAGE_TAG
$DOCKER pull ghcr.io/$GITHUB_REPO_OWNER/zapply-frontend:$IMAGE_TAG
$DOCKER pull postgres:15-alpine

# Stop and remove old containers
echo "🛑 Stopping old containers..."
$DOCKER stop zapply-backend-prod zapply-frontend-prod zapply-postgres-prod 2>/dev/null || true
$DOCKER rm zapply-backend-prod zapply-frontend-prod zapply-postgres-prod 2>/dev/null || true

# Create network if it doesn't exist
$DOCKER network create zapply_zapply-network 2>/dev/null || true

# Create volumes if they don't exist
$DOCKER volume create zapply_postgres_data 2>/dev/null || true
$DOCKER volume create zapply_app_logs 2>/dev/null || true
$DOCKER volume create zapply_app_data 2>/dev/null || true

# Start Postgres
echo "▶️  Starting PostgreSQL..."
$DOCKER run -d \
  --name zapply-postgres-prod \
  --network zapply_zapply-network \
  -e POSTGRES_DB=${POSTGRES_DB:-zapply} \
  -e POSTGRES_USER=${POSTGRES_USER:-zapply} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v zapply_postgres_data:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:15-alpine

# Wait for Postgres to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 15

# Start Backend
echo "▶️  Starting Backend..."
$DOCKER run -d \
  --name zapply-backend-prod \
  --network zapply_zapply-network \
  --env-file .env.production \
  -e DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-zapply}:${POSTGRES_PASSWORD}@zapply-postgres-prod:5432/${POSTGRES_DB:-zapply} \
  -e PYTHONUNBUFFERED=1 \
  -v zapply_app_logs:/app/logs \
  -v zapply_app_data:/app/data \
  -p 8000:8000 \
  --restart unless-stopped \
  ghcr.io/$GITHUB_REPO_OWNER/zapply-backend:$IMAGE_TAG

# Wait for Backend to be ready
echo "⏳ Waiting for Backend to be ready..."
sleep 20

# Show backend logs for debugging
echo "📋 Backend logs:"
$DOCKER logs zapply-backend-prod 2>&1 | tail -50

# Start Frontend
echo "▶️  Starting Frontend..."
$DOCKER run -d \
  --name zapply-frontend-prod \
  --network zapply_zapply-network \
  -p 3000:3000 \
  --restart unless-stopped \
  ghcr.io/$GITHUB_REPO_OWNER/zapply-frontend:$IMAGE_TAG

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
$DOCKER ps | grep zapply

# Show full backend logs after everything started
echo ""
echo "📋 Full Backend logs:"
$DOCKER logs zapply-backend-prod 2>&1 | tail -100

# Test health endpoint
echo ""
echo "🔍 Testing health endpoint..."
curl -s http://localhost:8000/api/health || echo "Health check failed"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your application at:"
echo "   Frontend: http://YOUR_SERVER_IP:3000"
echo "   Backend API: http://YOUR_SERVER_IP:8000/docs"
echo ""
echo "📊 View logs with:"
echo "   $DOCKER logs -f zapply-backend-prod"
echo "   $DOCKER logs -f zapply-frontend-prod"

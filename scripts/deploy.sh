#!/bin/bash
# Zapply Production Deployment Script for Synology NAS
# This script pulls the latest Docker images and restarts the services

set -e

echo "🚀 Starting Zapply deployment..."

# Configuration
DEPLOY_DIR="/volume1/docker/zapply"
IMAGE_TAG="${IMAGE_TAG:-latest}"
GITHUB_REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-vpetreski}"
DOCKER="/usr/local/bin/docker"

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
  -e DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-zapply}:${POSTGRES_PASSWORD}@zapply-postgres-prod:5432/${POSTGRES_DB:-zapply} \
  -e ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY} \
  -e WORKING_NOMADS_USERNAME=${WORKING_NOMADS_USERNAME} \
  -e WORKING_NOMADS_PASSWORD=${WORKING_NOMADS_PASSWORD} \
  -e ADMIN_EMAIL=${ADMIN_EMAIL} \
  -e ADMIN_PASSWORD=${ADMIN_PASSWORD} \
  -e JWT_SECRET_KEY=${JWT_SECRET_KEY} \
  -e JWT_ALGORITHM=${JWT_ALGORITHM:-HS256} \
  -e JWT_EXPIRE_MINUTES=${JWT_EXPIRE_MINUTES:-43200} \
  -e PYTHONUNBUFFERED=1 \
  -v zapply_app_logs:/app/logs \
  -v zapply_app_data:/app/data \
  -p 8000:8000 \
  --restart unless-stopped \
  ghcr.io/$GITHUB_REPO_OWNER/zapply-backend:$IMAGE_TAG

# Wait for Backend to be ready
echo "⏳ Waiting for Backend to be ready..."
sleep 20

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

echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your application at:"
echo "   Frontend: http://192.168.0.188:3000"
echo "   Backend API: http://192.168.0.188:8000/docs"
echo ""
echo "📊 View logs with:"
echo "   $DOCKER logs -f zapply-backend-prod"
echo "   $DOCKER logs -f zapply-frontend-prod"

#!/bin/bash
# Setup script for NAS infrastructure
# Run this from your local machine to set up the NAS for deployment

set -e

echo "🚀 Zapply NAS Setup Script"
echo "============================"
echo ""

NAS_HOST="192.168.0.188"
NAS_USER="vpetreski"
DEPLOY_DIR="/volume1/docker/zapply"

echo "📁 Creating directory structure on NAS..."
ssh ${NAS_USER}@${NAS_HOST} "mkdir -p ${DEPLOY_DIR}/{scripts,data/{postgres,logs,uploads}}"

echo "📋 Copying docker-compose.prod.yml..."
cat docker-compose.prod.yml | ssh ${NAS_USER}@${NAS_HOST} "cat > ${DEPLOY_DIR}/docker-compose.prod.yml"

echo "📋 Copying deployment script..."
cat scripts/deploy.sh | ssh ${NAS_USER}@${NAS_HOST} "cat > ${DEPLOY_DIR}/scripts/deploy.sh && chmod +x ${DEPLOY_DIR}/scripts/deploy.sh"

echo "🔑 Creating .env.production file..."
cat .env | ssh ${NAS_USER}@${NAS_HOST} "cat > ${DEPLOY_DIR}/.env.production"

echo ""
echo "✅ NAS setup complete!"
echo ""
echo "📍 Files created on NAS:"
ssh ${NAS_USER}@${NAS_HOST} "ls -la ${DEPLOY_DIR}/ && echo '' && ls -la ${DEPLOY_DIR}/scripts/"
echo ""
echo "⚠️  IMPORTANT: You still need to add authentication variables to .env.production:"
echo "   ssh ${NAS_USER}@${NAS_HOST}"
echo "   vi ${DEPLOY_DIR}/.env.production"
echo "   # Add these lines:"
echo "   ADMIN_USERNAME=vanja"
echo "   ADMIN_PASSWORD=<your-secure-password>"
echo "   JWT_SECRET_KEY=<random-secret-key>"
echo "   JWT_ALGORITHM=HS256"
echo "   JWT_EXPIRE_MINUTES=1440"

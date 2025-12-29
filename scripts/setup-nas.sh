#!/bin/bash
# Setup script for NAS/server infrastructure
# Run this from your local machine to set up the server for deployment

set -e

echo "🚀 Zapply Server Setup Script"
echo "============================"
echo ""

# CUSTOMIZE THESE FOR YOUR ENVIRONMENT
NAS_HOST="${NAS_HOST:-your_server_ip}"
NAS_USER="${NAS_USER:-your_username}"
DEPLOY_DIR="${DEPLOY_DIR:-/path/to/zapply}"

echo "📁 Creating directory structure on server..."
ssh ${NAS_USER}@${NAS_HOST} "mkdir -p ${DEPLOY_DIR}/{scripts,data/{postgres,logs,uploads}}"

echo "📋 Copying docker-compose.prod.yml..."
cat docker-compose.prod.yml | ssh ${NAS_USER}@${NAS_HOST} "cat > ${DEPLOY_DIR}/docker-compose.prod.yml"

echo "📋 Copying deployment script..."
cat scripts/deploy.sh | ssh ${NAS_USER}@${NAS_HOST} "cat > ${DEPLOY_DIR}/scripts/deploy.sh && chmod +x ${DEPLOY_DIR}/scripts/deploy.sh"

echo "🔑 Creating .env.production file..."
cat .env | ssh ${NAS_USER}@${NAS_HOST} "cat > ${DEPLOY_DIR}/.env.production"

echo ""
echo "✅ Server setup complete!"
echo ""
echo "📍 Files created on server:"
ssh ${NAS_USER}@${NAS_HOST} "ls -la ${DEPLOY_DIR}/ && echo '' && ls -la ${DEPLOY_DIR}/scripts/"
echo ""
echo "⚠️  IMPORTANT: Verify authentication variables in .env.production:"
echo "   ssh ${NAS_USER}@${NAS_HOST}"
echo "   cat ${DEPLOY_DIR}/.env.production"
echo ""
echo "   Make sure these are set:"
echo "   ADMIN_EMAIL=your_email@example.com"
echo "   ADMIN_PASSWORD=<bcrypt-hashed-password>"
echo "   JWT_SECRET_KEY=<random-secret-key>"
echo "   JWT_ALGORITHM=HS256"
echo "   JWT_EXPIRE_MINUTES=43200"

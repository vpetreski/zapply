# Zapply Deployment Guide

Complete guide for deploying Zapply to your Synology NAS with automated CI/CD.

## Overview

This setup provides:
- ✅ Automated deployment on merge to `main`
- ✅ Docker containers with health checks
- ✅ Zero-downtime updates
- ✅ Persistent data storage
- ✅ Resource limits and logging
- ✅ Secure authentication (JWT-based)

## Architecture

```
GitHub (main branch)
    ↓ (merge triggers)
GitHub Actions CI/CD
    ↓ (builds Docker images)
GitHub Container Registry
    ↓ (pulls & deploys)
Synology NAS (192.168.0.188)
    ↓ (serves application)
User (via QuickConnect)
```

## Prerequisites

- ✅ Synology NAS with Docker installed
- ✅ SSH access to NAS configured (`nas` command)
- ✅ GitHub repository access
- ⚠️ Authentication NOT yet implemented (see Security section)

## Step 1: Initial NAS Setup

Run the setup script to create directory structure and copy files:

```bash
./scripts/setup-nas.sh
```

This will:
1. Create `/volume1/docker/zapply/` directory structure
2. Copy `docker-compose.prod.yml` to NAS
3. Copy deployment scripts
4. Copy `.env` as `.env.production`

## Step 2: Configure GitHub Secrets

### 2.1 Add NAS SSH Private Key

The private key is at: `.github-deploy-key` (already generated)

1. Copy the private key content:
   ```bash
   cat .github-deploy-key
   ```

2. Go to GitHub repository → Settings → Secrets and variables → Actions

3. Click "New repository secret"

4. Name: `NAS_SSH_KEY`

5. Value: Paste the entire private key (including `-----BEGIN` and `-----END` lines)

6. Click "Add secret"

### 2.2 Verify GitHub Token

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions.
No action needed for this.

## Step 3: Test Deployment (Optional)

Before merging to `main`, you can test the deployment manually:

```bash
# SSH to NAS
ssh vpetreski@192.168.0.188

# Navigate to zapply directory
cd /volume1/docker/zapply

# Run deployment script
./scripts/deploy.sh
```

## Step 4: Enable Automated Deployment

Once GitHub secrets are configured, the deployment is fully automated:

1. Make changes to code
2. Commit and push to any branch
3. Create Pull Request
4. Merge to `main`
5. GitHub Actions automatically:
   - Builds Docker images
   - Pushes to GitHub Container Registry
   - Deploys to your NAS
   - Verifies deployment

**Deployment takes ~2-3 minutes**

## Access URLs

After deployment, access your application at:

- **Local Network**: http://192.168.0.188:3000
- **QuickConnect**: https://192-168-0-188.vpetreski.direct.quickconnect.to:3000
- **API Docs**: http://192.168.0.188:8000/docs (or add `:8000/docs` to QuickConnect)

## Management Commands

All commands are run from your local machine:

### View Logs

```bash
# Backend logs (live)
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml logs -f backend"

# Frontend logs
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml logs -f frontend"

# All logs (last 100 lines)
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml logs --tail=100"
```

### Check Service Status

```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml ps"
```

### Restart Services

```bash
# Restart all
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml restart"

# Restart specific service
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml restart backend"
```

### Access Database

```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml exec postgres psql -U zapply -d zapply"
```

### Manual Deployment

```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && ./scripts/deploy.sh"
```

### View Disk Usage

```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && du -sh data/*"
```

## Security - CRITICAL ⚠️

**IMPORTANT**: Before making the application publicly accessible:

### Authentication Must Be Implemented

Currently, the application has NO authentication. Anyone with the URL can access it.

**Required before public deployment:**

1. **Backend JWT Authentication** (pending implementation)
   - Login endpoint
   - Protected API routes
   - Token validation

2. **Frontend Login Page** (pending implementation)
   - Login form
   - Token storage
   - Route guards

3. **Environment Variables** (add to NAS .env.production):
   ```bash
   # SSH to NAS and edit
   ssh vpetreski@192.168.0.188
   vi /volume1/docker/zapply/.env.production

   # Add these lines:
   ADMIN_USERNAME=vanja
   ADMIN_PASSWORD=<your-secure-password-here>
   JWT_SECRET_KEY=<generate-random-secret-key>
   JWT_ALGORITHM=HS256
   JWT_EXPIRE_MINUTES=1440
   ```

To generate a secure JWT secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**DO NOT merge to `main` until authentication is implemented!**

## Troubleshooting

### Deployment fails with SSH error

Check that the private key was added to GitHub secrets correctly:
- Must include BEGIN and END lines
- No extra whitespace
- Exact copy of `.github-deploy-key`

### Services not starting

Check logs:
```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml logs"
```

Common issues:
- Missing environment variables in `.env.production`
- Database not healthy (check postgres logs)
- Port 3000 already in use

### Database connection issues

Verify database is healthy:
```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml exec postgres pg_isready"
```

### Cannot access via QuickConnect

- Verify ports are open in NAS firewall
- Check that services are running
- Try local IP first to isolate issue

## Rollback

To rollback to a previous version:

```bash
# SSH to NAS
ssh vpetreski@192.168.0.188
cd /volume1/docker/zapply

# Set IMAGE_TAG to previous git commit SHA
export IMAGE_TAG="main-abc1234"  # Replace with commit SHA

# Run deployment
./scripts/deploy.sh
```

## Monitoring

### Check Container Health

```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml ps"
```

Look for:
- `State: Up (healthy)` - Service is healthy
- `State: Up (unhealthy)` - Health check failing
- `State: Restarting` - Service crashing

### Check Resource Usage

```bash
ssh vpetreski@192.168.0.188 "docker stats --no-stream"
```

## Backup

### Database Backup

```bash
ssh vpetreski@192.168.0.188 "cd /volume1/docker/zapply && docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U zapply zapply > backup-$(date +%Y%m%d).sql"
```

### Data Backup

PostgreSQL data is in `/volume1/docker/zapply/data/postgres/`

Configure Synology Hyper Backup to include this directory.

## Next Steps

1. ✅ Complete GitHub secrets setup
2. ⚠️ **CRITICAL**: Implement authentication (backend + frontend)
3. ⚠️ Test authentication thoroughly
4. ✅ Merge to `main` when authentication is ready
5. ✅ Monitor first automated deployment
6. ✅ Access application via QuickConnect

## Files Reference

- `Dockerfile.prod` - Production backend Docker image
- `frontend/Dockerfile.prod` - Production frontend Docker image
- `docker-compose.prod.yml` - Production compose configuration
- `.github/workflows/deploy.yml` - GitHub Actions CI/CD workflow
- `scripts/deploy.sh` - Deployment script (runs on NAS)
- `scripts/setup-nas.sh` - Initial setup script (run locally)

## Support

If you encounter issues:
1. Check logs first
2. Verify all environment variables are set
3. Ensure services are healthy
4. Review this guide thoroughly

---

**Last Updated**: 2025-11-25

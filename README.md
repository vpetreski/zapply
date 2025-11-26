# Zapply

AI-powered remote job application automation system for software engineers.

## Overview

Zapply automates the tedious process of finding and applying to remote software engineering positions. It scrapes job boards, intelligently matches opportunities against your profile, and automatically submits applications - all while you sleep.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SCRAPER   │────▶│   MATCHER   │────▶│   APPLIER   │────▶│  REPORTER   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                    │
                              ┌─────▼─────┐
                              │  POSTGRES │
                              └───────────┘
                                    │
                              ┌─────▼─────┐
                              │  VUE.JS   │
                              │ DASHBOARD │
                              └───────────┘
```

### Components

- **Scraper**: Hourly job fetching from Working Nomads (extensible to other sources)
- **Matcher**: AI-powered job filtering using Claude API and your CV
- **Applier**: Automated application submission via Playwright + Claude AI
- **Reporter**: Status tracking and notifications
- **Dashboard**: Vue.js web interface for monitoring and control

## Tech Stack

- **Backend**: Python 3.12, FastAPI, JWT Authentication
- **Frontend**: Vue.js 3 with dark theme
- **Database**: PostgreSQL
- **Automation**: Playwright
- **AI**: Anthropic Claude API (Sonnet 4.5)
- **Package Manager**: uv
- **Deployment**: Docker on Synology NAS with GitHub Actions CI/CD

## Development Setup

### Prerequisites

- Python 3.12
- [uv](https://github.com/astral-sh/uv) package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [just](https://github.com/casey/just) command runner (`brew install just` or see [installation](https://github.com/casey/just#installation))
- Node.js 20+ (for frontend)
- Docker & Docker Compose
- Anthropic API key

### Quick Start

```bash
# 1. Install all dependencies
just setup

# 2. Edit .env file with your credentials
# ANTHROPIC_API_KEY, WORKING_NOMADS credentials, ADMIN_PASSWORD, JWT_SECRET_KEY

# 3. Start database and run migrations
just dev-setup

# 4. Run backend (in terminal 1)
just dev-backend

# 5. Run frontend (in terminal 2)
just dev-frontend
```

Access the application at `http://localhost:3000` and login with your admin credentials.

### Environment Variables

Zapply uses different environment configurations for local development and production deployment.

#### Local Development (`.env`)

For local development, copy `.env.example` to `.env` and configure:

```bash
# Database - Single URL for local development
DATABASE_URL=postgresql+asyncpg://zapply:zapply@localhost:5432/zapply

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

# Job Sources
WORKING_NOMADS_USERNAME=your_email@example.com
WORKING_NOMADS_PASSWORD=your_password

# Authentication
ADMIN_EMAIL=your_email@example.com
ADMIN_PASSWORD="$2b$12$..."  # Bcrypt hashed password (double quotes for local .env)
JWT_SECRET_KEY=your_random_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=43200  # 30 days
```

**Generating Required Values:**

```bash
# Generate JWT secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate bcrypt password hash
python -c "import bcrypt; print(bcrypt.hashpw('your_password'.encode('utf-8'), bcrypt.gensalt()).decode())"
```

#### Production (NAS) - `.env.production`

For production deployment on Synology NAS, create `/volume1/docker/zapply/.env.production`:

```bash
# PostgreSQL - Separate variables for Docker deployment
POSTGRES_USER=zapply
POSTGRES_PASSWORD=secure_production_password
POSTGRES_DB=zapply

# Application
APP_NAME=Zapply
DEBUG=false

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

# Job Sources
WORKING_NOMADS_USERNAME=your_email@example.com
WORKING_NOMADS_PASSWORD=your_password

# Authentication
ADMIN_EMAIL=your_email@example.com
ADMIN_PASSWORD='$2b$12$...'  # ⚠️ MUST use SINGLE quotes (see below)
JWT_SECRET_KEY=your_random_secret_key_here  # Same as local
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=43200

# GitHub (for CI/CD)
GITHUB_REPOSITORY_OWNER=your_github_username
IMAGE_TAG=latest
```

**Important Notes:**

- **Password Hash Quoting - CRITICAL:**
  - **Local .env**: Use **double quotes** `"$2b$12$..."` (Python reads .env directly)
  - **Production .env.production**: Use **SINGLE quotes** `'$2b$12$...'` (bash `source` command)
  - **Why**: Deploy script uses `source .env.production` which interprets `$` as shell variables
  - **With double quotes**: `"$2b$12$..."` → bash expands `$2b`, `$12` → BROKEN hash!
  - **With single quotes**: `'$2b$12$...'` → bash treats literally → CORRECT hash ✅

- **PostgreSQL**: Local uses `DATABASE_URL`, production uses separate `POSTGRES_*` variables
- **Passwords**: Use the same bcrypt hash and JWT secret in both environments
- **Security**: Never commit `.env` or `.env.production` to git
- **Template**: Use `.env.production.example` as a template for production setup

### Authentication

Zapply uses JWT-based authentication to secure access:

- **Login**: Email + password authentication
- **Token Expiry**: 30 days
- **Admin User**: Single admin user (email: configured in `.env`)
- **Password**: Set via `ADMIN_PASSWORD` in `.env`
- **JWT Secret**: Auto-generated or set via `JWT_SECRET_KEY` in `.env`

All routes except `/api/auth/login` require authentication.

### Common Commands

```bash
# Show all available commands
just

# Database operations
just db-start              # Start PostgreSQL
just db-stop               # Stop PostgreSQL
just db-status             # Check migration status
just db-upgrade            # Run pending migrations
just db-migrate "msg"      # Create new migration
just db-downgrade          # Rollback one migration

# Development
just dev-backend           # Run backend server
just dev-frontend          # Run frontend dev server
just dev-setup             # Setup database for development

# Deployment
just deploy                # Deploy to Synology NAS

# Code quality
just format                # Format Python code
just lint                  # Lint Python code
just test                  # Run tests

# Utilities
just health                # Check service health
just status                # Show current status
just clean                 # Remove generated files
```

### Environment Configuration

The `.env` file is created from `.env.example` during setup. Required variables:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
WORKING_NOMADS_USERNAME=your_email
WORKING_NOMADS_PASSWORD=your_password

# Authentication (auto-generated during setup)
ADMIN_EMAIL=your_email
ADMIN_PASSWORD=your_secure_password
JWT_SECRET_KEY=auto_generated_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=43200

# Optional (has defaults)
DATABASE_URL=postgresql+asyncpg://zapply:zapply@localhost:5432/zapply
DEBUG=false
```

## Production Deployment (Synology NAS)

Zapply uses **GitHub Actions with a self-hosted runner** on your NAS for automated deployments. This means GitHub Actions workflows run directly on your NAS with full local network access.

### Initial Setup

#### 1. Setup NAS Infrastructure
```bash
./scripts/setup-nas.sh
```
This creates directories and copies configuration to your NAS.

#### 2. Install GitHub Actions Runner on NAS
SSH to your NAS and run the setup script:
```bash
ssh vpetreski@192.168.0.188
cd /volume1/docker/zapply
./scripts/setup-github-runner.sh
```

The script will:
- Download and configure the GitHub Actions runner
- Register it with your repository
- Create start/stop scripts
- Start the runner

**Get the registration token before running:**
```bash
gh api -X POST repos/vpetreski/zapply/actions/runners/registration-token --jq .token
```

Or visit: https://github.com/vpetreski/zapply/settings/actions/runners/new

#### 3. Verify Runner is Connected
Check that the runner appears in GitHub:
https://github.com/vpetreski/zapply/settings/actions/runners

You should see "zapply-nas-runner" with status "Idle" (green dot).

#### 4. Test Deployment
Push to main branch or merge a PR. GitHub Actions will:
1. Build Docker images (on GitHub's cloud runners)
2. Push images to GitHub Container Registry
3. Deploy to NAS (on your self-hosted runner)

### Deployment Flow

```
Push to main → GitHub Actions (cloud) → Build Docker images → Push to GHCR
                      ↓
         Self-Hosted Runner (NAS) → Pull images → Deploy locally
```

**Benefits of self-hosted runner:**
- No SSH/port forwarding needed
- Runner initiates outbound connections only
- Runs on local network with direct access
- Free (GitHub doesn't charge for self-hosted runners)
- Secure (encrypted communication with GitHub)

### Accessing Production

#### Local Network Access
When connected to your home network:
- **Frontend**: http://192.168.0.188:3000
- **API/Swagger**: http://192.168.0.188:8000/docs

#### Remote Access (from anywhere)
For access outside your home network, you need to configure port forwarding on your Synology NAS:

**Option 1: Synology QuickConnect (Recommended)**
- QuickConnect URL: https://192-168-0-188.vpetreski.direct.quickconnect.to
- May require configuring reverse proxy in DSM for ports 3000 and 8000
- Steps:
  1. DSM → Control Panel → Application Portal → Reverse Proxy
  2. Create rules for ports 3000 (frontend) and 8000 (backend)

**Option 2: Direct Port Forwarding**
Configure your router to forward ports to your NAS:
- Forward external port 3000 → 192.168.0.188:3000 (frontend)
- Forward external port 8000 → 192.168.0.188:8000 (backend)
- Access via: `http://your-public-ip:3000`

**Option 3: DDNS + Port Forwarding**
1. Set up DDNS on Synology (Control Panel → External Access → DDNS)
2. Configure port forwarding as above
3. Access via: `http://your-ddns-name:3000`

#### First Login
1. Visit the frontend URL
2. You'll be redirected to `/login`
3. Login credentials:
   - **Email**: vanja@petreski.co (pre-filled)
   - **Password**: Your configured `ADMIN_PASSWORD`
4. Token valid for 30 days, stored in browser

### NAS SSH Setup

For easy access to your Synology NAS, set up passwordless SSH with an alias:

**Quick Setup:**
```bash
# 1. Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "vanja@petreski.co"

# 2. Copy key to NAS
ssh-copy-id vpetreski@192.168.0.188

# 3. Add alias for easy access
echo "alias nas='ssh vpetreski@192.168.0.188'" >> ~/.zshrc
source ~/.zshrc

# 4. Connect
nas
```

**Migrating to New Mac:**
```bash
# Copy these files from old Mac to new Mac:
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub

# On new Mac, set permissions:
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub

# Add alias
echo "alias nas='ssh vpetreski@192.168.0.188'" >> ~/.zshrc
source ~/.zshrc
```

**NAS Details:**
- **IP**: 192.168.0.188
- **Username**: vpetreski
- **Alias**: `nas`

### Production Management

```bash
# SSH to NAS (using alias)
nas

# Or directly
ssh vpetreski@192.168.0.188

# View application logs
cd /volume1/docker/zapply
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Check service status
docker compose -f docker-compose.prod.yml ps

# Manage GitHub Actions runner
/volume1/docker/zapply/start-runner.sh   # Start runner
/volume1/docker/zapply/stop-runner.sh    # Stop runner
tail -f /volume1/docker/zapply/runner.log  # View runner logs
ps aux | grep run.sh                      # Check runner status
```

## Database Migrations

Zapply uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. **Migrations must be run manually** - they do NOT run automatically on startup.

### Migration Workflow

**Check migration status:**
```bash
just db-status
```

**Run pending migrations:**
```bash
just db-upgrade
```

**Create a new migration (after changing models):**
```bash
just db-migrate "description of changes"
# Review the generated file in alembic/versions/ before applying!
```

**Rollback last migration (if needed):**
```bash
just db-downgrade
```

### Migration Best Practices

1. **Always review auto-generated migrations** - Alembic isn't perfect
2. **Run migrations before starting the app** - Avoid runtime schema errors
3. **Test migrations in development first** - Don't experiment in production
4. **Commit migration files with code changes** - Keep schema and code in sync
5. **Never edit applied migrations** - Create new ones instead

## Project Structure

```
zapply/
├── app/                    # Backend FastAPI application
│   ├── main.py            # Application entry point
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection and models
│   ├── routers/           # API routes (auth, jobs, runs, etc.)
│   ├── services/          # Business logic (scraper, matcher, scheduler)
│   └── utils/             # Utilities and helpers
├── frontend/              # Vue.js dashboard
│   ├── src/
│   │   ├── views/         # Page components (Dashboard, Jobs, Login, etc.)
│   │   ├── router/        # Vue Router with auth guards
│   │   └── main.js        # App entry with axios interceptors
│   ├── public/            # Static assets (favicon, etc.)
│   └── index.html         # HTML template
├── scripts/               # Deployment and utility scripts
│   ├── deploy.sh          # NAS deployment script
│   └── setup-nas.sh       # NAS initial setup
├── .github/workflows/     # GitHub Actions CI/CD
│   └── deploy.yml         # Automated deployment workflow
├── docker/                # Docker configuration files
├── docs/                  # Documentation
│   ├── ai.md             # AI context tracking
│   └── initial-prompt.md # Project requirements
├── CLAUDE.md              # Claude Code instructions
├── docker-compose.yml     # Local development compose
├── docker-compose.prod.yml # Production compose
├── Dockerfile.prod        # Production backend image
├── frontend/Dockerfile.prod # Production frontend image
├── pyproject.toml         # Python project configuration
└── justfile               # Command runner recipes
```

## Development Workflow

This project uses AI-assisted development with persistent context tracking:

1. **Start session**: Open Claude Code - it loads context from `docs/ai.md`
2. **Work together**: Collaborate on implementation
3. **Save progress**: Say "save" to update `docs/ai.md` and commit
4. **PR workflow**: All changes go through pull requests
5. **Automated deployment**: Merging to main triggers deployment to NAS

## Current Features

- ✅ Working Nomads scraper (hourly runs)
- ✅ AI-powered job matching with Claude Sonnet 4.5
- ✅ Profile management with CV upload
- ✅ PostgreSQL storage with status tracking
- ✅ Vue.js dashboard with dark theme
- ✅ Real-time run monitoring
- ✅ JWT authentication
- ✅ Docker deployment on Synology NAS
- ✅ GitHub Actions CI/CD

## Future Enhancements

- Application automation (Applier component)
- Additional job sources (We Work Remotely, Remotive, LinkedIn)
- Email/webhook notifications
- Advanced analytics and filtering
- Multi-user support
- Interview tracking

## License

Private project - All rights reserved.
# Test deployment

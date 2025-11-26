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

### Initial Setup

1. **Configure GitHub Secrets** (Settings → Secrets and variables → Actions):
   - `NAS_HOST`: Your NAS IP (e.g., `192.168.0.188`)
   - `NAS_USER`: SSH username (e.g., `vpetreski`)
   - `NAS_SSH_KEY`: Private SSH key for deployment (ED25519 recommended)

2. **Setup NAS Infrastructure** (one-time):
   ```bash
   ./scripts/setup-nas.sh
   ```
   This creates directories and copies configuration to your NAS.

3. **Merge to main branch**:
   - GitHub Actions automatically builds and deploys
   - Docker images pushed to GitHub Container Registry
   - NAS pulls latest images and restarts services

### Deployment Flow

```
Push to main → GitHub Actions → Build Docker images → Push to GHCR → SSH to NAS → Deploy
```

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

### Production Management

```bash
# Deploy manually (from main branch)
just deploy

# SSH to NAS
ssh vpetreski@192.168.0.188

# On NAS - view logs
cd /volume1/docker/zapply
docker compose -f docker-compose.prod.yml logs -f

# On NAS - restart services
docker compose -f docker-compose.prod.yml restart

# On NAS - check status
docker compose -f docker-compose.prod.yml ps
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

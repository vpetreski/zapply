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

- **Backend**: Python 3.12, FastAPI
- **Frontend**: Vue.js (latest)
- **Database**: PostgreSQL
- **Automation**: Playwright
- **AI**: Anthropic Claude API
- **Package Manager**: uv
- **Deployment**: Docker on Synology NAS

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

# 2. Edit .env file with your API keys
# ANTHROPIC_API_KEY, WORKING_NOMADS credentials, etc.

# 3. Start database and run migrations
just dev-setup

# 4. Run backend (in terminal 1)
just dev-backend

# 5. Run frontend (in terminal 2)
just dev-frontend
```

Access the dashboard at `http://localhost:3000`

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

# Docker (production-like)
just docker-up             # Start all services
just docker-down           # Stop all services
just docker-logs           # View logs

# Code quality
just format                # Format Python code
just lint                  # Lint Python code
just test                  # Run tests

# Utilities
just health                # Check service health
just status                # Show current status
just clean                 # Remove generated files
```

### Manual Setup (without just)

<details>
<summary>Click to expand manual setup instructions</summary>

```bash
# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment template
cp .env.example .env
# Edit .env with your API keys

# Start database
docker-compose up -d postgres

# IMPORTANT: Run migrations (required before first run)
uv run alembic upgrade head

# Run backend
uv run uvicorn app.main:app --reload

# Run frontend (in another terminal)
cd frontend && npm run dev
```

</details>

### Environment Configuration

The `.env` file is created from `.env.example` during setup. Edit it with your credentials:

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here
WORKING_NOMADS_USERNAME=your_username
WORKING_NOMADS_PASSWORD=your_password

# Optional (has defaults)
DATABASE_URL=postgresql+asyncpg://zapply:zapply@localhost:5432/zapply
SCHEDULER_INTERVAL_MINUTES=60
DEBUG=false
```

## Database Migrations

Zapply uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. **Migrations must be run manually** - they do NOT run automatically on startup.

### Migration Workflow

**When you need to run migrations:**
- After pulling new code that includes migration files
- After creating a new migration yourself
- Before starting the application if migrations are pending

**Check migration status:**
```bash
just db-status
# Shows current migration version and any pending migrations
```

**Run pending migrations:**
```bash
just db-upgrade
# Applies all pending migrations to bring database up to date
```

**Create a new migration (after changing models):**
```bash
just db-migrate "description of changes"
# Auto-generates migration based on model changes
# Review the generated file in alembic/versions/ before applying!
```

**Rollback last migration (if needed):**
```bash
just db-downgrade
# Rolls back one migration - use with caution!
```

### Why Manual Migrations?

Manual migrations give you:
- **Control**: Review migrations before applying
- **Safety**: No surprises in production
- **Debugging**: Easier to diagnose issues
- **Testing**: Can test migrations in staging first

### Migration Best Practices

1. **Always review auto-generated migrations** - Alembic isn't perfect
2. **Run migrations before starting the app** - Avoid runtime schema errors
3. **Test migrations in development first** - Don't experiment in production
4. **Commit migration files with code changes** - Keep schema and code in sync
5. **Never edit applied migrations** - Create new ones instead

### Troubleshooting

**Error: "Target database is not up to date"**
```bash
just db-status    # Check what's pending
just db-upgrade   # Apply pending migrations
```

**Error: "Can't locate revision"**
```bash
# You might be on wrong branch - switch to main and pull
git checkout main
git pull
just db-upgrade
```

**Want to reset everything? (DANGER: deletes all data)**
```bash
just db-reset
# This destroys the database and recreates it from scratch
```

## Project Structure

```
zapply/
├── app/                    # Backend FastAPI application
│   ├── main.py            # Application entry point
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection and models
│   ├── scraper/           # Job scraping module
│   ├── matcher/           # AI job matching module
│   ├── applier/           # Application automation module
│   └── reporter/          # Reporting and notifications
├── frontend/              # Vue.js dashboard
├── docker/                # Docker configuration
├── docs/                  # Documentation and AI context
│   ├── ai.md             # AI context tracking
│   └── initial-prompt.md # Project requirements
├── tests/                 # Test suite
├── CLAUDE.md              # Claude Code instructions
├── .cursorrules           # Cursor IDE configuration
├── docker-compose.yml     # Docker Compose setup
├── pyproject.toml         # Python project configuration
└── README.md              # This file
```

## Development Workflow

This project uses AI-assisted development with persistent context tracking:

1. **Start session**: Open Claude Code - it loads context from `docs/ai.md`
2. **Work together**: Collaborate on implementation
3. **Save progress**: Say "save" to update `docs/ai.md` and commit
4. **PR workflow**: All changes go through pull requests
5. **Code review**: Cursor Bugbot reviews PRs automatically

## MVP Scope (Week 1)

- ✅ Working Nomads scraper (single source)
- ✅ Basic matcher with Claude AI
- ✅ Basic applier with Playwright + Claude AI
- ✅ Simple status tracking in Postgres
- ✅ Basic reporter (console/logs initially)
- ✅ Minimal Vue.js dashboard

## Future Enhancements

- Additional job sources (We Work Remotely, Remotive, LinkedIn)
- Advanced dashboard features and analytics
- Email/webhook notifications
- Multi-user support
- Commercial features
# Zapply

> AI-powered job application automation for remote software engineers

[![Deploy](https://github.com/vpetreski/zapply/actions/workflows/deploy.yml/badge.svg)](https://github.com/YOUR_USERNAME/zapply/actions/workflows/deploy.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Vue.js 3](https://img.shields.io/badge/vue.js-3-green.svg)](https://vuejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Zapply automates the tedious process of finding and filtering remote software engineering positions. It scrapes multiple job boards, uses AI to match opportunities against your profile, and provides a clean dashboard for review and tracking.

**Key Features:**
- Multi-source job scraping (Working Nomads, We Work Remotely, Remotive, DailyRemote, Himalayas)
- AI-powered job matching using Claude API
- Intelligent filtering for remote/contractor-friendly positions
- Real-time dashboard with job review workflow
- Automated daily scheduling
- Self-hosted deployment with Docker

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SCRAPER   │────▶│   MATCHER   │────▶│  DASHBOARD  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                     ┌─────▼─────┐
                     │  POSTGRES │
                     └───────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **Scraper** | Multi-source job fetching with parallel execution |
| **Matcher** | AI-powered filtering using Claude Sonnet |
| **Dashboard** | Vue.js interface for job review and management |
| **Scheduler** | APScheduler for automated daily runs |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **Frontend**: Vue.js 3, Vite, dark theme
- **Database**: PostgreSQL 15
- **AI**: Anthropic Claude API
- **Automation**: Playwright
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **Deployment**: Docker, GitHub Actions

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [just](https://github.com/casey/just) command runner
- Node.js 20+
- Docker & Docker Compose
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/zapply.git
cd zapply

# Install dependencies
just setup

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Start database
just db-start

# Run migrations
just db-upgrade

# Start backend (terminal 1)
just dev-backend

# Start frontend (terminal 2)
just dev-frontend
```

Access the application at `http://localhost:3000`

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://zapply:zapply@localhost:5432/zapply

# AI
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Job Sources (optional - depends on which sources you enable)
WORKING_NOMADS_USERNAME=your_email
WORKING_NOMADS_PASSWORD=your_password
REMOTIVE_USERNAME=your_email
REMOTIVE_PASSWORD=your_password
DAILYREMOTE_TOKEN=your_token

# Authentication
ADMIN_EMAIL=your_email@example.com
ADMIN_PASSWORD="$2b$12$..."  # bcrypt hash
JWT_SECRET_KEY=your_secret_key
```

### Generating Credentials

```bash
# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate password hash
python -c "import bcrypt; print(bcrypt.hashpw('your_password'.encode(), bcrypt.gensalt()).decode())"
```

## Usage

### Daily Workflow

1. **Automated scraping** runs daily (configurable schedule)
2. **AI matching** evaluates each job against your profile
3. **Review jobs** in the dashboard, filter by match score
4. **Manual overrides** - mark jobs as matched/rejected
5. **Track applications** - mark jobs as applied

### Job Sources

| Source | Type | Auth | Notes |
|--------|------|------|-------|
| Working Nomads | Browser | Email/Password | Premium features |
| We Work Remotely | RSS | None | Public feeds |
| Remotive | Browser | Email/Password | Premium features |
| DailyRemote | Browser | Token | Premium session |
| Himalayas | API | None | Public API |

### Matching Criteria

The AI matcher evaluates jobs based on your profile and preferences:

**Accepts:**
- True remote positions
- International contractor friendly
- LATAM/timezone compatible

**Rejects:**
- Work authorization requirements
- Physical presence requirements
- Specific location restrictions

## Development

### Commands

```bash
# Show all commands
just

# Database
just db-start          # Start PostgreSQL
just db-stop           # Stop PostgreSQL
just db-status         # Migration status
just db-upgrade        # Run migrations
just db-migrate "msg"  # Create migration

# Development
just dev-backend       # Run backend
just dev-frontend      # Run frontend
just dev-setup         # Full dev setup

# Code quality
just format            # Format code
just lint              # Run linter
just test              # Run tests
```

### Project Structure

```
zapply/
├── app/                    # Backend application
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Configuration
│   ├── models.py          # Database models
│   ├── schemas.py         # Pydantic schemas
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic
│   └── scraper/           # Job scrapers
├── frontend/              # Vue.js application
│   ├── src/views/         # Page components
│   └── src/router/        # Routing
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── docker/                # Docker configs
```

## Deployment

### Docker Compose (Recommended)

```bash
# Build and start
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### GitHub Actions CI/CD

The repository includes GitHub Actions workflows for automated deployment:

1. Push to `main` triggers build
2. Docker images pushed to GitHub Container Registry
3. Self-hosted runner deploys to your infrastructure

See `.github/workflows/deploy.yml` for configuration.

### Self-Hosted Runner Setup

For automated deployments, set up a GitHub Actions runner on your server:

1. Go to repository Settings → Actions → Runners
2. Add new self-hosted runner
3. Follow installation instructions
4. Configure as a service for persistence

## Database Migrations

Zapply uses Alembic for schema management:

```bash
# Check status
just db-status

# Run pending migrations
just db-upgrade

# Create new migration
just db-migrate "description"

# Rollback
just db-downgrade
```

**Important:** Migrations must be run manually - they do not auto-run on startup.

## API Documentation

With the backend running, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/jobs` | GET | List jobs with filtering |
| `/api/jobs/{id}` | GET | Get job details |
| `/api/jobs/{id}/status` | PATCH | Update job status |
| `/api/runs` | GET | List scraper runs |
| `/api/scraper/run` | POST | Trigger manual run |
| `/api/profile` | GET/PUT | Manage user profile |
| `/api/sources` | GET | List scraper sources |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Tests
- `chore:` - Maintenance

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Anthropic Claude](https://www.anthropic.com/) for AI capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [Vue.js](https://vuejs.org/) for the frontend framework
- [Playwright](https://playwright.dev/) for browser automation

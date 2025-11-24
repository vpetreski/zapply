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
- uv package manager
- Node.js (for frontend)
- Docker & Docker Compose
- Anthropic API key

### Installation

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Environment Configuration

Create `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://zapply:zapply@localhost:5432/zapply

# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here

# Job Sources
WORKING_NOMADS_USERNAME=your_username
WORKING_NOMADS_PASSWORD=your_password

# Application
SCHEDULER_INTERVAL_MINUTES=60
```

### Running Locally

```bash
# Start database
docker-compose up -d postgres

# Run backend
uv run uvicorn app.main:app --reload

# Run frontend (in another terminal)
cd frontend
npm run dev
```

### Running with Docker

```bash
docker-compose up -d
```

Access the dashboard at `http://localhost:3000`

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
├── docs/                  # Documentation
├── tests/                 # Test suite
├── ai.md                  # AI context tracking
├── CLAUDE.md              # Claude Code instructions
├── .cursorrules           # Cursor IDE configuration
├── docker-compose.yml     # Docker Compose setup
├── pyproject.toml         # Python project configuration
└── README.md              # This file
```

## Development Workflow

This project uses AI-assisted development with persistent context tracking:

1. **Start session**: Open Claude Code - it loads context from `ai.md`
2. **Work together**: Collaborate on implementation
3. **Save progress**: Say "save" to update `ai.md` and commit
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

## License

Private - Vanja Petreski © 2024

## Contact

Vanja Petreski - vanja@petreski.co

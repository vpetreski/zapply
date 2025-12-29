# Claude Code Instructions for Zapply

## Project Overview

Zapply is an AI-powered job application automation system designed for remote software engineers seeking international contractor positions. The system automates the tedious process of finding, filtering, and tracking job applications.

## Architecture

### Core Components

1. **Scraper** - Fetches jobs from multiple sources (Working Nomads, We Work Remotely, Remotive, DailyRemote, Himalayas)
2. **Matcher** - Uses Claude AI to intelligently match jobs against user profile
3. **Dashboard** - Vue.js frontend for job review and management
4. **Scheduler** - APScheduler for automated daily scraping

### Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), Alembic
- **Frontend**: Vue.js 3, Vite
- **Database**: PostgreSQL
- **AI**: Anthropic Claude API (Sonnet model)
- **Automation**: Playwright for browser-based scraping
- **Package Manager**: uv
- **Deployment**: Docker, GitHub Actions CI/CD

## Development Guidelines

### Code Style

- Always use Python type hints
- Use async/await for I/O-bound operations
- Follow PEP 8 style guide
- Use Pydantic models for data validation
- Keep components loosely coupled

### Package Management

```bash
# Add dependency
uv add package-name

# Run backend
uv run uvicorn app.main:app --reload

# Run migrations
uv run alembic upgrade head
```

### Environment Configuration

All sensitive configuration is via environment variables in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/zapply
ANTHROPIC_API_KEY=your_api_key_here
ADMIN_EMAIL=your_email@example.com
ADMIN_PASSWORD="bcrypt_hashed_password"
JWT_SECRET_KEY=your_secret_key
```

See `.env.example` for the full list of configuration options.

## Key Features

### Job Matching Criteria

The AI matcher evaluates jobs based on:

**Accept if:**
- True remote positions (location agnostic)
- Open to international contractors
- Compatible with LATAM timezone

**Reject if:**
- Requires specific work authorization
- Physical presence requirements (hybrid/office)
- Location-specific restrictions

### User Profile System

Users manage their profile via the `/profile` UI:
- Upload CV (PDF)
- Add custom instructions for AI matching
- AI generates optimized profile summary

### Scraper Sources

| Source | Type | Auth Required |
|--------|------|---------------|
| Working Nomads | Browser | Yes |
| We Work Remotely | RSS | No |
| Remotive | Browser | Yes |
| DailyRemote | Browser | Token |
| Himalayas | API | No |

## Development Workflow

### Local Development

```bash
# Setup
just setup

# Start database
just db-start

# Run migrations
just db-upgrade

# Start backend
just dev-backend

# Start frontend (separate terminal)
just dev-frontend
```

### Git Workflow

- Create feature branches for major work
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`
- All changes through pull requests
- Never commit secrets or `.env` files

## Project Structure

```
zapply/
├── app/                    # Backend FastAPI application
│   ├── main.py            # Application entry point
│   ├── config.py          # Configuration management
│   ├── models.py          # SQLAlchemy models
│   ├── routers/           # API routes
│   ├── services/          # Business logic
│   └── scraper/           # Job source scrapers
├── frontend/              # Vue.js dashboard
│   ├── src/views/         # Page components
│   └── src/router/        # Vue Router
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
└── docs/                  # Documentation
```

## Deployment

The application is designed for self-hosted deployment:
- Docker Compose for container orchestration
- GitHub Actions for CI/CD
- Self-hosted runner for deployment

See `README.md` for detailed deployment instructions.

## Key Files

- `app/ai_models.py` - AI model constants
- `app/matcher/matcher.py` - Job matching logic
- `app/services/scraper_service.py` - Scraper orchestration
- `app/services/scheduler_service.py` - Scheduled job runs
- `frontend/src/views/Jobs.vue` - Main job review interface

## Best Practices

1. **Move fast, iterate quickly** - Focus on working features
2. **AI where it adds value** - Use AI for matching, not for simple logic
3. **Cost efficient** - Be mindful of API costs
4. **Simple over complex** - Avoid over-engineering
5. **Test with real data** - Verify against actual job postings

# Zapply - Development Context

## Current Status

**Phase:** Production Ready

The system is fully functional with:
- Multi-source job scraping
- AI-powered job matching
- Dashboard for job review
- Automated scheduling

## Architecture

### AI Models
- **Matching**: Claude Sonnet

### Components
- FastAPI backend with async SQLAlchemy
- Vue.js frontend with dark theme
- PostgreSQL database
- APScheduler for daily automation

### Job Sources
- Working Nomads
- We Work Remotely (RSS)
- Remotive
- DailyRemote
- Himalayas

## Workflow

```
Scheduler (daily) → Scraper → NEW jobs
                        ↓
                    Matcher → MATCHED / REJECTED (auto)
                        ↓
                  Dashboard → User reviews jobs
                        ↓
                  Manual Override (optional)
                        ↓
                  Track as Applied
```

## Key Files

| File | Purpose |
|------|---------|
| `app/ai_models.py` | AI model constants |
| `app/matcher/matcher.py` | Job matching logic |
| `app/scraper/*.py` | Job source scrapers |
| `app/services/scraper_service.py` | Scraper orchestration |
| `app/services/scheduler_service.py` | Daily scheduling |
| `frontend/src/views/Jobs.vue` | Main job review UI |
| `frontend/src/views/ProfileView.vue` | Profile management |

## Features

### Implemented
- [x] Multi-source scraping with parallel execution
- [x] AI-powered job matching (Claude Sonnet)
- [x] User profile with CV upload
- [x] Real-time dashboard
- [x] JWT authentication
- [x] Docker deployment
- [x] GitHub Actions CI/CD
- [x] Manual status overrides
- [x] Infinite scroll pagination

### Removed by Design
- ~~Automated application submission~~ (ATS compatibility issues)
- ~~Statistics dashboard~~ (Simplified to job-focused UI)

## Database

### Key Tables
- `jobs` - Job listings with status tracking
- `runs` - Scraper run history
- `source_runs` - Per-source run statistics
- `scraper_sources` - Source configuration
- `user_profiles` - User CV and preferences

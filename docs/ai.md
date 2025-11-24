# Zapply - AI Context

## Current Phase
**Phase 1: Project Foundation Complete**

Complete project structure with backend, frontend, Docker, and development automation ready. Foundation is solid and ready for feature implementation.

## Last Session - 2025-11-24

### Accomplished
**Initial Setup:**
- Read and understood project requirements from `docs/initial-prompt.md`
- Reviewed Vanja's resume (`docs/Resume-Vanja-Petreski.pdf`)
- Confirmed technology choices with user:
  - Python 3.12, uv for package management
  - Monorepo structure (backend + frontend together)
  - Fresh Docker setup

**Backend (Python/FastAPI):**
- ✅ Complete FastAPI application structure
- ✅ Database models: Job, UserProfile, ApplicationLog with proper status tracking
- ✅ Pydantic schemas for API requests/responses
- ✅ API endpoints: health check, jobs (list/detail/update), statistics
- ✅ SQLAlchemy async database setup
- ✅ Alembic migrations configuration
- ✅ Module skeletons for all 4 components (scraper, matcher, applier, reporter) with TODOs
- ✅ Configuration management via pydantic-settings
- ✅ pyproject.toml with all dependencies defined

**Frontend (Vue.js):**
- ✅ Vue 3 with Composition API and Vue Router
- ✅ Modern dark theme UI with clean styling
- ✅ Three main views: Dashboard (stats), Jobs (list with filters), Stats (detailed analytics)
- ✅ Axios integration for API communication
- ✅ Vite build configuration with proxy to backend

**Infrastructure:**
- ✅ Dockerfile for backend (Python + Playwright)
- ✅ Dockerfile for frontend (Node build + Nginx)
- ✅ docker-compose.yml with all services (postgres, backend, frontend)
- ✅ PostgreSQL service with health checks
- ✅ Nginx reverse proxy configuration for frontend

**Development Workflow:**
- ✅ Comprehensive Justfile with 30+ automation recipes
- ✅ Setup, database, development, docker, code quality, and utility commands
- ✅ README updated with quick start using just commands
- ✅ .env.example template for configuration
- ✅ Git repository initialized and pushed to GitHub

**Documentation & Tooling:**
- ✅ CLAUDE.md - Detailed instructions for Claude Code
- ✅ .cursorrules - Instructions for Cursor IDE
- ✅ docs/ai.md - Context tracking (this file)
- ✅ Moved ai.md to docs folder for better organization
- ✅ Created private GitHub repo: https://github.com/vpetreski/zapply

### Current Status
- **Project structure**: 100% complete and committed
- **Backend skeleton**: Ready for implementation (all TODOs marked)
- **Frontend UI**: Fully functional dashboard (will display data once backend implements features)
- **Database**: Models defined, migrations ready to run
- **Development workflow**: Streamlined with Justfile commands
- **Git repository**: Pushed to GitHub, all changes committed

### Next Steps (When User Returns)
**User will:**
1. Review the complete setup
2. Install just command runner
3. Run `just setup` to install dependencies
4. Test the application locally
5. Provide feedback on structure and approach

**Then implement core features:**
1. **Scraper**: Implement Working Nomads scraper with Playwright
2. **Matcher**: Integrate Claude API for intelligent job filtering
3. **Applier**: Build Playwright + Claude automation for applications
4. **Scheduler**: Set up APScheduler for hourly job fetching
5. **Testing**: Test with real Working Nomads data

## Decisions Log

### Technology Stack
- **Python 3.12**: Latest stable version for best performance
- **uv**: Ultra-fast Rust-based package manager for modern Python workflow
- **just**: Command runner for workflow automation (like make but better)
- **Monorepo**: Simpler for MVP, easier coordination between backend and frontend
- **Fresh Docker**: No existing Synology setup to integrate with

### Architecture Decisions
- **Monolith over microservices**: Simpler for MVP, can split later if needed
- **Sequential processing**: No message queues (Kafka) for MVP - use database status fields
- **Single database**: PostgreSQL for all data - jobs, status, configuration
- **Aggressive AI in Applier**: Cost-efficient in Matcher, but use Claude heavily in Applier
- **Justfile for automation**: Makes setup and development workflow much simpler

### File Organization
- **docs/ai.md**: Moved AI context to docs folder for cleaner project root
- **All docs in docs/**: Centralized documentation location

### MVP Scope (Week 1)
**In Scope:**
- Working Nomads scraper only (single source)
- Basic Claude-powered matcher
- Basic Playwright + Claude applier
- PostgreSQL status tracking
- Simple console/log reporter
- Minimal Vue.js dashboard

**Explicitly Out:**
- Additional job sources
- Advanced dashboard features
- Email/webhook notifications
- Analytics and insights
- Multi-user support
- Commercial features

## Target User Profile (for Matcher)

**Personal Info:**
- Name: Vanja Petreski
- Level: Principal Software Engineer
- Experience: 20 years
- Location: Colombia (Colombian and Serbian citizenship, NO US work permit)
- Work Style: 100% remote contractor via Petreski LLC
- Rate: $10,000 USD/month

**Skills:**
- Core: Java, Kotlin, Spring Boot, Backend, APIs, Architecture, Tech Leadership, Product Management
- Extended (AI-enabled): Python, FastAPI, Go, Node, TypeScript, mobile (iOS, Android, Flutter), frontend (Vue, React)
- Value Prop: Experience, architecture, product thinking, tech leadership - not limited to specific tech stack

**Job Criteria:**
- ✅ MUST HAVE: True remote (location doesn't matter), US companies open to international contractors OR Latam/Colombia hiring, Contract or FT compatible with contractor setup
- ❌ MUST REJECT: US work authorization required, Physical presence requirements, Hybrid positions, Location-specific requirements

## Key Architectural Components

### 1. Scraper (TODO - Implementation needed)
- Runs hourly via scheduler
- Fetches from Working Nomads (premium account)
- First run: last 2 weeks, subsequent: only new jobs
- NO AI - just Playwright data extraction
- Transform to source-agnostic internal model
- File: `app/scraper/working_nomads.py`

### 2. Matcher (TODO - Implementation needed)
- Triggered on new jobs
- Uses Claude API for intelligent matching
- Input: CV PDF + job description + filtering criteria
- Output: MATCHED/REJECTED with reasoning
- Must be cost-efficient with API calls
- File: `app/matcher/matcher.py` (prompt template already created)

### 3. Applier (TODO - Implementation needed)
- Triggered on MATCHED jobs
- Uses Playwright + Claude AI (aggressive usage)
- Navigate arbitrary ATS systems
- Fill forms, answer questions
- Mark as APPLIED/FAILED
- File: `app/applier/applier.py`

### 4. Reporter (TODO - Implementation needed)
- Triggered after application attempts
- Generate reports and notifications
- Initially: console/logs
- Future: email/webhook
- File: `app/reporter/reporter.py`

### Data Flow
```
NEW → MATCHED/REJECTED → APPLIED/FAILED → REPORTED
```

## Infrastructure Plan

**Local Development (using Justfile):**
```bash
just setup           # Install all dependencies
just dev-setup       # Start database and run migrations
just dev-backend     # Run backend (terminal 1)
just dev-frontend    # Run frontend (terminal 2)
```

**Production (Synology NAS):**
- All services in Docker containers via `just docker-up`
- docker-compose.yml for orchestration
- Benefits: 24/7 uptime, residential IP (avoids bot detection), local data storage
- Remote access via Synology QuickConnect

## Job Sources

**MVP:** Working Nomads only
- Vanja has premium account
- Clean UI, frequent updates, good quality
- Primary source for remote jobs

**Future:**
- We Work Remotely
- Remotive
- Gun.io (if quality improves)
- LinkedIn (scraping is complex, maybe use API)

**Explicitly Avoid:**
- JobCopilot (Vanja says ineffective)
- Direct LinkedIn application (bad filtering, no responses)

## Blockers
None currently. Waiting for user to review and provide feedback.

## Notes

### Project Timeline
- Start: November 24, 2025
- Target MVP: December 1, 2025 (1 week)
- This is aggressive but achievable with focused scope
- Day 1: ✅ Complete foundation and structure

### Development Workflow
1. Open Claude Code → loads this `docs/ai.md`
2. I tell user what's next based on this context
3. Work together on implementation
4. User says "save" → I update this file and commit
5. Session complete

### Important Context Files
- `docs/initial-prompt.md` - Original project requirements
- `docs/Resume-Vanja-Petreski.pdf` - Vanja's CV (use for matching)
- `CLAUDE.md` - My instructions (Claude Code)
- `.cursorrules` - Cursor IDE instructions
- `Justfile` - All automation commands

### Justfile Quick Reference
- `just` - Show all commands
- `just setup` - Install everything
- `just dev-setup` - Setup database
- `just dev-backend/frontend` - Run services
- `just docker-up` - Run everything in Docker
- `just health` - Check service status
- `just db-migrate "msg"` - Create migration

### Cost Considerations
- Matcher: Be efficient - don't call Claude API unnecessarily
- Applier: Use Claude aggressively - worth the cost to automate applications
- Monitor API usage during MVP to understand real costs

### Key Success Criteria
1. Can fetch jobs from Working Nomads hourly
2. Can accurately filter jobs (remote, contractor-friendly, Latam-OK)
3. Can submit at least 1 real application automatically
4. User can see jobs and status in dashboard
5. System runs unattended on Synology NAS

## Implementation Status

### ✅ Completed
- [x] Project structure and organization
- [x] Backend skeleton (FastAPI, models, schemas, endpoints)
- [x] Frontend UI (Vue.js, dashboard, views)
- [x] Database configuration (PostgreSQL, Alembic)
- [x] Docker configuration (all services)
- [x] Development automation (Justfile)
- [x] Documentation (README, CLAUDE.md, .cursorrules)
- [x] Git repository and GitHub setup
- [x] All files committed and pushed

### ⏳ Pending (MVP Week 1)
- [ ] Working Nomads scraper implementation (Playwright)
- [ ] Claude API integration for matcher
- [ ] PDF CV reading and text extraction
- [ ] Playwright + Claude applier implementation
- [ ] APScheduler integration for hourly runs
- [ ] Testing with real Working Nomads data
- [ ] First database migration
- [ ] End-to-end testing of complete workflow

### 🚀 Future Enhancements (Post-MVP)
- [ ] Additional job sources (We Work Remotely, Remotive)
- [ ] Email/webhook notifications
- [ ] Advanced dashboard analytics
- [ ] Multi-user support
- [ ] Commercial features

---

**Last Updated:** 2025-11-24 by Claude Code
**Next Session:** User will review setup, provide feedback, then implement core features (scraper, matcher, applier)
**GitHub:** https://github.com/vpetreski/zapply (private)

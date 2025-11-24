# Zapply - AI Context

## Current Phase
**Phase 0: Project Initialization**

Setting up the foundational structure for Zapply - the AI-powered job application automation system.

## Last Session - 2025-11-24

### Accomplished
- Read and understood project requirements from `docs/initial-prompt.md`
- Reviewed Vanja's resume (`docs/Resume-Vanja-Petreski.pdf`)
- Confirmed technology choices with user:
  - Python 3.12
  - uv for package management
  - Monorepo structure (backend + frontend together)
  - Fresh Docker setup
- Created foundational files:
  - `.gitignore` - Comprehensive ignore rules for Python, Node, Docker, etc.
  - `README.md` - Project overview, architecture diagram, setup instructions
  - `CLAUDE.md` - Detailed instructions for Claude Code (me!)
  - `.cursorrules` - Instructions for Cursor IDE
  - `ai.md` - This context tracking file

### Current Status
- Project structure initialized
- Documentation and AI tool configurations complete
- Ready to create backend and frontend scaffolding
- Git repository not yet initialized

### Next Steps
1. Initialize git repository
2. Create Python backend structure with FastAPI
3. Create Vue.js frontend structure
4. Set up Docker configuration files
5. Create initial database models and schemas
6. Implement basic scraper structure
7. Test setup works end-to-end

## Decisions Log

### Technology Stack
- **Python 3.12**: Latest stable version for best performance
- **uv**: Ultra-fast Rust-based package manager for modern Python workflow
- **Monorepo**: Simpler for MVP, easier coordination between backend and frontend
- **Fresh Docker**: No existing Synology setup to integrate with

### Architecture Decisions
- **Monolith over microservices**: Simpler for MVP, can split later if needed
- **Sequential processing**: No message queues (Kafka) for MVP - use database status fields
- **Single database**: PostgreSQL for all data - jobs, status, configuration
- **Aggressive AI in Applier**: Cost-efficient in Matcher, but use Claude heavily in Applier

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

### 1. Scraper
- Runs hourly via scheduler
- Fetches from Working Nomads (premium account)
- First run: last 2 weeks, subsequent: only new jobs
- NO AI - just Playwright data extraction
- Transform to source-agnostic internal model

### 2. Matcher
- Triggered on new jobs
- Uses Claude API for intelligent matching
- Input: CV PDF + job description + filtering criteria
- Output: MATCHED/REJECTED with reasoning
- Must be cost-efficient with API calls

### 3. Applier
- Triggered on MATCHED jobs
- Uses Playwright + Claude AI (aggressive usage)
- Navigate arbitrary ATS systems
- Fill forms, answer questions
- Mark as APPLIED/FAILED

### 4. Reporter
- Triggered after application attempts
- Generate reports and notifications
- Initially: console/logs
- Future: email/webhook

### Data Flow
```
NEW → MATCHED/REJECTED → APPLIED/FAILED → REPORTED
```

## Infrastructure Plan

**Local Development:**
- Backend runs via `uv run uvicorn`
- Frontend runs via `npm run dev`
- Database runs via `docker-compose up postgres`

**Production (Synology NAS):**
- All services in Docker containers
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
None currently.

## Notes

### Project Timeline
- Start: November 24, 2025
- Target MVP: December 1, 2025 (1 week)
- This is aggressive but achievable with focused scope

### Development Workflow
1. Open Claude Code → loads this `ai.md`
2. I tell user what's next based on this context
3. Work together on implementation
4. User says "save" → I update this file and commit
5. Session complete

### Important Context Files
- `docs/initial-prompt.md` - Original project requirements
- `docs/Resume-Vanja-Petreski.pdf` - Vanja's CV (use for matching)
- `CLAUDE.md` - My instructions (Claude Code)
- `.cursorrules` - Cursor IDE instructions

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

## Immediate Next Actions
1. ✅ Project structure and documentation files created
2. 🔄 Initialize git repository
3. ⏳ Create Python backend structure (FastAPI, folders, dependencies)
4. ⏳ Create Vue.js frontend structure
5. ⏳ Create Docker configuration
6. ⏳ Build database models and schemas
7. ⏳ Implement scraper module skeleton

---

**Last Updated:** 2025-11-24 by Claude Code
**Next Session:** Continue with backend structure setup

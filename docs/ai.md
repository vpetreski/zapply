# Zapply - AI Context

## Current Phase
**Phase 8 Complete: Final UI Polish & Manual Matching Controls**

The system is now polished for daily use with simplified UI, manual override controls, and auto/manual matching tracking.

**Current Branch:** `feature/applier` (PR #8 ready for merge to main)

## Last Session - 2025-12-07 (Final Polish)

### What Was Done

**UI Simplification:**

1. **Removed Dashboard and Statistics Pages**
   - Jobs page is now the initial landing page after login
   - Deleted `Dashboard.vue` and `Stats.vue`
   - Updated router and navigation

2. **Simplified Jobs Page Filters**
   - Removed "New" from status filter (only Matched/Rejected)
   - Removed Sort By filter (always sorts by date desc, then score desc)
   - Removed Min Score slider
   - Added Matching filter: Both (default), Auto, Manual
   - Added Date filter: Last 7 Days (default), 15 Days, 30 Days, All

3. **Manual Override Buttons**
   - "Mark Matched" button on rejected jobs
   - "Mark Rejected" button on matched jobs
   - "Mark Applied" button on matched jobs (not yet applied)
   - Available on both job cards and detail modal

4. **Matching Source Tracking**
   - Added `matching_source` field to Job model (auto/manual)
   - Display auto/manual badge next to status badge
   - Manual overrides set `matching_source` to "manual"
   - Database migration applied (all existing jobs set to "auto")

5. **Admin Page Cleanup**
   - Removed Database Cleanup section
   - Only Settings remain (Run Frequency, Scrape Limit)

6. **Scheduler Change**
   - Changed daily schedule from 9pm to 6am Colombian time

### Commits
- `346a9ad` - Add auto/manual matching source badge to job cards and detail modal
- `450c2a5` - Final polish: simplify UI and add manual matching controls

---

## New Workflow: Auto Scrape + Match, Manual Apply

### How Zapply Works Now

```
Scheduler (daily 6am) → Scraper → NEW jobs
                             ↓
                         Matcher → MATCHED / REJECTED (auto)
                             ↓
                       Jobs Page → User reviews jobs
                             ↓
                       Manual Override (optional) → MATCHED / REJECTED (manual)
                             ↓
                       User manually applies on job sites
                             ↓
                       Mark as Applied (optional tracking)
```

### User Daily Workflow

1. **Morning (after 6am)**: Open Zapply Jobs page
2. **Review**: Check MATCHED jobs from overnight scraping (default: Last 7 Days)
3. **Override**: Mark false positives as Rejected, or promote Rejected jobs to Matched
4. **Apply**: Click job URL, apply manually on the job site
5. **Track**: Click "Mark Applied" to track which jobs you've applied to

### Key Features

- **Auto/Manual Tracking**: See which jobs were matched by AI vs manually overridden
- **Date Filtering**: Focus on recent jobs (7/15/30 days or all)
- **Manual Override**: Correct AI matching mistakes with one click
- **Applied Tracking**: Keep track of jobs you've applied to

---

## Implementation Status

### ✅ Complete
- [x] FastAPI backend with async SQLAlchemy
- [x] Working Nomads scraper with Playwright
- [x] Claude API integration for matching (Sonnet model)
- [x] UserProfile management with AI generation
- [x] Real-time Vue.js Jobs page
- [x] APScheduler for daily scheduling (6am Colombian time)
- [x] Production deployment on Synology NAS
- [x] Simplified status workflow (NEW/MATCHED/REJECTED)
- [x] Manual override buttons (Match/Reject/Applied)
- [x] Auto/Manual matching source tracking
- [x] Date-based filtering (7/15/30 days)

### ❌ Removed (By Design)
- [x] ~~Dashboard page~~ - Jobs is now the landing page
- [x] ~~Statistics page~~ - Simplified to just Jobs view
- [x] ~~Sort By filter~~ - Always sorts by date then score
- [x] ~~Min Score filter~~ - Removed complexity
- [x] ~~Automated Applier~~ - Removed due to ATS compatibility issues
- [x] ~~Database Cleanup UI~~ - Removed from Admin page

---

## Key Files

- `app/ai_models.py` - AI model constants (CLAUDE_SONNET for matching)
- `app/models.py` - Job model with `matching_source` field
- `app/matcher/matcher.py` - Job matching logic
- `app/scraper/` - Working Nomads scraper
- `app/routers/jobs.py` - Jobs API with filtering and manual override
- `app/services/scheduler_service.py` - Daily scheduler at 6am
- `frontend/src/views/Jobs.vue` - Main job review page with filters and buttons
- `frontend/src/assets/main.css` - Badge styles (matched/rejected/auto/manual)

---

## Architecture Notes

### AI Models
- **Matching**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Profile Generation**: Claude Sonnet 4.5

### Database
- PostgreSQL with async SQLAlchemy
- Job statuses: NEW → MATCHED/REJECTED
- Matching source: auto (AI) / manual (user override)
- UserProfile with CV storage and AI-generated summary

### Deployment
- Docker Compose on Synology NAS
- Traefik reverse proxy
- PostgreSQL in container

---

**Last Updated:** 2025-12-07 by Claude Code

**Status:** Ready for daily use - auto scrape/match at 6am, manual review and override, manual apply workflow

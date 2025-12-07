# Zapply - AI Context

## Current Phase
**Phase 8 Complete: Final UI Polish & Simplification**

The system is polished for daily use with minimal UI, manual override controls, and streamlined profile management.

**Current Branch:** `feature/applier` (PR #8 merged to main)

## Last Session - 2025-12-07 (Final Polish Continued)

### What Was Done

**Profile Page Simplification:**

1. **Removed Basic Information Fields**
   - Removed from model: name, email, phone, location, rate, linkedin, github
   - Removed PDF binary storage (cv_data)
   - Profile now only has: cv_filename, cv_text, custom_instructions, skills, preferences, ai_generated_summary

2. **Simplified Profile UI**
   - Removed Basic Info section from view and edit modes
   - Edit mode: Just "Select PDF File" button + Custom Instructions textarea
   - Save/Cancel buttons at bottom with spinner, no helper text
   - User puts all their info (name, rate, location, preferences) in Custom Instructions

3. **Database Migration**
   - Dropped 8 columns from user_profiles table

**Runs Page Simplification:**

4. **Removed All Filters**
   - Removed status and phase filter dropdowns
   - Just "Start New Run" button remains
   - Shows all runs, all statuses, all phases
   - Sorted by latest first (started_at desc)
   - Infinite scroll pagination works

**Scraper Enhancement:**

5. **Working Nomads Last 7 Days Filter**
   - Scraper now filters by "Last 7 Days" posted date automatically
   - Shows "Last 7 Days" badge on Runs page

**Previous Session Changes:**

- Jobs page is the landing page (removed Dashboard/Stats)
- Simplified Jobs filters: Status, Matching (Auto/Manual), Date
- Manual override buttons: Mark Matched, Mark Rejected, Mark Applied
- Auto/Manual matching source tracking with badges
- Scheduler runs at 6am Colombian time

---

## Workflow: Auto Scrape + Match, Manual Apply

```
Scheduler (daily 6am) → Scraper (Last 7 Days jobs) → NEW jobs
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
2. **Review**: Check MATCHED jobs from overnight scraping
3. **Override**: Mark false positives as Rejected, or promote Rejected jobs to Matched
4. **Apply**: Click job URL, apply manually on the job site
5. **Track**: Click "Mark Applied" to track which jobs you've applied to

---

## Implementation Status

### ✅ Complete
- [x] FastAPI backend with async SQLAlchemy
- [x] Working Nomads scraper (Last 7 Days filter)
- [x] Claude API integration for matching (Sonnet model)
- [x] Simplified UserProfile (CV + Custom Instructions only)
- [x] Real-time Vue.js Jobs page with filters
- [x] APScheduler for daily scheduling (6am Colombian time)
- [x] Production deployment on Synology NAS
- [x] Simplified status workflow (NEW/MATCHED/REJECTED)
- [x] Manual override buttons (Match/Reject/Applied)
- [x] Auto/Manual matching source tracking
- [x] Date-based filtering (7/15/30 days)
- [x] Runs page with infinite scroll

### ❌ Removed (By Design)
- ~~Dashboard page~~ - Jobs is the landing page
- ~~Statistics page~~ - Simplified to just Jobs view
- ~~Profile basic info fields~~ - All info goes in Custom Instructions
- ~~PDF storage in database~~ - Not needed
- ~~Runs page filters~~ - Shows all runs
- ~~Automated Applier~~ - Removed due to ATS compatibility

---

## Key Files

- `app/ai_models.py` - AI model constants (CLAUDE_SONNET)
- `app/models.py` - Job model with matching_source, simplified UserProfile
- `app/matcher/matcher.py` - Job matching logic
- `app/scraper/working_nomads.py` - Scraper with Last 7 Days filter
- `app/routers/jobs.py` - Jobs API with filtering and manual override
- `app/routers/profile.py` - Simplified profile endpoints
- `app/services/scheduler_service.py` - Daily scheduler at 6am
- `frontend/src/views/Jobs.vue` - Main job review page
- `frontend/src/views/ProfileView.vue` - Simplified profile page
- `frontend/src/views/Runs.vue` - Runs page (no filters)

---

## Architecture

### AI Models
- **Matching**: Claude Sonnet 4.5
- **Profile Generation**: Claude Sonnet 4.5

### Database
- PostgreSQL with async SQLAlchemy
- Job statuses: NEW → MATCHED/REJECTED
- Matching source: auto (AI) / manual (user override)
- UserProfile: cv_filename, cv_text, custom_instructions, skills, preferences, ai_generated_summary

### Deployment
- Docker Compose on Synology NAS
- Traefik reverse proxy
- PostgreSQL in container

---

**Last Updated:** 2025-12-07 by Claude Code

**Status:** Production ready - minimal UI, auto scrape/match at 6am, manual review and apply

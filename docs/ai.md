# Zapply - AI Context

## Current Phase
**Phase 7 Complete: Applier Removed, Manual Apply Workflow**

After extensive experimentation, the automated Applier was removed. The system now focuses on what works well: automated scraping and AI-powered matching. Users manually apply to matched jobs.

**Current Branch:** `feature/applier` (ready for merge to main)

## Last Session - 2025-12-03 (Applier Removal & Cleanup)

### What Was Done

**Decision: Remove Applier Entirely**

After multiple sessions attempting to make automated form filling work with modern React-based ATS systems (Greenhouse, Lever, etc.), we concluded that:

1. React forms maintain internal state that doesn't sync with DOM manipulation
2. Google Places autocomplete requires actual dropdown selection
3. Each ATS has unique quirks making a generic solution impractical
4. The complexity and brittleness outweighed the benefits for MVP

**Cleanup Completed:**

1. **Removed Applier Module**
   - Deleted `app/applier/__init__.py`
   - Deleted `app/applier/applier.py` (2050 lines of Playwright + Claude code)
   - Deleted `app/services/applier_service.py` (249 lines)
   - Deleted `app/routers/applier.py` (233 lines)
   - Deleted `docs/applier-instructions.md`

2. **Simplified Job Statuses**
   - Removed APPLIED, FAILED, REPORTED from `JobStatus` enum
   - Now only: `NEW`, `MATCHED`, `REJECTED`
   - Updated `app/models.py`, `app/schemas.py`, `app/routers/stats.py`
   - Updated `app/reporter/reporter.py` to only track simplified statuses

3. **Frontend Cleanup**
   - Removed "Apply" buttons from Jobs.vue
   - Removed applied/failed styling
   - Removed "expired" from status filter dropdown
   - Updated Stats.vue for simplified status display

4. **Code Cleanup**
   - Removed unused `CLAUDE_OPUS` model constant from `app/ai_models.py`

### Commits in This Branch
- `09fd3a2` - Remove applier and simplify job statuses to new/matched/rejected
- Previous commits: Applier implementation attempts (now reverted)

---

## New Workflow: Auto Scrape + Match, Manual Apply

### How Zapply Works Now

```
Scheduler (hourly) → Scraper → NEW jobs
                         ↓
                     Matcher → MATCHED / REJECTED
                         ↓
                   Dashboard → User reviews MATCHED jobs
                         ↓
                   User manually applies on job sites
```

### User Daily Workflow

1. **Morning**: Open Zapply dashboard
2. **Review**: Check MATCHED jobs from overnight scraping
3. **Apply**: Click job URL, apply manually on the job site
4. **Track**: (Optional) Mark jobs in some way if needed

### Why This Works

- Scraping and matching are automated and work reliably
- AI matching with Claude Sonnet is accurate and cost-effective
- Manual application avoids ATS compatibility issues
- User maintains control over application quality
- Simple, reliable, maintainable

---

## Implementation Status

### ✅ Complete
- [x] FastAPI backend with async SQLAlchemy
- [x] Working Nomads scraper with Playwright
- [x] Claude API integration for matching (Sonnet model)
- [x] UserProfile management with AI generation
- [x] Real-time Vue.js dashboard
- [x] APScheduler for hourly/daily scheduling
- [x] Production deployment on Synology NAS
- [x] Simplified status workflow (NEW/MATCHED/REJECTED)

### ❌ Removed (By Design)
- [x] ~~Automated Applier~~ - Removed due to ATS compatibility issues
- [x] ~~APPLIED/FAILED/REPORTED statuses~~ - No longer needed

### 📋 Next Steps: Polish for Daily Use

**Tomorrow's Focus:**
1. Review scraping reliability - ensure all jobs are captured
2. Review matching quality - fine-tune prompts if needed
3. Test scheduler - verify hourly scrape + match runs smoothly
4. UI polish - make daily review workflow smooth
5. Consider adding "applied" checkbox or note field for manual tracking

---

## Key Files

- `app/ai_models.py` - AI model constants (CLAUDE_SONNET for matching)
- `app/matcher/matcher.py` - Job matching logic
- `app/scraper/` - Working Nomads scraper
- `app/routers/` - API endpoints (jobs, profile, stats, runs)
- `frontend/src/views/Jobs.vue` - Main job review dashboard

---

## Architecture Notes

### AI Models
- **Matching**: Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`)
- **Profile Generation**: Claude Sonnet 4.5

### Database
- PostgreSQL with async SQLAlchemy
- Job statuses: NEW → MATCHED/REJECTED
- UserProfile with CV storage and AI-generated summary

### Deployment
- Docker Compose on Synology NAS
- Traefik reverse proxy
- PostgreSQL in container

---

**Last Updated:** 2025-12-03 by Claude Code

**Status:** Ready for daily use - auto scrape/match, manual apply workflow

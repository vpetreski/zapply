# Zapply - AI Context

## Current Phase
**Phase 7: Applier Implementation** 🤖

System fully operational. Next priority is implementing the Applier - the most critical missing piece that actually submits job applications.

**Current Branch:** `main`

## Last Session - 2025-11-29 (New Mac Setup & Code Cleanup)

### Accomplished This Session

**1. New Mac Environment Setup** 💻 → ✅

Set up development environment on new Mac:
- Created `.env` file with all required secrets (copied from NAS production)
- Configured Claude Code global permissions (`~/.claude/settings.json`)

**2. Environment Variable Cleanup** 🧹 → ✅

#### Removed Unused Environment Variables
- `SCRAPER_JOB_LIMIT` - was dead code, actually reads from DB via Admin UI
- `MATCHING_COMMIT_INTERVAL` - defined but never used
- `MATCHING_LOG_INTERVAL` - rarely changed, kept in code with default
- Legacy user profile vars (`user_name`, `user_email`, etc.) - managed via `/profile` UI

#### Cleaned Up Files
- `.env` - minimal, only required vars
- `.env.example` - updated template
- `.env.production.example` - updated template
- `app/config.py` - removed dead code

**3. AI Model Refactoring** 🤖 → ✅

#### Created `app/ai_models.py`
Centralized AI model constants per use case:
```python
CLAUDE_SONNET = "claude-sonnet-4-5-20250929"  # $3/$15 per MTok
CLAUDE_OPUS = "claude-opus-4-5-20251101"      # $5/$25 per MTok

# Per-feature assignments
MATCHING_MODEL = CLAUDE_SONNET           # Job matching
PROFILE_GENERATION_MODEL = CLAUDE_SONNET # CV profile generation
APPLIER_MODEL = CLAUDE_OPUS              # Job applications (future)
```

#### Rationale
- **Sonnet** for Matcher & Profile: Fast, cost-effective, good for structured analysis
- **Opus** for Applier: Maximum intelligence for navigating arbitrary ATS systems

#### Files Modified
- Created `app/ai_models.py` - centralized model constants
- `app/services/matching_service.py` - uses `MATCHING_MODEL`
- `app/routers/profile.py` - uses `PROFILE_GENERATION_MODEL`
- `app/config.py` - removed `anthropic_model`
- `app/main.py` - removed model from startup log
- Removed `ANTHROPIC_MODEL` from all `.env` files

---

## Previous Sessions Summary

### Session - 2025-11-26 (Critical Login Fix & Deployment Automation)
- Fixed production login (bcrypt hash quote handling)
- Automated deployment file sync via GitHub Actions
- Fixed database migration conflict
- Confirmed matching quality ("fucking brilliant")

### Session - 2025-11-26 (Performance Optimization)
- Scraper optimization: 80-97% faster on subsequent runs
- Fixed jobs display issue (770 jobs visible)
- All Claude Code Review issues resolved
- Matching quality verified

---

## Implementation Status

### ✅ Phase 1-6: Complete
- [x] Backend and frontend
- [x] Working Nomads scraper with Playwright (optimized)
- [x] Claude API integration for matching
- [x] UserProfile management with AI generation
- [x] Real-time dashboard and scheduler
- [x] Production deployment to NAS (24/7)
- [x] Environment cleanup and AI model refactoring

### 🎯 Phase 7: Applier Implementation (NEXT PRIORITY)
The most critical missing piece - actually submitting job applications!

**Requirements:**
- [ ] Playwright + Claude Opus for intelligent form filling
- [ ] Navigate arbitrary ATS systems (Greenhouse, Lever, Workday, etc.)
- [ ] Fill forms intelligently based on user profile
- [ ] Handle custom questions with AI
- [ ] Upload resume/CV
- [ ] Mark jobs as APPLIED/FAILED with details
- [ ] Screenshot on failure for debugging
- [ ] Test with real applications (supervised)

**Architecture:**
```
MATCHED Job → Applier →
  1. Open job URL
  2. Find "Apply" button
  3. Navigate application flow
  4. Fill forms (AI-powered)
  5. Answer custom questions (AI)
  6. Submit application
  7. Update job status → APPLIED/FAILED
```

**Model:** Uses `APPLIER_MODEL` (Claude Opus 4.5) for maximum intelligence

### 📋 Phase 8: External Access (Low Priority)
- [ ] Configure zapply.dev domain
- [ ] Set up nginx reverse proxy with SSL
- [ ] Router port forwarding

---

## Decisions Log

### AI Model Strategy (2025-11-29)
- **Hardcoded models per feature** instead of env var
- **Sonnet** for Matcher/Profile (cost-effective, fast)
- **Opus** for Applier (maximum intelligence needed)
- Models defined in `app/ai_models.py` for easy updates

### Technology Stack
- Python 3.12, FastAPI, uv
- Vue.js 3 frontend with dark theme
- PostgreSQL, Playwright
- Claude API (Sonnet for matching, Opus for applying)
- Docker on Synology NAS

---

## Access URLs

- **NAS Frontend**: http://192.168.0.188:3000/
- **NAS API**: http://192.168.0.188:8000/docs
- **Local Dev**: http://localhost:3000/, http://localhost:8000/docs

---

## Key Files

- `app/ai_models.py` - AI model constants per feature
- `app/services/matching_service.py` - Job matching logic
- `app/routers/profile.py` - Profile generation
- `app/applier/applier.py` - Applier (to be implemented)
- `docs/ai.md` - This file (AI context)
- `CLAUDE.md` - Claude Code instructions

---

**Last Updated:** 2025-11-29 by Claude Code

**Next Session Priority:**
1. **Implement Applier** - The most critical missing feature
2. Design the application flow architecture
3. Start with a single ATS (e.g., Greenhouse) as MVP
4. Test with real applications (supervised)

**GitHub:** https://github.com/vpetreski/zapply (private)

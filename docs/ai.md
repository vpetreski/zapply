# Zapply - AI Context

## Current Phase
**Phase 4: Production Deployment to Synology NAS**

Setting up automated CI/CD deployment pipeline with GitHub Actions. User is testing matching quality while deployment infrastructure is being prepared.

## Last Session - 2025-11-25 (Late Evening - Deployment Planning)

### NAS Deployment Plan - DOCUMENTED

**Goal:** Fully automated production deployment to Synology NAS with GitHub Actions CI/CD

#### Infrastructure Setup
**NAS Details:**
- IP: 192.168.0.188 (local network)
- QuickConnect: https://192-168-0-188.vpetreski.direct.quickconnect.to
- SSH access: `nas` command (passwordless, key-based auth)
- Docker + docker-compose installed ✅

**Deployment Architecture:**
```
GitHub (main branch)
    ↓ (on merge)
GitHub Actions CI/CD
    ↓ (builds)
GitHub Container Registry
    ↓ (deploys)
Synology NAS (192.168.0.188)
    ↓ (serves)
User (QuickConnect URL)
```

#### Directory Structure on NAS
```
/volume1/docker/zapply/
├── docker-compose.prod.yml    # Production compose file
├── .env.production             # All secrets (auto-created from repo .env)
├── data/
│   ├── postgres/              # PostgreSQL persistent data
│   ├── logs/                  # Application logs
│   └── uploads/               # CV/profile files
└── scripts/
    └── deploy.sh              # Automated deployment script
```

#### Port Mapping & Access
- **Frontend**: Port 3000 → QuickConnect:3000
- **Backend API**: Port 8000 → QuickConnect:8000/docs (Swagger)
- **PostgreSQL**: Port 5432 (internal Docker network only)
- **Logs**: SSH + `docker logs` or volume mount

#### Automated CI/CD Pipeline
**Trigger:** Merge to `main` branch

**GitHub Actions Workflow Steps:**
1. Checkout code
2. Build optimized Docker images (multi-stage builds)
   - Backend: Python + uv + dependencies
   - Frontend: Node build → Nginx serve
3. Push images to GitHub Container Registry (ghcr.io)
4. SSH to NAS
5. Pull latest images
6. Run `docker-compose up -d` (zero-downtime restart)
7. Health check verification
8. Deployment complete (~2-3 minutes total)

#### What User Needs to Do (One-Time, ~5 mins)
**Step 1: Create GitHub Personal Access Token**
- Go to: https://github.com/settings/tokens
- Click "Generate new token (classic)"
- Select scope: `write:packages`
- Copy token value
- Add to repository secrets as `GHCR_TOKEN`

**Step 2: Add NAS SSH Key to GitHub Secrets**
- Claude will generate SSH key pair (or use existing)
- User copies private key
- Add to repository secrets as `NAS_SSH_KEY`
- Claude adds public key to NAS authorized_keys

**Note:** Claude will guide with step-by-step instructions and screenshots when ready.

#### What Claude Will Automate
1. ✅ Create production Dockerfiles (optimized multi-stage builds)
2. ✅ Create docker-compose.prod.yml with:
   - Health checks
   - Restart policies
   - Volume mounts
   - Network configuration
   - Environment variables
3. ✅ Create GitHub Actions workflow (.github/workflows/deploy.yml)
4. ✅ Create deployment script for NAS (scripts/deploy.sh)
5. ✅ SSH to NAS and create directory structure
6. ✅ Copy .env to NAS as .env.production
7. ✅ Generate/configure SSH keys for deployment
8. ✅ Set up log rotation
9. ✅ Create helper scripts for common operations
10. ✅ Document all access URLs and commands
11. ✅ Optional: Configure Traefik/Nginx reverse proxy for SSL

#### Easy Management Commands (Post-Deployment)
```bash
# View live logs
nas "cd /volume1/docker/zapply && docker-compose logs -f backend"
nas "cd /volume1/docker/zapply && docker-compose logs -f frontend"

# Restart services
nas "cd /volume1/docker/zapply && docker-compose restart"

# Check service status
nas "cd /volume1/docker/zapply && docker-compose ps"

# Access database
nas "cd /volume1/docker/zapply && docker-compose exec postgres psql -U zapply"

# Manual deployment (if needed)
nas "cd /volume1/docker/zapply && ./scripts/deploy.sh"

# View disk usage
nas "cd /volume1/docker/zapply && du -sh data/*"
```

#### Access URLs (Post-Deployment)
- Frontend: https://192-168-0-188.vpetreski.direct.quickconnect.to:3000
- API Docs: https://192-168-0-188.vpetreski.direct.quickconnect.to:8000/docs
- API Base: https://192-168-0-188.vpetreski.direct.quickconnect.to:8000/api

#### Production Considerations
- **Zero-downtime deployments**: docker-compose handles graceful restart
- **Data persistence**: PostgreSQL data survives container restarts
- **Log rotation**: Prevent disk space issues
- **Health checks**: Auto-restart unhealthy containers
- **Resource limits**: CPU/memory limits if needed
- **Backup strategy**: PostgreSQL data volume backups
- **SSL/HTTPS**: Optional Traefik setup for proper certificates

#### Timeline
1. **Now**: Document plan in ai.md ✅
2. **Next**: Create all Docker/deployment files
3. **Then**: Set up NAS infrastructure (SSH, directories, .env)
4. **Then**: Create GitHub Actions workflow
5. **Finally**: Guide user through GitHub secrets setup
6. **Deploy**: Merge to main → automatic deployment!

**Estimated Total Setup Time:** 1-2 hours for full automation

---

## Previous Session - 2025-11-25 (Evening - Critical Bug Fixes)

### Accomplished This Session

**CRITICAL FIXES: Real-Time Logging & Claude API Integration**

#### 1. Fixed Claude API JSON Parsing Error ⚠️ → ✅
**Problem:** All 10 jobs failing with "Error during matching: Expecting value: line 1 column 1 (char 0)"
- ❌ Claude API was returning valid JSON wrapped in markdown code fences (```json ... ```)
- ❌ json.loads() failing when encountering opening ``` characters
- ❌ All jobs getting 0.0 score with error reasoning

**Solution:**
- ✅ Added markdown fence stripping logic in `match_job_with_claude()`
- ✅ Strips opening ```json or ``` line
- ✅ Strips closing ``` line
- ✅ Added extensive DEBUG logging to see exact Claude responses
- ✅ Jobs now matching successfully with actual scores (45.0, 15.0, 58.0, 25.0, etc.)

**Code Added (matching_service.py:128-138):**
```python
# Strip markdown code fences if present (```json ... ```)
if response_text.strip().startswith("```"):
    lines = response_text.strip().split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    response_text = "\n".join(lines)
    logger.info(f"DEBUG: Stripped markdown fences")
```

#### 2. Fixed Real-Time UI Logging 📊 → ✅
**Problem:** UI only showing logs at job 1/10 and 10/10, missing all intermediate jobs
- ❌ `matching_commit_interval` was 25, so commits only at start/end with 10 jobs
- ❌ Match results logged to console but NOT to run logs
- ❌ UI felt stuck during matching phase

**Solution:**
- ✅ Changed `matching_commit_interval` from 25 to 1 (commit after every job)
- ✅ Changed `matching_log_interval` from 10 to 1 (log every job)
- ✅ Added match results to run logs (not just console)
- ✅ Commit after EVERY job for real-time UI updates

**Code Changes:**
- `config.py:42-43` - Set both intervals to 1
- `matching_service.py:282-293` - Add result logs and commit every job

#### 3. Migrated to Standard Python Logging 📝 → ✅
**Problem:** Using custom `log_to_console()` instead of standard logger
- ❌ User explicitly requested: "not to use log_to_console magic but normal logger everywhere"

**Solution:**
- ✅ Replaced all `log_to_console()` calls with `logger.info()` in matching_service.py
- ✅ Removed `from app.utils import log_to_console` import
- ✅ Added `import logging` and `logger = logging.getLogger(__name__)`
- ✅ Consistent logging pattern across all services

#### 4. Fixed Scraper Real-Time Logging 🔍 → ✅
**Problem:** Scraper only logging every 10th job during scraping phase
- ❌ Line 342: `if progress_callback and i % 10 == 0:`
- ❌ UI showing "Scraping job 1/20" then "Scraping job 10/20" then "Scraping job 20/20"

**Solution:**
- ✅ Changed to `if progress_callback:` (removed modulo check)
- ✅ Now logs EVERY job: "Scraping job 1/20", "Scraping job 2/20", etc.
- ✅ Real-time progress visibility for scraping phase

**Code Change (working_nomads.py:342-344):**
```python
# Log every job for real-time UI updates
if progress_callback:
    await progress_callback(f"Scraping job {i}/{len(slugs)}...", "info")
```

### Testing Results
**Tested with 10 jobs from Working Nomads:**
- ✅ First 3 jobs failed with old code (error 0.0 scores)
- ✅ Backend auto-reloaded with fix
- ✅ Jobs 4-10 matched successfully with actual scores:
  - Job 4: 45.0/100 (REJECTED)
  - Job 5: 15.0/100 (REJECTED)
  - Job 6: 58.0/100 (REJECTED)
  - Job 7: 25.0/100 (REJECTED)
  - Job 8-10: Various scores
- ✅ UI now shows ALL job progress (1/10, 2/10, 3/10, etc.)
- ✅ Real-time updates work perfectly
- ✅ Match reasoning is detailed and accurate

**User Feedback:** "wow matching is fucking brilliant so far"

### Files Modified
1. **`app/services/matching_service.py`** (Major changes)
   - Replaced log_to_console with standard logger
   - Added markdown fence stripping (lines 128-138)
   - Added DEBUG logging for Claude responses
   - Added match result logging to run logs
   - Commit after every job instead of batches

2. **`app/config.py`**
   - `matching_log_interval: 1` (was 10)
   - `matching_commit_interval: 1` (was 25)

3. **`app/scraper/working_nomads.py`**
   - Line 342: Removed `i % 10 == 0` check
   - Now logs every job during scraping

### Current Status
- ✅ **Claude API integration working perfectly** - Handles markdown-wrapped JSON
- ✅ **Real-time UI updates working** - Every job logged and committed
- ✅ **Standard logging everywhere** - No more custom utilities
- ✅ **Scraping progress visible** - Every job shows in UI
- ✅ **Matching is brilliant** - Accurate scores and detailed reasoning
- 🎯 **Ready for full testing** - User testing with 20 jobs

### Next Steps
- [ ] User will test with 20 jobs to validate all fixes
- [ ] Monitor for any edge cases or issues
- [ ] Update PR #3 with these critical fixes
- [ ] Continue with profile review and pipeline testing

---

## Previous Session - 2025-11-25 (Full Day)

### Accomplished

**MAJOR MILESTONE: Complete Testing & Polish PR (#3)**

#### 1. Fixed All UI Issues (Multiple Iterations)
- ✅ **Slider Thumb Visibility** - FINALLY FIXED after 5+ attempts!
  - Increased slider height from 6px to 20px
  - Added 3px white border for visibility
  - Removed problematic scale transform
  - Used !important flags and z-index: 999
  - Added overflow: visible to parent container
- ✅ **Live Indicator** - Changed from blue to green (#10b981)
  - No longer looks like a clickable link
  - Clear "active/live" status indication
- ✅ **Dropdown Arrow Padding** - Custom SVG arrow solution
  - Removed native select arrow with `appearance: none`
  - Added custom SVG arrow positioned 1rem from right
  - 3rem right padding for proper text spacing
- ✅ **Clickable Logo** - Made Zapply logo navigate to dashboard

#### 2. Implemented Full Scheduler System with APScheduler
- ✅ Created `scheduler_service.py` with AsyncIOScheduler
- ✅ Support for manual, daily (9pm Colombian time), and hourly runs
- ✅ Daily runs at 9pm America/Bogota time (proper timezone handling)
- ✅ Hourly runs at start of each hour
- ✅ Scheduler starts/stops with application lifecycle
- ✅ Reconfigures on setting changes via admin endpoint
- ✅ Settings persist in `data/admin_settings.json`
- ✅ Added `trigger_type` field to Run model (manual/scheduled_daily/scheduled_hourly)
- ✅ Created and applied Alembic migration for trigger_type
- ✅ Display trigger type badges in runs list and detail views

#### 3. Built Real-Time Dashboard
- ✅ Stats auto-refresh every 10 seconds
- ✅ Recent Activity auto-refresh every 3 seconds
- ✅ Shows active run OR most recent completed run
- ✅ Displays run status, phase, trigger type
- ✅ Last 5 log entries with live updates
- ✅ Live elapsed time for running jobs
- ✅ Color-coded status badges
- ✅ "📡 Live" indicator (green, not blue)

#### 4. Added Admin Settings Section
- ✅ New Settings section above Database Cleanup
- ✅ Run Frequency dropdown (Manual/Daily/Hourly)
- ✅ Immediately reconfigures scheduler on change
- ✅ Success/error feedback with auto-clear
- ✅ Backend endpoints for frequency settings
- ✅ Renamed Settings → Admin throughout UI and backend
- ✅ Moved database stats under cleanup section
- ✅ Auto-refresh database stats every 5 seconds

#### 5. Documented Database Migrations
- ✅ Comprehensive migration section in README
- ✅ Explained why migrations are manual (not automatic)
- ✅ Added `just db-status` command to check migration state
- ✅ Best practices guide for migrations
- ✅ Troubleshooting guide for common issues
- ✅ Updated Justfile with helpful migration commands

#### 6. Fixed All Claude Bot Review Issues
**Critical Issues:**
- ✅ Removed misleading SQL injection parameterized query attempt
- ✅ Added clear safety comments explaining string formatting

**High Priority Issues:**
- ✅ Fixed database session generator pattern with proper `aclose()`
- ✅ Removed unused `Sequence` import from admin.py

**Medium Priority Issues:**
- ✅ Added migration comments explaining index drop
- ✅ Created shared `settings_manager.py` module (DRY principle)
- ✅ Removed duplicate settings functions from admin.py and scheduler_service.py
- ✅ Updated scheduler to use `ZoneInfo("America/Bogota")` instead of hardcoded UTC-5

#### 7. Created Pull Request #3
- ✅ Comprehensive PR description with test plan
- ✅ 21 commits covering all features and fixes
- ✅ All checklist items addressed
- ✅ Ready for review and merge

### Key Technical Improvements
- **Proper timezone handling** - Using zoneinfo for Colombian time
- **Async generator pattern** - Proper cleanup with aclose()
- **DRY principle** - Shared settings management module
- **Code quality** - Removed unused imports, added clear comments
- **Security** - Clear documentation of safe string formatting
- **Real-time updates** - Polling-based auto-refresh for dashboard

### Files Created
- `app/services/scheduler_service.py` - Full scheduler implementation
- `app/services/settings_manager.py` - Shared settings management
- `frontend/src/views/AdminView.vue` - Renamed from SettingsView
- `alembic/versions/2025_11_25_0949-*.py` - Migration for trigger_type

### Files Modified (Major Changes)
- `app/main.py` - Start/stop scheduler on startup/shutdown
- `app/routers/admin.py` - Frequency settings, use shared settings
- `app/routers/runs.py` - Return trigger_type in all endpoints
- `app/services/scraper_service.py` - Accept trigger_type parameter
- `app/database.py` - Added get_db_session() for background tasks
- `app/models.py` - RunTriggerType enum and trigger_type field
- `frontend/src/views/Dashboard.vue` - Real-time updates, Recent Activity
- `frontend/src/views/Jobs.vue` - Slider bug fixes (FINALLY!)
- `frontend/src/views/Runs.vue` - Display trigger type badges
- `frontend/src/App.vue` - Clickable logo
- `README.md` - Database migration documentation
- `Justfile` - Migration status commands

### Current Status
- ✅ **PR #3 created and pushed** - https://github.com/vpetreski/zapply/pull/3
- ✅ **All UI issues fixed** - Slider, Live indicator, dropdown padding
- ✅ **Scheduler fully implemented** - Manual/Daily/Hourly runs
- ✅ **Real-time dashboard working** - Live updates without refresh
- ✅ **Trigger type tracking** - All runs show how they were triggered
- ✅ **Migration documentation complete** - Users know when/how to migrate
- ✅ **All Claude Bot issues fixed** - Code quality improved
- 🟡 **PR awaiting review** - Ready to merge

### Next Steps (User's Plan)

#### 1. Review and Polish User Profile Feature 👤
**Goal:** Ensure profile management is production-ready

**Areas to Review:**
- Profile display (name, email, location, rate, skills)
- CV upload functionality
- AI profile generation quality
- Update and delete operations
- Error handling and validation
- UI/UX polish
- Rate limiting effectiveness

**Test Cases:**
- Upload various CV formats (PDF)
- Generate profile with different custom instructions
- Update existing profile
- Delete profile (verify confirmation works)
- Test with large CVs
- Test AI generation with edge cases
- Verify profile is used correctly in matching

**Potential Improvements:**
- Better error messages
- Loading states during AI generation
- Preview of generated profile before saving
- Validation of required fields
- Better styling/layout
- Help text for custom instructions

#### 2. Test Complete Pipeline End-to-End 🧪
**Goal:** Verify entire workflow with real data

**Test Sequence:**
1. **Clean Database** (via Admin page)
   - Delete all test jobs and runs
   - Keep user profile

2. **Verify Profile** (via Profile page)
   - Check profile is complete and correct
   - Update if needed with new instructions

3. **Trigger Manual Scraping** (via Runs page)
   - Click "Start New Run"
   - Watch real-time progress in dashboard
   - Verify scraping phase completes

4. **Monitor Matching** (via Dashboard/Runs)
   - Watch matching phase in real-time
   - Check match scores and reasoning
   - Verify MATCHED vs REJECTED logic

5. **Review Results** (via Jobs page)
   - Filter by status (matched/rejected)
   - Review match scores
   - Check reasoning quality
   - Verify no false positives/negatives

6. **Test Filters** (via Jobs page)
   - Filter by status
   - Filter by min score
   - Sort by date/score
   - Search functionality

7. **Verify Run Tracking** (via Runs page)
   - Check run shows "Manual" trigger type
   - Review complete logs
   - Check statistics accuracy
   - Verify timestamps

8. **Test Scheduler** (via Admin page)
   - Change to Hourly frequency
   - Wait for next hour boundary
   - Verify automatic run triggers
   - Check run shows "Hourly" trigger type
   - Change to Daily frequency
   - Verify configuration (9pm Colombian time)
   - Change back to Manual

**Success Criteria:**
- [ ] Scraper fetches 50+ jobs from Working Nomads
- [ ] Matcher processes all jobs without errors
- [ ] Match scores are reasonable (not all 0 or 100)
- [ ] Reasoning is detailed and makes sense
- [ ] MATCHED jobs meet criteria (remote, contractor-friendly)
- [ ] REJECTED jobs properly filtered out
- [ ] Real-time updates work smoothly
- [ ] Trigger types display correctly
- [ ] Scheduler runs automatically at configured times
- [ ] No crashes or unhandled errors

**Areas to Watch For:**
- API rate limits (Claude API calls)
- Memory usage during matching
- Database performance with many jobs
- Playwright stability
- Network error handling
- Session timeout issues
- UI responsiveness with large datasets

### After Testing Complete
- Fix any bugs found during testing
- Merge PR #3
- Update ai.md with test results
- Plan next phase: Applier implementation

## Previous Sessions

### Session - 2025-11-25 (Morning - Part 1)
**Fixed All Claude Bot Review Issues:**
- ✅ Fixed Python 3.12+ datetime.utcnow() deprecation
- ✅ Added API key validation
- ✅ Added response validation
- ✅ Moved configuration to config.py
- ✅ Added database index on match_score
- ✅ Added retry logic with tenacity
- ✅ Added rate limiting with slowapi

### Session - 2025-11-24 (Evening)
**Fixed Critical Matcher Bug & Built Profile System:**
- ✅ Built complete UserProfile management UI
- ✅ AI-powered profile generation with Claude
- ✅ Removed hardcoded CV from repository
- ✅ Created cleanup script for test data

**Working Nomads Scraper - COMPLETE:**
- ✅ Playwright-based scraper
- ✅ Login with premium account
- ✅ Apply filters (Development + Anywhere,Colombia)
- ✅ Load all jobs with "Show more" pagination
- ✅ Save to database with duplicate detection

**AI Matcher - COMPLETE:**
- ✅ Claude API integration
- ✅ Score-based matching (0-100 scale)
- ✅ Detailed reasoning with strengths/concerns
- ✅ MATCHED (≥60) vs REJECTED (<60) status

### Session - 2025-11-24 (Morning)
**Initial Setup:**
- ✅ Complete FastAPI application structure
- ✅ Database models with status tracking
- ✅ Vue.js frontend with dark theme
- ✅ Docker configuration for all services
- ✅ Comprehensive Justfile with 30+ commands
- ✅ GitHub repository setup

## Decisions Log

### Technology Stack
- **Python 3.12**: Latest stable version
- **uv**: Ultra-fast package manager
- **just**: Command runner for automation
- **APScheduler**: For scheduled runs
- **zoneinfo**: Proper timezone handling

### Architecture Decisions
- **Manual migrations**: Control and safety over convenience
- **Shared settings module**: DRY principle for settings management
- **Polling for real-time**: Simple and effective for MVP
- **JSON for settings**: Simple persistence for single setting
- **Global scheduler**: Acceptable for monolithic MVP

### Security Decisions
- **String formatting for DDL**: Safe with validated hardcoded values
- **Settings file permissions**: Should be restricted in production
- **Rate limiting**: Protect API endpoints from abuse

## Implementation Status

### ✅ Phase 1 & 2: Foundation & Core Features (COMPLETE)
- [x] Project structure and organization
- [x] Backend (FastAPI, models, schemas, endpoints)
- [x] Frontend UI (Vue.js, dashboard, views)
- [x] Database (PostgreSQL, Alembic, migrations)
- [x] Docker configuration
- [x] Development automation (Justfile)
- [x] Working Nomads scraper with Playwright
- [x] Claude API integration for matching
- [x] UserProfile management with AI generation
- [x] Service layer (scraper_service, matching_service)
- [x] Run tracking with logs and statistics

### ✅ Phase 3: Testing & Polish (COMPLETE - PR #3)
- [x] Real-time dashboard with Recent Activity
- [x] Automated scheduler (Manual/Daily/Hourly)
- [x] Trigger type tracking for all runs
- [x] Admin settings section with frequency control
- [x] Database migration documentation
- [x] All UI fixes (slider, Live indicator, dropdown)
- [x] All Claude Bot review issues fixed
- [x] Pull request created and pushed

### 🎯 Phase 4: Profile Review & Pipeline Testing (NEXT)
- [ ] Review and polish User Profile feature
- [ ] Test complete pipeline end-to-end
- [ ] Verify matching quality with real data
- [ ] Test scheduler functionality
- [ ] Fix any bugs found
- [ ] Merge PR #3

### 📋 Phase 5: Applier Implementation (UPCOMING)
- [ ] Playwright + Claude applier implementation
- [ ] Navigate arbitrary ATS systems
- [ ] Fill forms intelligently
- [ ] Handle custom questions
- [ ] Mark as APPLIED/FAILED
- [ ] Test with real job applications

### 🚀 Phase 6: Production Deployment
- [ ] Deploy to Synology NAS
- [ ] 24/7 automated operation
- [ ] Reporter component (notifications)
- [ ] Monitoring and logging

## Target User Profile

**Vanja Petreski:**
- Principal Software Engineer with 20 years experience
- Location: Colombia (NO US work authorization)
- Work Style: 100% remote contractor via Petreski LLC
- Rate: $10,000 USD/month
- Core Skills: Java, Kotlin, Spring Boot, Backend, APIs, Architecture
- Extended: Python, FastAPI, Go, Node, TypeScript, mobile, frontend

**Job Criteria:**
- ✅ MUST HAVE: True remote, US companies + international contractors OR Latam hiring
- ❌ MUST REJECT: US work authorization required, Physical presence, Hybrid positions

## Key Success Criteria

1. ✅ Can fetch jobs from Working Nomads (scraper working)
2. ✅ Can accurately filter jobs (matcher working)
3. 🎯 Can test complete pipeline end-to-end (NEXT)
4. [ ] Can submit at least 1 real application automatically
5. [ ] System runs unattended on Synology NAS

## Blockers
None! PR #3 ready for review. Next: Profile review and pipeline testing.

## Notes

### Important Files & URLs
- **GitHub PR #3**: https://github.com/vpetreski/zapply/pull/3
- **Profile Page**: http://localhost:5173/profile
- **Admin Page**: http://localhost:5173/admin (was /settings)
- **Docs**: `docs/ai.md`, `CLAUDE.md`, `.cursorrules`
- **Automation**: `Justfile` - run `just` to see all commands

### Development Workflow
1. Open Claude Code → loads this `docs/ai.md`
2. Continue from "Next Steps" section
3. User says "save" → update this file and commit
4. Session complete

### Cost Considerations
- Matcher: Be efficient with Claude API calls
- Applier: Use Claude aggressively (worth the cost)
- Monitor API usage during testing

---

**Last Updated:** 2025-11-25 (Full Day Session) by Claude Code
**Next Session:**
1. Review and polish User Profile feature in detail
2. Test complete pipeline end-to-end with real data
3. Fix any issues found
4. Merge PR #3

**GitHub:** https://github.com/vpetreski/zapply (private)
**Current PR:** https://github.com/vpetreski/zapply/pull/3

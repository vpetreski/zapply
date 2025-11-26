# Zapply - AI Context

## Current Phase
**Phase 6: Production Ready - Focus on MVP** 🚀

System fully operational with optimized scraper and verified matching quality. Ready to use as-is for job applications.

**Current Branch:** `feature/nas-external-access` (about to merge)

## Last Session - 2025-11-26 (Critical Login Fix & Deployment Automation)

### Accomplished This Session

**1. Fixed Critical Production Login Issue** 🔐 → ✅

#### Problem Discovery
Login stopped working on NAS production after deployment at 11:48 AM. User reported "Login failed. Please try again."

#### Root Cause Analysis
1. **.env.production** uses single quotes around ADMIN_PASSWORD to prevent bash $ expansion:
   ```bash
   ADMIN_PASSWORD='$2b$12$w2zQdrjCI6xfPWjDFQ6hpeCFGS2t3Yf35RYOqsfQ0.tmrJ1ONqmAG'
   ```
2. **deploy.sh** was passing those quotes to Docker environment variable
3. **Python received hash WITH quotes**: `'$2b$12$...'` instead of `$2b$12$...`
4. **bcrypt fails** with "Invalid salt" when hash starts with single quote

#### Solution Implemented
**Modified scripts/deploy.sh** to strip quotes after sourcing .env.production:
```bash
# Strip quotes from ADMIN_PASSWORD if present (bcrypt hashes fail with quotes)
ADMIN_PASSWORD=$(echo "$ADMIN_PASSWORD" | sed "s/^'\\(.*\\)'\$/\\1/")
```

This ensures:
- Bash protects `$` from expansion (single quotes in file) ✅
- Python receives clean hash without quotes ✅

**Files Modified:**
- `scripts/deploy.sh` - Added quote-stripping logic (line 31)
- `.env.production.example` - Updated comment to clarify single quotes are REQUIRED

---

**2. Automated Deployment File Sync** 🤖 → ✅

#### Problem
Scripts on NAS (`/volume1/docker/zapply/scripts/`) were **manually managed**, not synced from git. This caused the login issue because the old deploy.sh didn't have the fix.

#### Solution
Enhanced `.github/workflows/deploy.yml` to automatically sync all deployment files:
```yaml
# Sync deployment files from git (preserving .env.production)
echo "📋 Syncing deployment files from git..."
cp $GITHUB_WORKSPACE/docker-compose.prod.yml /volume1/docker/zapply/
cp -r $GITHUB_WORKSPACE/scripts/* /volume1/docker/zapply/scripts/
chmod +x scripts/*.sh
```

**Result:** All scripts now auto-update on every deployment. .env.production remains manually managed (intentionally).

---

**3. Fixed Database Migration Conflict** 🗄️ → ✅

#### Problem
After fixing the password and restarting containers, login still failed. Backend was crashing on startup:
```
sqlalchemy.exc.ProgrammingError: relation "ix_jobs_source_id" already exists
ERROR: Application startup failed. Exiting.
```

#### Root Cause
Migration `2025_11_26_1133-21383ec8a724_fix_index_on_job_source_id.py` tried to create index that already existed from earlier manual database fix. The alembic_version table wasn't updated to reflect the manual change.

#### Solution
Manually updated alembic_version table to mark migration as applied:
```sql
UPDATE alembic_version SET version_num = '21383ec8a724';
```

**Result:** Backend now starts successfully, all services running properly.

---

**4. Matching Quality Confirmation** 🎯 → ✅

**User Feedback:** "matching is fucking brilliant so far"

**Decision:** NO matching optimization needed. System works exactly as intended.

---

## Previous Session - 2025-11-26 (Performance Optimization & Matching Verification)

### Accomplished This Session

**1. Scraper Performance Optimization** ⚡ → ✅

#### Implemented Deduplication
**Problem:** Scraper was scraping ALL jobs every run (6-10 minutes), even when most already existed
**Solution:** Pre-fetch existing slugs, skip scraping details for known jobs
**Result:** 80-97% faster on subsequent runs (40-60 seconds vs 6-10 minutes)

**Implementation:**
- Pre-fetch existing job slugs from database into memory (O(1) lookup)
- Pass `existing_slugs` set to scraper
- Skip `_scrape_job_details()` for existing jobs
- Only scrape NEW jobs
- Real-time logging shows SKIP vs SCRAPING actions

**Performance Gains:**
- First run (empty DB): No change (baseline)
- After 1 hour (~180 existing + ~20 new): **90% faster** 🚀
- After 1 day (~195 existing + ~5 new): **97% faster** 🚀

**Files Modified:**
- `app/services/scraper_service.py` - Pre-fetch existing slugs
- `app/scraper/working_nomads.py` - Skip logic, enhanced logging

---

**2. Fixed Jobs Display Issue** 📋 → ✅

#### Problem: 770 Jobs in Database But Not Showing in UI
**Investigation:**
- Database query confirmed: **770 jobs successfully stored** ✅
- Frontend showing: **0 jobs** ❌
- Backend logs: `GET /api/jobs HTTP/1.1" 307 Temporary Redirect`
- **Root cause:** FastAPI redirecting `/api/jobs` to `/api/jobs/`
- Frontend not following 307 redirect → empty response

**Solution:**
1. Added `redirect_slashes=False` to FastAPI app (main.py:87)
2. Added dual route decorators: `@router.get("")` + `@router.get("/")`
3. Handles both `/api/jobs` and `/api/jobs/` without redirecting

**Result:** ✅ All 770 jobs now visible in UI!

---

**3. Fixed All Claude Code Review Issues** 🔍 → ✅

#### From PR #6 Review Comments:

**Critical Issues Fixed:**
1. **Progress callback spam** - Removed callbacks for skipped jobs
   - Was: 180 skipped × 2 = 360 DB commits
   - Now: ~20 DB commits (only for actual scraping)

2. **Database index strategy** - Created composite index `(source, source_id)`
   - Optimizes query: `SELECT source_id FROM jobs WHERE source = 'working_nomads'`
   - Migration: `alembic/versions/2025_11_26_1133-21383ec8a724_fix_index_on_job_source_id.py`

3. **Missing imports** - Added `from app.config import settings`
   - Fixed runtime error in debug mode

4. **N+1 query pattern** - Use in-memory set lookup instead of DB queries
   - Eliminated ~200 redundant queries per scrape
   - Changed from O(n) to O(1) performance

**PR #6 Status:** ✅ Merged to main (commit 31d6741)

---

**4. Matching Quality Verification** 🎯 → ✅

#### Analysis Results (770 Jobs Matched):
**User Feedback:** "matching is fucking brilliant so far" ✅

**Quality Assessment:**
- ✅ Scores are reasonable and nuanced (not all 0 or 100)
- ✅ Reasoning is detailed and makes sense
- ✅ 60% threshold works perfectly:
  - **MATCHED jobs:** True remote, contractor-friendly, good tech fit
  - **REJECTED jobs:** US auth required, hybrid, poor tech match, or location restrictions
- ✅ Algorithm properly handles:
  - Expanding to adjacent technologies (Go, TypeScript, Node)
  - Filtering out non-remote or US-only positions
  - Evaluating based on contractor setup compatibility

**Decision:** 🎯 NO MATCHING OPTIMIZATION NEEDED
- Current algorithm works exactly as intended
- Focus on shipping MVP and using the system
- Matching quality will be validated through real-world usage

---

### Current Status

**System State:**
- ✅ **Scraper:** Optimized, 80-97% faster on subsequent runs
- ✅ **Matcher:** Working brilliantly, accurate scores and reasoning
- ✅ **Jobs Display:** All 770 jobs visible, fast API responses
- ✅ **Database:** Indexed properly, N+1 queries eliminated
- ✅ **Code Quality:** All Claude Code Review issues resolved
- ✅ **Production:** Running on NAS, 24/7 automated operation

**Access URLs:**
- Frontend: http://192.168.0.188:3000/
- API Docs: http://192.168.0.188:8000/docs
- Local Dev: http://localhost:3000/, http://localhost:8000/docs
- Quick Connect (internal only): http://192-168-0-188.vpetreski.direct.quickconnect.to:3000/

---

### Next Steps - FUTURE WORK (Not Urgent)

**Phase 7: External Access via zapply.dev** 🌐
**Status:** Documented, Low Priority - Focus on MVP usage first

#### Goal
Enable external access to Zapply via https://zapply.dev with proper SSL and security

#### Implementation Plan (When Ready)

**1. Domain & DNS Setup**
- Point `zapply.dev` A record to NAS public IP
- Set up DDNS if IP is dynamic (Synology has built-in DDNS)
- DNS propagation: 5-60 minutes

**2. SSL/HTTPS Certificates**
- Use Let's Encrypt via Certbot in nginx container
- Auto-renewal every 90 days
- Free and trusted certificates

**3. Nginx Reverse Proxy**
- Add nginx container to docker-compose
- HTTPS termination (port 443)
- HTTP redirect (80 → 443)
- Reverse proxy to frontend:80 and backend:8000
- Security headers (HSTS, CSP, etc.)
- Rate limiting

**Architecture:**
```
Internet → Router:443 → NAS:443 (nginx) →
  ├─ zapply.dev/ → frontend:80
  └─ zapply.dev/api, /docs → backend:8000
```

**4. Network Configuration**
- Router port forwarding:
  - Port 80 → NAS 192.168.0.188:80
  - Port 443 → NAS 192.168.0.188:443
- Synology firewall: Allow ports 80, 443

**5. Security Features**
- HTTPS only (redirect HTTP → HTTPS)
- Strong SSL configuration (A+ rating)
- Security headers
- Rate limiting
- Existing authentication (login required)
- Hide backend ports (only nginx exposed)

**Files to Create:**
- `nginx/nginx.conf` - Reverse proxy config
- `nginx/Dockerfile` - Custom nginx image
- `docker-compose.yml` - Add nginx + certbot services
- Update deployment scripts

**Estimated Time:** 30-90 minutes (DNS propagation dependent)

**Why Deferred:** System works great locally and via QuickConnect. External access is nice-to-have but not critical for MVP validation. Focus on using the system first.

---

**Phase 8: Applier Implementation** 🤖
**Status:** Next major feature after MVP validation

Will implement when ready to automate job applications:
- Playwright + Claude applier
- Navigate arbitrary ATS systems
- Fill forms intelligently
- Handle custom questions
- Mark as APPLIED/FAILED
- Test with real applications

---

## Previous Sessions

### Session - 2025-11-26 (Late Morning - Jobs Display Fix)
**Fixed critical jobs display issue and API slash handling**
- 307 redirect problem with FastAPI trailing slashes
- All 770 jobs now visible in UI
- Backend properly handles both `/api/endpoint` forms

### Session - 2025-11-26 (Early Morning - Playwright Browser Fix)
**Fixed scraper not working in production**
- Playwright browsers installed as root, app runs as zapply user
- Solution: Install as root, copy to zapply user directory
- Scraper now working, 770 jobs fetched

### Session - 2025-11-26 (Early Morning - Production Password Fix)
**Fixed production login and completed deployment**
- Password hash escaping issue in .env.production
- Must use single quotes for bcrypt hashes
- Full deployment workflow operational

### Session - 2025-11-25 (Evening - Critical Bug Fixes)
**Fixed Claude API integration and real-time logging**
- Claude API returning JSON wrapped in markdown fences
- Real-time UI updates now working perfectly
- Standard Python logging everywhere

### Session - 2025-11-25 (Full Day - Testing & Polish)
**Completed PR #3 with scheduler and dashboard**
- Full scheduler system (Manual/Daily/Hourly)
- Real-time dashboard with auto-refresh
- All UI issues fixed
- Database migration documentation

---

## Decisions Log

### Technology Stack
- **Python 3.12**: Latest stable version
- **uv**: Ultra-fast package manager
- **just**: Command runner for automation
- **APScheduler**: For scheduled runs
- **Playwright**: Browser automation for scraping
- **Claude API**: AI-powered job matching

### Architecture Decisions
- **Manual migrations**: Control and safety over convenience
- **Polling for real-time**: Simple and effective for MVP
- **Deduplication in-memory**: O(1) set lookups, simple and fast
- **Composite database index**: Optimizes source+source_id queries
- **Progress callback optimization**: Only for actual work, not skips

### Performance Decisions
- **Pre-fetch existing slugs**: Single query, O(1) lookups
- **Skip scraping existing jobs**: 80-97% time savings
- **Composite index on (source, source_id)**: Faster deduplication queries
- **In-memory duplicate check**: No redundant DB queries

### Matching Decisions
- **60% threshold**: Perfect balance for matching
- **No further optimization**: Algorithm works as intended
- **Focus on usage**: Real-world validation over theoretical tuning

---

## Implementation Status

### ✅ Phase 1-5: Foundation Through Optimization (COMPLETE)
- [x] Complete backend and frontend
- [x] Working Nomads scraper with Playwright
- [x] Claude API integration for matching
- [x] UserProfile management with AI generation
- [x] Real-time dashboard and scheduler
- [x] Production deployment to NAS
- [x] Performance optimization (80-97% faster)
- [x] Jobs display fix (770 jobs visible)
- [x] All Claude Code Review issues resolved
- [x] Matching quality verified (works brilliantly)

### 🎯 Phase 6: MVP Usage & Validation (CURRENT)
- [x] System deployed and running 24/7
- [x] Scraper optimized and efficient
- [x] Matching verified and working great
- [ ] Use system for real job search
- [ ] Monitor and validate in production
- [ ] Gather learnings for future improvements

### 📋 Phase 7: External Access (FUTURE - Low Priority)
- [ ] Configure zapply.dev domain
- [ ] Set up nginx reverse proxy
- [ ] Implement SSL with Let's Encrypt
- [ ] Configure router port forwarding
- [ ] Test external access

### 🤖 Phase 8: Applier Implementation (FUTURE)
- [ ] Playwright + Claude applier
- [ ] Navigate ATS systems
- [ ] Fill forms intelligently
- [ ] Handle custom questions
- [ ] Test with real applications

---

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

---

## Key Success Criteria

1. ✅ Can fetch jobs from Working Nomads (scraper working, optimized)
2. ✅ Can accurately filter jobs (matcher working brilliantly)
3. ✅ System runs unattended on Synology NAS (24/7 operation)
4. ✅ Performance is excellent (80-97% faster on subsequent runs)
5. 🎯 Validate system with real job search (CURRENT FOCUS)
6. [ ] Can submit at least 1 real application automatically (Phase 8)

---

## Blockers

**None!** System is production-ready and working excellently.

Focus now: Use the system, validate in real-world, gather learnings.

---

## Notes

### Important Files & URLs
- **GitHub Repo**: https://github.com/vpetreski/zapply (private)
- **NAS Frontend**: http://192.168.0.188:3000/
- **NAS API**: http://192.168.0.188:8000/docs
- **Local Dev**: http://localhost:3000/, http://localhost:8000/docs
- **Profile Page**: /profile
- **Admin Page**: /admin
- **Docs**: `docs/ai.md`, `CLAUDE.md`, `.cursorrules`
- **Automation**: `Justfile` - run `just` to see all commands

### Development Workflow
1. Open Claude Code → loads this `docs/ai.md`
2. Continue from "Next Steps" section
3. User says "save" → update this file and commit
4. Session complete

### Cost Considerations
- Matcher: Be efficient with Claude API calls ✅
- Applier: Use Claude aggressively (worth the cost) - Future
- Monitor API usage during production use

### Performance Notes
- **First scrape:** 6-10 minutes (scrapes all jobs)
- **Subsequent scrapes:** 40-60 seconds (skips existing jobs)
- **Time savings:** 80-97% on hourly/daily runs
- **Database queries:** Optimized with composite index
- **Memory usage:** Minimal (storing slugs as strings in set)

---

**Last Updated:** 2025-11-26 (Session: Performance Optimization & Matching Verification) by Claude Code

**Next Session:**
1. Use the system for real job searching
2. Monitor production performance
3. Gather feedback and learnings
4. Plan Applier implementation when ready

**GitHub:** https://github.com/vpetreski/zapply (private)
**Current Branch:** `main` (feature/nas-external-access created for future work)

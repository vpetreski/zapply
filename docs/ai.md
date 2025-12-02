# Zapply - AI Context

## Current Phase
**Phase 7: Applier Implementation** 🤖 - IN PROGRESS

Implementing the Applier - the most critical component that actually submits job applications.

**Current Branch:** `feature/applier`

## Last Session - 2025-12-02 (Applier Implementation Start)

### Accomplished This Session

**1. Profile Improvements** ✅
- Added LinkedIn and GitHub fields to UserProfile
- Fixed CV upload to always read fresh from disk
- Renamed "Generate Profile" to "Analyze CV & Update Profile"
- Database migration for new fields

**2. Infrastructure Fixes** ✅
- Added `nas-local-sync` and `local-nas-sync` Justfile recipes
- Fixed Playwright browser installation issue
- Synced production data to local for testing

**3. Applier Planning** ✅
- Comprehensive codebase analysis
- Detailed implementation plan created (see below)

---

## Applier Implementation Plan

### Overview
The Applier navigates to matched job URLs, finds application forms, fills them intelligently using Claude Opus, and submits applications automatically.

### Architecture Flow
```
MATCHED Job → ApplierService →
  1. Launch Playwright browser
  2. Navigate to job.url
  3. Find "Apply" button and click it
  4. Detect ATS type (Greenhouse, Lever, Workday, direct form, etc.)
  5. Extract form structure using Claude (analyze HTML/screenshot)
  6. Fill form fields from UserProfile data
  7. Answer custom questions using Claude
  8. Upload CV (PDF from profile)
  9. Submit application
  10. Verify success (check for confirmation)
  11. Update job status → APPLIED/FAILED
  12. Log to ApplicationLog with screenshots
```

### Implementation Steps

#### Step 1: Core ApplierService ⬜
- Create `app/services/applier_service.py` (orchestration layer)
- Handle database operations, logging, error handling
- Query matched jobs, process one by one
- Update job status and create ApplicationLog entries

#### Step 2: JobApplier Class Rewrite ⬜
- Initialize Playwright browser (reuse pattern from scraper)
- Accept UserProfile as input
- Screenshot capture for debugging at each step
- Return detailed results (success/failure, data, screenshots)

#### Step 3: Page Analysis with Claude ⬜
- Take screenshot of application page
- Send to Claude Opus with prompt to analyze form structure
- Parse response to understand fields, types, required status
- Identify submit button

#### Step 4: Form Filling Logic ⬜
- Map UserProfile fields to form fields:
  - name → name/first_name/last_name
  - email → email
  - phone → phone/telephone
  - linkedin → linkedin/social
  - github → github/portfolio/website
  - location → location/city/address
  - cv_data → resume/cv file upload
- Use Claude for ambiguous field mapping

#### Step 5: Custom Question Handling ⬜
- Detect text areas and unusual fields
- Send question + job context + profile to Claude
- Generate contextual answers
- Log Q&A pairs in ApplicationLog

#### Step 6: CV Upload ⬜
- Detect file upload input (input[type="file"])
- Save cv_data to temp file, upload it
- Handle different upload mechanisms

#### Step 7: Submission & Verification ⬜
- Click submit button
- Wait for confirmation (page change, success message)
- Take final screenshot
- Detect success/failure indicators

#### Step 8: API & UI Integration ⬜
- Add `/api/applier/run` endpoint
- Add `/api/applier/apply/{job_id}` for single job
- Add "Apply" button in jobs dashboard
- Show application status/logs

### Profile Data Available
```python
UserProfile:
  - name, email, phone, location, rate
  - linkedin, github  # Just added
  - cv_filename, cv_data (binary PDF), cv_text
  - custom_instructions, skills, preferences
  - ai_generated_summary
```

### Database Fields (Already Exist)
```python
Job:
  - status: MATCHED → APPLIED/FAILED
  - applied_at: timestamp
  - application_data: JSON (form data, screenshots)
  - application_error: error message

ApplicationLog:
  - job_id, status, error_message
  - screenshots: JSON array
  - ai_prompts, ai_responses: JSON arrays
  - started_at, completed_at, duration_seconds
```

### AI Model
- `APPLIER_MODEL` = Claude Opus 4.5 (maximum intelligence for arbitrary ATS)

### MVP Constraints
1. **Manual trigger only** - Not automatic after matching
2. **One job at a time** - With logging between each
3. **Screenshot everything** - For debugging and verification
4. **Human supervision** - First applications need oversight
5. **Simple forms first** - Direct apply before complex multi-page ATS

### Files to Create/Modify
1. `app/services/applier_service.py` - NEW
2. `app/applier/applier.py` - REWRITE
3. `app/routers/applier.py` - NEW
4. `app/main.py` - Add router
5. `frontend/src/views/JobsView.vue` - Add apply button (later)

### Success Criteria
- [ ] Can navigate to job URL
- [ ] Can find and click Apply button
- [ ] Can analyze form with Claude
- [ ] Can fill standard fields (name, email, phone, etc.)
- [ ] Can upload CV
- [ ] Can answer custom questions
- [ ] Can submit application
- [ ] Can verify success/failure
- [ ] Can process all matched jobs sequentially
- [ ] Proper error handling and logging

---

## Previous Sessions Summary

### Session - 2025-11-29 (New Mac Setup & Code Cleanup)
- New Mac environment setup
- Environment variable cleanup
- AI model refactoring (created `app/ai_models.py`)

### Session - 2025-11-26 (Critical Login Fix & Deployment)
- Fixed production login (bcrypt hash handling)
- Automated deployment file sync
- Matching quality verified

---

## Implementation Status

### ✅ Phase 1-6: Complete
- [x] Backend and frontend
- [x] Working Nomads scraper with Playwright
- [x] Claude API integration for matching
- [x] UserProfile management with AI generation
- [x] Real-time dashboard and scheduler
- [x] Production deployment to NAS

### 🔄 Phase 7: Applier Implementation (IN PROGRESS)
- [x] Planning and architecture
- [ ] Core ApplierService
- [ ] JobApplier with Playwright
- [ ] Claude page analysis
- [ ] Form filling logic
- [ ] CV upload
- [ ] Submission and verification
- [ ] API endpoints
- [ ] UI integration

### 📋 Phase 8: External Access (Future)
- [ ] Configure zapply.dev domain
- [ ] nginx reverse proxy with SSL

---

## Key Files

- `app/ai_models.py` - AI model constants
- `app/services/applier_service.py` - Applier orchestration (to create)
- `app/applier/applier.py` - Core applier logic (to rewrite)
- `app/routers/applier.py` - API endpoints (to create)
- `docs/ai.md` - This file

---

**Last Updated:** 2025-12-02 by Claude Code

**Current Task:** Implementing Applier Step 1 & 2

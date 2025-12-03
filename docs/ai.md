# Zapply - AI Context

## Current Phase
**Phase 7: Applier Implementation** - BLOCKED

Implementing the Applier - the most critical component that actually submits job applications.

**Current Branch:** `feature/applier`

## Last Session - 2025-12-02 (Form Filling Issues - BLOCKED)

### Status: BLOCKED

Form filling with Greenhouse ATS is not working properly. React forms are rejecting our input methods.

### What Was Attempted

**1. Location Autocomplete**
- Tried Google Places `.pac-item` selectors
- Tried ArrowDown + Enter keyboard navigation
- Tried JS click on dropdown items
- **RESULT:** Location field stays empty or doesn't pass React validation

**2. Text Field Validation (LinkedIn, Other fields)**
- Tried native HTMLInputElement value setter pattern
- Tried `_set_react_input_value` method with event dispatching
- Tried Tab-through validation after filling
- **RESULT:** Fields show RED validation errors despite having values

**3. CV Upload**
- File uploads to input element
- Tried various event triggering after upload
- **RESULT:** Still shows validation errors

### Root Cause Analysis

Greenhouse (and other modern ATS) use React-based forms that:
1. Override native DOM `value` property setters
2. Maintain internal state that doesn't sync with DOM manipulation
3. Require specific React event dispatching to update state
4. Use Google Places autocomplete which needs actual dropdown selection

### Files Modified
- `app/applier/applier.py` - Multiple fix attempts (none working)
- `docs/applier-instructions.md` - Created for reference

### Next Steps (Tomorrow)

**Need a Different Approach:**
1. Research how Playwright handles React forms properly
2. Look at how other automation tools (Puppeteer, Selenium) solve this
3. Consider using Claude Computer Use for form filling instead of direct DOM manipulation
4. Test on simpler non-React forms first to establish baseline
5. Possibly use browser devtools to inspect React component state

### Current Applier Code State
The applier code has multiple attempted fixes that don't work:
- `_set_react_input_value` - attempts React-compatible value setting
- Google Places selectors - attempts autocomplete selection
- Event dispatching - attempts to trigger React state updates

All these need to be revisited with a fresh approach.

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

### Profile Data Available
```python
UserProfile:
  - name, email, phone, location, rate
  - linkedin, github
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

---

## Previous Sessions Summary

### Session - 2025-12-02 (Profile Improvements)
- Added LinkedIn and GitHub fields to UserProfile
- Fixed CV upload to always read fresh from disk
- Database migration for new fields
- Added Justfile sync recipes

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

### ⏸️ Phase 7: Applier Implementation (BLOCKED)
- [x] Planning and architecture
- [x] ApplierService orchestration layer
- [x] JobApplier with Playwright
- [x] Claude page analysis
- [ ] **BLOCKED:** Form filling logic (React compatibility issues)
- [ ] CV upload validation
- [ ] Submission and verification
- [x] API endpoints
- [ ] UI integration

### 📋 Phase 8: External Access (Future)
- [ ] Configure zapply.dev domain
- [ ] nginx reverse proxy with SSL

---

## Key Files

- `app/ai_models.py` - AI model constants
- `app/services/applier_service.py` - Applier orchestration
- `app/applier/applier.py` - Core applier logic (needs rewrite)
- `app/routers/applier.py` - API endpoints
- `docs/ai.md` - This file

---

**Last Updated:** 2025-12-02 by Claude Code

**Current Blocker:** React form filling not working - need different approach

# Session Notes - Run Tracking System Implementation

## Date
2024-11-24

## What We Built

### Complete Run Tracking System
Implemented comprehensive pipeline run tracking with real-time logs and UI monitoring.

#### Backend Features
- **Run Model**: Track pipeline executions with status, phase, stats, and logs
- **Run Status**: `running`, `completed`, `failed`, `partial`
- **Run Phases**: `scraping`, `matching`, `applying`, `reporting`
- **Real-time Logs**: JSON array of timestamped log entries with levels (info, success, warning, error)
- **Background Execution**: Non-blocking API endpoint using asyncio tasks
- **Run Prevention**: Only allows one run at a time (HTTP 409 if already running)
- **Progress Callbacks**: Scraper sends progress updates during execution

#### API Endpoints
- `POST /api/scraper/run` - Start new scraping run (background task, returns run_id)
- `GET /api/runs` - List runs with pagination and filtering (status, phase)
- `GET /api/runs/{run_id}` - Get detailed run information with logs

#### Frontend Features
- **Runs Page**: List all runs with infinite scroll
- **Filtering**: Filter by status and phase
- **Start Run Button**: Disabled when run is in progress
- **Run Detail Modal**: Shows timing, stats, and real-time logs
- **Auto-refresh**: Updates every 2 seconds for running runs (both list and modal)
- **Terminal-style Logs**: Color-coded by level, monospace font
- **Auto-scroll Toggle**: Checkbox to enable/disable automatic scroll to latest log (unchecked by default)
- **Colombian Timezone**: All timestamps displayed in UTC-5

#### Database
- Created runs table with all tracking fields
- Added logs field as JSON array
- Database migrations included
- Utility script: `scripts/clean_database.py`

## Key Technical Decisions

### Timezone Handling (Colombian UTC-5)
```javascript
const formatTimestamp = (timestamp) => {
  const isoString = timestamp.includes('Z') ? timestamp : timestamp + 'Z'
  const utcDate = new Date(isoString)
  const colombianDate = new Date(utcDate.getTime() - (5 * 60 * 60 * 1000))
  
  // Use UTC methods on adjusted timestamp
  const year = colombianDate.getUTCFullYear()
  // ... format using UTC methods
}
```

### SQLAlchemy JSON Field Modification
Critical fix for updating JSON arrays:
```python
def add_log(run: Run, message: str, level: str = "info") -> None:
    if run.logs is None:
        run.logs = []
    
    run.logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message
    })
    
    # REQUIRED: Mark field as modified for SQLAlchemy to detect change
    from sqlalchemy.orm import attributes
    attributes.flag_modified(run, "logs")
```

### Background Task Execution
```python
async def run_scraper(db: AsyncSession = Depends(get_db)):
    # Start scraper in background
    asyncio.create_task(run_scraper_background())
    
    # Wait for run to be created
    await asyncio.sleep(0.5)
    
    # Return immediately with run_id
    return StartRunResponse(run_id=new_run.id)
```

### Vue Reactivity for Nested Objects
```javascript
// Force reactivity by creating new object
selectedRun.value = { ...response.data }

// Use unique keys for v-for
:key="`${log.timestamp}-${index}`"
```

## Project Organization

Reorganized project structure:
```
zapply/
├── app/              # Backend application
├── frontend/         # Vue.js frontend
├── scripts/          # Utility scripts
│   ├── README.md
│   ├── clean_database.py
│   ├── test_scraper.py
│   └── test_scraper_simple.py
├── alembic/          # Database migrations
└── uv.lock           # Dependency lock file
```

## Issues Resolved

1. **UI Not Updating**: Fixed by using spread operator for Vue reactivity
2. **Logs Not Persisting**: Added `attributes.flag_modified` for JSON field
3. **Button Freezing**: Made scraper endpoint non-blocking with background tasks
4. **Timezone Display**: Implemented proper UTC-5 conversion for Colombian time
5. **Auto-scroll UX**: Added toggle checkbox for user control

## Usage

### Start a Run
1. Navigate to Runs page
2. Click "Start New Run" button
3. Modal opens automatically showing progress
4. Enable "Auto-scroll to latest" checkbox if desired
5. Watch real-time logs update every 2 seconds

### Clean Database
```bash
uv run python scripts/clean_database.py
```

## Commits Made
1. Add comprehensive run tracking system with real-time logs
2. Organize project structure: move scripts to scripts/ directory
3. Add uv.lock for reproducible dependency installation

## Next Steps (Not Implemented)
- Phase 2: Job matching (AI-powered CV matching)
- Phase 3: Automated applications
- Phase 4: Reporting and analytics
- Add more scraper progress callbacks (every job scraped)
- Consider WebSocket for truly real-time updates (vs polling)

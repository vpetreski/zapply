# Scraper System Documentation

## Architecture Overview

Zapply uses a **registry-based multi-scraper architecture** that supports:
- Multiple job sources running in sequence
- Per-source logging and statistics
- Database-driven configuration (enable/disable, priority, settings)
- Cross-source deduplication via `resolved_url`

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ScraperRegistry` | `app/scraper/registry.py` | Central registry for all scrapers |
| `BaseScraper` | `app/scraper/base.py` | Base class with common interface |
| `source_service` | `app/services/source_service.py` | Source CRUD and credential management |
| `scraper_service` | `app/services/scraper_service.py` | Orchestrates scraping runs |
| `ScraperSource` model | `app/models.py` | Database config for each source |
| `SourceRun` model | `app/models.py` | Per-source execution tracking |

### Data Flow

```
Run triggered (manual/scheduled)
    |
    +-> Get enabled sources from DB (ordered by priority)
    |
    +-> For each source:
    |       +-> Create SourceRun record
    |       +-> Get credentials from env vars
    |       +-> Instantiate scraper via registry
    |       +-> Execute scrape
    |       +-> Deduplicate (source_id + resolved_url)
    |       +-> Update SourceRun stats
    |
    +-> Aggregate stats into parent Run
```

### Database Tables

**`scraper_sources`** - Configuration per source:
- `name`: Unique identifier (e.g., `working_nomads`)
- `label`: Display name (e.g., `Working Nomads`)
- `enabled`: Whether to run this source
- `priority`: Lower runs first (100 = default)
- `credentials_env_prefix`: Prefix for env vars (e.g., `WORKING_NOMADS`)
- `settings`: JSON with source-specific config

**`source_runs`** - Per-source execution within a Run:
- `run_id`: Parent run
- `source_name`: Which source
- `status`: pending/running/completed/failed/skipped
- `jobs_found`, `jobs_new`, `jobs_duplicate`, `jobs_failed`
- `logs`: Per-source log entries

### Credential Management

Credentials are stored in environment variables, not the database.

For a source with `credentials_env_prefix = "WORKING_NOMADS"`, the system looks for:
- `WORKING_NOMADS_USERNAME`
- `WORKING_NOMADS_PASSWORD`
- `WORKING_NOMADS_API_KEY` (optional)

The Admin UI shows which credentials are configured (green) or missing (red).

---

## Adding a New Scraper

1. **Create scraper file**: `app/scraper/new_source.py`
   ```python
   from app.scraper.base import BaseScraper
   from app.scraper.registry import ScraperRegistry

   @ScraperRegistry.register("new_source")
   class NewSourceScraper(BaseScraper):
       SOURCE_NAME = "new_source"
       SOURCE_LABEL = "New Source"
       SOURCE_DESCRIPTION = "Description here"
       REQUIRES_LOGIN = True  # or False
       REQUIRED_CREDENTIALS = ["username", "password"]  # or ["api_key"]

       async def scrape(self, since_days=1, progress_callback=None, job_limit=0, existing_slugs=None, **kwargs):
           # Implementation - return list of job dicts
           pass

       async def login(self):
           # Login implementation if REQUIRES_LOGIN=True
           return True
   ```

2. **Add import** to `app/scraper/__init__.py`:
   ```python
   from app.scraper import new_source  # Triggers registration
   ```

3. **Add migration** to seed database record with default settings

4. **Add env vars** to `.env`:
   ```
   NEW_SOURCE_USERNAME=...
   NEW_SOURCE_PASSWORD=...
   ```

5. **Restart app** - sources auto-sync on startup, then **enable in Admin UI**

---

## Configured Scrapers

### Working Nomads

| Property | Value |
|----------|-------|
| **Name** | `working_nomads` |
| **File** | `app/scraper/working_nomads.py` |
| **Type** | Premium (login required) |
| **Auth** | Email/password |

**Environment Variables:**
```
WORKING_NOMADS_USERNAME=your_email@example.com
WORKING_NOMADS_PASSWORD=your_password
```

**How it works:**
1. Launches headless Chromium via Playwright
2. Logs in at `https://www.workingnomads.com/users/sign_in`
3. Navigates to jobs page with filters
4. Scrapes job listings via DOM parsing
5. For each job, extracts: title, company, description, tags, URL
6. Resolves redirect URLs to get actual job page (for deduplication)

**Default Settings** (stored in `scraper_sources.settings`):
```json
{
  "category": "development",
  "location": "anywhere,colombia",
  "posted_days": 7
}
```

**Filter Options:**

| Filter | Options | Notes |
|--------|---------|-------|
| `category` | `development`, `design`, `marketing`, etc. | Job category |
| `location` | `anywhere`, `colombia`, `usa`, etc. | Comma-separated |
| `posted_days` | `1`, `7`, `14`, `30` | Jobs posted within N days |

**URL Pattern:**
```
https://www.workingnomads.com/jobs?category=development&location=anywhere,colombia&postedDate=7
```

**Deduplication:**
- Within source: `source_id` (Working Nomads job ID)
- Cross-source: `resolved_url` (actual job posting URL after redirect)

**Rate Limiting:**
- 1-2 second delays between page loads
- Respects `networkidle` state before scraping

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sources` | GET | List all sources |
| `/api/sources/{name}` | GET | Get single source |
| `/api/sources/{name}` | PATCH | Update source (enable/disable) |

---

## Frontend Features

- **Jobs page**: Filter by source, source label shown on each job
- **Runs page**: Per-source results with stats (found/new/duplicate)
- **Admin page**: Simple toggle to enable/disable sources

# Scraper System Documentation

## Architecture Overview

Zapply uses a **registry-based multi-scraper architecture** that supports:
- Multiple job sources running in **parallel** via `asyncio.gather()`
- Per-source logging and statistics
- Database-driven configuration (enable/disable, priority, settings)
- **Two-level deduplication**: same-source (`source_id`) + cross-source (`resolved_url`)

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
    +-> PHASE 1: PARALLEL SCRAPING (asyncio.gather)
    |   |
    |   +-> Get enabled sources from DB
    |   |
    |   +-> For each source IN PARALLEL:
    |   |       +-> Create SourceRun record
    |   |       +-> Get credentials from env vars
    |   |       +-> Instantiate scraper via registry
    |   |       +-> Execute scrape (browser automation)
    |   |       +-> Return ScrapeResult with job data (NOT saved yet)
    |   |
    |   +-> Wait for all sources to complete
    |
    +-> PHASE 2: SEQUENTIAL SAVE (deduplication)
    |   |
    |   +-> For each ScrapeResult IN ORDER:
    |   |       +-> Check same-source dedup (source_id)
    |   |       +-> Check cross-source dedup (resolved_url)
    |   |       +-> Save new jobs to database
    |   |       +-> Update SourceRun stats
    |
    +-> PHASE 3: AI MATCHING
    |   |
    |   +-> Match new jobs against user profile
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

## Parallelization Strategy

### Why Parallel Scraping?

When multiple scrapers are enabled, they run **concurrently** using `asyncio.gather()`:

```python
scrape_tasks = [scrape_source_parallel(...) for source in sources]
results = await asyncio.gather(*scrape_tasks, return_exceptions=True)
```

**Benefits:**
- **Speed**: 3 sources scraping 30 jobs each takes ~same time as 1 source
- **Isolation**: One source failing doesn't stop others
- **Resource efficiency**: Browser automation waits are overlapped

**Implementation Details:**
- Each parallel task gets its own database session (`async_session_maker()`)
- Job data is returned in memory, not saved during scrape
- `ScrapeResult` dataclass holds: source info, job data list, stats, errors

### Why Sequential Saving?

Deduplication **must** happen sequentially to ensure correctness:

```python
# This runs AFTER all parallel scrapes complete
for result in scrape_results:
    for job in result.jobs_data:
        if job.resolved_url in seen_urls:
            # Cross-source duplicate!
            continue
        save_job(job)
        seen_urls.add(job.resolved_url)
```

**Why not parallel?**
- Race condition: Two sources might try to save the same job simultaneously
- First-wins semantics: We want deterministic behavior (first source by priority wins)
- Correctness > Speed: Saving is fast, deduplication logic is critical

---

## Deduplication Strategy

### Two-Level Deduplication

Jobs are deduplicated at two levels:

| Level | Field | Purpose | When |
|-------|-------|---------|------|
| **Same-source** | `source_id` | Prevent re-scraping same job from same source | During scrape |
| **Cross-source** | `resolved_url` | Prevent duplicate jobs across different sources | During save |

### Same-Source Deduplication

Each scraper has a unique ID for jobs within that source:
- Working Nomads: Job slug from URL (e.g., `senior-python-developer-acme-corp`)
- Other sources: Job ID, URL hash, or similar unique identifier

```python
# Before scraping, fetch existing source_ids for this source
existing_slugs = get_existing_source_ids(source_name)

# During scrape, skip already-seen jobs
if job_slug in existing_slugs:
    continue  # Already scraped this job before
```

**Result:** Each source only scrapes new jobs, even across multiple runs.

### Cross-Source Deduplication

Many job aggregators list the same job. We use `resolved_url` to detect these.

> **Note:** Cross-source dedup only works for sources that can resolve the actual job URL
> (e.g., Working Nomads). Sources like WWR that only provide their own page URL due to
> Cloudflare restrictions cannot participate in cross-source deduplication.

**The Problem:**
```
Working Nomads: https://workingnomads.com/j/abc123 → redirects to → https://company.com/careers/job-456
RemoteOK:       https://remoteok.com/jobs/xyz789 → redirects to → https://company.com/careers/job-456
```

Both point to the same actual job posting!

**The Solution:**
1. During scraping, resolve redirect URLs to get the final destination
2. Store `resolved_url` in the jobs table
3. During save, check if `resolved_url` already exists

```python
# Track URLs seen in this batch AND in database
seen_urls = get_all_resolved_urls_from_db()

for job in jobs_to_save:
    if job.resolved_url in seen_urls:
        stats.duplicate += 1
        continue

    save_job(job)
    seen_urls.add(job.resolved_url)
    stats.new += 1
```

**First Source Wins:** If two sources have the same job, the source with lower priority number (runs first in the save phase) keeps the job.

### How Duplicates Are Marked

Jobs are **not** marked as duplicates in the database - they're simply **not saved**:

| Stat | Meaning |
|------|---------|
| `jobs_found` | Total jobs scraped from source |
| `jobs_new` | Jobs saved to database (passed dedup) |
| `jobs_duplicate` | Jobs skipped (same-source OR cross-source duplicate) |
| `jobs_failed` | Jobs that failed to save (error) |

The `duplicate` count is shown in:
- Run detail modal (per-source breakdown)
- Source run stats
- Console logs during scraping

### Database Schema for Deduplication

```sql
-- jobs table
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    source VARCHAR NOT NULL,           -- e.g., "working_nomads"
    source_id VARCHAR NOT NULL,        -- unique within source
    url VARCHAR NOT NULL,              -- original URL from source
    resolved_url VARCHAR,              -- final URL after redirects
    -- ... other fields

    UNIQUE(source, source_id)          -- same-source dedup constraint
);

-- Index for cross-source dedup lookups
CREATE INDEX ix_jobs_resolved_url ON jobs(resolved_url) WHERE resolved_url IS NOT NULL;
```

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

### We Work Remotely

| Property | Value |
|----------|-------|
| **Name** | `we_work_remotely` |
| **File** | `app/scraper/weworkremotely.py` |
| **Type** | RSS-based (no browser, no login needed) |
| **Auth** | None (public RSS feeds) |

**Environment Variables:** None required

**How it works:**
1. Fetches job listings from RSS feeds (no Cloudflare, fast)
2. Parses RSS XML to extract: title, company, region, description, skills
3. Filters by region (`Anywhere in the World`, `Latin America Only`)
4. Filters by post date (default: last 7 days)
5. Returns WWR job page URLs

**RSS Feeds:**
| Category | URL |
|----------|-----|
| Backend | `https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss` |
| Fullstack | `https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss` |

**Default Settings** (stored in `scraper_sources.settings`):
```json
{
  "categories": ["backend", "fullstack"],
  "posted_days": 7
}
```

**Region Filtering:**

Jobs are only included if region matches:
- `Anywhere in the World`
- `Latin America Only`

Jobs with other regions (e.g., `USA Only`) are skipped.

**Deduplication:**
- Within source: `source_id` (job slug from URL, e.g., `company-job-title`) ✅
- Cross-source: **Not available** ❌

**Why no cross-source dedup?**

WWR uses Cloudflare protection that blocks headless browsers. We can't programmatically:
- Login to Pro account
- Access job detail pages
- Extract the real Apply URL (which would be used for cross-source dedup)

This means if the same job appears on both Working Nomads and WWR, it will be stored twice.
This is acceptable because:
- Job overlap between sources is relatively low
- The Matcher will evaluate both - same result either way
- Manual review during matching catches obvious duplicates
- Low job volume makes this a minor inconvenience

**Manual Application:**

The URL stored is the WWR job page. To apply:
1. Click "View Job" to open WWR job page
2. Click "Apply" button on WWR (requires Pro account to see real URL)
3. Apply on company's actual job page

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

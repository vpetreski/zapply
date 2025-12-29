# Scripts

Utility scripts for development and testing.

## Available Scripts

### clean_database.py
Cleans the database by deleting all jobs and runs, and resetting ID sequences.

Usage:
```bash
uv run python scripts/clean_database.py
```

### test_scraper.py
Interactive test script for debugging the Working Nomads scraper. Runs in visible browser mode with slow motion.

Usage:
```bash
uv run python scripts/test_scraper.py
```

### test_scraper_simple.py
Simpler test script for the Working Nomads scraper.

Usage:
```bash
uv run python scripts/test_scraper_simple.py
```

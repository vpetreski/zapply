# Remotive Scraper Implementation Notes

This document contains implementation notes for the Remotive scraper. The scraper is now implemented - see `docs/scrapping.md` for the full documentation.

## Configuration

Set environment variables:
```
REMOTIVE_USERNAME=your_email@example.com
REMOTIVE_PASSWORD=your_password
```

## How It Works

1. Login at https://remotive.com/web/login (premium account required)
2. Navigate to https://remotive.com/remote-jobs/software-development with location filters
3. Click "More Jobs" button until jobs older than 2 weeks appear
4. Extract job slugs from listing page
5. Visit each job detail page to scrape full information
6. Resolve "Apply for this position" URLs for cross-source deduplication

## Filters

- Location: Worldwide, Latin America (LATAM), Colombia
- Category: Software Development
- Date: Last 7 days (stop loading when 2wks+ jobs appear)

## Job Details Extraction

- Title and Company parsed from format: `[Hiring] Job Title @CompanyName`
- Description extracted from page body text
- Apply URL resolved from "Apply for this position" button

# Zapply - Project Requirements

## Overview

Zapply is an AI-powered remote job application automation system designed to solve the pain points of manually searching and applying for remote software engineering jobs.

## Problem Statement

### Current Pain Points
1. Job application process is tedious, boring, and time-consuming
2. Most job boards don't distinguish between "remote but US-authorized" vs "truly remote, contractor-friendly"
3. Manual filtering wastes significant time on incompatible positions
4. Speed matters - applying quickly to new postings increases chances of getting hired

## Solution Architecture

### High-Level Design

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SCRAPER   │────▶│   MATCHER   │────▶│  DASHBOARD  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                     ┌─────▼─────┐
                     │  POSTGRES │
                     └───────────┘
```

### Components

#### 1. Scraper
- Fetches jobs from multiple sources
- Runs on configurable schedule
- Transforms to internal data model (source-agnostic)
- NO AI - just data transformation
- Stores raw job data in database

#### 2. Matcher
- Triggered when new jobs detected
- Uses Claude API for intelligent matching
- Input: User profile + job description + filtering criteria
- Output: MATCHED/REJECTED status with reasoning
- Cost-efficient with API calls

#### 3. Dashboard
- Vue.js web interface
- Job review and filtering
- Status tracking
- Profile management

### Data Flow

```
NEW → MATCHED/REJECTED → APPLIED (manual)
```

## Technology Stack

### Backend
- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- Playwright for browser automation
- Anthropic Claude API

### Frontend
- Vue.js 3
- Vite
- Dark theme

### Infrastructure
- PostgreSQL database
- Docker containers
- GitHub Actions CI/CD
- Self-hosted deployment

## Job Matching Criteria

### Accept If
- True remote positions (location doesn't matter)
- Companies open to international contractors
- LATAM/timezone compatible
- Contract or full-time arrangements compatible with contractor setup

### Reject If
- Work authorization requirements
- Physical presence requirements (hybrid, office-based)
- Location-specific requirements

## Key Principles

1. **Simple over complex** - Avoid over-engineering
2. **AI where it adds value** - Use AI for matching, not for simple logic
3. **Cost efficient** - Be mindful of API costs
4. **Local first** - Designed for self-hosted deployment
5. **Fast iteration** - Working features over perfect code

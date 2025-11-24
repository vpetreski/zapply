# Zapply - Initial Project Prompt

## Overview

Zapply is an AI-powered remote job application automation system designed to solve the pain points of manually searching and applying for remote software engineering jobs. The goal is to have a working MVP in one week, with potential to evolve into a commercial product.

---

## About the User

### Profile
- **Name:** Vanja Petreski
- **Role:** Principal Software Engineer with 20 years of experience
- **Location:** Colombia (Colombian and Serbian citizenship, no US work permit)
- **Work Style:** 100% remote contractor
- **Business Entity:** Petreski LLC
- **Rate:** $10,000 USD/month (or equivalent hourly/yearly)
- **Payment:** US Payoneer account

### Core Skills
- Primary: Java, Kotlin, Spring Boot, Backend, APIs, Architecture, Tech Leadership, Product Management
- Extended (AI-enabled): Python, FastAPI, Go, Node, TypeScript, mobile (iOS, Android, Flutter), frontend (Vue, React)
- Key Value Proposition: Experience, architecture, product thinking, tech leadership - not limited to specific tech stack

### Target Job Criteria
**Must Have:**
- True remote positions (location doesn't matter)
- US companies open to international contractors, OR
- Companies specifically hiring in Latam/Colombia
- Contract or full-time arrangements that work with contractor setup

**Must NOT Have:**
- US work authorization requirements
- Physical presence requirements
- Hybrid positions requiring specific location

---

## The Problem

### Current Pain Points
1. Job application process is tedious, boring, and time-consuming
2. Existing tools don't fit needs and don't deliver results
3. Most job boards don't distinguish between "remote but US-authorized" vs "truly remote, contractor-friendly"
4. Manual filtering wastes significant time on incompatible positions
5. Speed matters - applying quickly to new postings increases chances of getting hired

### Current Manual Workflow
| Source | Usage | Notes |
|--------|-------|-------|
| LinkedIn | Respond to recruiters only | Don't apply directly - bad filtering, no responses |
| JobCopilot | Automated apply | Ineffective, mostly US-presence-required jobs |
| Working Nomads | Primary source | Premium account, clean UI, frequent updates, good quality |
| We Work Remotely | Secondary source | Don't love it but major source |
| Remotive | Maybe | To evaluate |
| Gun.io | Declining | Quality has dropped |

---

## Solution Architecture

### High-Level Design

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SCRAPER   │────▶│   MATCHER   │────▶│   APPLIER   │────▶│  REPORTER   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                    │
                              ┌─────▼─────┐
                              │  POSTGRES │
                              └───────────┘
                                    │
                              ┌─────▼─────┐
                              │  VUE.JS   │
                              │ DASHBOARD │
                              └───────────┘
```

### Components

#### 1. Scraper
- **Trigger:** Runs hourly via scheduler
- **Function:** Fetches new jobs from configured sources
- **Initial Source:** Working Nomads (extensible to others later)
- **Behavior:**
  - First run: Fetch last 2 weeks of jobs for initial load
  - Subsequent runs: Fetch only new jobs since last run
  - If system was off: Catch up on jobs up to 2 weeks back
- **Filtering:** Very broad at this stage - fetch almost everything, don't filter by tech
- **Output:** Jobs transformed to internal data model (source-agnostic format)
- **Tech:** Playwright for automation (NO AI here - just data transformation)
- **Data captured:** Job URL, title, company, description, requirements, source identifier, timestamps

#### 2. Matcher
- **Trigger:** When new jobs are detected
- **Function:** Match jobs against user profile and preferences
- **Inputs:**
  - User's CV (PDF stored in system)
  - User's preferences (remote, contract, Colombia/Latam friendly)
- **AI:** Claude API for intelligent matching
- **Filtering criteria:**
  - YES: Remote, contractor-friendly, Latam/Colombia accepted
  - NO: Hybrid, requires specific location (Germany, US, etc.), requires work authorization
- **Output:** Jobs marked as "ready to apply" or "rejected" with reasoning
- **Cost consideration:** Must be efficient with AI API calls

#### 3. Applier
- **Trigger:** When jobs are marked "ready to apply"
- **Function:** Automate the application process
- **Tech:** Playwright + Claude AI (aggressive AI usage here)
- **Capabilities:**
  - Navigate arbitrary ATS systems and job pages
  - Fill forms intelligently
  - Answer custom questions appropriately
  - Handle different application flows
- **Output:** Jobs marked as "applied" or "failed" with details

#### 4. Reporter
- **Trigger:** After application attempts complete
- **Function:** Generate detailed reports and notifications
- **Content:**
  - What was done (applications submitted)
  - Errors encountered
  - Jobs requiring manual intervention
  - Statistics and summaries
- **Output:** Notifications to user (method TBD - email, webhook, dashboard)

### Data Flow & Status Management

Jobs flow through the system with status tracking in Postgres:

```
NEW → MATCHED/REJECTED → APPLIED/FAILED → REPORTED
```

Sequential processing with status fields - no Kafka needed for MVP.

---

## Technology Stack

### Backend
- **Language:** Python (latest)
- **Framework:** FastAPI (latest)
- **Architecture:** Monolith with internal modules (Scraper, Matcher, Applier, Reporter)
- **Database:** PostgreSQL
- **Automation:** Playwright
- **AI:** Anthropic Claude API

### Frontend
- **Framework:** Vue.js (latest)
- **Design:** Modern dark theme
- **Features:** Dashboard for monitoring jobs, viewing reports, managing CV, system status

### Infrastructure
- **Hosting:** Synology NAS (Docker containers)
- **Benefits:**
  - Runs 24/7 even when computer is off
  - Residential IP avoids bot detection
  - All data stays local
  - Remote access via Synology QuickConnect
- **Deployment:** Docker containers for all components

---

## Development Workflow

### Tools
- **Primary:** Claude Code
- **Secondary:** Cursor
- **Code Review:** Cursor Bugbot on PRs
- **Version Control:** Git with PR workflow

### Context Management

Single file approach using `ai.md` for all AI tool context:
- Replaces multiple files (task.md, session.md, workflow.md)
- Contains: phases, sessions, work history, current status, next steps
- Loaded automatically by AI tools at session start
- Updated when user says "save"

**Workflow cycle:**
1. Open Claude Code
2. AI loads context from `ai.md`
3. AI tells user what's next
4. Work together
5. User says "save"
6. AI updates `ai.md` and pushes
7. Session complete

### AI Tool Configuration
- `CLAUDE.md` - Instructions for Claude Code
- `.cursorrules` - Instructions for Cursor

---

## MVP Scope (Week 1)

### In Scope
1. Working Nomads scraper (single source)
2. Basic matcher with Claude AI
3. Basic applier with Playwright + Claude AI
4. Simple status tracking in Postgres
5. Basic reporter (console/logs initially)
6. Minimal Vue.js dashboard to view jobs and status

### Out of Scope (Future)
- Additional job sources (We Work Remotely, Remotive, etc.)
- Advanced dashboard features
- Email/webhook notifications
- Analytics and insights
- Commercial features

---

## First Steps for Claude Code

When Claude Code reads this document, it should:

1. **Confirm understanding** of the project scope, architecture, and workflow
2. **Create initial project structure:**
   - `CLAUDE.md` - Claude Code instructions
   - `.cursorrules` - Cursor instructions
   - `ai.md` - AI context tracking file
   - `.gitignore` - Git ignore rules
   - `README.md` - Project overview
   - Basic folder structure for the Python/FastAPI backend
3. **Initialize git repository** (if not already done)
4. **Discuss and confirm** the first development phase

---

## Key Principles

1. **Move fast, iterate quickly** - MVP in one week
2. **Start narrow, expand later** - One source first, extensible design
3. **AI where it adds value** - Matcher and Applier, not Scraper
4. **Cost efficient** - Don't burn money on unnecessary API calls
5. **Simple over complex** - No Kafka, no microservices, monolith is fine
6. **Local first** - All infrastructure on Synology NAS
7. **Persistent context** - Everything tracked in `ai.md`

---

## Resume Reference

The user's full resume is available and should be used for:
- Understanding the full professional background
- Crafting application responses
- Matching job requirements to experience

Key highlights:
- Principal Software Engineer level
- 20 years experience
- Strong backend (Java, Kotlin, Spring Boot)
- Recent AI-native development experience
- Experience across fintech, healthcare, gaming, enterprise
- AWS certified
- Masters in Computer Science

---

## Questions for Claude Code to Clarify

Before starting, Claude Code should confirm:
1. Is the project folder structure clear?
2. Any preferences on Python version (3.11, 3.12, etc.)?
3. Any preferences on package management (pip, poetry, uv)?
4. Should the Vue.js dashboard be in the same repo or separate?
5. Any existing Synology Docker setup to consider?

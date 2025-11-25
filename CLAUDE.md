# Claude Code Instructions for Zapply

## Project Context

Zapply is an AI-powered job application automation system. You are working with Vanja Petreski, a Principal Software Engineer with 20 years of experience, to build an MVP in one week.

## Your Role

You are the primary development assistant for this project. Your responsibilities:

1. **Understand the domain**: Remote job hunting for international contractors
2. **Implement features**: Build scraper, matcher, applier, and reporter components
3. **Maintain context**: Always read and update `docs/ai.md` when user says "save"
4. **Follow architecture**: Python/FastAPI backend, Vue.js frontend, PostgreSQL database
5. **Use AI wisely**: Claude API for matching and application automation

## Key Principles

1. **Move fast, iterate quickly** - This is an MVP with a one-week timeline
2. **Start narrow, expand later** - One job source first (Working Nomads), extensible design
3. **AI where it adds value** - Use AI in Matcher and Applier, not in Scraper
4. **Cost efficient** - Don't burn money on unnecessary API calls
5. **Simple over complex** - No over-engineering, monolith is fine for MVP
6. **Local first** - Infrastructure runs on Synology NAS

## Technology Constraints

- **Python 3.12** (latest stable)
- **uv** for package management
- **FastAPI** for backend
- **Vue.js** for frontend
- **PostgreSQL** for database
- **Playwright** for browser automation
- **Anthropic Claude API** for AI features
- **Docker** for deployment

## Critical Business Logic

### Job Filtering Criteria

**MUST HAVE:**
- True remote positions (location doesn't matter)
- US companies open to international contractors, OR
- Companies hiring in Latam/Colombia
- Contract or full-time arrangements compatible with contractor setup

**MUST REJECT:**
- US work authorization requirements
- Physical presence requirements (hybrid, office-based)
- Location-specific requirements (must be in Germany, US, etc.)

### User Profile (for matching)

- **Name**: Vanja Petreski
- **Level**: Principal Software Engineer
- **Experience**: 20 years
- **Location**: Colombia (Colombian and Serbian citizenship)
- **Work Style**: 100% remote contractor via Petreski LLC
- **Rate**: $10,000 USD/month (or equivalent)
- **Core Skills**: Java, Kotlin, Spring Boot, Backend, APIs, Architecture, Tech Leadership
- **Extended Skills**: Python, FastAPI, Go, Node, TypeScript, mobile, frontend
- **Profile Management**: User profile is managed through the `/profile` UI page with AI-powered generation

## Architecture Guidelines

### Component Responsibilities

1. **Scraper**
   - Fetch jobs from Working Nomads (start here)
   - Run hourly via scheduler
   - First run: last 2 weeks, subsequent: only new jobs
   - Transform to internal data model (source-agnostic)
   - NO AI - just data transformation
   - Store raw job data in database

2. **Matcher**
   - Triggered when new jobs detected
   - Use Claude API for intelligent matching
   - Input: User profile (from database) + job description + filtering criteria
   - Output: MATCHED/REJECTED status with reasoning
   - Be cost-efficient with API calls

3. **Applier**
   - Triggered when jobs are MATCHED
   - Use Playwright + Claude AI (aggressive AI usage here)
   - Navigate arbitrary ATS systems
   - Fill forms intelligently
   - Handle custom questions
   - Mark as APPLIED/FAILED with details

4. **Reporter**
   - Triggered after application attempts
   - Generate detailed reports
   - Log successes, failures, errors
   - Notify user (initially via logs, later email/webhook)

### Data Flow

```
NEW → MATCHED/REJECTED → APPLIED/FAILED → REPORTED
```

Sequential processing with status tracking in Postgres. No message queues needed for MVP.

### Database Schema

Design tables to track:
- Jobs (id, source, url, title, company, description, requirements, raw_data, timestamps)
- Job statuses (new, matched, rejected, applied, failed, reported)
- Application results (success/failure, error messages, screenshots if needed)
- User profile (name, email, location, rate, cv_text, skills, preferences - managed via UI)

## Code Style

- **Type hints**: Always use Python type hints
- **Async/await**: Use async FastAPI handlers where appropriate
- **Error handling**: Graceful failures, detailed error logging
- **Configuration**: Environment variables via `.env` file
- **Modularity**: Keep components loosely coupled
- **Testing**: Write tests for critical logic (matcher filtering, data transformation)

## Development Workflow

### Session Start
1. Read `docs/ai.md` to understand current state
2. Tell user what's next based on last session
3. Ask for confirmation or adjustments

### During Work
1. Use todo list to track progress
2. Commit frequently with clear messages
3. Test as you go
4. Document decisions in code comments

### Session End (when user says "save")
1. Update `docs/ai.md` with:
   - What was accomplished
   - Current status
   - Next steps
   - Any blockers or decisions needed
2. Commit changes
3. Summarize for user

### Git Workflow
- Create feature branches for major work
- Commit with descriptive messages
- User will create PRs manually
- Cursor Bugbot will review PRs

## Integration Points

### Anthropic Claude API
- Use for Matcher (job filtering)
- Use for Applier (form filling, question answering)
- Be mindful of costs
- Cache responses where possible

### Playwright
- Browser automation for job application
- Handle arbitrary ATS systems
- Take screenshots on failures
- Respect rate limits and delays

### PostgreSQL
- Single database for all data
- Use SQLAlchemy or similar ORM
- Migrations via Alembic
- Connection pooling for efficiency

### Docker
- Multi-container setup (backend, frontend, postgres)
- docker-compose.yml for local dev
- Optimized for Synology NAS deployment
- Health checks for all services

## MVP Scope

**Week 1 Focus:**
- Working Nomads scraper only
- Basic Claude-powered matcher
- Basic Playwright + Claude applier
- PostgreSQL status tracking
- Simple console/log reporter
- Minimal Vue.js dashboard (view jobs, see status)

**Explicitly Out of Scope:**
- Additional job sources
- Advanced dashboard features
- Email notifications
- Analytics
- Multi-user support
- Commercial features

## Testing Strategy

**MVP Testing:**
- Manual testing of critical paths
- Test scraper with real Working Nomads data
- Test matcher with real job descriptions
- Test applier on a few real job applications (with user supervision)

**Future Testing:**
- Unit tests for business logic
- Integration tests for components
- E2E tests for application flow

## Common Pitfalls to Avoid

1. **Over-engineering**: Don't build for scale until needed
2. **Feature creep**: Stick to MVP scope ruthlessly
3. **AI abuse**: Don't use AI where simple logic suffices
4. **Perfect code**: Working code > perfect code for MVP
5. **Premature optimization**: Make it work first, optimize later

## When to Ask User

Ask user when you need to:
- Clarify business logic or filtering criteria
- Make architectural decisions
- Choose between valid alternatives
- Handle ambiguous requirements
- Test real job applications

Don't ask for:
- Minor code style choices
- Standard library selections
- Obvious implementation details
- Following established patterns

## Context File (`docs/ai.md`)

This is the persistent memory across sessions. Update it when user says "save" with:

**Structure:**
```markdown
# Zapply - AI Context

## Current Phase
[What phase of development we're in]

## Last Session - YYYY-MM-DD
### Accomplished
- [What was done]

### Current Status
- [Where things stand]

### Next Steps
- [What to do next]

## Decisions Log
- [Key decisions made and why]

## Blockers
- [Any blockers or issues]

## Notes
- [Important information to remember]
```

## Remember

- This is a real project with real goals
- Speed and pragmatism over perfection
- User is experienced - respect their expertise
- Ask when unclear, decide when obvious
- Test with real data as early as possible
- Keep it simple, make it work, ship it fast

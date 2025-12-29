# AI Job Matching System

## Overview

Zapply uses Claude AI for intelligent job matching. The system analyzes each job against your profile and provides match scores with detailed reasoning.

## How It Works

### Matching Pipeline

```
1. SCRAPE → Job listings from enabled sources
2. SAVE → New jobs to database (status: NEW)
3. MATCH → Claude AI analyzes each job
4. SCORE → Assign 0-100 score + reasoning
5. CLASSIFY → Mark as MATCHED (≥60) or REJECTED (<60)
6. DISPLAY → Show in dashboard with filters
```

### AI Analysis

For each job, Claude receives:
- **Job Data**: Title, company, description, requirements, tags, salary, location
- **Your Profile**: Skills, preferences, custom instructions
- **Your CV**: Full resume text

Claude returns:
```json
{
  "score": 85,
  "reasoning": "Strong alignment with required skills...",
  "strengths": ["Relevant experience", "Remote friendly"],
  "concerns": ["No direct industry experience"],
  "recommendation": "Highly recommended - excellent match"
}
```

## Configuration

### Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Matching Threshold

Default minimum score: **60/100**

Jobs scoring below this threshold are marked as REJECTED.

## Scoring Rubric

| Score | Category | Meaning |
|-------|----------|---------|
| 90-100 | Excellent | Perfect match, apply immediately |
| 75-89 | Good | Strong match, highly recommended |
| 60-74 | Fair | Moderate match, worth considering |
| 40-59 | Weak | Some alignment, probably not ideal |
| 0-39 | Poor | Not recommended, skip |

## UI Features

### Match Score Display
- Color-coded badges (green/blue/yellow/red)
- Score prominently shown on job cards
- Detailed reasoning in job modal

### Filtering
- Filter by minimum score
- Sort by match score or date
- Status filter (Matched/Rejected/Applied)

## Performance

### API Costs (Claude Sonnet)
- Input: ~$3 per million tokens
- Output: ~$15 per million tokens
- Per job: ~$0.01

### Processing Speed
- ~2-3 jobs/second
- Sequential processing for cost control
- Progress logged every 10 jobs

## Best Practices

### Profile Setup
1. Upload comprehensive CV
2. Add custom instructions for preferences
3. Specify target industries and technologies
4. Include location/timezone preferences

### Filtering Results
1. Start with min score of 75
2. Sort by match score
3. Review highest scores first
4. Use manual override for edge cases

## Error Handling

- API errors: Job scored 0, marked as REJECTED
- Missing profile: Clear error message in logs
- Rate limits: Graceful retry with backoff

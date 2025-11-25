"""AI-powered job matching service using Claude."""

from datetime import datetime
from typing import Optional

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from app.config import settings
from app.models import Job, JobStatus, Run, UserProfile


def add_log(run: Run, message: str, level: str = "info") -> None:
    """Add a log entry to the run."""
    if run.logs is None:
        run.logs = []

    run.logs.append({
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "message": message
    })

    # Mark the logs field as modified so SQLAlchemy detects the change
    attributes.flag_modified(run, "logs")


async def get_active_user_profile(db: AsyncSession) -> Optional[UserProfile]:
    """Get the first user profile (for MVP, we assume single user)."""
    result = await db.execute(select(UserProfile).limit(1))
    return result.scalar_one_or_none()


async def match_job_with_claude(
    job: Job,
    user_profile: UserProfile,
    client: anthropic.AsyncAnthropic
) -> tuple[float, str]:
    """
    Match a single job against user profile using Claude AI.

    Returns:
        Tuple of (match_score, reasoning)
        - match_score: 0-100 score indicating fit
        - reasoning: Detailed explanation of the match
    """
    # Build the matching prompt
    prompt = f"""You are an expert job matching assistant. Analyze this job posting against the candidate's profile and provide a match score and detailed reasoning.

**CANDIDATE PROFILE:**
Name: {user_profile.name}
Location: {user_profile.location}
Rate: {user_profile.rate}
Skills: {', '.join(user_profile.skills) if user_profile.skills else 'Not specified'}

**CANDIDATE CV/RESUME:**
{user_profile.cv_text or 'No CV text available'}

**JOB POSTING:**
Title: {job.title}
Company: {job.company}
Location: {job.location or 'Not specified'}
Salary: {job.salary or 'Not specified'}
Tags: {', '.join(job.tags) if job.tags else 'None'}

Description:
{job.description}

{f"Requirements:\n{job.requirements}" if job.requirements else ""}

**INSTRUCTIONS:**
1. Analyze the job requirements against the candidate's skills and experience
2. Consider location compatibility, salary expectations, and tech stack alignment
3. Identify key strengths and potential gaps
4. Provide a match score from 0-100:
   - 90-100: Exceptional fit, highly recommended
   - 75-89: Strong fit, good match
   - 60-74: Moderate fit, worth considering
   - 40-59: Weak fit, some alignment
   - 0-39: Poor fit, not recommended

Respond in this exact JSON format:
{{
  "score": <number 0-100>,
  "reasoning": "<detailed explanation>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "concerns": ["<concern 1>", "<concern 2>", ...],
  "recommendation": "<brief summary recommendation>"
}}"""

    try:
        # Call Claude API (async)
        message = await client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0.3,  # Lower temperature for more consistent scoring
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract response
        response_text = message.content[0].text

        # Parse JSON response
        import json
        match_data = json.loads(response_text)

        score = float(match_data["score"])

        # Build detailed reasoning from response
        reasoning = f"""**Match Score: {score}/100**

**Reasoning:**
{match_data['reasoning']}

**Key Strengths:**
{chr(10).join(f"• {s}" for s in match_data['strengths'])}

**Potential Concerns:**
{chr(10).join(f"• {c}" for c in match_data['concerns']) if match_data['concerns'] else '• None identified'}

**Recommendation:**
{match_data['recommendation']}"""

        return (score, reasoning)

    except Exception as e:
        print(f"Error matching job {job.id}: {str(e)}")
        # Return low score and error reasoning
        return (0.0, f"Error during matching: {str(e)}")


async def match_jobs(db: AsyncSession, run: Run, min_score: float = 60.0) -> dict[str, int]:
    """
    Match all new jobs against user profile using Claude AI.

    Args:
        db: Database session
        run: Current run for logging
        min_score: Minimum score threshold (default 60)

    Returns:
        Dictionary with statistics
    """
    add_log(run, "Starting AI-powered job matching phase", "info")
    await db.commit()

    stats = {
        "total_jobs": 0,
        "matched": 0,
        "rejected": 0,
        "errors": 0,
        "average_score": 0.0,
    }

    try:
        # Get user profile
        user_profile = await get_active_user_profile(db)

        if not user_profile:
            add_log(run, "No user profile found. Please create a profile first.", "error")
            await db.commit()
            raise ValueError("No user profile found")

        add_log(run, f"Using profile: {user_profile.name}", "info")
        await db.commit()

        # Get all NEW jobs (not yet matched)
        result = await db.execute(
            select(Job).where(Job.status == JobStatus.NEW.value)
        )
        jobs = result.scalars().all()
        stats["total_jobs"] = len(jobs)

        if stats["total_jobs"] == 0:
            add_log(run, "No new jobs to match", "info")
            await db.commit()
            return stats

        add_log(run, f"Found {stats['total_jobs']} new jobs to match", "info")
        await db.commit()

        # Initialize async Claude client
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        add_log(run, "Initialized Claude AI client (async)", "info")
        await db.commit()

        # Match each job
        total_score = 0.0

        for i, job in enumerate(jobs, 1):
            try:
                # Log progress every 10 jobs
                if i % 10 == 0 or i == 1:
                    add_log(run, f"Matching job {i}/{stats['total_jobs']}: {job.title}", "info")
                    await db.commit()

                # Match job with Claude
                score, reasoning = await match_job_with_claude(job, user_profile, client)

                # Update job with match results
                job.match_score = score
                job.match_reasoning = reasoning
                job.matched_at = datetime.utcnow()

                total_score += score

                # Update status based on score
                if score >= min_score:
                    job.status = JobStatus.MATCHED.value
                    stats["matched"] += 1
                    print(f"  ✅ MATCHED ({score:.1f}/100): {job.title} at {job.company}")
                else:
                    job.status = JobStatus.REJECTED.value
                    stats["rejected"] += 1
                    print(f"  ❌ REJECTED ({score:.1f}/100): {job.title} at {job.company}")

                # Commit every 5 jobs to save progress
                if i % 5 == 0:
                    await db.commit()

            except Exception as e:
                stats["errors"] += 1
                job.match_score = 0.0
                job.match_reasoning = f"Error during matching: {str(e)}"
                job.status = JobStatus.REJECTED.value
                print(f"  ❌ Error matching job {job.id}: {str(e)}")
                add_log(run, f"Error matching job {job.id}: {str(e)}", "error")
                await db.commit()

        # Calculate average score
        if stats["total_jobs"] > 0:
            stats["average_score"] = round(total_score / stats["total_jobs"], 2)

        # Final commit
        await db.commit()

        # Log summary
        add_log(
            run,
            f"Matching completed: {stats['matched']} matched, {stats['rejected']} rejected, {stats['errors']} errors",
            "success"
        )
        add_log(run, f"Average match score: {stats['average_score']}/100", "info")
        await db.commit()

        print(f"\n📊 Matching Summary:")
        print(f"  Total jobs analyzed: {stats['total_jobs']}")
        print(f"  ✅ Matched (≥{min_score}): {stats['matched']}")
        print(f"  ❌ Rejected (<{min_score}): {stats['rejected']}")
        print(f"  ⚠️  Errors: {stats['errors']}")
        print(f"  📈 Average score: {stats['average_score']}/100")

    except Exception as e:
        add_log(run, f"Matching phase failed: {str(e)}", "error")
        await db.commit()
        print(f"❌ Matching failed: {str(e)}")
        raise

    return stats

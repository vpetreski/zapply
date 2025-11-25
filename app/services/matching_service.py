"""AI-powered job matching service using Claude."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models import Job, JobStatus, Run, UserProfile

logger = logging.getLogger(__name__)


def add_log(run: Run, message: str, level: str = "info") -> None:
    """Add a log entry to the run."""
    if run.logs is None:
        run.logs = []

    run.logs.append({
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "level": level,
        "message": message
    })

    # Mark the logs field as modified so SQLAlchemy detects the change
    attributes.flag_modified(run, "logs")


async def get_active_user_profile(db: AsyncSession) -> Optional[UserProfile]:
    """Get the first user profile (for MVP, we assume single user)."""
    result = await db.execute(select(UserProfile).limit(1))
    return result.scalar_one_or_none()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError)),
    reraise=True
)
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
            model=settings.anthropic_model,
            max_tokens=2000,
            # Use lower temperature (0.3) for more consistent scoring across jobs
            # Higher temp would vary scores too much for similar jobs
            # Lower temp ensures reliable, reproducible match scores
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Extract response
        logger.info(f"DEBUG: Claude message type: {type(message)}")
        logger.info(f"DEBUG: Claude message content length: {len(message.content)}")
        logger.info(f"DEBUG: Claude message content[0] type: {type(message.content[0])}")

        response_text = message.content[0].text
        logger.info(f"DEBUG: Raw Claude response (first 500 chars): {response_text[:500]}")
        logger.info(f"DEBUG: Response text length: {len(response_text)}")

        # Strip markdown code fences if present (```json ... ```)
        if response_text.strip().startswith("```"):
            # Remove opening ```json or ```
            lines = response_text.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove closing ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)
            logger.info(f"DEBUG: Stripped markdown fences, new length: {len(response_text)}")

        # Parse JSON response
        match_data = json.loads(response_text)

        # Validate required fields
        required_fields = ["score", "reasoning", "strengths", "concerns", "recommendation"]
        missing_fields = [field for field in required_fields if field not in match_data]
        if missing_fields:
            raise ValueError(f"Missing required fields in Claude response: {missing_fields}")

        score = float(match_data["score"])

        # Validate score range
        if not 0 <= score <= 100:
            raise ValueError(f"Invalid score: {score} (must be 0-100)")

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
        logger.info(f"Error matching job {job.id}: {str(e)}")
        # Return low score and error reasoning
        return (0.0, f"Error during matching: {str(e)}")


async def match_jobs(db: AsyncSession, run: Run, min_score: float = None) -> dict[str, int]:
    """
    Match all new jobs against user profile using Claude AI.

    Args:
        db: Database session
        run: Current run for logging
        min_score: Minimum score threshold (defaults to config value)

    Returns:
        Dictionary with statistics
    """
    # Use config default if not provided
    if min_score is None:
        min_score = settings.matching_min_score_threshold

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

        logger.info(f"\n🔍 Found {stats['total_jobs']} new jobs to match")
        add_log(run, f"Found {stats['total_jobs']} new jobs to match", "info")
        await db.commit()

        # Validate API key before initializing client
        if not settings.anthropic_api_key:
            logger.info("❌ ANTHROPIC_API_KEY not configured!")
            add_log(run, "ANTHROPIC_API_KEY not configured", "error")
            await db.commit()
            raise ValueError("Missing Anthropic API key - set ANTHROPIC_API_KEY in .env")

        # Validate API key format
        logger.info(f"🔑 API Key validated (length: {len(settings.anthropic_api_key)} characters)")

        # Initialize async Claude client
        logger.info(f"🤖 Initializing Claude AI client (model: {settings.anthropic_model})...")
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        add_log(run, "Initialized Claude AI client (async)", "info")
        await db.commit()
        logger.info("✅ Claude AI client initialized")

        # Match each job
        logger.info(f"\n🎯 Starting job matching (threshold: {min_score})...")
        total_score = 0.0

        for i, job in enumerate(jobs, 1):
            try:
                # Log progress at configured interval
                if i % settings.matching_log_interval == 0 or i == 1:
                    logger.info(f"\n[{i}/{stats['total_jobs']}] Matching: {job.title} @ {job.company}")
                    add_log(run, f"Matching job {i}/{stats['total_jobs']}: {job.title}", "info")
                    await db.commit()

                # Match job with Claude
                score, reasoning = await match_job_with_claude(job, user_profile, client)

                # Update job with match results
                job.match_score = score
                job.match_reasoning = reasoning
                job.matched_at = datetime.now(timezone.utc).replace(tzinfo=None)

                total_score += score

                # Update status based on score
                if score >= min_score:
                    job.status = JobStatus.MATCHED.value
                    stats["matched"] += 1
                    result_msg = f"✅ MATCHED ({score:.1f}/100): {job.title} at {job.company}"
                    logger.info(f"  {result_msg}")
                    add_log(run, result_msg, "success")
                else:
                    job.status = JobStatus.REJECTED.value
                    stats["rejected"] += 1
                    result_msg = f"❌ REJECTED ({score:.1f}/100): {job.title} at {job.company}"
                    logger.info(f"  {result_msg}")
                    add_log(run, result_msg, "info")

                # Commit after EVERY job for real-time UI updates
                await db.commit()

            except Exception as e:
                stats["errors"] += 1
                job.match_score = 0.0
                error_msg = str(e)
                job.match_reasoning = f"Error during matching: {error_msg}"
                job.status = JobStatus.REJECTED.value
                logger.info(f"  ❌ ERROR matching job {job.id} ({job.title})")
                logger.info(f"     Error: {error_msg}")

                # Log detailed error for debugging
                import traceback
                if settings.debug:
                    logger.info(f"     Traceback:\n{traceback.format_exc()}")

                add_log(run, f"Error matching job {job.id}: {error_msg}", "error")
                await db.commit()

        # Calculate average score
        if stats["total_jobs"] > 0:
            stats["average_score"] = round(total_score / stats["total_jobs"], 2)

        # Final commit
        await db.commit()

        # Log summary
        logger.info(f"\n✅ Matching completed!")
        logger.info(f"   Total: {stats['total_jobs']} jobs")
        logger.info(f"   ✅ Matched: {stats['matched']} jobs")
        logger.info(f"   ❌ Rejected: {stats['rejected']} jobs")
        logger.info(f"   ⚠️  Errors: {stats['errors']} jobs")
        logger.info(f"   📊 Average score: {stats['average_score']}/100")

        add_log(
            run,
            f"Matching completed: {stats['matched']} matched, {stats['rejected']} rejected, {stats['errors']} errors",
            "success"
        )
        add_log(run, f"Average match score: {stats['average_score']}/100", "info")
        await db.commit()

        logger.info(f"\n📊 Matching Summary:")
        logger.info(f"  Total jobs analyzed: {stats['total_jobs']}")
        logger.info(f"  ✅ Matched (≥{min_score}): {stats['matched']}")
        logger.info(f"  ❌ Rejected (<{min_score}): {stats['rejected']}")
        logger.info(f"  ⚠️  Errors: {stats['errors']}")
        logger.info(f"  📈 Average score: {stats['average_score']}/100")

    except Exception as e:
        add_log(run, f"Matching phase failed: {str(e)}", "error")
        await db.commit()
        logger.info(f"❌ Matching failed: {str(e)}")
        raise

    return stats

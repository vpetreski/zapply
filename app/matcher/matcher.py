"""AI-powered job matcher using Claude API."""

from pathlib import Path
from typing import Optional

import anthropic

from app.config import settings
from app.models import Job


class JobMatcher:
    """Match jobs against user profile using Claude AI."""

    def __init__(self) -> None:
        """Initialize job matcher."""
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.cv_text: Optional[str] = None

    async def load_cv(self) -> str:
        """
        Load CV text from PDF file.

        TODO: Implement PDF reading with pypdf
        """
        cv_path = Path(settings.user_cv_path)
        if not cv_path.exists():
            raise FileNotFoundError(f"CV not found at {cv_path}")

        # TODO: Read PDF and extract text
        # For now, return placeholder
        self.cv_text = "CV content placeholder"
        return self.cv_text

    async def match_job(self, job: Job) -> tuple[bool, str, float]:
        """
        Match a job against user profile using Claude AI.

        Args:
            job: Job object to match

        Returns:
            Tuple of (is_match, reasoning, confidence_score)

        TODO: Implement Claude API integration
        """
        if not self.cv_text:
            await self.load_cv()

        # TODO: Implement Claude API call for matching
        # Prompt should include:
        # - User's CV
        # - Job details
        # - Filtering criteria (remote, contractor-friendly, Colombia/Latam)
        # - Ask Claude to respond with MATCH/REJECT + reasoning + confidence

        # Placeholder response
        is_match = False
        reasoning = "Matching not yet implemented"
        confidence = 0.0

        return is_match, reasoning, confidence

    def _build_matching_prompt(self, job: Job) -> str:
        """
        Build prompt for Claude API to match job.

        Args:
            job: Job to match

        Returns:
            Formatted prompt string
        """
        return f"""
You are helping match a job posting against a candidate's profile.

CANDIDATE PROFILE:
{self.cv_text}

Additional Context:
- Name: {settings.user_name}
- Location: {settings.user_location} (Colombian and Serbian citizenship, NO US work permit)
- Rate: {settings.user_rate}
- Work Style: 100% remote contractor

JOB POSTING:
Title: {job.title}
Company: {job.company}
Location: {job.location or "Not specified"}
URL: {job.url}

Description:
{job.description}

Requirements:
{job.requirements or "Not specified"}

MATCHING CRITERIA:
MUST HAVE (auto-match if all present):
- Truly remote position (location doesn't matter)
- Accepts international contractors OR specifically hiring in Latam/Colombia
- Contract or full-time compatible with contractor setup

MUST REJECT (auto-reject if any present):
- Requires US work authorization
- Requires physical presence (hybrid, office-based)
- Location-specific requirements (must be in specific country/city)

INSTRUCTIONS:
1. Analyze if the job meets the MUST HAVE criteria
2. Check if any MUST REJECT criteria apply
3. Evaluate candidate's fit for the role based on skills and experience
4. Provide your assessment in this exact format:

DECISION: [MATCH or REJECT]
CONFIDENCE: [0.0 to 1.0]
REASONING: [2-3 sentence explanation focusing on: remote/contractor compatibility, location requirements, and skill match]

Be strict about filtering - it's better to reject a questionable match than apply to incompatible positions.
"""

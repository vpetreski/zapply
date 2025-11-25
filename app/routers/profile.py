"""User profile management endpoints."""

import base64
from datetime import datetime
from typing import Optional

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import UserProfile

router = APIRouter()


class ProfileResponse(BaseModel):
    """User profile response."""

    id: int
    name: str
    email: str
    location: str
    rate: str
    cv_path: Optional[str]
    cv_text: Optional[str]
    skills: Optional[list[str]]
    preferences: Optional[dict]
    created_at: datetime
    updated_at: datetime


class GenerateProfileRequest(BaseModel):
    """Request to generate profile using Claude AI."""

    cv_text: str
    custom_prompt: str
    name: str
    email: str
    location: str
    rate: str


class GenerateProfileResponse(BaseModel):
    """Generated profile response from Claude."""

    cv_text: str
    skills: list[str]
    preferences: dict
    generated_summary: str


class UpdateProfileRequest(BaseModel):
    """Request to update profile."""

    name: str
    email: str
    location: str
    rate: str
    cv_text: str
    skills: list[str]
    preferences: dict


@router.get("", response_model=Optional[ProfileResponse])
async def get_profile(db: AsyncSession = Depends(get_db)) -> Optional[ProfileResponse]:
    """
    Get the current user profile.

    For MVP, we assume single user, so we return the first profile.
    """
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()

    if not profile:
        return None

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        email=profile.email,
        location=profile.location,
        rate=profile.rate,
        cv_path=profile.cv_path,
        cv_text=profile.cv_text,
        skills=profile.skills,
        preferences=profile.preferences,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post("/generate", response_model=GenerateProfileResponse)
async def generate_profile(
    request: GenerateProfileRequest,
    db: AsyncSession = Depends(get_db)
) -> GenerateProfileResponse:
    """
    Generate optimized user profile using Claude AI.

    Takes CV text and custom instructions, uses Claude to:
    1. Extract and structure CV information
    2. Generate comprehensive skills list
    3. Create preferences based on user input
    4. Produce optimized profile text for matching
    """
    # Build prompt for Claude
    prompt = f"""You are an expert career advisor helping to create an optimized job seeker profile.

**INPUT CV:**
{request.cv_text}

**USER INSTRUCTIONS:**
{request.custom_prompt}

**USER DETAILS:**
- Name: {request.name}
- Email: {request.email}
- Location: {request.location}
- Rate: {request.rate}

**YOUR TASK:**
Analyze the CV and user instructions to create an optimized profile for AI-powered job matching. Generate:

1. **Comprehensive Skills List**: Extract all technical and business skills from CV
2. **Job Preferences**: Determine preferred industries, company sizes, work arrangements based on CV and instructions
3. **Optimized Profile Text**: Create a detailed, well-structured profile that highlights key experience and strengths

**IMPORTANT CONSTRAINTS** (from user instructions):
- Location: {request.location} (Colombian and Serbian citizenship, NO US work authorization)
- Work Type: 100% remote contractor only
- Must reject jobs requiring US work authorization
- Must reject jobs requiring physical presence or hybrid work
- Focus on roles matching experience level and rate expectations

Respond in this exact JSON format:
{{
  "cv_text": "<optimized profile text - comprehensive, well-structured, highlights key strengths>",
  "skills": ["skill1", "skill2", ...],
  "preferences": {{
    "rate_monthly": {request.rate.replace('$', '').replace(',', '').replace('/month', '').strip()},
    "remote_only": true,
    "contractor_only": true,
    "location_restrictions": "NO US work authorization - must accept international contractors or hire in Latam/Colombia",
    "preferred_industries": ["Industry1", "Industry2", ...],
    "preferred_roles": ["Role1", "Role2", ...],
    "willing_to_relocate": false
  }},
  "generated_summary": "<brief 2-3 sentence summary of key changes/highlights>"
}}"""

    try:
        # Call Claude API
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        # Parse response
        import json
        response_text = message.content[0].text
        profile_data = json.loads(response_text)

        return GenerateProfileResponse(
            cv_text=profile_data["cv_text"],
            skills=profile_data["skills"],
            preferences=profile_data["preferences"],
            generated_summary=profile_data["generated_summary"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate profile: {str(e)}"
        )


@router.post("/upload-cv")
async def upload_cv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Upload CV file (PDF) and extract text.

    Returns extracted text to be used in profile generation.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    try:
        # Read PDF content
        content = await file.read()

        # TODO: Extract text from PDF using pypdf or similar
        # For now, return a placeholder
        # In production, use: from pypdf import PdfReader
        extracted_text = f"[PDF content from {file.filename}]\n\nTODO: Implement PDF text extraction"

        return {
            "success": True,
            "filename": file.filename,
            "text": extracted_text,
            "size": len(content)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}"
        )


@router.put("", response_model=ProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    """
    Update or create user profile.

    If profile exists, updates it. If not, creates new one.
    """
    # Check if profile exists
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()

    if profile:
        # Update existing profile
        profile.name = request.name
        profile.email = request.email
        profile.location = request.location
        profile.rate = request.rate
        profile.cv_text = request.cv_text
        profile.skills = request.skills
        profile.preferences = request.preferences
        profile.updated_at = datetime.utcnow()
    else:
        # Create new profile
        profile = UserProfile(
            name=request.name,
            email=request.email,
            location=request.location,
            rate=request.rate,
            cv_path="",  # No longer using file path
            cv_text=request.cv_text,
            skills=request.skills,
            preferences=request.preferences,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        email=profile.email,
        location=profile.location,
        rate=profile.rate,
        cv_path=profile.cv_path,
        cv_text=profile.cv_text,
        skills=profile.skills,
        preferences=profile.preferences,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.delete("")
async def delete_profile(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Delete the user profile.

    WARNING: This will remove all profile data!
    """
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    await db.delete(profile)
    await db.commit()

    return {
        "success": True,
        "message": "Profile deleted successfully"
    }

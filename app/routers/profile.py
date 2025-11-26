"""User profile management endpoints."""

import base64
from datetime import datetime, timezone
from typing import Annotated, Optional

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import UserProfile
from app.routers.auth import User, get_current_user

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


class ProfileResponse(BaseModel):
    """User profile response."""

    id: int
    name: str
    email: str
    phone: Optional[str]
    location: str
    rate: str
    cv_filename: Optional[str]
    cv_text: Optional[str]
    custom_instructions: Optional[str]
    skills: Optional[list[str]]
    preferences: Optional[dict]
    ai_generated_summary: Optional[str]
    created_at: datetime
    updated_at: datetime


class ProfileExistsResponse(BaseModel):
    """Response indicating if a profile exists."""

    exists: bool


class GenerateProfileRequest(BaseModel):
    """Request to generate profile using Claude AI."""

    cv_text: str
    custom_instructions: str
    name: str
    email: str
    phone: Optional[str]
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
    phone: Optional[str]
    location: str
    rate: str
    cv_filename: Optional[str]
    cv_data_base64: Optional[str]  # Base64 encoded PDF file
    cv_text: str
    custom_instructions: Optional[str]
    skills: list[str]
    preferences: dict
    ai_generated_summary: Optional[str]


@router.get("/exists", response_model=ProfileExistsResponse)
async def check_profile_exists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> ProfileExistsResponse:
    """
    Check if a user profile exists.

    Returns a simple boolean indicating profile existence.
    Fast endpoint for UI to check profile status.
    """
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()
    return ProfileExistsResponse(exists=profile is not None)


@router.get("", response_model=Optional[ProfileResponse])
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> Optional[ProfileResponse]:
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
        phone=profile.phone,
        location=profile.location,
        rate=profile.rate,
        cv_filename=profile.cv_filename,
        cv_text=profile.cv_text,
        custom_instructions=profile.custom_instructions,
        skills=profile.skills,
        preferences=profile.preferences,
        ai_generated_summary=profile.ai_generated_summary,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post("/generate", response_model=GenerateProfileResponse)
@limiter.limit("10/minute")
async def generate_profile(
    request: Request,
    profile_request: GenerateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
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
{profile_request.cv_text}

**CUSTOM INSTRUCTIONS FROM USER:**
{profile_request.custom_instructions}

**USER DETAILS:**
- Name: {profile_request.name}
- Email: {profile_request.email}
- Phone: {profile_request.phone or 'Not provided'}
- Location: {profile_request.location}
- Rate: {profile_request.rate}

**YOUR TASK:**
Analyze the CV and custom instructions to create an optimized profile for AI-powered job matching.

The custom instructions contain ALL user preferences, requirements, and constraints. Pay close attention to them.

Generate:

1. **Comprehensive Skills List**: Extract all technical and business skills from CV
2. **Job Preferences**: Extract and structure preferences from custom instructions (work type, location requirements, rate expectations, etc.)
3. **Optimized Profile Text**: Create a detailed, well-structured profile that highlights key experience and strengths from the CV

Respond in this exact JSON format:
{{
  "cv_text": "<optimized profile text - comprehensive, well-structured, highlights key strengths>",
  "skills": ["skill1", "skill2", ...],
  "preferences": {{
    "rate": "{profile_request.rate}",
    "location": "{profile_request.location}",
    "key_requirements": ["requirement1", "requirement2", ...],
    "preferred_industries": ["Industry1", "Industry2", ...],
    "preferred_roles": ["Role1", "Role2", ...]
  }},
  "generated_summary": "<brief 2-3 sentence summary of the profile and key highlights>"
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
        import re
        response_text = message.content[0].text

        # Extract JSON from response (may be wrapped in markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON if no code blocks
            json_str = response_text.strip()

        try:
            profile_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Log the actual response for debugging
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse Claude response as JSON: {str(e)}. Response: {response_text[:500]}"
            )

        return GenerateProfileResponse(
            cv_text=profile_data["cv_text"],
            skills=profile_data["skills"],
            preferences=profile_data["preferences"],
            generated_summary=profile_data["generated_summary"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate profile: {str(e)}"
        )


@router.post("/upload-cv")
async def upload_cv(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> dict:
    """
    Upload CV file (PDF) and extract text.

    Returns extracted text and base64 encoded file to be used in profile generation.
    """
    if not file.filename or not file.filename.endswith('.pdf'):
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

        # Encode as base64 for transmission
        file_base64 = base64.b64encode(content).decode('utf-8')

        return {
            "success": True,
            "filename": file.filename,
            "text": extracted_text,
            "size": len(content),
            "file_data": file_base64
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}"
        )


@router.put("", response_model=ProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    """
    Update or create user profile.

    If profile exists, updates it. If not, creates new one.
    """
    # Check if profile exists
    result = await db.execute(select(UserProfile).limit(1))
    profile = result.scalar_one_or_none()

    # Decode CV data if provided
    cv_data = None
    if request.cv_data_base64:
        try:
            cv_data = base64.b64decode(request.cv_data_base64)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid CV data encoding: {str(e)}"
            )

    if profile:
        # Update existing profile
        profile.name = request.name
        profile.email = request.email
        profile.phone = request.phone
        profile.location = request.location
        profile.rate = request.rate
        if request.cv_filename:
            profile.cv_filename = request.cv_filename
        if cv_data:
            profile.cv_data = cv_data
        profile.cv_text = request.cv_text
        profile.custom_instructions = request.custom_instructions
        profile.skills = request.skills
        profile.preferences = request.preferences
        profile.ai_generated_summary = request.ai_generated_summary
        profile.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        # Create new profile
        profile = UserProfile(
            name=request.name,
            email=request.email,
            phone=request.phone,
            location=request.location,
            rate=request.rate,
            cv_filename=request.cv_filename,
            cv_data=cv_data,
            cv_text=request.cv_text,
            custom_instructions=request.custom_instructions,
            skills=request.skills,
            preferences=request.preferences,
            ai_generated_summary=request.ai_generated_summary,
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)

    return ProfileResponse(
        id=profile.id,
        name=profile.name,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        rate=profile.rate,
        cv_filename=profile.cv_filename,
        cv_text=profile.cv_text,
        custom_instructions=profile.custom_instructions,
        skills=profile.skills,
        preferences=profile.preferences,
        ai_generated_summary=profile.ai_generated_summary,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.delete("")
async def delete_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
) -> dict:
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

"""Interview management endpoints."""

import re
from io import BytesIO
from pathlib import Path
from typing import Annotated, Optional

import bleach
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Interview, InterviewStatus, utc_now
from app.routers.auth import User, get_current_user
from app.schemas import (
    InterviewCreate,
    InterviewListResponse,
    InterviewResponse,
    InterviewUpdate,
)
from app.utils import log_to_console

router = APIRouter()

# Valid status values for interviews
VALID_STATUSES = frozenset(s.value for s in InterviewStatus)

# HTML sanitization settings - allow only safe tags from TipTap editor
ALLOWED_TAGS = ["p", "h2", "h3", "ul", "ol", "li", "a", "strong", "br"]
ALLOWED_ATTRS = {"a": ["href", "target", "rel"]}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]  # Prevent javascript: URLs


def sanitize_html(html: Optional[str]) -> Optional[str]:
    """Sanitize HTML content to prevent XSS attacks."""
    if not html:
        return html
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def sanitize_filename(filename: Optional[str], default: str = "Resume.pdf") -> str:
    """Sanitize filename to prevent path traversal and invalid characters."""
    if not filename:
        return default
    # Get just the filename, no path components
    safe_name = Path(filename).name
    # Remove any non-alphanumeric chars except . - _
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", safe_name)
    # Limit length and ensure it has .pdf extension
    safe_name = safe_name[:250]
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    return safe_name or "resume.pdf"


def interview_to_response(interview: Interview) -> InterviewResponse:
    """Convert Interview model to response schema with has_cv computed."""
    return InterviewResponse(
        id=interview.id,
        title=interview.title,
        description=interview.description,
        status=interview.status,
        cv_filename=interview.cv_filename,
        has_cv=interview.cv_data is not None,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
    )


@router.get("", response_model=InterviewListResponse)
@router.get("/", response_model=InterviewListResponse)
async def list_interviews(
    current_user: Annotated[User, Depends(get_current_user)],
    status: Optional[str] = Query(None, description="Filter by status (active, closed)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> InterviewListResponse:
    """List interviews ordered by updated_at desc with optional status filter."""
    log_to_console(f"📡 API: GET /api/interviews - List interviews (page={page}, status={status})")

    # Build query
    query = select(Interview)

    # Filter by status (with validation)
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {list(VALID_STATUSES)}")
        query = query.filter(Interview.status == status)

    # Get total count (more efficient than subquery)
    count_query = select(func.count(Interview.id))
    if status:
        count_query = count_query.filter(Interview.status == status)
    total = (await db.execute(count_query)).scalar() or 0

    # Order by updated_at descending (most recently updated first)
    query = query.order_by(Interview.updated_at.desc())

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    interviews = result.scalars().all()

    log_to_console(f"✅ Returned {len(interviews)} interviews (total: {total})")

    return InterviewListResponse(
        interviews=[interview_to_response(i) for i in interviews],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> InterviewResponse:
    """Get a specific interview by ID."""
    log_to_console(f"📡 API: GET /api/interviews/{interview_id} - Get interview details")

    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalar_one_or_none()

    if not interview:
        log_to_console(f"❌ Interview {interview_id} not found")
        raise HTTPException(status_code=404, detail="Interview not found")

    log_to_console(f"✅ Returned interview: {interview.title}")
    return interview_to_response(interview)


@router.post("", response_model=InterviewResponse, status_code=201)
@router.post("/", response_model=InterviewResponse, status_code=201)
async def create_interview(
    interview_data: InterviewCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> InterviewResponse:
    """Create a new interview."""
    log_to_console(f"📡 API: POST /api/interviews - Create interview: {interview_data.title}")

    interview = Interview(
        title=interview_data.title,
        description=sanitize_html(interview_data.description),
        status=InterviewStatus.ACTIVE.value,
    )

    db.add(interview)
    await db.commit()
    await db.refresh(interview)

    log_to_console(f"✅ Created interview {interview.id}: {interview.title}")
    return interview_to_response(interview)


@router.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview(
    interview_id: int,
    update_data: InterviewUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> InterviewResponse:
    """Update an interview."""
    log_to_console(f"📡 API: PUT /api/interviews/{interview_id} - Update interview")

    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalar_one_or_none()

    if not interview:
        log_to_console(f"❌ Interview {interview_id} not found")
        raise HTTPException(status_code=404, detail="Interview not found")

    # Update fields if provided
    if update_data.title is not None:
        interview.title = update_data.title
    if update_data.description is not None:
        interview.description = sanitize_html(update_data.description)
    if update_data.status is not None:
        if update_data.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {list(VALID_STATUSES)}")
        interview.status = update_data.status

    await db.commit()
    await db.refresh(interview)

    log_to_console(f"✅ Updated interview {interview_id}: {interview.title}")
    return interview_to_response(interview)


@router.delete("/{interview_id}")
async def delete_interview(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete an interview."""
    log_to_console(f"📡 API: DELETE /api/interviews/{interview_id} - Delete interview")

    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalar_one_or_none()

    if not interview:
        log_to_console(f"❌ Interview {interview_id} not found")
        raise HTTPException(status_code=404, detail="Interview not found")

    await db.delete(interview)
    await db.commit()

    log_to_console(f"✅ Interview {interview_id} deleted successfully")
    return {"message": f"Interview {interview_id} deleted successfully"}


# =============================================================================
# CV Endpoints
# =============================================================================


@router.get("/{interview_id}/cv")
async def download_cv(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Download interview CV as PDF."""
    log_to_console(f"📡 API: GET /api/interviews/{interview_id}/cv - Download CV")

    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalar_one_or_none()

    if not interview:
        log_to_console(f"❌ Interview {interview_id} not found")
        raise HTTPException(status_code=404, detail="Interview not found")

    if not interview.cv_data:
        log_to_console(f"❌ No CV attached to interview {interview_id}")
        raise HTTPException(status_code=404, detail="No CV attached to this interview")

    # Sanitize filename again to prevent header injection from legacy data
    download_filename = sanitize_filename(interview.cv_filename)
    log_to_console(f"✅ Downloading CV for interview {interview_id}: {download_filename}")
    return StreamingResponse(
        BytesIO(interview.cv_data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"'
        },
    )


# PDF magic bytes signature
PDF_MAGIC_BYTES = b"%PDF-"
MAX_CV_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/{interview_id}/cv")
async def upload_cv(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Upload CV PDF for an interview."""
    log_to_console(f"📡 API: POST /api/interviews/{interview_id}/cv - Upload CV")

    # Validate content-type header (basic check, validated further with magic bytes)
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check file size before reading full content (if size is available)
    if file.size is not None and file.size > MAX_CV_SIZE:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")

    # Read file content
    cv_data = await file.read()

    # Validate file size after reading (in case size wasn't available beforehand)
    if len(cv_data) > MAX_CV_SIZE:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")

    # Validate PDF magic bytes to prevent content-type spoofing
    if not cv_data.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(status_code=400, detail="Invalid PDF file")

    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalar_one_or_none()

    if not interview:
        log_to_console(f"❌ Interview {interview_id} not found")
        raise HTTPException(status_code=404, detail="Interview not found")

    # Update interview with explicit updated_at (SQLAlchemy onupdate may not fire for binary)
    safe_filename = sanitize_filename(file.filename)
    interview.cv_data = cv_data
    interview.cv_filename = safe_filename
    interview.updated_at = utc_now()

    await db.commit()

    log_to_console(f"✅ CV uploaded for interview {interview_id}: {safe_filename}")
    return {"message": "CV uploaded successfully", "filename": safe_filename}


@router.delete("/{interview_id}/cv")
async def remove_cv(
    interview_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Remove CV from an interview."""
    log_to_console(f"📡 API: DELETE /api/interviews/{interview_id}/cv - Remove CV")

    result = await db.execute(select(Interview).filter(Interview.id == interview_id))
    interview = result.scalar_one_or_none()

    if not interview:
        log_to_console(f"❌ Interview {interview_id} not found")
        raise HTTPException(status_code=404, detail="Interview not found")

    if not interview.cv_data:
        log_to_console(f"❌ No CV attached to interview {interview_id}")
        raise HTTPException(status_code=404, detail="No CV attached to this interview")

    # Update with explicit updated_at (SQLAlchemy onupdate may not fire for binary)
    interview.cv_data = None
    interview.cv_filename = None
    interview.updated_at = utc_now()

    await db.commit()

    log_to_console(f"✅ CV removed from interview {interview_id}")
    return {"message": "CV removed successfully"}

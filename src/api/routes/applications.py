"""
Applications routes — submitted apps, queue, interview pipeline.
Dashboard Sections ③④⑤⑥
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.models import Application, JobStatus, InterviewStage, ApplicationSource, Tier

router = APIRouter()


@router.get("/")
async def list_applications(
    status: Optional[str] = None,
    stage: Optional[str] = None,
    source_type: Optional[str] = None,  # auto or manual
    company: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all applications with filters."""
    query = select(Application).order_by(desc(Application.created_at))

    if status:
        query = query.where(Application.status == status)
    if stage:
        query = query.where(Application.interview_stage == stage)
    if source_type:
        query = query.where(Application.application_source == source_type)
    if company:
        query = query.where(Application.company.ilike(f"%{company}%"))
    if search:
        query = query.where(
            Application.role.ilike(f"%{search}%") |
            Application.company.ilike(f"%{search}%")
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    apps = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "applications": [_serialize_app(a) for a in apps],
    }


@router.get("/queue")
async def get_queue(db: AsyncSession = Depends(get_db)):
    """Get the current application queue (Section ④)."""
    statuses = [
        JobStatus.queued, JobStatus.optimizing,
        JobStatus.applying, JobStatus.needs_review,
    ]
    result = await db.execute(
        select(Application)
        .where(Application.status.in_([s.value for s in statuses]))
        .order_by(Application.created_at)
    )
    apps = result.scalars().all()

    # Group by status
    grouped = {}
    for app in apps:
        status = app.status.value if hasattr(app.status, 'value') else str(app.status)
        if status not in grouped:
            grouped[status] = []
        grouped[status].append(_serialize_app(app))

    return {"queue": grouped, "total": len(apps)}


@router.get("/pipeline")
async def get_interview_pipeline(db: AsyncSession = Depends(get_db)):
    """Get the interview pipeline Kanban (Section ⑤)."""
    result = await db.execute(
        select(Application)
        .where(Application.status == JobStatus.submitted.value)
        .order_by(Application.applied_date)
    )
    apps = result.scalars().all()

    # Group by interview stage
    pipeline = {}
    for stage in InterviewStage:
        pipeline[stage.value] = []

    for app in apps:
        stage = app.interview_stage.value if hasattr(app.interview_stage, 'value') else str(app.interview_stage)
        if stage in pipeline:
            pipeline[stage].append(_serialize_app(app))

    return {"pipeline": pipeline}


@router.put("/{app_id}/stage")
async def update_interview_stage(
    app_id: str,
    stage: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    """Update an application's interview stage (drag-drop on Kanban)."""
    result = await db.execute(
        select(Application).where(Application.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        return {"error": "Application not found"}, 404

    app.interview_stage = stage
    app.last_updated = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "updated", "stage": stage}


@router.post("/manual")
async def add_manual_application(
    company: str = Body(...),
    role: str = Body(...),
    apply_url: str = Body(...),
    applied_date: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
):
    """Add a manually tracked application (Section ⑥)."""
    app = Application(
        job_id="00000000-0000-0000-0000-000000000000",  # No linked job
        company=company,
        role=role,
        source="manual",
        apply_url=apply_url,
        application_source=ApplicationSource.manual,
        status=JobStatus.submitted,
        interview_stage=InterviewStage.applied,
        applied_date=datetime.fromisoformat(applied_date) if applied_date else datetime.now(timezone.utc),
    )
    db.add(app)
    await db.commit()
    return {"status": "created", "id": app.id}


def _serialize_app(app: Application) -> dict:
    return {
        "id": app.id,
        "company": app.company,
        "role": app.role,
        "source": app.source,
        "apply_url": app.apply_url,
        "match_score": app.match_score,
        "ats_score": app.ats_score,
        "tier": app.tier.value if hasattr(app.tier, 'value') else str(app.tier) if app.tier else None,
        "status": app.status.value if hasattr(app.status, 'value') else str(app.status),
        "interview_stage": app.interview_stage.value if hasattr(app.interview_stage, 'value') else str(app.interview_stage),
        "resume_url": app.resume_url,
        "screenshot_url": app.screenshot_url,
        "cover_letter": app.cover_letter[:200] + "..." if app.cover_letter and len(app.cover_letter) > 200 else app.cover_letter,
        "confirmation_number": app.confirmation_number,
        "error_log": app.error_log,
        "applied_date": app.applied_date.isoformat() if app.applied_date else None,
        "last_updated": app.last_updated.isoformat() if app.last_updated else None,
        "application_source": app.application_source.value if hasattr(app.application_source, 'value') else str(app.application_source),
    }

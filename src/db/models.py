"""
SQLAlchemy async models for the AutoApply Agent.
All metadata lives here — files go to B2 as flat blobs.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime,
    Enum, Index, UniqueConstraint, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Use String(36) for UUID — works with both SQLite and PostgreSQL
_UUID = String(36)


class Base(DeclarativeBase):
    pass


# ── Enums ───────────────────────────────────────────────

class JobStatus(str, PyEnum):
    scraped = "scraped"
    visa_blocked = "visa_blocked"
    visa_unclear = "visa_unclear"
    gate_blocked = "gate_blocked"
    scoring = "scoring"
    below_threshold = "below_threshold"
    queued = "queued"
    optimizing = "optimizing"
    optimization_failed = "optimization_failed"
    applying = "applying"
    submitted = "submitted"
    failed = "failed"
    needs_review = "needs_review"


class VisaStatus(str, PyEnum):
    ok = "ok"
    blocked = "blocked"
    unclear = "unclear"
    unchecked = "unchecked"


class Tier(str, PyEnum):
    standard = "standard"
    top_tier = "top_tier"


class InterviewStage(str, PyEnum):
    applied = "applied"
    assessment = "assessment"
    phone_screen = "phone_screen"
    technical = "technical"
    final_round = "final_round"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class ApplicationSource(str, PyEnum):
    auto = "auto"           # Applied by the agent
    manual = "manual"       # Tracked manually by user


# ── Job Listing (scraped, pre-application) ──────────────

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        _UUID, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(200), index=True)
    company_normalized: Mapped[str] = mapped_column(String(200), index=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source: Mapped[str] = mapped_column(String(50))            # adzuna, jsearch, remoteok, greenhouse, lever...
    source_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    apply_url: Mapped[str] = mapped_column(Text)
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    posted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ats_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)  # workday, greenhouse, lever...
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    visa_status: Mapped[str] = mapped_column(
        Enum(VisaStatus), default=VisaStatus.unchecked
    )
    visa_reason: Mapped[str | None] = mapped_column(Text, nullable=True)    # Why blocked/unclear
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # Why current status
    tier: Mapped[str | None] = mapped_column(Enum(Tier), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(JobStatus), default=JobStatus.scraped, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_jobs_posted_date", "posted_date"),
        Index("ix_jobs_status_score", "status", "match_score"),
    )


# ── Application (after submission) ──────────────────────

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(
        _UUID, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str] = mapped_column(
        _UUID, index=True
    )
    # Denormalized for dashboard speed
    company: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(50))
    apply_url: Mapped[str] = mapped_column(Text)
    jd_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ATS & Optimization
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ats_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tier: Mapped[str] = mapped_column(Enum(Tier), default=Tier.standard)
    optimization_iterations: Mapped[int] = mapped_column(Integer, default=0)

    # Files (stored in B2, URLs here)
    resume_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    resume_filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    screenshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status tracking
    application_source: Mapped[str] = mapped_column(
        Enum(ApplicationSource), default=ApplicationSource.auto
    )
    status: Mapped[str] = mapped_column(
        Enum(JobStatus), default=JobStatus.queued, index=True
    )
    interview_stage: Mapped[str] = mapped_column(
        Enum(InterviewStage), default=InterviewStage.applied
    )
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dates
    applied_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_app_company_status", "company", "status"),
        Index("ix_app_interview", "interview_stage"),
    )


# ── Cost Tracking ───────────────────────────────────────

class CostLog(Base):
    __tablename__ = "cost_logs"

    id: Mapped[str] = mapped_column(
        _UUID, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    category: Mapped[str] = mapped_column(String(50))        # llm_haiku, llm_sonnet, captcha, proxy, infra
    description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    amount_usd: Mapped[float] = mapped_column(Float)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_id: Mapped[str | None] = mapped_column(_UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_cost_date", "created_at"),
        Index("ix_cost_category", "category"),
    )


# ── Email Tracking (Phase 2) ───────────────────────────

class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[str] = mapped_column(
        _UUID, primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    gmail_id: Mapped[str] = mapped_column(String(100), unique=True)
    subject: Mapped[str] = mapped_column(String(500))
    sender: Mapped[str] = mapped_column(String(300))
    received_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # interview, rejection, assessment, offer, follow_up, irrelevant
    application_id: Mapped[str | None] = mapped_column(_UUID, nullable=True)
    extracted_data: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

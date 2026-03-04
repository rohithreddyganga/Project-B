"""
Resume routes — ATS scoring studio, optimization on-demand.
Dashboard Section ②: Resume Optimization Studio
"""
from typing import Optional

from fastapi import APIRouter, Depends, Body, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.scorer.jd_analyzer import analyze_jd
from src.scorer.ats_scorer import score_ats
from src.optimizer.latex_optimizer import optimize_resume
from src.optimizer.latex_compiler import compile_latex, extract_pdf_text
from src.db.models import Job, Tier

router = APIRouter()


@router.post("/score")
async def score_resume(
    resume_text: str = Body(..., description="Resume text content"),
    jd_text: str = Body(..., description="Job description text"),
):
    """Score a resume against a JD. Returns score + missing keywords."""
    # Analyze JD
    jd_analysis = await analyze_jd(jd_text)

    # Score
    score = await score_ats(
        resume_text=resume_text,
        jd_text=jd_text,
        jd_analysis=jd_analysis,
        use_llm=True,
    )

    # Find missing keywords
    resume_lower = resume_text.lower()
    missing = [
        kw for kw in jd_analysis.all_keywords
        if kw.lower() not in resume_lower
    ]
    present = [
        kw for kw in jd_analysis.all_keywords
        if kw.lower() in resume_lower
    ]

    return {
        "ats_score": score,
        "missing_keywords": missing,
        "present_keywords": present,
        "required_skills": jd_analysis.required_skills,
        "preferred_skills": jd_analysis.preferred_skills,
        "tools": jd_analysis.tools_and_technologies,
        "experience_years": jd_analysis.experience_years,
    }


@router.post("/optimize")
async def optimize_resume_endpoint(
    latex_source: str = Body(..., description="LaTeX resume source"),
    jd_text: str = Body(..., description="Job description text"),
    company: str = Body("Unknown", description="Company name"),
    title: str = Body("Unknown", description="Job title"),
    tier: str = Body("standard", description="standard or top_tier"),
):
    """Optimize a LaTeX resume for a specific JD. Returns optimized source + score."""
    # Create a temporary Job object
    job = Job(
        title=title,
        company=company,
        company_normalized=company.lower(),
        jd_text=jd_text,
        source="manual",
        apply_url="",
        fingerprint="manual",
        tier=Tier.top_tier if tier == "top_tier" else Tier.standard,
    )

    # Run optimization
    result = await optimize_resume(latex_source, job)

    return {
        "success": result.success,
        "ats_score": result.ats_score,
        "iterations": result.iterations,
        "needs_review": result.needs_review,
        "optimized_latex": result.tex_source,
        "error": result.error,
    }


@router.post("/compile")
async def compile_latex_endpoint(
    latex_source: str = Body(..., description="LaTeX source to compile"),
):
    """Compile LaTeX to PDF and return text extraction."""
    pdf_path, error = await compile_latex(latex_source)
    if error:
        return {"success": False, "error": error}

    text = extract_pdf_text(pdf_path) if pdf_path else ""
    return {
        "success": True,
        "pdf_path": pdf_path,
        "extracted_text": text[:3000],
    }

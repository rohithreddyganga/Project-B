"""
Pipeline Orchestrator — The main brain that runs the 11-stage pipeline.
Called by the scheduler on a daily cycle, or triggered manually from dashboard.
"""
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from src.db.models import Job, Application, ApplicationStatus, VisaStatus, JobTier, CostLog
from src.db.database import async_session
from src.scraper.orchestrator import run_all_scrapers
from src.filters.visa_filter import check_visa_eligibility
from src.filters.gate_checker import check_all_gates
from src.filters.freshness import sort_jobs_by_priority, compute_priority_score
from src.scorer.match_scorer import quick_match_score
from src.scorer.jd_analyzer import analyze_jd
from src.scorer.ats_scorer import score_ats
from src.scorer.tier_classifier import classify_tier, get_tier_config
from src.optimizer.latex_optimizer import optimize_resume, generate_cover_letter, compile_to_pdf
from src.archive.manager import save_resume, save_tex_source
from src.notifications.telegram import send_daily_report, send_alert
from src.config import get_config
import logging

logger = logging.getLogger(__name__)


class PipelineStats:
    """Track daily pipeline statistics."""
    def __init__(self):
        self.scraped = 0
        self.visa_ok = 0
        self.visa_blocked = 0
        self.visa_unclear = 0
        self.gates_passed = 0
        self.gates_failed = 0
        self.scored = 0
        self.optimized = 0
        self.submitted = 0
        self.failed = 0
        self.needs_review = 0
        self.skipped = 0
        self.cost_today = 0.0


async def run_daily_pipeline():
    """
    Main daily pipeline: Scrape → Filter → Score → Optimize → Queue for Apply.
    Note: Actual application (form filling) is handled by the applicant engine
    on a separate schedule with human-paced timing.
    """
    stats = PipelineStats()
    logger.info("=" * 60)
    logger.info("🚀 Starting daily pipeline")
    logger.info("=" * 60)
    
    async with async_session() as session:
        try:
            # ── Stage 2: Scrape ──────────────────────────
            logger.info("📡 Stage 2: Scraping jobs...")
            new_jobs = await run_all_scrapers(session)
            stats.scraped = len(new_jobs)
            await session.commit()
            logger.info(f"  → {stats.scraped} new jobs found")
            
            # ── Stage 3: Visa Filter ─────────────────────
            logger.info("🛂 Stage 3: Visa filtering...")
            unprocessed = await session.execute(
                select(Job).where(
                    Job.processed == False,
                    Job.visa_status == VisaStatus.UNCLEAR,
                ).order_by(Job.posted_date.desc())
            )
            jobs_to_filter = unprocessed.scalars().all()
            
            for job in jobs_to_filter:
                if not job.description:
                    continue
                status, signals = await check_visa_eligibility(job.description)
                job.visa_status = status
                job.visa_signals = signals
                
                if status == VisaStatus.BLOCKED:
                    stats.visa_blocked += 1
                elif status in (VisaStatus.OK, VisaStatus.BOOST):
                    stats.visa_ok += 1
                else:
                    stats.visa_unclear += 1
            
            await session.commit()
            logger.info(f"  → OK: {stats.visa_ok}, Blocked: {stats.visa_blocked}, Unclear: {stats.visa_unclear}")
            
            # ── Stage 4 + 5: Gate Check + Match Score ────
            logger.info("🚦 Stage 4-5: Gates + Match scoring...")
            eligible_jobs = await session.execute(
                select(Job).where(
                    Job.processed == False,
                    Job.visa_status.in_([VisaStatus.OK, VisaStatus.BOOST, VisaStatus.UNCLEAR]),
                ).order_by(Job.posted_date.desc())
            )
            candidates = eligible_jobs.scalars().all()
            
            min_match = get_config("gates.min_match_score", 80)
            qualified = []
            
            for job in candidates:
                # Gate check
                passed, reason = await check_all_gates(session, job)
                if not passed:
                    stats.gates_failed += 1
                    job.processed = True
                    continue
                stats.gates_passed += 1
                
                # Quick match score
                score, details = quick_match_score(
                    job.title, job.description or "", job.location or ""
                )
                job.match_score = score
                job.processed = True
                
                if score >= min_match:
                    qualified.append(job)
                    stats.scored += 1
                else:
                    stats.skipped += 1
            
            await session.commit()
            logger.info(f"  → {stats.gates_passed} passed gates, {stats.scored} scored above {min_match}%")
            
            # ── Stage 6: Tier Assignment ─────────────────
            logger.info("⭐ Stage 6: Assigning tiers...")
            for job in qualified:
                job.tier = classify_tier(job)
            await session.commit()
            
            top_tier_count = sum(1 for j in qualified if j.tier == JobTier.TOP_TIER)
            logger.info(f"  → {top_tier_count} top-tier, {len(qualified) - top_tier_count} standard")
            
            # ── Sort by priority ─────────────────────────
            qualified = sort_jobs_by_priority(qualified)
            
            # Limit to daily target + buffer
            max_daily = get_config("gates.max_daily_apps", 60)
            buffer = 5
            batch = qualified[:max_daily + buffer]
            logger.info(f"  → Processing top {len(batch)} jobs for today")
            
            # ── Stage 7: Optimize Resumes ────────────────
            logger.info("✍️ Stage 7: Optimizing resumes...")
            master_tex = _load_master_resume()
            if not master_tex:
                logger.error("❌ No master resume found! Place your .tex file in src/optimizer/templates/")
                await send_alert("Missing Resume", "No master.tex found in templates directory")
                return stats
            
            profile = get_config("profile", {})
            
            for i, job in enumerate(batch):
                try:
                    logger.info(f"  [{i+1}/{len(batch)}] {job.company} — {job.title}")
                    
                    # Create application record
                    app = Application(
                        job_id=job.id,
                        job_fingerprint=job.fingerprint,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        source=job.source,
                        apply_url=job.apply_url,
                        jd_text=job.description,
                        match_score=job.match_score,
                        tier=job.tier,
                        visa_status=job.visa_status,
                        status=ApplicationStatus.OPTIMIZING,
                    )
                    session.add(app)
                    await session.flush()
                    
                    # Analyze JD
                    jd_keywords = await analyze_jd(job.description or "")
                    
                    # Run optimization loop
                    optimized_tex, ats_score, opt_details = await optimize_resume(
                        master_tex, job.description or "", jd_keywords, job.tier or JobTier.STANDARD, profile
                    )
                    
                    app.ats_score_after = ats_score
                    app.optimization_iterations = opt_details.get("iterations", 0)
                    
                    tier_cfg = get_tier_config(job.tier or JobTier.STANDARD)
                    
                    if ats_score >= tier_cfg["min_submit_score"]:
                        # Save optimized resume
                        pdf_path = f"/tmp/resume_{job.fingerprint[:8]}.pdf"
                        compiled = await compile_to_pdf(optimized_tex, pdf_path)
                        
                        if compiled:
                            with open(pdf_path, "rb") as f:
                                resume_path = save_resume(f.read(), job.company, job.title)
                            app.resume_url = resume_path
                            save_tex_source(optimized_tex, job.company, job.title)
                        
                        # Generate cover letter for top-tier
                        if job.tier == JobTier.TOP_TIER and tier_cfg.get("generate_cover_letter"):
                            cover = await generate_cover_letter(job.description or "", jd_keywords, profile)
                            app.cover_letter = cover
                        
                        app.status = ApplicationStatus.QUEUED
                        app.optimized_at = datetime.utcnow()
                        stats.optimized += 1
                        logger.info(f"    ✅ ATS: {ats_score}% → queued for application")
                    
                    elif opt_details.get("status") == "needs_review":
                        app.status = ApplicationStatus.NEEDS_REVIEW
                        app.error_log = f"ATS score {ats_score}% below minimum {tier_cfg['min_submit_score']}%"
                        stats.needs_review += 1
                        logger.info(f"    ⚠️ ATS: {ats_score}% → needs review")
                    
                    else:
                        app.status = ApplicationStatus.SKIPPED
                        app.error_log = f"Low match: {ats_score}%"
                        stats.skipped += 1
                        logger.info(f"    ⏭ ATS: {ats_score}% → skipped (low match)")
                    
                    await session.commit()
                
                except Exception as e:
                    logger.error(f"    ❌ Error processing {job.company}/{job.title}: {e}")
                    stats.failed += 1
                    await session.rollback()
            
            # ── Summary ──────────────────────────────────
            logger.info("=" * 60)
            logger.info("📊 Pipeline Summary:")
            logger.info(f"  Scraped: {stats.scraped}")
            logger.info(f"  Visa OK: {stats.visa_ok}, Blocked: {stats.visa_blocked}")
            logger.info(f"  Qualified: {stats.scored}")
            logger.info(f"  Optimized & Queued: {stats.optimized}")
            logger.info(f"  Needs Review: {stats.needs_review}")
            logger.info(f"  Skipped: {stats.skipped}")
            logger.info("=" * 60)
            
            # Send Telegram report
            await send_daily_report({
                "scraped": stats.scraped,
                "visa_blocked": stats.visa_blocked,
                "submitted": stats.optimized,
                "failed": stats.failed,
                "needs_review": stats.needs_review,
                "cost_today": stats.cost_today,
            })
        
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            await send_alert("Pipeline Error", str(e))
    
    return stats


def _load_master_resume() -> Optional[str]:
    """Load the master LaTeX resume template."""
    templates_dir = Path(__file__).parent.parent / "optimizer" / "templates"
    
    for name in ["master.tex", "resume.tex", "main.tex"]:
        path = templates_dir / name
        if path.exists():
            return path.read_text()
    
    # Also check config directory
    config_dir = Path(__file__).parent.parent.parent / "config"
    for name in ["resume.tex", "master.tex"]:
        path = config_dir / name
        if path.exists():
            return path.read_text()
    
    return None

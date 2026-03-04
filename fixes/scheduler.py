"""
Pipeline Orchestrator & Scheduler.
Runs the full daily cycle: harvest → filter → score → optimize → apply → report.

FIXES:
1. Improved LaTeX text extraction (was stripping too aggressively)
2. Added better error messages at each stage
3. Added resume text quality check before scoring
"""
import asyncio
import os
import re
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.config import config
from src.db.models import Job, Application, JobStatus, VisaStatus, Tier, ApplicationSource, InterviewStage
from src.db.session import async_session
from src.scraper.orchestrator import harvest_jobs
from src.filters.visa_filter import check_visa
from src.filters.gate_checker import process_gates
from src.filters.freshness import sort_by_freshness_and_score
from src.scorer.match_scorer import score_and_classify_jobs
from src.optimizer.latex_optimizer import optimize_resume, generate_cover_letter
from src.optimizer.latex_compiler import extract_pdf_text
from src.applicant.engine import application_engine
from src.archive.manager import archive_manager


async def run_daily_pipeline():
    """
    Execute the full daily pipeline.
    Called by APScheduler at the configured harvest time.
    """
    logger.info("=" * 60)
    logger.info("DAILY PIPELINE STARTED")
    logger.info("=" * 60)

    async with async_session() as db:
        try:
            # ── Stage 1-2: Harvest ──────────────────────────
            new_jobs = await harvest_jobs(db)
            if not new_jobs:
                logger.info("No new jobs found. Pipeline complete.")
                return

            # ── Stage 3: Visa Filter ────────────────────────
            visa_passed = []
            for job in new_jobs:
                status, reason = await check_visa(job.jd_text or "")
                job.visa_status = status
                if status == VisaStatus.ok or status == VisaStatus.unchecked:
                    visa_passed.append(job)
                elif status == VisaStatus.unclear:
                    job.status = JobStatus.needs_review
                    visa_passed.append(job)  # Still process, but flag
                else:
                    job.status = JobStatus.visa_blocked
            await db.commit()
            logger.info(f"Visa filter: {len(visa_passed)}/{len(new_jobs)} passed")

            if not visa_passed:
                logger.warning("All jobs blocked by visa filter. Pipeline complete.")
                return

            # ── Stage 4: Gate Check ─────────────────────────
            gate_passed = await process_gates(visa_passed, db)

            if not gate_passed:
                logger.warning("All jobs blocked by gate checker. Pipeline complete.")
                return

            # ── Stage 5-6: Score & Classify ─────────────────
            resume_text = _load_master_resume_text()
            if not resume_text or len(resume_text) < 100:
                logger.error(
                    f"Resume text too short ({len(resume_text)} chars)! "
                    "Check src/optimizer/templates/master.tex — "
                    "make sure it has your real resume content."
                )
                return

            logger.info(f"Resume text loaded: {len(resume_text)} chars, ~{len(resume_text.split())} words")

            scored_jobs = await score_and_classify_jobs(gate_passed, resume_text, db)

            if not scored_jobs:
                logger.warning(
                    "No jobs passed scoring threshold. "
                    "This usually means your resume keywords don't match the JDs. "
                    "Try: 1) Check master.tex has real skills, "
                    "2) Lower min_match_score in settings.yaml temporarily"
                )
                # Still proceed to start/stop engine cleanly
                await application_engine.start()
                await application_engine.stop()
                logger.info("=" * 60)
                logger.info("DAILY PIPELINE COMPLETE: 0 applied, 0 failed")
                logger.info("=" * 60)
                return

            # ── Sort by freshness + score ───────────────────
            sorted_jobs = sort_by_freshness_and_score(scored_jobs)

            # Limit to daily quota
            max_daily = config.rules.get("max_apps_per_day", 55)
            queue = sorted_jobs[:max_daily]

            logger.info(f"Application queue: {len(queue)} jobs (max {max_daily}/day)")

            # ── Stage 7-9: Optimize + Apply ─────────────────
            master_tex = _load_master_tex()
            if not master_tex:
                logger.error("No master LaTeX resume found!")
                return

            await application_engine.start()

            applied = 0
            failed = 0

            for job in queue:
                try:
                    # Optimize resume
                    job.status = JobStatus.optimizing
                    await db.commit()

                    opt_result = await optimize_resume(master_tex, job, resume_text)

                    if not opt_result.success:
                        job.status = JobStatus.optimization_failed
                        await db.commit()
                        failed += 1
                        logger.warning(f"Optimization failed: {job.company} — {opt_result.error}")
                        continue

                    if opt_result.needs_review:
                        job.status = JobStatus.needs_review
                        await db.commit()
                        continue

                    # Generate cover letter for top-tier
                    cover_letter = None
                    if job.tier == Tier.top_tier and opt_result.pdf_path:
                        pdf_text = extract_pdf_text(opt_result.pdf_path)
                        cover_letter = await generate_cover_letter(job, pdf_text)

                    # Archive resume
                    resume_url = await archive_manager.upload_resume(
                        opt_result.pdf_path, job.company, job.title
                    ) if opt_result.pdf_path else None

                    # Apply
                    job.status = JobStatus.applying
                    await db.commit()

                    apply_result = await application_engine.apply_to_job(
                        job=job,
                        resume_path=opt_result.pdf_path or "",
                        cover_letter=cover_letter,
                    )

                    # Create Application record
                    app = Application(
                        job_id=job.id,
                        company=job.company_normalized,
                        role=job.title,
                        source=job.source,
                        apply_url=job.apply_url,
                        jd_text=job.jd_text,
                        match_score=job.match_score,
                        ats_score=opt_result.ats_score,
                        tier=job.tier or Tier.standard,
                        optimization_iterations=opt_result.iterations,
                        resume_url=resume_url,
                        cover_letter=cover_letter,
                        confirmation_number=apply_result.get("confirmation_number"),
                    )

                    if apply_result["success"]:
                        app.status = JobStatus.submitted
                        app.applied_date = datetime.now(timezone.utc)
                        job.status = JobStatus.submitted
                        applied += 1

                        # Archive screenshot
                        if apply_result.get("screenshot_path"):
                            app.screenshot_url = await archive_manager.upload_screenshot(
                                apply_result["screenshot_path"], job.company, job.title
                            )
                    else:
                        app.status = JobStatus.failed
                        app.error_log = apply_result.get("error", "Unknown error")
                        job.status = JobStatus.failed
                        failed += 1

                    db.add(app)
                    await db.commit()

                    # Random delay between applications
                    min_gap = config.schedule.get("min_gap_minutes", 18) * 60
                    max_gap = config.schedule.get("max_gap_minutes", 28) * 60
                    delay = random.uniform(min_gap, max_gap)
                    logger.info(f"Next application in {delay/60:.1f} minutes")
                    await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"Pipeline error for {job.company}: {e}")
                    job.status = JobStatus.failed
                    await db.commit()
                    failed += 1

            await application_engine.stop()

            # ── Daily Report ────────────────────────────────
            logger.info("=" * 60)
            logger.info(f"DAILY PIPELINE COMPLETE: {applied} applied, {failed} failed")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Pipeline fatal error: {e}")
            raise


def _load_master_tex() -> Optional[str]:
    """Load the master LaTeX resume template."""
    template_dir = Path(config.settings.get("resume_template_dir",
                        str(Path(__file__).parent.parent / "optimizer" / "templates")))
    tex_path = template_dir / "master.tex"
    if tex_path.exists():
        return tex_path.read_text()

    # Check config directory
    config_dir = Path(__file__).parent.parent.parent / "config"
    for f in config_dir.glob("*.tex"):
        return f.read_text()

    logger.warning("No master .tex file found")
    return None


def _load_master_resume_text() -> str:
    """
    Load and extract readable text from the master LaTeX resume for ATS scoring.
    
    FIX: The original regex was too aggressive:
    - re.sub(r'\\[a-zA-Z]+\\{([^}]*)\\}', r'\\1', tex) would strip ALL commands
    - But commands like \\textbf{important skill} would lose the command and 
      nested content was mangled
    
    New approach: multi-pass extraction that preserves content.
    """
    tex = _load_master_tex()
    if not tex:
        return ""

    text = tex
    
    # Step 1: Remove comments (lines starting with %)
    text = re.sub(r'%.*$', '', text, flags=re.MULTILINE)
    
    # Step 2: Remove document preamble (everything before \begin{document})
    doc_start = text.find(r'\begin{document}')
    if doc_start >= 0:
        text = text[doc_start + len(r'\begin{document}'):]
    
    # Step 3: Remove \end{document}
    text = text.replace(r'\end{document}', '')
    
    # Step 4: Remove environment markers but keep content
    text = re.sub(r'\\begin\{[^}]*\}(?:\[[^\]]*\])?', ' ', text)
    text = re.sub(r'\\end\{[^}]*\}', ' ', text)
    
    # Step 5: Extract content from formatting commands (keep the content)
    # \textbf{content} → content
    # \textit{content} → content
    # \href{url}{text} → text
    text = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', text)
    
    # Iteratively strip \command{content} → content (handles nesting)
    for _ in range(5):  # Multiple passes for nested commands
        prev = text
        text = re.sub(r'\\[a-zA-Z]+\*?\{([^{}]*)\}', r' \1 ', text)
        if text == prev:
            break
    
    # Step 6: Remove remaining bare commands (\item, \vspace, \hfill, etc.)
    text = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?', ' ', text)
    
    # Step 7: Remove LaTeX special characters
    text = text.replace('~', ' ')
    text = text.replace('\\\\', ' ')
    text = re.sub(r'[{}\\$&^_#|]', ' ', text)
    
    # Step 8: Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    if len(text) < 50:
        logger.warning(
            f"Extracted resume text is very short ({len(text)} chars). "
            "Check that master.tex has real content."
        )
    else:
        logger.debug(f"Resume text extracted: {len(text)} chars, ~{len(text.split())} words")
        # Show first 200 chars for debugging
        logger.debug(f"Preview: {text[:200]}...")
    
    return text

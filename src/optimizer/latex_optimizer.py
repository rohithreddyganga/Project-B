"""
LaTeX Resume Optimizer.
Iterative loop: analyze JD → rewrite LaTeX → compile → score → repeat.
ABSOLUTE RULE: Never fabricate experience. Only rephrase and mirror keywords.
"""
import os
import tempfile
from typing import Tuple, Optional
from datetime import datetime

import anthropic
from loguru import logger

from src.config import config
from src.db.models import Job, Tier
from src.scorer.jd_analyzer import analyze_jd, JDAnalysis
from src.scorer.ats_scorer import score_ats
from src.optimizer.latex_compiler import compile_latex, extract_pdf_text


class OptimizationResult:
    """Result of a resume optimization attempt."""
    def __init__(
        self,
        success: bool,
        ats_score: float,
        pdf_path: Optional[str],
        tex_source: str,
        iterations: int,
        needs_review: bool = False,
        error: Optional[str] = None,
    ):
        self.success = success
        self.ats_score = ats_score
        self.pdf_path = pdf_path
        self.tex_source = tex_source
        self.iterations = iterations
        self.needs_review = needs_review
        self.error = error


async def optimize_resume(
    master_tex: str,
    job: Job,
    resume_text: str | None = None,
) -> OptimizationResult:
    """
    Optimize a LaTeX resume for a specific job.
    Runs the iterative loop based on the job's tier.

    Args:
        master_tex: The master LaTeX source to modify
        job: The target job
        resume_text: Pre-extracted resume text (optional, will extract if not provided)
    """
    rules = config.rules
    is_top_tier = job.tier == Tier.top_tier

    target_score = (
        rules.get("ats_threshold_top_tier", 96)
        if is_top_tier
        else rules.get("ats_threshold_standard", 90)
    )
    max_iters = (
        rules.get("max_iterations_top_tier", 3)
        if is_top_tier
        else rules.get("max_iterations_standard", 2)
    )

    logger.info(
        f"Optimizing resume for {job.company} — {job.title} "
        f"(tier={job.tier.value if job.tier else 'std'}, target={target_score}%)"
    )

    # Step 1: Analyze JD
    jd_analysis = await analyze_jd(job.jd_text or "")

    # Step 2: Iterative optimization loop
    current_tex = master_tex
    best_score = 0.0
    best_tex = master_tex
    best_pdf = None

    for iteration in range(1, max_iters + 1):
        logger.debug(f"Optimization iteration {iteration}/{max_iters}")

        # Rewrite LaTeX source
        optimized_tex = await _rewrite_latex(
            current_tex, job, jd_analysis, iteration
        )

        if not optimized_tex:
            logger.warning(f"Iteration {iteration}: LLM rewrite failed")
            continue

        # Compile to PDF
        work_dir = tempfile.mkdtemp(prefix=f"opt_{iteration}_")
        pdf_path, compile_error = await compile_latex(optimized_tex, work_dir)

        if not pdf_path:
            logger.warning(f"Iteration {iteration}: Compile failed: {compile_error}")
            continue

        # Extract text and score
        pdf_text = extract_pdf_text(pdf_path)
        if not pdf_text:
            logger.warning(f"Iteration {iteration}: PDF text extraction failed")
            continue

        score = await score_ats(
            resume_text=pdf_text,
            jd_text=job.jd_text or "",
            jd_analysis=jd_analysis,
            use_llm=True,
        )

        logger.info(f"Iteration {iteration}: ATS score = {score:.1f}% (target={target_score}%)")

        if score > best_score:
            best_score = score
            best_tex = optimized_tex
            best_pdf = pdf_path

        # Check if we hit the target
        if score >= target_score:
            return OptimizationResult(
                success=True,
                ats_score=score,
                pdf_path=pdf_path,
                tex_source=optimized_tex,
                iterations=iteration,
            )

        current_tex = optimized_tex

    # Didn't hit target after all iterations
    # Standard tier: submit if ≥ 90%
    # Top tier: submit if ≥ 93%, else flag for review
    submit_threshold = 90 if not is_top_tier else 93

    if best_score >= submit_threshold:
        return OptimizationResult(
            success=True,
            ats_score=best_score,
            pdf_path=best_pdf,
            tex_source=best_tex,
            iterations=max_iters,
        )
    elif best_score >= 90:
        # Still decent — flag for review but don't auto-skip
        return OptimizationResult(
            success=True,
            ats_score=best_score,
            pdf_path=best_pdf,
            tex_source=best_tex,
            iterations=max_iters,
            needs_review=True,
        )
    else:
        # Below 90% after all iterations — bad match, skip
        return OptimizationResult(
            success=False,
            ats_score=best_score,
            pdf_path=best_pdf,
            tex_source=best_tex,
            iterations=max_iters,
            needs_review=True,
            error=f"Could not reach {submit_threshold}% (best: {best_score}%)",
        )


async def _rewrite_latex(
    tex_source: str,
    job: Job,
    jd_analysis: JDAnalysis,
    iteration: int,
) -> Optional[str]:
    """
    Use Claude Sonnet to rewrite LaTeX resume for this specific job.
    CRITICAL: Only rephrase real experience, NEVER fabricate.
    """
    api_key = config.env.anthropic_api_key
    if not api_key:
        return None

    keywords_str = ", ".join(jd_analysis.required_skills[:30])
    preferred_str = ", ".join(jd_analysis.preferred_skills[:15])
    tools_str = ", ".join(jd_analysis.tools_and_technologies[:20])

    prompt = f"""You are an expert ATS resume optimizer. Modify this LaTeX resume to better match the job description.

ABSOLUTE RULES:
1. NEVER fabricate, invent, or add skills/experience the person doesn't have
2. ONLY rephrase existing bullets to naturally include JD keywords
3. Keep ALL dates, company names, and job titles exactly as they are
4. Maintain the LaTeX structure — do NOT break compilation
5. The output must be COMPLETE, compilable LaTeX — include ALL sections

OPTIMIZATION STRATEGY (iteration {iteration}):
- Mirror these required skills in bullet points where truthful: {keywords_str}
- Include preferred skills if they relate to existing experience: {preferred_str}
- Reference these tools/technologies naturally: {tools_str}
- Ensure the Skills section uses the JD's exact terminology
- Use strong action verbs from the JD: {', '.join(jd_analysis.action_verbs[:10])}
- Keep the summary/objective aligned with the role: {job.title} at {job.company}

TARGET ROLE: {job.title} at {job.company}

JOB DESCRIPTION (key requirements):
{job.jd_text[:2500] if job.jd_text else 'No JD text available'}

CURRENT LATEX RESUME:
{tex_source}

Return ONLY the complete, modified LaTeX source. No explanations or markdown."""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=config.llm_config.get("writing_model", "claude-sonnet-4-5-20250929"),
            max_tokens=config.llm_config.get("max_tokens_writing", 4096),
            temperature=config.llm_config.get("temperature_writing", 0.3),
            messages=[{"role": "user", "content": prompt}],
        )

        tex = response.content[0].text.strip()

        # Clean potential markdown wrapping
        if tex.startswith("```"):
            lines = tex.split("\n")
            tex = "\n".join(lines[1:])  # Remove first line
            if tex.endswith("```"):
                tex = tex[:-3]

        # Basic validation
        if "\\begin{document}" not in tex or "\\end{document}" not in tex:
            logger.warning("LLM output missing document structure — attempting fix")
            if "\\begin{document}" not in tex:
                return None

        return tex.strip()

    except Exception as e:
        logger.error(f"LaTeX rewrite failed: {e}")
        return None


async def generate_cover_letter(
    job: Job,
    resume_text: str,
) -> Optional[str]:
    """Generate a tailored cover letter for top-tier applications."""
    api_key = config.env.anthropic_api_key
    if not api_key:
        return None

    profile = config.profile
    personal = profile.get("personal", {})
    name = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip()

    prompt = f"""Write a concise, professional cover letter (250-350 words) for this job application.

Candidate: {name}
Target Role: {job.title} at {job.company}

Resume Summary:
{resume_text[:1500]}

Job Description:
{job.jd_text[:2000] if job.jd_text else 'N/A'}

Guidelines:
- Professional but not stiff — sound like a real human
- Connect specific resume achievements to JD requirements
- Show genuine interest in the company
- Keep it under 350 words
- Do NOT mention visa status or sponsorship needs
- No generic filler — every sentence should add value

Write the cover letter (plain text, no formatting):"""

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=config.llm_config.get("writing_model", "claude-sonnet-4-5-20250929"),
            max_tokens=1024,
            temperature=0.4,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        return None

"""
Cover Letter Generator — creates tailored cover letters for top-tier applications.
Uses Claude Sonnet for high-quality professional writing.
"""
import logging
from typing import Optional

from src.config import config
from src import llm_client

logger = logging.getLogger(__name__)


async def generate_cover_letter(
    jd_text: str,
    jd_analysis: dict,
    company: str,
    title: str,
    application_id: str = None,
) -> Optional[str]:
    """Generate a tailored cover letter for a specific role."""
    profile = config.profile
    personal = profile.get("personal", {})
    name = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip()
    skills = profile.get("skills", {})

    key_skills = ", ".join(jd_analysis.get("required_skills", [])[:5])

    prompt = f"""Write a concise, professional cover letter for this job application.

CANDIDATE: {name}
TARGET ROLE: {title} at {company}
KEY MATCHING SKILLS: {key_skills}
EXPERIENCE: {profile.get('experience_years', 0)} years
EDUCATION: {profile.get('education', {}).get('degree', '')} in {profile.get('education', {}).get('major', '')}

JOB DESCRIPTION (first 1500 chars):
{jd_text[:1500]}

RULES:
1. 3-4 paragraphs max (250-350 words total)
2. Open with genuine enthusiasm for the specific role/company
3. Highlight 2-3 specific experiences that match JD requirements
4. Use concrete numbers/achievements where possible
5. Close with clear call to action
6. Professional but warm tone — not generic
7. Do NOT mention visa status or sponsorship
8. ONLY reference real skills from the candidate profile

Output ONLY the cover letter text. No headers, no "Dear Hiring Manager," prefix — just the body paragraphs."""

    try:
        letter = await llm_client.call_sonnet(
            prompt=prompt,
            system="You write compelling, authentic cover letters. Each one is specific to the company and role. Never generic.",
            operation="cover_letter",
            application_id=application_id,
        )
        logger.info(f"Cover letter generated for {company} - {title} ({len(letter)} chars)")
        return letter.strip()
    except Exception as e:
        logger.error(f"Cover letter generation failed: {e}")
        return None

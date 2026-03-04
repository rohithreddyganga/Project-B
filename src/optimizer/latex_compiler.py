"""
LaTeX compilation wrapper.
Compiles .tex → .pdf using tectonic (or pdflatex fallback).
Extracts text from compiled PDF for ATS scoring.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import Tuple, Optional

import fitz  # PyMuPDF
from loguru import logger


async def compile_latex(tex_source: str, output_dir: str | None = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Compile LaTeX source to PDF.
    Returns (pdf_path, error_message).
    Uses tectonic (preferred) or pdflatex as fallback.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="autoapply_")

    tex_path = os.path.join(output_dir, "resume.tex")
    pdf_path = os.path.join(output_dir, "resume.pdf")

    # Write .tex source
    with open(tex_path, "w") as f:
        f.write(tex_source)

    # Try tectonic first (cleaner, auto-downloads packages)
    try:
        proc = await asyncio.create_subprocess_exec(
            "tectonic", tex_path,
            "--outdir", output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode == 0 and os.path.exists(pdf_path):
            logger.debug(f"LaTeX compiled with tectonic: {pdf_path}")
            return pdf_path, None
        else:
            error = stderr.decode()[:500] if stderr else "Unknown tectonic error"
            logger.warning(f"Tectonic failed, trying pdflatex: {error}")
    except FileNotFoundError:
        logger.info("Tectonic not found, trying pdflatex")
    except asyncio.TimeoutError:
        logger.warning("Tectonic timed out, trying pdflatex")

    # Fallback: pdflatex
    try:
        proc = await asyncio.create_subprocess_exec(
            "pdflatex",
            "-interaction=nonstopmode",
            f"-output-directory={output_dir}",
            tex_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode == 0 and os.path.exists(pdf_path):
            logger.debug(f"LaTeX compiled with pdflatex: {pdf_path}")
            return pdf_path, None
        else:
            error = stdout.decode()[-500:] if stdout else "Unknown pdflatex error"
            return None, f"pdflatex failed: {error}"

    except FileNotFoundError:
        return None, "Neither tectonic nor pdflatex found. Install texlive or tectonic."
    except asyncio.TimeoutError:
        return None, "LaTeX compilation timed out (60s)"


def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from a PDF using PyMuPDF. Returns clean text."""
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts).strip()
    except Exception as e:
        logger.error(f"PDF text extraction failed: {e}")
        return ""

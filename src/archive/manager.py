"""
Archive Manager — DB-indexed flat storage.
Files go to Backblaze B2, metadata lives in PostgreSQL.
No folders, no chaos.
"""
import os
import hashlib
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig
from loguru import logger

from src.config import config


class ArchiveManager:
    """Manages file storage in Backblaze B2 with DB indexing."""

    def __init__(self):
        self._client = None
        self._bucket = config.env.b2_bucket_name

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=config.env.b2_endpoint,
                aws_access_key_id=config.env.b2_key_id,
                aws_secret_access_key=config.env.b2_app_key,
                config=BotoConfig(signature_version="s3v4"),
            )
        return self._client

    def _generate_key(self, prefix: str, company: str, role: str, ext: str) -> str:
        """Generate a flat file key: prefix/date_company_role_hash.ext"""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Sanitize company and role for filenames
        company_clean = "".join(c if c.isalnum() else "-" for c in company.lower())[:30]
        role_clean = "".join(c if c.isalnum() else "-" for c in role.lower())[:30]
        # Short hash for uniqueness
        raw = f"{company}{role}{date_str}{os.urandom(4).hex()}"
        short_hash = hashlib.md5(raw.encode()).hexdigest()[:6]
        return f"{prefix}/{date_str}_{company_clean}_{role_clean}_{short_hash}.{ext}"

    async def upload_resume(self, pdf_path: str, company: str, role: str) -> Optional[str]:
        """Upload a tailored resume PDF. Returns the public URL."""
        if not os.path.exists(pdf_path):
            logger.error(f"Resume file not found: {pdf_path}")
            return None

        key = self._generate_key("resumes", company, role, "pdf")
        try:
            self.client.upload_file(
                pdf_path, self._bucket, key,
                ExtraArgs={"ContentType": "application/pdf"}
            )
            url = f"{config.env.b2_endpoint}/{self._bucket}/{key}"
            logger.info(f"Resume uploaded: {key}")
            return url
        except Exception as e:
            logger.error(f"Resume upload failed: {e}")
            # Fallback: keep local copy
            return f"local://{pdf_path}"

    async def upload_screenshot(self, png_path: str, company: str, role: str) -> Optional[str]:
        """Upload a confirmation screenshot. Returns the URL."""
        if not os.path.exists(png_path):
            return None

        key = self._generate_key("screenshots", company, role, "png")
        try:
            self.client.upload_file(
                png_path, self._bucket, key,
                ExtraArgs={"ContentType": "image/png"}
            )
            url = f"{config.env.b2_endpoint}/{self._bucket}/{key}"
            logger.info(f"Screenshot uploaded: {key}")
            return url
        except Exception as e:
            logger.error(f"Screenshot upload failed: {e}")
            return f"local://{png_path}"

    async def upload_file(self, local_path: str, prefix: str, company: str, role: str, ext: str) -> Optional[str]:
        """Generic file upload."""
        key = self._generate_key(prefix, company, role, ext)
        try:
            self.client.upload_file(local_path, self._bucket, key)
            return f"{config.env.b2_endpoint}/{self._bucket}/{key}"
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return None


# Singleton
archive_manager = ArchiveManager()

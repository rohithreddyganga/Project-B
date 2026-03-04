"""
Centralized configuration loader.
Reads .env, settings.yaml, profile.json, priority list, and blacklist.
"""
import os
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings
from pydantic import Field
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


class EnvSettings(BaseSettings):
    """Environment variables from .env file."""
    # Database — defaults to local SQLite for zero-config setup
    database_url: str = Field(default="sqlite+aiosqlite:///autoapply.db")
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    # Anthropic
    anthropic_api_key: str = Field(default="")
    # Job APIs
    adzuna_app_id: str = Field(default="")
    adzuna_api_key: str = Field(default="")
    jsearch_api_key: str = Field(default="")
    # Backblaze B2
    b2_key_id: str = Field(default="")
    b2_app_key: str = Field(default="")
    b2_bucket_name: str = Field(default="autoapply-archive")
    b2_endpoint: str = Field(default="https://s3.us-west-004.backblazeb2.com")
    # Proxy
    proxy_url: str = Field(default="")
    # CAPTCHA
    capsolver_api_key: str = Field(default="")
    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    # Gmail (Phase 2)
    gmail_client_id: str = Field(default="")
    gmail_client_secret: str = Field(default="")
    gmail_refresh_token: str = Field(default="")
    # App
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8"}


def load_yaml(filename: str) -> dict:
    """Load a YAML config file."""
    path = CONFIG_DIR / filename
    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_json(filename: str) -> dict:
    """Load a JSON config file."""
    path = CONFIG_DIR / filename
    if not path.exists():
        logger.warning(f"Config file not found: {path}")
        return {}
    with open(path) as f:
        return json.load(f)


class AppConfig:
    """Unified application configuration."""

    def __init__(self):
        self.env = EnvSettings()
        self.settings = load_yaml("settings.yaml")
        self.profile = load_json("profile.json")
        self.priority_companies = load_yaml("priority_companies.yaml").get("priority", [])
        blacklist_data = load_yaml("blacklist.yaml")
        self.blacklist = blacklist_data.get("blacklist", [])
        self.blocked_domains = blacklist_data.get("blocked_domains", [])

    @property
    def rules(self) -> dict:
        return self.settings.get("rules", {})

    @property
    def schedule(self) -> dict:
        return self.settings.get("schedule", {})

    @property
    def visa_filter_config(self) -> dict:
        return self.settings.get("visa_filter", {})

    @property
    def sources(self) -> dict:
        return self.settings.get("sources", {})

    @property
    def job_criteria(self) -> dict:
        return self.settings.get("job_criteria", {})

    @property
    def stealth_config(self) -> dict:
        return self.settings.get("stealth", {})

    @property
    def scoring_config(self) -> dict:
        return self.settings.get("scoring", {})

    @property
    def llm_config(self) -> dict:
        return self.settings.get("llm", {})

    def is_priority_company(self, company_name: str) -> bool:
        """Check if company is on the top-tier priority list."""
        name_lower = company_name.lower().strip()
        return any(p.lower() in name_lower or name_lower in p.lower()
                    for p in self.priority_companies)

    def is_blacklisted(self, company_name: str) -> bool:
        """Check if company is blacklisted."""
        name_lower = company_name.lower().strip()
        return any(b.lower() in name_lower for b in self.blacklist)


# Singleton
config = AppConfig()

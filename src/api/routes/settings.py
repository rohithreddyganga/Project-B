"""API Routes — Section ⑦ Rules & Settings Panel"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.config import config, load_yaml
import yaml
from pathlib import Path

router = APIRouter()

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "settings.yaml"


class SettingsUpdate(BaseModel):
    path: str       # Dot-notation path like "gates.max_per_company"
    value: object   # New value


class BlacklistUpdate(BaseModel):
    companies: Optional[List[str]] = None
    domains: Optional[List[str]] = None


@router.get("/")
async def get_settings():
    """Get current settings (safe subset for dashboard)."""
    cfg = config.settings
    return {
        "gates": cfg.get("gates", {}),
        "ats": cfg.get("ats", {}),
        "scraping": {
            "sources": {k: {"enabled": v.get("enabled", True)} 
                       for k, v in cfg.get("scraping", {}).get("sources", {}).items()
                       if isinstance(v, dict)},
            "search_queries": cfg.get("scraping", {}).get("search_queries", []),
            "max_job_age_days": cfg.get("scraping", {}).get("max_job_age_days", 14),
        },
        "applicant": {
            "start_hour": cfg.get("applicant", {}).get("start_hour", 8),
            "end_hour": cfg.get("applicant", {}).get("end_hour", 22),
        },
        "blacklist": cfg.get("blacklist", {}),
    }


@router.put("/blacklist")
async def update_blacklist(body: BlacklistUpdate):
    """Update the blacklist."""
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = yaml.safe_load(f)
        
        if body.companies is not None:
            cfg.setdefault("blacklist", {})["companies"] = body.companies
        if body.domains is not None:
            cfg.setdefault("blacklist", {})["domains"] = body.domains
        
        with open(CONFIG_PATH, "w") as f:
            yaml.dump(cfg, f, default_flow_style=False)
        
        # Reload config from disk
        config.settings = load_yaml("settings.yaml")

        return {"status": "updated", "blacklist": cfg["blacklist"]}
    except Exception as e:
        raise HTTPException(500, f"Failed to update settings: {e}")

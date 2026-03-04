"""
Settings routes — configuration management.
Dashboard Section ⑦: Rules & Policies
"""
from fastapi import APIRouter, Body
from src.config import config
import yaml
from pathlib import Path

router = APIRouter()

CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"


@router.get("/rules")
async def get_rules():
    """Get current rules configuration."""
    return {
        "rules": config.rules,
        "schedule": config.schedule,
        "blacklist": config.blacklist,
        "priority_companies": config.priority_companies,
    }


@router.put("/rules")
async def update_rules(rules: dict = Body(...)):
    """Update rules configuration."""
    # Load current settings
    settings_path = CONFIG_DIR / "settings.yaml"
    current = config.settings.copy()
    current["rules"] = {**current.get("rules", {}), **rules}

    with open(settings_path, "w") as f:
        yaml.dump(current, f, default_flow_style=False)

    # Reload
    config.settings = current
    return {"status": "updated", "rules": current["rules"]}


@router.put("/blacklist")
async def update_blacklist(companies: list = Body(...)):
    """Update blacklisted companies."""
    bl_path = CONFIG_DIR / "blacklist.yaml"
    data = {"blacklist": companies, "blocked_domains": config.blocked_domains}

    with open(bl_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    config.blacklist = companies
    return {"status": "updated", "blacklist": companies}


@router.put("/priority")
async def update_priority_companies(companies: list = Body(...)):
    """Update priority companies list."""
    pri_path = CONFIG_DIR / "priority_companies.yaml"

    with open(pri_path, "w") as f:
        yaml.dump({"priority": companies}, f, default_flow_style=False)

    config.priority_companies = companies
    return {"status": "updated", "priority": companies}

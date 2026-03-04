"""API Routes — Pipeline control (start, stop, status, manual triggers)."""
import asyncio
from fastapi import APIRouter
from src.pipeline.orchestrator import run_daily_pipeline
from src.pipeline.scheduler import scheduler

router = APIRouter()

_running_task = None


@router.post("/run")
async def trigger_pipeline():
    """Manually trigger the daily pipeline."""
    global _running_task
    
    if _running_task and not _running_task.done():
        return {"status": "already_running"}
    
    _running_task = asyncio.create_task(run_daily_pipeline())
    return {"status": "started"}


@router.get("/status")
async def pipeline_status():
    """Check if pipeline is currently running."""
    running = _running_task is not None and not _running_task.done()
    
    # Get scheduled jobs info
    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    
    return {
        "pipeline_running": running,
        "scheduled_jobs": jobs_info,
        "scheduler_running": scheduler.running,
    }


@router.post("/stop")
async def stop_pipeline():
    """Cancel running pipeline."""
    global _running_task
    if _running_task and not _running_task.done():
        _running_task.cancel()
        return {"status": "cancelled"}
    return {"status": "not_running"}

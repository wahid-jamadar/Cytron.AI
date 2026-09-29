"""
modules/build_complete_project/router.py
─────────────────────────────────────────
FastAPI router for the Build Complete Project module.

Endpoints:
  GET  /build-complete-project/           → Serve the HTML page
  POST /build-complete-project/generate   → Start a real generation job
  GET  /build-complete-project/stream/{job_id}  → SSE stream of progress events
  GET  /build-complete-project/download/{job_id} → Download generated ZIP
  GET  /build-complete-project/status/{job_id}  → Poll job status (JSON)
"""

import asyncio
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from modules.common.utils import templates
from .generator import job_manager, run_real_generation
from .analyzer import analyze_tech_stack, AnalyzerResponse
from modules.auth.rbac import get_current_user_optional
from modules.database.models import User

router = APIRouter(prefix="/build-complete-project", tags=["build-complete-project"])


class ProjectConfig(BaseModel):
    frontend:     str = "React"
    backend:      str = "FastAPI"
    architecture: str = "Monolith"
    details:      str = ""
    clarified_decisions: dict = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    prompt: str
    selected_tech_stack: dict


# ── Page ─────────────────────────────────────────────────────────────────────

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse(
        "build_complete_project.html", {"request": request}
    )


# ── Generate ─────────────────────────────────────────────────────────────────

@router.post("/analyze-stack", response_model=AnalyzerResponse)
async def analyze_stack(request: AnalyzeRequest):
    """
    Analyze the project prompt and selected tech stack for completeness and conflicts.
    Returns clarification questions if necessary.
    """
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail="Project details cannot be empty.",
        )
    return analyze_tech_stack(request.prompt, request.selected_tech_stack)


@router.post("/generate")
async def generate_project(config: ProjectConfig, background_tasks: BackgroundTasks, current_user: User | None = Depends(get_current_user_optional)):
    """
    Start a real autonomous code generation job.
    Returns a job_id that the client uses for SSE streaming and download.
    """
    if not config.details.strip():
        raise HTTPException(
            status_code=400,
            detail="Project details cannot be empty. Please describe what you want to build.",
        )

    job_data = config.model_dump()
    if current_user:
        job_data["user_id"] = current_user.id
        
    job_id = job_manager.create_job(job_data)
    # Launch real pipeline as a background task — non-blocking
    background_tasks.add_task(run_real_generation, job_id)
    return {"job_id": job_id, "status": "started"}


# ── SSE Stream ────────────────────────────────────────────────────────────────

@router.get("/stream/{job_id}")
async def stream_generation(job_id: str, request: Request):
    """
    Server-Sent Events stream. Yields real pipeline events until the job
    completes or errors. Supports client reconnection.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(job["queue"].get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send a heartbeat to keep the connection alive
                    yield {"event": "heartbeat", "data": "{}"}
                    continue

                yield event

                # Stop streaming after terminal events
                if event["event"] in ("complete", "error"):
                    break

        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())


# ── Download ─────────────────────────────────────────────────────────────────

@router.get("/download/{job_id}")
async def download_project(job_id: str):
    """
    Download the generated project ZIP file once the job is complete.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") not in ("completed",):
        status = job.get("status", "unknown")
        error  = job.get("error", "")
        if status == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Job failed and no ZIP is available. Error: {error}",
            )
        raise HTTPException(
            status_code=202,
            detail=f"Job is still in progress (status: {status}). Try again shortly.",
        )

    zip_path = job.get("zip_path")
    if not zip_path:
        raise HTTPException(
            status_code=404,
            detail="ZIP file path not set — the packaging stage may not have completed.",
        )

    zip_file = Path(zip_path)
    if not zip_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"ZIP file not found on disk: {zip_path}",
        )

    app_name = job.get("app_name", "project")
    return FileResponse(
        str(zip_file),
        media_type="application/zip",
        filename=f"{app_name}.zip",
    )


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status/{job_id}")
async def job_status(job_id: str):
    """Return current job status for polling clients."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    elapsed = round(__import__("time").time() - job.get("started_at", 0))
    return {
        "job_id":    job_id,
        "status":    job.get("status"),
        "app_name":  job.get("app_name"),
        "zip_ready": bool(job.get("zip_path") and Path(job["zip_path"]).exists()),
        "elapsed_s": elapsed,
        "error":     job.get("error"),
    }
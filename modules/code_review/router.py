import asyncio
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import Dict, Optional
from modules.common.utils import templates
from .generator import job_manager, run_hybrid_generation, apply_fix_and_reanalyze

router = APIRouter(prefix="/code-review", tags=["code-review"])

class CodeReviewConfig(BaseModel):
    code: str = ""
    files: Dict[str, str] = {}
    depth: str
    opt_sec: bool
    opt_perf: bool
    opt_style: bool
    opt_docs: bool

class ApplyFixRequest(BaseModel):
    files: Dict[str, str]
    finding_id: str
    patch: str
    filename: str
    depth: str

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("code_review.html", {"request": request})

@router.post("/analyze")
async def analyze_code(config: CodeReviewConfig, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job(config.model_dump())
    background_tasks.add_task(run_hybrid_generation, job_id)
    return {"job_id": job_id}

@router.post("/analyze/apply-fix")
async def apply_fix(req: ApplyFixRequest, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job({
        "files": req.files,
        "patch": req.patch,
        "filename": req.filename,
        "finding_id": req.finding_id,
        "depth": req.depth,
        "is_re_review": True
    })
    background_tasks.add_task(apply_fix_and_reanalyze, job_id)
    return {"job_id": job_id}

@router.get("/stream/{job_id}")
async def stream_generation(job_id: str, request: Request):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        try:
            while True:
                event = await job["queue"].get()
                yield event
                
                if event["event"] in ["complete", "error"]:
                    break
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())

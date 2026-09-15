import asyncio
from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from modules.common.utils import templates
from .generator import job_manager, run_mock_generation

router = APIRouter(prefix="/code-generation", tags=["code-generation"])

class CodeGenConfig(BaseModel):
    language: str
    requirements: str
    inc_comments: bool
    inc_tests: bool
    strict_typing: bool

@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("code_generation.html", {"request": request})

@router.post("/generate")
async def generate_code(config: CodeGenConfig, background_tasks: BackgroundTasks):
    job_id = job_manager.create_job(config.model_dump())
    background_tasks.add_task(run_mock_generation, job_id)
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
                
                # Stop streaming after completion or error
                if event["event"] in ["complete", "error"]:
                    break
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())

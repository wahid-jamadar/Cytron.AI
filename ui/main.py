"""
ui/main.py
───────────
FastAPI backend for the Cytron.AI Web UI.

Serves:
  - Static React frontend (ui/static/)
  - POST /api/run        — Start a pipeline run
  - GET  /api/stream/{run_id} — SSE stream of pipeline progress
  - GET  /api/status/{run_id} — Current run status
  - GET  /api/runs        — List of recent runs
  - GET  /health          — Health check
"""

import asyncio
import json
import uuid
import time
from collections import deque
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config.settings import settings
from orchestrator.runner import get_runner
from modules.common.logger import setup_logging, platform_logger, metrics_collector, user_id_var, session_id_var, request_id_var
from modules.auth.rbac import get_current_user_optional
from modules.database.models import User

setup_logging()
logger = platform_logger

# Import modular routers
from modules.hub.router import router as hub_router
from modules.requirement_analyzer.router import router as req_router
from modules.build_complete_project.router import router as build_router
from modules.code_generation.router import router as codegen_router
from modules.code_review.router import router as review_router
from modules.database_schema.router import router as db_router
from modules.system_design.router import router as sysdesign_router
from modules.test_case_generator.router import router as test_router
from modules.documentation_generator.router import router as docs_router
from modules.sql_query_generator.router import router as sql_router

from modules.auth.router import router as auth_router
from modules.admin.router import router as admin_router
from modules.notifications.websocket import router as ws_router

logger = platform_logger

app = FastAPI(
    title="Cytron.AI",
    description="Autonomous multi-agent platform for end-to-end application generation",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*50)
    print("Cytron.AI is successfully running!")
    print("Please use this URL to access the system:")
    print("http://localhost:8000")
    print("="*50 + "\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from modules.auth.service import verify_token

# Global Authentication & RBAC Guard Middleware
@app.middleware("http")
async def auth_guard_middleware(request: Request, call_next):
    path = request.url.path
    
    # 1. Extract and verify token
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get("access_token")
        
    payload = None
    if token:
        payload = verify_token(token)
        
    # 2. Server-side redirect for authenticated Normal Users trying to load the React app (/app)
    if path.startswith("/app"):
        if payload and payload.get("type") == "access":
            roles = payload.get("roles", [])
            is_admin = any(r in ["SUPER_ADMIN", "ADMIN", "SUPPORT", "READ_ONLY_ADMIN"] for r in roles)
            if not is_admin:
                return RedirectResponse(url="/hub")
                
    # 3. Define public paths
    is_public = (
        path.startswith("/static/") or
        path == "/health" or
        path.startswith("/app") or  # React SPA must load so client can handle login/signup
        path in [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/auth/forgot-password",
            "/api/auth/reset-password"
        ]
    )
    
    if is_public:
        return await call_next(request)
        
    # 4. If unauthenticated, redirect to login or return 401
    if not payload or payload.get("type") != "access":
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"}
            )
        return RedirectResponse(url="/app/#/login")
        
    # 5. Strict RBAC for Admin endpoints
    if path.startswith("/api/admin/"):
        roles = payload.get("roles", [])
        is_admin = any(r in ["SUPER_ADMIN", "ADMIN", "SUPPORT", "READ_ONLY_ADMIN"] for r in roles)
        if not is_admin:
            return JSONResponse(
                status_code=403,
                content={"detail": "Operation not permitted. Administrative access required."}
            )
            
    return await call_next(request)

# HTTP Request Logging Middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
    session_id = request.query_params.get("session_id") or request.headers.get("x-session-id", request_id)
    user_id = request.headers.get("x-user-id", "AJ")
    
    req_token = request_id_var.set(request_id)
    sess_token = session_id_var.set(session_id)
    usr_token = user_id_var.set(user_id)
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    if request.url.path in ("/", "/hub", "/health"):
        logger.user_action(
            "User Connected",
            username=user_id,
            session_id=session_id,
            user_id=user_id,
            request_id=request_id,
            details={"ip": client_ip, "browser": user_agent}
        )
        
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        metrics_collector.record_api_request(duration_ms)
        logger.api_call(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            payload_size=request.headers.get("content-length"),
            response_size=response.headers.get("content-length")
        )
        return response
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        metrics_collector.record_api_request(duration_ms)
        logger.error(f"API Request Failed: {exc}", exc_info=True)
        raise
    finally:
        try:
            request_id_var.reset(req_token)
        except ValueError:
            request_id_var.set("")
        try:
            session_id_var.reset(sess_token)
        except ValueError:
            session_id_var.set("")
        try:
            user_id_var.reset(usr_token)
        except ValueError:
            user_id_var.set("")

# Include module routers
app.include_router(hub_router)
app.include_router(req_router)
app.include_router(build_router)
app.include_router(codegen_router)
app.include_router(review_router)
app.include_router(db_router)
app.include_router(sysdesign_router)
app.include_router(test_router)
app.include_router(docs_router)
app.include_router(sql_router)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ws_router)

# ── In-memory run registry ─────────────────────────────────────────────────────
runs: dict[str, dict[str, Any]] = {}
run_events: dict[str, deque] = {}


class RunRequest(BaseModel):
    requirement: str
    run_id: str | None = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    stream_url: str


# ── API Routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/run", response_model=RunResponse)
async def start_run(request: RunRequest, current_user = Depends(get_current_user_optional)):
    """Start a new pipeline run and return a run_id to stream progress."""
    if not request.requirement.strip():
        raise HTTPException(status_code=400, detail="requirement cannot be empty")

    run_id = request.run_id or str(uuid.uuid4())[:8]

    if run_id in runs and runs[run_id]["status"] == "running":
        raise HTTPException(status_code=409, detail=f"Run {run_id} is already in progress")

    user_id_for_log = str(current_user.id) if current_user else "AJ"
    username_for_log = f"{current_user.first_name} {current_user.last_name}" if current_user else "Wahid Jamadar"

    # Log Prompt Submission
    logger.user_action(
        "Prompt Submitted",
        username=username_for_log,
        session_id=run_id,
        user_id=user_id_for_log,
        request_id=run_id,
        details={"requirement": request.requirement}
    )

    runs[run_id] = {
        "run_id": run_id,
        "requirement": request.requirement,
        "status": "running",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "stages": [],
        "result": None,
        "errors": [],
    }
    run_events[run_id] = deque(maxlen=200)

    # Fire and forget — run pipeline in background
    user_id_val = current_user.id if current_user else None
    asyncio.create_task(_run_pipeline(run_id, request.requirement, user_id=user_id_val))

    return RunResponse(
        run_id=run_id,
        status="running",
        stream_url=f"/api/stream/{run_id}",
    )


@app.get("/api/stream/{run_id}")
async def stream_run(run_id: str):
    """Server-Sent Events stream for real-time pipeline progress."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    async def event_generator():
        # Replay already-seen events for reconnections
        for event in list(run_events.get(run_id, [])):
            yield {"data": json.dumps(event)}
            await asyncio.sleep(0)

        # Stream new events until completion
        last_count = len(run_events.get(run_id, []))
        while True:
            current = run_events.get(run_id, deque())
            events = list(current)
            if len(events) > last_count:
                for event in events[last_count:]:
                    yield {"data": json.dumps(event)}
                last_count = len(events)

            if runs.get(run_id, {}).get("status") in ("complete", "error"):
                break
            await asyncio.sleep(0.3)

    return EventSourceResponse(event_generator())


@app.get("/api/status/{run_id}")
async def get_status(run_id: str):
    """Get the current status of a pipeline run."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return runs[run_id]


@app.get("/api/runs")
async def list_runs():
    """List all runs (most recent first)."""
    return sorted(runs.values(), key=lambda r: r["started_at"], reverse=True)[:20]


# ── Pipeline background task ───────────────────────────────────────────────────

async def _run_pipeline(run_id: str, user_input: str, user_id: int | None = None):
    """Execute the pipeline and push events to the run's event queue."""
    runner = get_runner()
    events = run_events[run_id]

    seen_files = set()
    app_name = None
    project_dir = None

    req_token = request_id_var.set(run_id)
    sess_token = session_id_var.set(run_id)
    usr_token = user_id_var.set(str(user_id) if user_id else "AJ")
    workflow_token = workflow_step_var.set("start")

    logger.user_action("Session Started", username="User" if user_id else "Wahid Jamadar", session_id=run_id, user_id=str(user_id) if user_id else "AJ", request_id=run_id)

    try:
        async for update in runner.run(user_input=user_input, run_id=run_id, user_id=user_id):
            events.append(update)
            stage = update.get("stage", "")
            if stage:
                runs[run_id]["stages"].append({
                    "stage": stage,
                    "label": update.get("label", stage),
                    "timestamp": datetime.utcnow().isoformat(),
                })

            # Check for newly generated files
            if not app_name:
                agent_logs = update.get("data", {}).get("agent_logs", {})
                ra_log = agent_logs.get("requirement_analyzer", {})
                if ra_log.get("app_name"):
                    app_name = ra_log["app_name"]
                    project_dir = Path(settings.output_dir) / app_name
            
            if project_dir and project_dir.exists():
                current = {
                    str(p.relative_to(project_dir)).replace("\\", "/")
                    for p in project_dir.rglob("*")
                    if p.is_file()
                }
                new_files = current - seen_files
                for rel in sorted(new_files):
                    from modules.build_complete_project.generator import _detect_file_type
                    ftype = _detect_file_type(rel)
                    events.append({
                        "type": "file_update",
                        "stage": stage,
                        "label": f"Generated: {rel}",
                        "data": {
                            "name": rel,
                            "type": ftype,
                            "status": "completed"
                        }
                    })
                seen_files = current

            if update["type"] == "complete":
                # Final scan
                if not app_name:
                    app_name = update.get("data", {}).get("app_name", "generated_app")
                    project_dir = Path(settings.output_dir) / app_name
                if project_dir and project_dir.exists():
                    current = {
                        str(p.relative_to(project_dir)).replace("\\", "/")
                        for p in project_dir.rglob("*")
                        if p.is_file()
                    }
                    new_files = current - seen_files
                    for rel in sorted(new_files):
                        from modules.build_complete_project.generator import _detect_file_type
                        ftype = _detect_file_type(rel)
                        events.append({
                            "type": "file_update",
                            "stage": stage,
                            "label": f"Generated: {rel}",
                            "data": {
                                "name": rel,
                                "type": ftype,
                                "status": "completed"
                            }
                        })
                    seen_files = current

                runs[run_id]["status"] = "complete"
                runs[run_id]["result"] = update.get("data", {})
                runs[run_id]["completed_at"] = datetime.utcnow().isoformat()
                
                logger.user_action("Task Completed", username="AJ", session_id=run_id, user_id="AJ", request_id=run_id)
                logger.user_action("Session Closed", username="AJ", session_id=run_id, user_id="AJ", request_id=run_id)

            elif update["type"] == "error":
                runs[run_id]["status"] = "error"
                runs[run_id]["errors"].append(update.get("data", {}).get("error", "Unknown error"))
                runs[run_id]["completed_at"] = datetime.utcnow().isoformat()
                
                logger.user_action("Task Cancelled" if "halt" in stage else "Task Failed", username="AJ", session_id=run_id, user_id="AJ", request_id=run_id)
                logger.user_action("Session Closed", username="AJ", session_id=run_id, user_id="AJ", request_id=run_id)

    except Exception as exc:
        logger.exception(f"[UI] Pipeline run {run_id} crashed: {exc}")
        error_event = {"type": "error", "stage": "crash", "label": str(exc), "data": {}}
        events.append(error_event)
        runs[run_id]["status"] = "error"
        runs[run_id]["errors"].append(str(exc))
        runs[run_id]["completed_at"] = datetime.utcnow().isoformat()
        
        logger.user_action("Task Failed", username="AJ", session_id=run_id, user_id="AJ", request_id=run_id)
        logger.user_action("Session Closed", username="AJ", session_id=run_id, user_id="AJ", request_id=run_id)
        
    finally:
        try:
            request_id_var.reset(req_token)
        except ValueError:
            request_id_var.set("")
        try:
            session_id_var.reset(sess_token)
        except ValueError:
            session_id_var.set("")
        try:
            user_id_var.reset(usr_token)
        except ValueError:
            user_id_var.set("")
        try:
            workflow_step_var.reset(workflow_token)
        except ValueError:
            workflow_step_var.set("")


# ── Serve React frontend ───────────────────────────────────────────────────────
import os
from pathlib import Path
from fastapi.responses import HTMLResponse

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/app")
    @app.get("/app/{path:path}")
    async def serve_react_app(request: Request, path: str = ""):
        react_index = static_dir / "react" / "index.html"
        if react_index.exists():
            return FileResponse(str(react_index))
        return HTMLResponse("<h1>Cytron.AI</h1><p>React UI not built yet. Run 'npm run build' in ui/frontend.</p>")

    @app.get("/")
    async def root():
        # Serve splash.html directly on root
        splash_file = static_dir / "splash.html"
        if splash_file.exists():
            return FileResponse(str(splash_file))
        return RedirectResponse(url="/hub")
else:
    @app.get("/")
    async def root():
        return HTMLResponse("<h1>Cytron.AI</h1><p>UI not built yet.</p>")

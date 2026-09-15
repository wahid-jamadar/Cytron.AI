from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from modules.database.connection import get_db
from modules.database.models import AgentTask, AgentRun, Project, FeatureFlag, UserPreferences, HistoryEvent
from modules.auth.rbac import get_current_user
from modules.common.utils import templates
from modules.build_complete_project.tech_registry import FRONTEND_REGISTRY, BACKEND_REGISTRY, ARCH_REGISTRY
from config.settings import settings

router = APIRouter()

# ── Page Routes ───────────────────────────────────────────────────────────────
@router.get("/hub")
async def hub_page(request: Request):
    return templates.TemplateResponse("hub.html", {"request": request})

@router.get("/states")
async def states_page(request: Request):
    return templates.TemplateResponse("states_showcase.html", {"request": request})

@router.get("/agents")
async def agents_page(request: Request):
    return templates.TemplateResponse("agents.html", {"request": request})

@router.get("/workflows")
async def workflows_page(request: Request):
    return templates.TemplateResponse("workflows.html", {"request": request})

@router.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

@router.get("/templates")
async def templates_page(request: Request):
    return templates.TemplateResponse("templates.html", {"request": request})

@router.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


# ── REST API Routes (Real-time data, no mock data) ───────────────────────────

# 1. Agents Telemetry & Restart API
@router.get("/api/hub/agents")
async def get_hub_agents(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    tasks = db.query(AgentTask).order_by(AgentTask.updated_at.desc()).all()
    return [{
        "id": t.id,
        "agent_name": t.agent_name,
        "status": t.status,
        "execution_duration_ms": t.execution_duration_ms,
        "progress_pct": t.progress_pct,
        "cpu_usage": t.cpu_usage,
        "memory_usage": t.memory_usage,
        "output_stage": t.output_stage,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None
    } for t in tasks]

@router.post("/api/hub/agents/{task_id}/restart")
async def restart_agent_task(task_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")
    task.status = "initializing"
    task.progress_pct = 0.0
    db.commit()
    return {"status": "success", "message": f"Signalled restart for agent {task.agent_name}"}

# 2. Workflows & Run Progress API
@router.get("/api/hub/workflows")
async def get_hub_workflows(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    runs = db.query(AgentRun).order_by(AgentRun.created_at.desc()).all()
    results = []
    for run in runs:
        project = db.query(Project).filter(Project.id == run.project_id).first()
        project_name = project.name if project else "Unknown Project"
        tasks = [{
            "id": t.id,
            "agent_name": t.agent_name,
            "status": t.status,
            "progress_pct": t.progress_pct,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        } for t in run.tasks]
        results.append({
            "id": run.id,
            "project_id": run.project_id,
            "project_name": project_name,
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "tasks": tasks
        })
    return results

from fastapi import Query
from sqlalchemy import or_, and_, func

# 3. Runs History API
@router.get("/api/hub/history")
async def get_hub_history(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    agent: str = Query(None),
    activity: str = Query(None),
    status: str = Query(None),
    search: str = Query(None)
):
    query = db.query(HistoryEvent)
    
    # Filter by user (assuming users can only see their own history unless they are an admin. For simplicity, we just return the events for the current user. To be more comprehensive, we might want to check roles, but let's stick to the current user's runs for now).
    query = query.filter(HistoryEvent.user_id == current_user.id)
    
    if agent and agent != "all":
        query = query.filter(HistoryEvent.agent_name == agent)
    if activity and activity != "all":
        query = query.filter(HistoryEvent.activity_type == activity)
    if status and status != "all":
        query = query.filter(HistoryEvent.status == status)
        
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(
            HistoryEvent.project_name.ilike(search_pattern),
            HistoryEvent.agent_name.ilike(search_pattern),
            HistoryEvent.activity_type.ilike(search_pattern),
            HistoryEvent.execution_id.ilike(search_pattern),
            HistoryEvent.error.ilike(search_pattern)
        ))
        
    total = query.count()
    events = query.order_by(HistoryEvent.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for event in events:
        results.append({
            "id": event.id,
            "agent_name": event.agent_name,
            "activity_type": event.activity_type,
            "action_type": event.action_type,
            "project_name": event.project_name,
            "status": event.status,
            "result": event.result,
            "error_details": event.error,
            "error_code": event.error_code,
            "duration_ms": event.duration_ms,
            "execution_id": event.execution_id,
            "workflow_id": event.workflow_id,
            "files_generated": event.files_generated,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "completed_at": event.completed_at.isoformat() if event.completed_at else None,
            "input_summary": event.input_summary,
            "output_summary": event.output_summary,
        })
        
    return {
        "items": results,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/api/hub/history/statistics")
async def get_hub_history_statistics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    agent: str = Query(None),
    activity: str = Query(None),
    status: str = Query(None),
    search: str = Query(None)
):
    query = db.query(HistoryEvent).filter(HistoryEvent.user_id == current_user.id)
    
    if agent and agent != "all":
        query = query.filter(HistoryEvent.agent_name == agent)
    if activity and activity != "all":
        query = query.filter(HistoryEvent.activity_type == activity)
    if status and status != "all":
        query = query.filter(HistoryEvent.status == status)
        
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(
            HistoryEvent.project_name.ilike(search_pattern),
            HistoryEvent.agent_name.ilike(search_pattern),
            HistoryEvent.activity_type.ilike(search_pattern),
            HistoryEvent.execution_id.ilike(search_pattern),
            HistoryEvent.error.ilike(search_pattern)
        ))
        
    total_activities = query.count()
    successful = query.filter(HistoryEvent.status.in_(["COMPLETED", "SUCCESS"])).count()
    failed = query.filter(HistoryEvent.status.in_(["FAILED", "ERROR"])).count()
    running = query.filter(HistoryEvent.status.in_(["RUNNING", "IN_PROGRESS"])).count()
    
    agents_used = query.with_entities(HistoryEvent.agent_name).filter(HistoryEvent.agent_name.isnot(None)).distinct().count()
    
    return {
        "total_activities": total_activities,
        "successful": successful,
        "failed": failed,
        "running": running,
        "agents_used": agents_used
    }

@router.get("/api/hub/history/export")
async def export_hub_history(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    agent: str = Query(None),
    activity: str = Query(None),
    status: str = Query(None),
    search: str = Query(None)
):
    import csv
    from io import StringIO
    from fastapi.responses import StreamingResponse
    
    query = db.query(HistoryEvent).filter(HistoryEvent.user_id == current_user.id)
    
    if agent and agent != "all":
        query = query.filter(HistoryEvent.agent_name == agent)
    if activity and activity != "all":
        query = query.filter(HistoryEvent.activity_type == activity)
    if status and status != "all":
        query = query.filter(HistoryEvent.status == status)
        
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(
            HistoryEvent.project_name.ilike(search_pattern),
            HistoryEvent.agent_name.ilike(search_pattern),
            HistoryEvent.activity_type.ilike(search_pattern),
            HistoryEvent.execution_id.ilike(search_pattern),
            HistoryEvent.error.ilike(search_pattern)
        ))
        
    events = query.order_by(HistoryEvent.created_at.desc()).limit(10000).all() # limit to 10k for safety
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Created At", "Agent", "Activity", "Action Type", 
        "Target/Project", "Status", "Result", "Duration (ms)", "Error"
    ])
    
    for event in events:
        writer.writerow([
            event.id,
            event.created_at.isoformat() if event.created_at else "",
            event.agent_name or "",
            event.activity_type or "",
            event.action_type or "",
            event.project_name or "",
            event.status or "",
            event.result or "",
            event.duration_ms or "",
            event.error or ""
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=history_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"}
    )


# 4. Tech Registry Templates API
@router.get("/api/hub/templates")
async def get_hub_templates(current_user = Depends(get_current_user)):
    frontend_templates = []
    for key, config in FRONTEND_REGISTRY.items():
        frontend_templates.append({
            "id": key,
            "name": config.name,
            "prompt_guidelines": config.prompt_guidelines,
            "files_schema": config.files_schema,
            "key_deps": config.key_deps
        })
    backend_templates = []
    for key, config in BACKEND_REGISTRY.items():
        backend_templates.append({
            "id": key,
            "name": config.name,
            "language": config.language,
            "prompt_guidelines": config.prompt_guidelines,
            "files_schema": config.files_schema,
            "key_deps": config.key_deps
        })
    arch_templates = []
    for key, config in ARCH_REGISTRY.items():
        arch_templates.append({
            "id": key,
            "name": config.name,
            "prompt_guidelines": config.prompt_guidelines
        })
    return {
        "frontend": frontend_templates,
        "backend": backend_templates,
        "architecture": arch_templates
    }

# 5. User Settings & Feature Flags API
class UserPreferencesUpdateRequest(BaseModel):
    preferred_provider: str
    preferred_language: str
    ui_theme: str
    timezone: str
    notification_preferences: str

class FlagToggleRequest(BaseModel):
    is_enabled: bool

@router.get("/api/hub/settings")
async def get_hub_settings(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        
    flags = db.query(FeatureFlag).all()
    
    system_config = {
        "groq_model": settings.groq_model,
        "github_org": settings.github_org,
        "github_default_visibility": settings.github_default_visibility,
        "gcp_project_id": settings.gcp_project_id,
        "gcp_region": settings.gcp_region,
        "gcp_artifact_registry": settings.gcp_artifact_registry,
        "max_retry_cycles": settings.max_retry_cycles,
        "pipeline_timeout_seconds": settings.pipeline_timeout_seconds,
        "ui_host": settings.ui_host,
        "ui_port": settings.ui_port,
        "github_token_configured": bool(settings.github_token),
        "gcp_configured": settings.gcp_enabled
    }
    
    return {
        "preferences": {
            "preferred_provider": prefs.preferred_provider,
            "preferred_language": prefs.preferred_language,
            "ui_theme": prefs.ui_theme,
            "timezone": prefs.timezone,
            "notification_preferences": prefs.notification_preferences
        },
        "system": system_config,
        "feature_flags": [{
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "is_enabled": f.is_enabled
        } for f in flags]
    }

@router.post("/api/hub/settings/save")
async def save_hub_settings(req: UserPreferencesUpdateRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    prefs = db.query(UserPreferences).filter(UserPreferences.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
    
    prefs.preferred_provider = req.preferred_provider
    prefs.preferred_language = req.preferred_language
    prefs.ui_theme = req.ui_theme
    prefs.timezone = req.timezone
    prefs.notification_preferences = req.notification_preferences
    
    db.commit()
    return {"status": "success", "message": "Preferences updated successfully"}

@router.post("/api/hub/settings/flags/{flag_id}")
async def toggle_feature_flag(flag_id: int, req: FlagToggleRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
        
    flag.is_enabled = req.is_enabled
    db.commit()
    return {"status": "success", "message": f"Feature flag '{flag.name}' status updated to {flag.is_enabled}"}
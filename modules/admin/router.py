import psutil
import csv
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from modules.database.connection import get_db
from modules.database.models import (
    User, Role, Project, Organization, AuditLog, SecurityEvent, 
    FeatureFlag, AIRequest, TokenUsage, AgentRun, AgentTask, ApiKey,
    UserPreferences, SystemSettings, Session as UserSession
)
from modules.auth.rbac import has_role, has_permission, get_current_user
from modules.auth.service import create_access_token

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(has_permission("admin.access"))])

# ── Pydantic Request Schemas ──────────────────────────────────────────────────

class UserStatusRequest(BaseModel):
    status: str # active, suspended, banned

class UserRoleRequest(BaseModel):
    role_name: str

class OrgQuotaRequest(BaseModel):
    storage_quota_gb: float
    ai_quota_requests: int
    project_limit: int

class FeatureFlagRequest(BaseModel):
    is_enabled: bool

class PricingRequest(BaseModel):
    provider: str
    model: str
    input_cost_per_m: float
    output_cost_per_m: float

# ── 1. Admin Dashboard Metrics ───────────────────────────────────────────────

@router.get("/dashboard/metrics", dependencies=[Depends(has_permission("read:admin_dashboard"))])
async def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Fetch dashboard counters and utilization metrics."""
    # 1. User Counters
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.status == "active").count()
    suspended_users = db.query(User).filter(User.status == "suspended").count()
    
    # Online users: active sessions in the last 15 minutes
    fifteen_mins_ago = datetime.utcnow() - timedelta(minutes=15)
    online_users = db.query(func.count(func.distinct(UserSession.user_id)))\
        .filter(UserSession.is_active == True, UserSession.created_at >= fifteen_mins_ago).scalar() or 0
        
    # 2. Projects Counters
    total_projects = db.query(Project).filter(Project.is_deleted == False).count()
    running_projects = db.query(Project).filter(Project.status == "running", Project.is_deleted == False).count()
    projects_today = db.query(Project).filter(Project.created_at >= datetime.utcnow().date(), Project.is_deleted == False).count()
    
    # 3. AI / Token Counters
    total_llm_requests = db.query(AIRequest).count()
    tokens_consumed = db.query(func.sum(AIRequest.total_tokens)).scalar() or 0
    estimated_costs = db.query(func.sum(AIRequest.estimated_cost)).scalar() or 0.0
    requests_today = db.query(AIRequest).filter(AIRequest.created_at >= datetime.utcnow().date()).count()
    
    # 4. Agent Stats
    running_agents = db.query(AgentTask).filter(AgentTask.status == "running").count()
    failed_agents = db.query(AgentTask).filter(AgentTask.status == "failed").count()
    
    # 5. System Utilization
    cpu_util = psutil.cpu_percent()
    ram_util = psutil.virtual_memory().percent
    disk_util = psutil.disk_usage('/').percent
    db_size_mb = 12.5 # Mock/Calculated database size
    
    # 6. WebSocket connections & Queues (Mock/In-Memory)
    from ui.main import runs
    active_ws_connections = len(runs) * 2 + 3
    active_queue_sizes = len([r for r in runs.values() if r.get("status") == "running"])
    
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "suspended": suspended_users,
            "online": online_users,
        },
        "projects": {
            "total": total_projects,
            "running": running_projects,
            "created_today": projects_today
        },
        "ai": {
            "total_requests": total_llm_requests,
            "tokens_consumed": int(tokens_consumed),
            "estimated_costs": float(round(estimated_costs, 4)),
            "requests_today": requests_today
        },
        "agents": {
            "running": running_agents,
            "failed": failed_agents
        },
        "system": {
            "cpu_util": cpu_util,
            "ram_util": ram_util,
            "disk_util": disk_util,
            "db_size_mb": db_size_mb,
            "ws_connections": active_ws_connections,
            "queue_sizes": active_queue_sizes
        }
    }

@router.get("/dashboard/charts", dependencies=[Depends(has_permission("read:admin_dashboard"))])
async def get_dashboard_charts(db: Session = Depends(get_db)):
    """Retrieve time-series chart data for analytics visualization."""
    # Last 7 days user registration trend
    user_growth = []
    for i in range(6, -1, -1):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        count = db.query(User).filter(func.date(User.created_at) <= date).count()
        user_growth.append({"date": date.strftime("%Y-%m-%d"), "users": count})
        
    # Cost & Token trends last 7 days
    ai_trends = []
    for i in range(6, -1, -1):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        tokens = db.query(func.sum(AIRequest.total_tokens)).filter(func.date(AIRequest.created_at) == date).scalar() or 0
        costs = db.query(func.sum(AIRequest.estimated_cost)).filter(func.date(AIRequest.created_at) == date).scalar() or 0.0
        ai_trends.append({
            "date": date.strftime("%Y-%m-%d"),
            "tokens": int(tokens),
            "cost": float(round(costs, 4))
        })
        
    # Model Usage distribution
    model_counts = db.query(AIRequest.model, func.count(AIRequest.id))\
        .group_by(AIRequest.model).all()
    model_usage = [{"model": m, "count": c} for m, c in model_counts]
    
    # Agent execution trends
    agent_counts = db.query(AgentTask.agent_name, func.count(AgentTask.id))\
        .group_by(AgentTask.agent_name).all()
    agent_trends = [{"agent": name, "count": count} for name, count in agent_counts]

    return {
        "user_growth": user_growth,
        "ai_trends": ai_trends,
        "model_usage": model_usage,
        "agent_trends": agent_trends
    }

# ── 2. User Management ────────────────────────────────────────────────────────

@router.get("/users", dependencies=[Depends(has_permission("read:users"))])
async def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all registered platform users with roles and preferences."""
    active_sessions = db.query(UserSession.user_id).filter(
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).all()
    active_user_ids = {s.user_id for s in active_sessions}
    active_user_ids.add(current_user.id)

    users = db.query(User).filter(User.is_deleted == False).all()
    results = []
    for u in users:
        roles_list = [r.name for r in u.roles]
        prefs = db.query(UserPreferences).filter(UserPreferences.user_id == u.id).first()
        
        if u.status in ["suspended", "banned"]:
            display_status = u.status
        else:
            display_status = "active" if u.id in active_user_ids else "inactive"
            
        results.append({
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "status": display_status,
            "roles": roles_list,
            "created_at": u.created_at,
            "preferences": {
                "preferred_provider": prefs.preferred_provider if prefs else "groq",
                "ui_theme": prefs.ui_theme if prefs else "dark"
            }
        })
    return results

@router.put("/users/{user_id}/status", dependencies=[Depends(has_permission("write:users"))])
async def update_user_status(user_id: int, request: UserStatusRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ban or suspend user logins."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot alter your own status")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_status = user.status
    user.status = request.status
    
    # Log audit event
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="update_user_status",
        resource="users",
        resource_id=user_id,
        old_values=f"status: {old_status}",
        new_values=f"status: {request.status}",
        result="success"
    )
    db.add(audit)
    db.commit()
    return {"message": f"User status updated from {old_status} to {request.status}"}

@router.put("/users/{user_id}/role", dependencies=[Depends(has_permission("write:users"))])
async def change_user_role(user_id: int, request: UserRoleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Change a user's RBAC role assignments."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    role = db.query(Role).filter(Role.name == request.role_name).first()
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{request.role_name}' does not exist")
        
    # Restrict SUPER_ADMIN role assignment or revocation to SUPER_ADMINs only
    current_user_roles = [r.name for r in current_user.roles]
    is_acting_super_admin = "SUPER_ADMIN" in current_user_roles
    target_is_super_admin = request.role_name == "SUPER_ADMIN"
    user_is_super_admin = any(r.name == "SUPER_ADMIN" for r in user.roles)
    
    if (target_is_super_admin or user_is_super_admin) and not is_acting_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a SUPER_ADMIN can assign or revoke the SUPER_ADMIN role."
        )
        
    old_roles = ", ".join([r.name for r in user.roles])
    user.roles = [role] # assign single role for now
    
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="change_user_role",
        resource="users",
        resource_id=user_id,
        old_values=f"roles: {old_roles}",
        new_values=f"roles: {request.role_name}",
        result="success"
    )
    db.add(audit)
    db.commit()
    return {"message": f"User roles updated to {request.role_name}"}

@router.post("/users/{user_id}/impersonate", dependencies=[Depends(has_permission("impersonate:users"))])
async def impersonate_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Impersonate a user securely for support and debugging."""
    # Ensure only SUPER_ADMIN or ADMIN can impersonate
    admin_roles = [r.name for r in current_user.roles]
    if "SUPER_ADMIN" not in admin_roles and "ADMIN" not in admin_roles:
        raise HTTPException(status_code=403, detail="Unprivileged action")
        
    target_user = db.query(User).filter(User.id == user_id, User.status == "active").first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found or inactive")
        
    # Generate token
    roles_list = [r.name for r in target_user.roles]
    impersonate_token = create_access_token(target_user.id, target_user.email, roles_list)
    
    # Log Audit
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="impersonate_user",
        resource="users",
        resource_id=user_id,
        old_values=None,
        new_values=f"Impersonated user: {target_user.email}",
        result="success"
    )
    db.add(audit)
    db.commit()
    
    return {
        "access_token": impersonate_token,
        "token_type": "bearer",
        "message": f"Impersonating user '{target_user.email}'"
    }

@router.delete("/users/{user_id}", dependencies=[Depends(has_permission("write:users"))])
async def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Soft delete a user."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    target_user.is_deleted = True
    target_user.deleted_at = datetime.utcnow()
    target_user.status = "suspended" # Suspend them to prevent further logins
    
    # Log Audit
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="delete_user",
        resource="users",
        resource_id=user_id,
        old_values=f"is_deleted: False",
        new_values=f"is_deleted: True",
        result="success"
    )
    db.add(audit)
    db.commit()
    
    return {"message": f"User '{target_user.email}' deleted successfully"}

# ── 3. Project Management ─────────────────────────────────────────────────────

@router.get("/projects", dependencies=[Depends(has_permission("read:projects"))])
async def list_all_projects(db: Session = Depends(get_db)):
    """List all projects across organizations."""
    projects = db.query(Project).filter(Project.is_deleted == False).order_by(Project.created_at.desc()).all()
    return [{
        "id": p.id,
        "name": p.name,
        "status": p.status,
        "owner_email": p.owner.email if p.owner else None,
        "organization": p.organization.name if p.organization else None,
        "deployment_status": p.deployment_status,
        "is_archived": p.is_archived,
        "created_at": p.created_at,
        "updated_at": p.updated_at
    } for p in projects]

@router.post("/projects/{project_id}/archive", dependencies=[Depends(has_permission("archive:projects"))])
async def archive_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Archive projects to reduce active cloud footprint."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project.is_archived = True
    project.status = "archived"
    
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="archive_project",
        resource="projects",
        resource_id=project_id,
        result="success"
    )
    db.add(audit)
    db.commit()
    return {"message": "Project archived successfully"}

@router.delete("/projects/{project_id}", dependencies=[Depends(has_permission("delete:projects"))])
async def soft_delete_project(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Soft delete projects, retaining records for recovery window."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="soft_delete_project",
        resource="projects",
        resource_id=project_id,
        result="success"
    )
    db.add(audit)
    db.commit()
    return {"message": "Project soft deleted successfully"}

# ── 4. AI Agent Monitoring & Telemetry ───────────────────────────────────────

@router.get("/agents/status", dependencies=[Depends(has_permission("read:admin_dashboard"))])
async def get_agents_telemetry(db: Session = Depends(get_db)):
    """Fetch live status, resource loads, and metrics for all agent nodes."""
    tasks = db.query(AgentTask).order_by(AgentTask.updated_at.desc()).all()
    
    unique_agents = {}
    for t in tasks:
        if t.agent_name not in unique_agents:
            unique_agents[t.agent_name] = t
            
    return [{
        "id": t.id,
        "agent_name": t.agent_name,
        "status": t.status,
        "execution_duration_ms": t.execution_duration_ms,
        "progress_pct": t.progress_pct,
        "cpu_usage": t.cpu_usage,
        "memory_usage": t.memory_usage,
        "output_stage": t.output_stage,
        "updated_at": t.updated_at
    } for t in unique_agents.values()]

@router.post("/agents/{task_id}/restart", dependencies=[Depends(has_permission("write:system_settings"))])
async def restart_agent_node(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Restart or retry a stuck agent node execution."""
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Agent task not found")

    task.status = "initializing"
    task.progress_pct = 0.0
    
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="restart_agent_node",
        resource="agent_tasks",
        resource_id=task_id,
        result="success"
    )
    db.add(audit)
    db.commit()
    return {"message": f"Signalled restart for agent {task.agent_name}"}

# ── 5. Feature Flags ─────────────────────────────────────────────────────────

@router.get("/feature-flags", dependencies=[Depends(has_permission("read:admin_dashboard"))])
async def list_feature_flags(db: Session = Depends(get_db)):
    """List system feature flags configuration."""
    return db.query(FeatureFlag).all()

@router.put("/feature-flags/{flag_id}", dependencies=[Depends(has_permission("write:system_settings"))])
async def update_feature_flag(flag_id: int, request: FeatureFlagRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Toggle experimental features or agent gates dynamically."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found")
        
    old_val = flag.is_enabled
    flag.is_enabled = request.is_enabled
    
    audit = AuditLog(
        acting_user_id=current_user.id,
        action="update_feature_flag",
        resource="feature_flags",
        resource_id=flag_id,
        old_values=f"enabled: {old_val}",
        new_values=f"enabled: {request.is_enabled}",
        result="success"
    )
    db.add(audit)
    db.commit()
    return {"message": f"Feature flag '{flag.name}' updated successfully"}

# ── 6. Audit Logs ─────────────────────────────────────────────────────────────

@router.get("/audit-logs", dependencies=[Depends(has_permission("read:logs"))])
async def get_audit_logs(db: Session = Depends(get_db)):
    """Retrieve platform logs."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return [{
        "id": l.id,
        "user": db.query(User.email).filter(User.id == l.acting_user_id).scalar() if l.acting_user_id else "System",
        "action": l.action,
        "resource": l.resource,
        "resource_id": l.resource_id,
        "ip_address": l.ip_address,
        "old_values": l.old_values,
        "new_values": l.new_values,
        "result": l.result,
        "created_at": l.created_at
    } for l in logs]

# ── 7. Reports Exporter ───────────────────────────────────────────────────────

@router.get("/reports/export", dependencies=[Depends(has_permission("read:logs"))])
async def export_report(format: str = "csv", db: Session = Depends(get_db)):
    """Export users audit trail and usage logs as CSV or JSON."""
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
        
    projects = db.query(Project).all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Name", "Status", "Deployment Status", "Storage MB", "Created At"])
        for p in projects:
            writer.writerow([p.id, p.name, p.status, p.deployment_status, p.storage_usage_mb, p.created_at.strftime("%Y-%m-%d")])
            
        response = Response(content=output.getvalue(), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=projects_report.csv"
        return response
        
    else: # JSON
        data = [{
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "deployment_status": p.deployment_status,
            "storage_usage_mb": p.storage_usage_mb,
            "created_at": p.created_at.isoformat()
        } for p in projects]
        return data

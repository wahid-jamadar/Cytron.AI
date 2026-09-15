from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, Table, Index
from sqlalchemy.orm import relationship
from modules.database.connection import Base

# ── Many-to-Many Association Tables ──────────────────────────────────────────

user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('org_id', Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True) # Optional org-scoped roles
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

# ── Core Authentication Models ───────────────────────────────────────────────

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(191), unique=True, index=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    status = Column(String(20), default="active") # active, suspended, banned
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    preferences = relationship("UserPreferences", uselist=False, back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    password_history = relationship("PasswordHistory", back_populates="user", cascade="all, delete-orphan")
    organizations = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False) # USER, ADMIN, SUPER_ADMIN, SUPPORT, READ_ONLY_ADMIN
    description = Column(String(255), nullable=True)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False) # e.g. read:projects, write:users
    description = Column(String(255), nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class UserPreferences(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    preferred_provider = Column(String(50), default="groq")
    preferred_language = Column(String(50), default="javascript")
    ui_theme = Column(String(20), default="dark") # dark, light, oled
    timezone = Column(String(50), default="UTC")
    notification_preferences = Column(Text, default="all") # JSON string or text preference
    dashboard_widgets = Column(Text, default="[]") # JSON list of widgets
    avatar_url = Column(String(255), nullable=True)
    
    user = relationship("User", back_populates="preferences")

class Session(Base):
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="sessions")

class PasswordHistory(Base):
    __tablename__ = 'password_history'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="password_history")

class LoginHistory(Base):
    __tablename__ = 'login_history'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False) # success, failed
    details = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="login_history")

# ── Organization & Teams Models ──────────────────────────────────────────────

class Organization(Base):
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    storage_quota_gb = Column(Float, default=10.0)
    ai_quota_requests = Column(Integer, default=1000)
    project_limit = Column(Integer, default=20)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization")

class OrganizationMember(Base):
    __tablename__ = 'organization_members'
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_name = Column(String(50), default="MEMBER") # ADMIN, MEMBER
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organizations")

class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

class TeamMember(Base):
    __tablename__ = 'team_members'
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    team = relationship("Team", back_populates="members")

# ── Project Models ───────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    name = Column(String(100), nullable=False)
    status = Column(String(50), default="queued") # queued, running, completed, error, archived
    deployment_status = Column(String(50), default="none") # none, deploying, active, failed
    storage_usage_mb = Column(Float, default=0.0)
    is_archived = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    history = relationship("ProjectHistory", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="project", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="project", cascade="all, delete-orphan")

class ProjectMember(Base):
    __tablename__ = 'project_members'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), default="collaborator") # owner, collaborator, reader
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="members")

class ProjectHistory(Base):
    __tablename__ = 'project_history'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False) # e.g. "code_generation", "deployment"
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="history")

class ProjectFile(Base):
    __tablename__ = 'project_files'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    filepath = Column(String(255), nullable=False)
    filetype = Column(String(50), nullable=True)
    size_bytes = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="files")

# ── Chat & Conversation Models ────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(150), default="New Agent Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    sender_type = Column(String(20), nullable=False) # user, agent
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

# ── AI Metrics, Tokens, & Cost Tracking ──────────────────────────────────────

class AIRequest(Base):
    __tablename__ = 'ai_requests'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    agent_name = Column(String(100), nullable=True)
    provider = Column(String(50), nullable=False) # OpenAI, Anthropic, Gemini, Groq, etc.
    model = Column(String(100), nullable=False)
    prompt_size = Column(Integer, default=0)
    completion_size = Column(Integer, default=0)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)
    temperature = Column(Float, default=0.0)
    top_p = Column(Float, default=1.0)
    status_code = Column(Integer, default=200)
    request_status = Column(String(20), default="success") # success, error
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TokenUsage(Base):
    __tablename__ = 'token_usage'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    token_count = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    agent_name = Column(String(100), nullable=True)

class CostTracking(Base):
    __tablename__ = 'cost_tracking'
    
    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(50), nullable=False) # user, organization, project
    target_id = Column(Integer, nullable=False)
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

# ── Agent Runs & Observability ────────────────────────────────────────────────

class AgentRun(Base):
    __tablename__ = 'agent_runs'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    status = Column(String(50), default="running") # running, completed, failed
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    tasks = relationship("AgentTask", back_populates="run", cascade="all, delete-orphan")
    logs = relationship("AgentLog", back_populates="run", cascade="all, delete-orphan")

class AgentTask(Base):
    __tablename__ = 'agent_tasks'
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(50), default="initializing") # idle, initializing, running, waiting, queued, failed, completed
    input_prompt = Column(Text, nullable=True)
    output_stage = Column(Text, nullable=True)
    execution_duration_ms = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    run = relationship("AgentRun", back_populates="tasks")

class AgentLog(Base):
    __tablename__ = 'agent_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False)
    agent_name = Column(String(100), nullable=False)
    log_level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("AgentRun", back_populates="logs")

# ── Audit, Logging & Compliance ──────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    acting_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False) # e.g. login, delete_project, impersonate
    resource = Column(String(100), nullable=True) # e.g. projects, users
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    old_values = Column(Text, nullable=True) # JSON details
    new_values = Column(Text, nullable=True) # JSON details
    result = Column(String(50), default="success") # success, failed
    created_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    event_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class HistoryEvent(Base):
    __tablename__ = 'history_events'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    agent_id = Column(String(100), nullable=True)
    agent_name = Column(String(100), nullable=True)
    activity_type = Column(String(100), nullable=False)
    action_type = Column(String(50), nullable=False) # USER, AGENT, SYSTEM
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), nullable=True)
    project_name = Column(String(255), nullable=True)
    workflow_id = Column(String(100), nullable=True)
    execution_id = Column(String(100), nullable=True)
    parent_execution_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False) # QUEUED, RUNNING, COMPLETED, FAILED, etc.
    result = Column(String(50), nullable=True)
    error = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    files_generated = Column(Text, nullable=True) # JSON list
    metadata_json = Column(Text, nullable=True) # JSON
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SecurityEvent(Base):
    __tablename__ = 'security_events'
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False) # e.g. failed_login, brute_force_suspect
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    severity = Column(String(20), default="medium") # low, medium, high, critical
    created_at = Column(DateTime, default=datetime.utcnow)

# ── General System Models ────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="general") # info, success, warning, error, billing, security
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="notifications")

class FeatureFlag(Base):
    __tablename__ = 'feature_flags'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    description = Column(String(255), nullable=True)

class ApiKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True) # Null if global system API key
    provider = Column(String(50), nullable=False) # openai, anthropic, groq, etc.
    encrypted_key = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="api_keys")

class SystemSettings(Base):
    __tablename__ = 'system_settings'
    
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, index=True, nullable=False)
    setting_value = Column(Text, nullable=True)

class Deployment(Base):
    __tablename__ = 'deployments'
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    app_url = Column(String(255), nullable=True)
    repo_url = Column(String(255), nullable=True)
    status = Column(String(50), default="deploying") # deploying, active, failed
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    project = relationship("Project", back_populates="deployments")

class Report(Base):
    __tablename__ = 'reports'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    file_path = Column(String(255), nullable=False)
    format = Column(String(20), nullable=False) # CSV, EXCEL, JSON, PDF
    created_at = Column(DateTime, default=datetime.utcnow)

# ── Index Definitions ────────────────────────────────────────────────────────
Index('idx_audit_logs_action', AuditLog.action)
Index('idx_audit_logs_user', AuditLog.acting_user_id)
Index('idx_ai_requests_user', AIRequest.user_id)
Index('idx_ai_requests_project', AIRequest.project_id)
Index('idx_ai_requests_agent', AIRequest.agent_name)
Index('idx_token_usage_date', TokenUsage.date)
Index('idx_notifications_user_read', Notification.user_id, Notification.is_read)
Index('idx_history_events_user', HistoryEvent.user_id)
Index('idx_history_events_agent', HistoryEvent.agent_name)
Index('idx_history_events_action_type', HistoryEvent.action_type)
Index('idx_history_events_status', HistoryEvent.status)
Index('idx_history_events_created_at', HistoryEvent.created_at)

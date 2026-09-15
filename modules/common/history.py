import json
from datetime import datetime
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session
from modules.database.models import HistoryEvent

def log_history_event(
    db: Session,
    activity_type: str,
    action_type: str,
    status: str,
    user_id: Optional[int] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    project_id: Optional[int] = None,
    project_name: Optional[str] = None,
    workflow_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    parent_execution_id: Optional[str] = None,
    result: Optional[str] = None,
    error: Optional[str] = None,
    error_code: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    duration_ms: Optional[int] = None,
    input_summary: Optional[str] = None,
    output_summary: Optional[str] = None,
    files_generated: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None
) -> HistoryEvent:
    """
    Standardized utility for logging activity and execution history events.
    """
    event = HistoryEvent(
        user_id=user_id,
        agent_id=agent_id,
        agent_name=agent_name,
        activity_type=activity_type,
        action_type=action_type,
        project_id=project_id,
        project_name=project_name,
        workflow_id=workflow_id,
        execution_id=execution_id,
        parent_execution_id=parent_execution_id,
        status=status,
        result=result,
        error=error,
        error_code=error_code,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        input_summary=input_summary,
        output_summary=output_summary,
        files_generated=json.dumps(files_generated) if files_generated is not None else None,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
        source=source,
        created_at=datetime.utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

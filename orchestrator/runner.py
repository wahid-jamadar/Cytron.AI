"""
orchestrator/runner.py
───────────────────────
Pipeline runner with real-time progress streaming.

Used by both the CLI (main.py) and the Web UI (ui/main.py) to execute the
pipeline graph and yield stage-by-stage updates to the caller.
"""

import asyncio
import time
import logging
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from config.settings import settings
from state.pipeline_state import PipelineState, initial_state
from orchestrator.graph import build_graph

from datetime import datetime
from modules.common.logger import platform_logger, metrics_collector, session_id_var, request_id_var, user_id_var, workflow_step_var, db_run_id_var
logger = platform_logger


# ── Stage display labels ───────────────────────────────────────────────────────
STAGE_LABELS: dict[str, str] = {
    "start":                         "Pipeline started",
    "requirement_analyzer_complete": "Requirements analyzed",
    "project_planner_complete":      "Project plan created",
    "frontend_agent_complete":       "Frontend generated",
    "backend_agent_complete":        "Backend generated",
    "database_agent_complete":       "Database schema generated",
    "build_agents_complete":         "All build agents done",
    "code_review_complete":          "Code review complete",
    "testing_agent_complete":        "Tests executed",
    "bug_fixing_complete":           "Bug fixes applied",
    "deployment_agent_complete":     "Deployment complete",
    "documentation_complete":        "Documentation generated",
    "repository_agent_complete":     "Repository created",
    "halted":                        "Pipeline halted (max retries exceeded)",
}


def _safe_label(stage: str) -> str:
    return STAGE_LABELS.get(stage, f"{stage.replace('_', ' ').title()}")


class PipelineRunner:
    """
    Wraps the compiled LangGraph and provides an async streaming interface.
    """

    def __init__(self):
        self.graph = build_graph(use_checkpointing=True)

    async def run(
        self,
        user_input: str,
        run_id: str | None = None,
        user_id: int | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Run the full pipeline and yield progress updates as dicts.

        Each yielded dict has the shape:
        {
            "type": "progress" | "complete" | "error",
            "stage": str,
            "label": str,
            "data": dict   # Full or partial pipeline state
        }

        Args:
            user_input: The natural-language application requirement.
            run_id: Optional run identifier (generated if not provided).
            user_id: Optional user identifier to assign project ownership.

        Yields:
            Progress update dicts.
        """
        run_id = run_id or str(uuid.uuid4())[:8]
        thread_config = {"configurable": {"thread_id": run_id}}

        req_token = request_id_var.set(run_id)
        sess_token = session_id_var.set(run_id)
        usr_token = user_id_var.set("AJ")
        workflow_token = workflow_step_var.set("start")

        # Open database session to create project and run records
        from modules.database.connection import SessionLocal
        from modules.database.models import User, Project, AgentRun
        db = SessionLocal()
        
        db_proj_id = None
        db_run_id = None
        
        try:
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
            else:
                # Query admin or first user
                user = db.query(User).filter(User.email == "admin@etoagent.com").first() or \
                       db.query(User).filter(User.email == "wahidjamadar2020@gmail.com").first() or \
                       db.query(User).first()
                       
            user_id_to_use = user.id if user else None
            
            project_name = user_input[:50] + "..." if len(user_input) > 50 else user_input
            project = Project(
                owner_id=user_id_to_use,
                name=project_name,
                status="running",
                deployment_status="none"
            )
            db.add(project)
            db.flush()
            db_proj_id = project.id
            
            agent_run = AgentRun(
                project_id=project.id,
                user_id=user_id_to_use,
                status="running"
            )
            db.add(agent_run)
            db.flush()
            db_run_id = agent_run.id
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to create run/project records in database: {e}")
            db.rollback()
        finally:
            db.close()
            
        db_run_token = None
        if db_run_id:
            db_run_token = db_run_id_var.set(db_run_id)

        def update_db_failure(error_msg: str):
            if db_proj_id and db_run_id:
                try:
                    db_session = SessionLocal()
                    db_run = db_session.query(AgentRun).filter(AgentRun.id == db_run_id).first()
                    if db_run:
                        db_run.status = "failed"
                        db_run.error_details = error_msg
                        db_run.completed_at = datetime.utcnow()
                    db_proj = db_session.query(Project).filter(Project.id == db_proj_id).first()
                    if db_proj:
                        db_proj.status = "error"
                    db_session.commit()
                    db_session.close()
                except Exception as e:
                    logger.warning(f"Failed to update failure state in DB: {e}")

        state = initial_state(
            user_input=user_input,
            max_retries=settings.max_retry_cycles,
        )

        logger.info(f"[Runner] Starting pipeline run {run_id}")
        yield {"type": "progress", "stage": "start", "label": "Starting pipeline...", "data": {}}

        start_time = time.time()
        workflow_nodes = [
            "requirement_analyzer",
            "project_planner",
            "frontend_agent",
            "backend_agent",
            "database_agent",
            "code_review",
            "testing_agent",
            "bug_fixing",
            "deployment",
            "documentation",
            "repository"
        ]

        try:
            async for chunk in self.graph.astream(state, config=thread_config):
                for node_name, node_output in chunk.items():
                    if node_name == "__end__":
                        continue

                    stage = node_output.get("stage", node_name)
                    label = _safe_label(stage)

                    # Highlight the executing node in the active workflow visualization
                    if node_name in workflow_nodes:
                        logger.workflow(nodes=workflow_nodes, active_node=node_name)

                    # Check for halt condition
                    if node_output.get("should_halt"):
                        errors = node_output.get("errors", [])
                        error_msg = "; ".join(errors) if errors else "Pipeline halted"
                        update_db_failure(error_msg)
                        
                        elapsed = time.time() - start_time
                        mins, secs = divmod(elapsed, 60)
                        elapsed_str = f"{int(mins)}m {int(secs)}s"
                        
                        logger.execution_summary({
                            "Project": "N/A",
                            "Execution Time": elapsed_str,
                            "Agents Used": ", ".join(sorted(list(node_output.get("agent_logs", {}).keys()))),
                            "Tools Used": ", ".join(sorted(list(metrics_collector.tools_used))),
                            "LLM Calls": metrics_collector.llm_calls,
                            "API Calls": len(metrics_collector.api_requests),
                            "Database Queries": metrics_collector.db_queries_count,
                            "Files Generated": 0,
                            "Warnings": metrics_collector.warnings_count,
                            "Errors": metrics_collector.errors_count + len(errors),
                            "Total Tokens": metrics_collector.total_tokens,
                            "Average Latency": f"{metrics_collector.get_average_latency():.2f}s",
                            "Peak RAM Usage": f"{metrics_collector.peak_ram:.1f}%",
                            "Peak CPU Usage": f"{metrics_collector.peak_cpu:.1f}%",
                            "Status": "FAILED"
                        })
                        
                        yield {
                            "type": "error",
                            "stage": stage,
                            "label": label,
                            "data": {
                                "errors": errors,
                                "retry_count": node_output.get("retry_count", 0),
                            },
                        }
                        return

                    yield {
                        "type": "progress",
                        "stage": stage,
                        "label": label,
                        "data": _safe_state_summary(node_output),
                    }

            # Retrieve final state
            final_state = await self.graph.aget_state(thread_config)
            final = final_state.values if final_state else {}

            final_summary = _build_final_summary(final)
            
            elapsed = time.time() - start_time
            mins, secs = divmod(elapsed, 60)
            elapsed_str = f"{int(mins)}m {int(secs)}s"
            
            logger.execution_summary({
                "Project": final_summary.get("app_name", "generated_app"),
                "Execution Time": elapsed_str,
                "Agents Used": ", ".join(sorted(list(final.get("agent_logs", {}).keys()))),
                "Tools Used": ", ".join(sorted(list(metrics_collector.tools_used))),
                "LLM Calls": metrics_collector.llm_calls,
                "API Calls": len(metrics_collector.api_requests),
                "Database Queries": metrics_collector.db_queries_count,
                "Files Generated": final_summary.get("total_files", 0),
                "Warnings": metrics_collector.warnings_count,
                "Errors": metrics_collector.errors_count,
                "Total Tokens": metrics_collector.total_tokens,
                "Average Latency": f"{metrics_collector.get_average_latency():.2f}s",
                "Peak RAM Usage": f"{metrics_collector.peak_ram:.1f}%",
                "Peak CPU Usage": f"{metrics_collector.peak_cpu:.1f}%",
                "Status": "SUCCESS"
            })

            if db_proj_id and db_run_id:
                try:
                    from modules.database.connection import SessionLocal
                    from modules.database.models import Project, AgentRun
                    db_session = SessionLocal()
                    
                    # Update AgentRun
                    db_run = db_session.query(AgentRun).filter(AgentRun.id == db_run_id).first()
                    if db_run:
                        db_run.status = "completed"
                        db_run.completed_at = datetime.utcnow()
                        
                    # Update Project
                    db_proj = db_session.query(Project).filter(Project.id == db_proj_id).first()
                    if db_proj:
                        db_proj.status = "completed"
                        db_proj.deployment_status = "active"
                        if final_summary.get("app_name"):
                            db_proj.name = final_summary.get("app_name")
                            
                    db_session.commit()
                    db_session.close()
                except Exception as e:
                    logger.warning(f"Failed to update success run state in DB: {e}")

            yield {
                "type": "complete",
                "stage": "done",
                "label": "Pipeline complete!",
                "data": final_summary,
            }
            logger.info(f"[Runner] Pipeline run {run_id} completed successfully.")

        except Exception as exc:
            logger.exception(f"[Runner] Unhandled pipeline error: {exc}")
            update_db_failure(str(exc))
            
            elapsed = time.time() - start_time
            mins, secs = divmod(elapsed, 60)
            elapsed_str = f"{int(mins)}m {int(secs)}s"
            
            logger.execution_summary({
                "Project": "N/A",
                "Execution Time": elapsed_str,
                "Agents Used": "N/A",
                "Tools Used": ", ".join(sorted(list(metrics_collector.tools_used))),
                "LLM Calls": metrics_collector.llm_calls,
                "API Calls": len(metrics_collector.api_requests),
                "Database Queries": metrics_collector.db_queries_count,
                "Files Generated": 0,
                "Warnings": metrics_collector.warnings_count,
                "Errors": metrics_collector.errors_count + 1,
                "Total Tokens": metrics_collector.total_tokens,
                "Average Latency": f"{metrics_collector.get_average_latency():.2f}s",
                "Peak RAM Usage": f"{metrics_collector.peak_ram:.1f}%",
                "Peak CPU Usage": f"{metrics_collector.peak_cpu:.1f}%",
                "Status": "FAILED"
            })
            
            yield {
                "type": "error",
                "stage": "crash",
                "label": f"Unexpected error: {exc}",
                "data": {"error": str(exc)},
            }
        finally:
            if db_run_id and db_run_token:
                try:
                    db_run_id_var.reset(db_run_token)
                except ValueError:
                    db_run_id_var.set(0)
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


def _safe_state_summary(node_output: dict) -> dict:
    """Extract a safe, serialisable summary from a node output dict."""
    return {
        k: v for k, v in node_output.items()
        if k in (
            "stage", "retry_count", "errors",
            "agent_logs", "repo_url",
        )
    }


def _build_final_summary(final: dict) -> dict:
    """Build a clean final result summary from the completed pipeline state."""
    deployment = final.get("deployment_info") or {}
    docs = final.get("docs") or {}
    spec = final.get("structured_spec") or {}
    plan = final.get("project_plan") or {}
    test_results = final.get("test_results") or {}

    app_name = plan.get("app_name", spec.get("app_name", "app"))
    from pathlib import Path
    from config.settings import settings
    project_dir = settings.output_dir / app_name
    total_files = 0
    total_loc = 0
    if project_dir.exists():
        for p in project_dir.rglob("*"):
            if p.is_file():
                total_files += 1
                if p.suffix in (".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".sql", ".sh", ".yaml", ".yml", ".json"):
                    try:
                        total_loc += sum(1 for _ in p.read_text(encoding="utf-8", errors="ignore").splitlines())
                    except Exception:
                        pass

    return {
        "app_name": app_name,
        "app_url": deployment.get("app_url"),
        "repo_url": final.get("repo_url"),
        "tests_passed": test_results.get("passed", False),
        "test_summary": test_results.get("summary", ""),
        "docker_images": deployment.get("docker_images", []),
        "docs_generated": list((docs.get("files") or {}).keys()),
        "agent_logs": final.get("agent_logs", {}),
        "errors": final.get("errors", []),
        "retry_count": final.get("retry_count", 0),
        "total_files": total_files,
        "total_loc": total_loc,
    }


# ── Module-level singleton ─────────────────────────────────────────────────────
_runner: PipelineRunner | None = None


def get_runner() -> PipelineRunner:
    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner

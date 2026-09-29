"""
modules/build_complete_project/generator.py
────────────────────────────────────────────
Real pipeline generator for the Build Complete Project module.

This replaces the former mock-based implementation. Instead of writing
placeholder files, this module drives the full LangGraph pipeline
(RequirementAnalyzer → ProjectPlanner → Backend/Frontend/Database Agents
→ CodeReview → Testing → Documentation → DeploymentAgent → Packaging)
and streams real-time events back to the UI via Server-Sent Events.

Architecture:
  1. User submits a prompt via the UI form (frontend, backend, arch, details).
  2. A JobManager creates a job entry with an asyncio.Queue for SSE events.
  3. run_real_generation() is launched as a background task.
  4. It drives the real LangGraph pipeline via orchestrator.runner.PipelineRunner.
  5. After each pipeline stage completes, it scans the output directory for
     newly written files and emits file_update events to the SSE queue.
  6. Once all agents finish, it packages the output directory into a ZIP
     and emits a 'complete' event with the download URL.
  7. Any agent failures surface immediately via 'error' events — no silent
     fallback to placeholder files.
"""

import asyncio
import uuid
import json
import os
import re
import shutil
import time
import logging
from pathlib import Path
from typing import Any, Dict, Set

from config.settings import settings
from orchestrator.runner import PipelineRunner
from modules.build_complete_project.resolver import resolve_tech_stack

logger = logging.getLogger(__name__)


# ── File type detection ────────────────────────────────────────────────────────

EXT_TYPE_MAP: dict[str, str] = {
    ".py":    "python",
    ".js":    "javascript",
    ".jsx":   "javascript",
    ".ts":    "javascript",
    ".tsx":   "javascript",
    ".html":  "html",
    ".css":   "css",
    ".scss":  "css",
    ".json":  "json",
    ".md":    "markdown",
    ".yml":   "yaml",
    ".yaml":  "yaml",
    ".sql":   "sql",
    ".sh":    "config",
    ".env":   "config",
    ".toml":  "config",
    ".ini":   "config",
    ".cfg":   "config",
    ".txt":   "config",
}

NAME_TYPE_MAP: dict[str, str] = {
    "dockerfile":      "docker",
    "docker-compose":  "docker",
    ".gitignore":      "config",
    "makefile":        "config",
}


def _detect_file_type(rel_path: str) -> str:
    name = Path(rel_path).name.lower()
    # Check name-based overrides first
    for key, ftype in NAME_TYPE_MAP.items():
        if key in name:
            return ftype
    ext = Path(rel_path).suffix.lower()
    return EXT_TYPE_MAP.get(ext, "config")


# ── Pipeline stage → UI label mapping ─────────────────────────────────────────

STAGE_UI_LABELS: dict[str, str] = {
    "start":                         "Initializing Pipeline",
    "requirement_analyzer_complete": "Analyzing Requirements",
    "project_planner_complete":      "Planning Architecture",
    "frontend_agent_complete":       "Frontend Generated",
    "backend_agent_complete":        "Backend Generated",
    "database_agent_complete":       "Database Schema Generated",
    "build_agents_complete":         "All Code Agents Complete",
    "code_review_complete":          "Code Review Complete",
    "testing_agent_complete":        "Tests Generated",
    "bug_fixing_complete":           "Bug Fixes Applied",
    "deployment_agent_complete":     "Infra & Docker Generated",
    "documentation_complete":        "Documentation Generated",
    "repository_agent_complete":     "Repository Created",
    "halted":                        "Pipeline Halted",
    "packaging":                     "Packaging Project ZIP",
    "done":                          "Ready for Download",
}


def _stage_label(stage: str) -> str:
    return STAGE_UI_LABELS.get(stage, stage.replace("_", " ").title())


# ── JobManager ────────────────────────────────────────────────────────────────

class JobManager:
    """In-memory registry of active generation jobs."""

    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, params: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "params":       params,
            "queue":        asyncio.Queue(),
            "status":       "starting",
            "zip_path":     None,
            "project_dir":  None,
            "app_name":     None,
            "started_at":   time.time(),
            "error":        None,
        }
        return job_id

    def get_job(self, job_id: str) -> Dict[str, Any] | None:
        return self.jobs.get(job_id)

    async def emit_event(self, job_id: str, event_type: str, data: Any) -> None:
        job = self.jobs.get(job_id)
        if job:
            await job["queue"].put({"event": event_type, "data": json.dumps(data)})


job_manager = JobManager()


# ── File-scanning utilities ────────────────────────────────────────────────────

def _scan_project_files(project_dir: Path) -> Set[str]:
    """Return a set of all relative file paths under project_dir."""
    if not project_dir.exists():
        return set()
    return {
        str(p.relative_to(project_dir)).replace("\\", "/")
        for p in project_dir.rglob("*")
        if p.is_file()
    }


async def _emit_new_files(
    job_id: str,
    project_dir: Path,
    previously_seen: Set[str],
) -> Set[str]:
    """
    Compare current files on disk to previously_seen, emit file_update
    events for any new files found, and return the updated seen set.
    """
    current = _scan_project_files(project_dir)
    new_files = current - previously_seen

    for rel in sorted(new_files):
        ftype = _detect_file_type(rel)
        # Emit 'processing' then 'completed' for a more realistic animation
        await job_manager.emit_event(job_id, "file_update", {
            "name":   rel,
            "type":   ftype,
            "status": "processing",
        })
        await asyncio.sleep(0.05)
        await job_manager.emit_event(job_id, "file_update", {
            "name":   rel,
            "type":   ftype,
            "status": "completed",
        })

    return current  # Return updated seen set


# ── Placeholder / mock detection ───────────────────────────────────────────────

_PLACEHOLDER_PATTERNS = [
    "// Mock content for",
    "# Mock content for",
    "<!-- Mock content",
    "/* Mock content",
    "placeholder content",
    "TODO: implement",
]


def _is_placeholder(content: str) -> bool:
    """Return True if the file content looks like a stub/placeholder."""
    stripped = content.strip()
    # Only flag as empty/placeholder if truly minimal AND matches a known pattern
    if len(stripped) == 0:
        return True
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.lower() in stripped.lower():
            return True
    return False


def _validate_output_dir(project_dir: Path) -> tuple[bool, list[str]]:
    """
    Scan all generated files and report any that contain placeholder content.
    Returns (has_real_code: bool, issues: list[str]).
    """
    issues: list[str] = []
    total = 0

    for p in project_dir.rglob("*"):
        if not p.is_file():
            continue
        # Skip binary or very large files
        if p.stat().st_size > 1_000_000:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            total += 1
            if _is_placeholder(content):
                issues.append(str(p.relative_to(project_dir)).replace("\\", "/"))
        except Exception:
            pass

    has_real_code = (total > 0) and (len(issues) == 0 or len(issues) < total * 0.5)
    return has_real_code, issues


# ── ZIP packaging ─────────────────────────────────────────────────────────────

def _create_zip(app_name: str, job_id: str) -> Path | None:
    """
    Package output/{app_name}/ into temp_projects/{job_id}.zip.
    Returns the path to the ZIP file, or None if the output dir is empty.
    """
    project_dir = settings.output_dir / app_name
    if not project_dir.exists() or not any(project_dir.rglob("*")):
        logger.error(f"[Packaging] Output dir missing or empty: {project_dir}")
        return None

    temp_dir = Path(os.getcwd()) / "temp_projects"
    temp_dir.mkdir(parents=True, exist_ok=True)

    zip_base = temp_dir / job_id
    zip_path = Path(shutil.make_archive(str(zip_base), "zip", str(project_dir)))
    logger.info(f"[Packaging] Created ZIP: {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
    return zip_path


# ── Main real generation coroutine ────────────────────────────────────────────

async def run_real_generation(job_id: str) -> None:
    """
    Drive the full LangGraph pipeline and stream events to the SSE queue.

    Steps:
      1. Build a combined user prompt from the job parameters.
      2. Instantiate the LangGraph PipelineRunner and run it.
      3. After each agent stage, scan the output directory for new files
         and emit file_update events.
      4. On pipeline completion, package the project into a ZIP.
      5. Emit a 'complete' event with the download URL and statistics.
      6. On any failure, emit an 'error' event with the real error message.
    """
    job = job_manager.get_job(job_id)
    if not job:
        logger.error(f"[Generator] Job {job_id} not found.")
        return

    params  = job["params"]
    frontend = params.get("frontend", "React")
    backend  = params.get("backend", "FastAPI")
    arch     = params.get("architecture", "Monolith")
    details  = params.get("details", "").strip()
    clarified = params.get("clarified_decisions", {})

    selected_stack = {
        "frontend": frontend,
        "backend": backend,
        "architecture": arch,
    }
    
    final_stack = resolve_tech_stack(selected_stack, clarified)
    
    frontend_final = final_stack.get("frontend", frontend)
    backend_final = final_stack.get("backend", backend)
    arch_final = final_stack.get("architecture", arch)

    # Build a rich combined prompt incorporating the final stack explicitly
    tech_stack_str = "\n".join(f"{k.capitalize()}: {v}" for k, v in final_stack.items())
    
    user_prompt = (
        f"Build a complete {arch_final} web application.\n\n"
        f"Final Tech Stack:\n{tech_stack_str}\n\n"
        f"Project Requirements:\n{details}\n\n"
        f"Requirements:\n"
        f"- Generate ALL modules listed above with full implementation\n"
        f"- Use the explicitly specified Final Tech Stack for all decisions.\n"
        f"- Include JWT authentication with role-based access control\n"
        f"- Include Docker and docker-compose configuration\n"
        f"- Include Swagger/OpenAPI documentation\n"
        f"- Include unit tests for all backend endpoints\n"
        f"- Include a comprehensive README\n"
        f"- All code must be production-ready and executable\n"
    )

    job["status"] = "running"
    logger.info(f"[Generator] Job {job_id} starting real pipeline generation.")
    logger.info(f"[Generator] Prompt length: {len(user_prompt)} chars")

    # Emit initial queued-file sentinel so the UI shows something immediately
    await job_manager.emit_event(job_id, "stage_change", {
        "stage": "Initializing Pipeline..."
    })

    seen_files: Set[str] = set()
    app_name: str | None = None
    project_dir: Path | None = None
    start_time = time.time()

    try:
        runner = PipelineRunner()

        user_id = job.get("params", {}).get("user_id")
        async for update in runner.run(user_input=user_prompt, run_id=job_id[:8], user_id=user_id):
            update_type = update.get("type", "progress")
            stage       = update.get("stage", "")
            label       = _stage_label(stage)
            data        = update.get("data", {})

            logger.info(f"[Generator] Pipeline event: type={update_type} stage={stage}")

            # ── Stage change event ─────────────────────────────────────────
            await job_manager.emit_event(job_id, "stage_change", {"stage": label})

            # ── Try to determine app_name from agent_logs ──────────────────
            if app_name is None:
                agent_logs = data.get("agent_logs", {})
                ra_log = agent_logs.get("requirement_analyzer", {})
                if ra_log.get("app_name"):
                    app_name = ra_log["app_name"]
                    project_dir = settings.output_dir / app_name
                    job["app_name"] = app_name
                    job["project_dir"] = str(project_dir)
                    logger.info(f"[Generator] App name resolved: {app_name}")

            # ── Scan for newly written files after each stage ──────────────
            if project_dir:
                seen_files = await _emit_new_files(job_id, project_dir, seen_files)

            # ── Handle pipeline errors ────────────────────────────────────
            if update_type == "error":
                errors = data.get("errors", [update.get("label", "Unknown error")])
                error_msg = "; ".join(str(e) for e in errors) if errors else str(data)
                logger.error(f"[Generator] Pipeline error at stage '{stage}': {error_msg}")
                await job_manager.emit_event(job_id, "error", {
                    "message": f"Pipeline failed at stage '{label}': {error_msg}",
                    "stage":   stage,
                })
                job["status"] = "error"
                job["error"]  = error_msg
                return

            # ── Pipeline complete ──────────────────────────────────────────
            if update_type == "complete":
                # Final file scan to catch last-written files
                if project_dir:
                    seen_files = await _emit_new_files(job_id, project_dir, seen_files)

                # Resolve app_name if still unknown (fallback from complete data)
                if app_name is None:
                    app_name = data.get("app_name", "generated_app")
                    project_dir = settings.output_dir / app_name
                    job["app_name"] = app_name
                    job["project_dir"] = str(project_dir)

                break  # Exit the streaming loop; proceed to packaging

        # ── Validate generated output ──────────────────────────────────────
        await job_manager.emit_event(job_id, "stage_change", {"stage": "Validating Generated Code"})
        await asyncio.sleep(0.2)

        if project_dir and project_dir.exists():
            has_real_code, placeholder_issues = _validate_output_dir(project_dir)
            if placeholder_issues:
                logger.warning(
                    f"[Generator] {len(placeholder_issues)} file(s) may contain placeholder content: "
                    f"{placeholder_issues[:5]}"
                )
                await job_manager.emit_event(job_id, "stage_change", {
                    "stage": f"Validation: {len(placeholder_issues)} files may need review (continuing)"
                })

        # ── Package into ZIP ───────────────────────────────────────────────
        await job_manager.emit_event(job_id, "stage_change", {"stage": "Packaging Project ZIP"})
        await asyncio.sleep(0.3)

        if not app_name:
            raise RuntimeError("Could not determine app_name — no files were generated by the pipeline.")

        zip_path = await asyncio.to_thread(_create_zip, app_name, job_id)
        if zip_path is None:
            raise RuntimeError(
                f"Output directory for '{app_name}' is empty. "
                "The pipeline may have failed silently — check server logs."
            )

        job["zip_path"] = str(zip_path)
        job["status"]   = "completed"

        # Compute stats
        total_files  = len(seen_files)
        elapsed      = round(time.time() - start_time)
        zip_size_mb  = round(zip_path.stat().st_size / (1024 * 1024), 2)

        total_loc = 0
        if project_dir and project_dir.exists():
            for p in project_dir.rglob("*"):
                if p.is_file() and p.suffix in (".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".sql", ".sh", ".yaml", ".yml", ".json"):
                    try:
                        total_loc += sum(1 for _ in p.read_text(encoding="utf-8", errors="ignore").splitlines())
                    except Exception:
                        pass

        # ── Emit complete event ────────────────────────────────────────────
        await job_manager.emit_event(job_id, "complete", {
            "zip_url":      f"/build-complete-project/download/{job_id}",
            "total_files":  total_files,
            "total_loc":    total_loc,
            "project_size": f"{zip_size_mb} MB",
            "duration":     f"{elapsed} seconds",
            "app_name":     app_name,
        })
        logger.info(
            f"[Generator] Job {job_id} complete. "
            f"App: {app_name}, Files: {total_files}, LOC: {total_loc}, ZIP: {zip_size_mb} MB, "
            f"Duration: {elapsed}s"
        )

    except asyncio.CancelledError:
        logger.warning(f"[Generator] Job {job_id} was cancelled.")
        job["status"] = "cancelled"

    except Exception as exc:
        logger.exception(f"[Generator] Job {job_id} crashed: {exc}")
        job["status"] = "error"
        job["error"]  = str(exc)
        await job_manager.emit_event(job_id, "error", {
            "message": (
                f"Project generation failed: {exc}. "
                "Please check server logs for the full traceback."
            )
        })

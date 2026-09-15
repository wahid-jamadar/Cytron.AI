"""
agents/backend_agent.py
────────────────────────
Backend Agent — Stage 3b of the pipeline (runs in parallel with Frontend & Database).

Responsibilities:
  - Generate FastAPI application from the ProjectPlan's API contracts.
  - Implement Pydantic request/response models.
  - Integrate with SQLAlchemy models from the Database Agent.
  - Generate JWT authentication scaffolding when required.
  - Generate OpenAPI-compatible docstrings and router structure.
  - Write all files to output/<project>/backend/.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, CodeArtifact
from tools.chroma_store import upsert_context
from tools.file_writer import write_files_sync

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Backend Agent for an automated software development pipeline.
You generate a complete FastAPI Python backend from an API contract specification and data model.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{
  "files": {
    "main.py": "...FastAPI app entrypoint...",
    "routers/<resource>.py": "...APIRouter for a resource...",
    "schemas/<resource>.py": "...Pydantic models...",
    "services/<resource>.py": "...business logic / DB queries...",
    "auth/jwt.py": "...JWT auth utilities (if auth_strategy=jwt)...",
    "auth/dependencies.py": "...FastAPI auth dependencies...",
    "requirements.txt": "...python deps for generated backend...",
    "Dockerfile": "...Dockerfile for the backend service..."
  },
  "entry_point": "main.py",
  "notes": "any notes about implementation choices"
}

Requirements:
- FastAPI 0.111+, Python 3.11+.
- main.py: create FastAPI app, include all routers, configure CORS, add /health endpoint.
- Each router file: use APIRouter with prefix and tags; import and call service functions.
- Each schema file: define Request/Response Pydantic models with field validation.
- Each service file: implement CRUD operations using SQLAlchemy Session (injected via get_db).
- Import SQLAlchemy models from: from database.models.<model> import <Model>
- Import get_db from: from database.database import get_db
- JWT auth: use python-jose for token creation/verification; use passlib for password hashing.
- auth/dependencies.py: define get_current_user FastAPI dependency.
- Dockerfile: use python:3.11-slim, install deps, run with uvicorn on port 8000.
- Include CORS middleware allowing all origins (configurable via env).
- All env vars (DATABASE_URL, SECRET_KEY, etc.) loaded from environment, not hardcoded."""


BACKEND_PROMPT_TEMPLATE = """Project Plan:
App Name: {app_name}
Auth Strategy: {auth_strategy}

API Contracts:
{api_contracts}

Data Model:
{data_model}

Backend Tasks:
{backend_tasks}

Generate all files as specified."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )


def _build_system_prompt(backend_name: str, architecture_name: str) -> str:
    from modules.build_complete_project.tech_registry import get_backend_config, get_architecture_config
    be_cfg = get_backend_config(backend_name)
    ar_cfg = get_architecture_config(architecture_name)
    lang = be_cfg.language.lower()

    if lang == "python":
        file_desc = """
    "main.py": "...FastAPI app entrypoint...",
    "routers/<resource>.py": "...APIRouter for a resource...",
    "schemas/<resource>.py": "...Pydantic models...",
    "services/<resource>.py": "...business logic / DB queries...",
    "requirements.txt": "...python dependencies...",
    "Dockerfile": "...Dockerfile..."
"""
    elif lang in ("javascript", "typescript"):
        file_desc = """
    "package.json": "...package config...",
    "app.js": "...Express app entrypoint...",
    "routes/<resource>.js": "...routes routing setup...",
    "controllers/<resource>.js": "...logic controllers...",
    "Dockerfile": "...Dockerfile..."
"""
    elif lang == "go":
        file_desc = """
    "go.mod": "...Go module config...",
    "main.go": "...Go entry point...",
    "handlers/<resource>.go": "...Go HTTP route handlers...",
    "Dockerfile": "...Dockerfile..."
"""
    elif lang == "rust":
        file_desc = """
    "Cargo.toml": "...Cargo crate manifest...",
    "src/main.rs": "...Rust main endpoint...",
    "src/handlers/<resource>.rs": "...Rust routing handlers...",
    "Dockerfile": "...Dockerfile..."
"""
    elif lang == "php":
        file_desc = """
    "composer.json": "...Composer deps config...",
    "routes/api.php": "...Laravel API endpoints...",
    "app/Http/Controllers/<Resource>Controller.php": "...Laravel controllers...",
    "Dockerfile": "...Dockerfile..."
"""
    elif lang == "java":
        file_desc = """
    "pom.xml": "...Maven build file...",
    "src/main/java/com/app/Application.java": "...Spring Boot entrypoint...",
    "src/main/java/com/app/controller/<Resource>Controller.java": "...Spring Controller class...",
    "Dockerfile": "...Dockerfile..."
"""
    else:
        file_desc = f"""
    "main.{lang}": "...application entrypoint...",
    "Dockerfile": "...Dockerfile for the backend service..."
"""

    return f"""You are the Backend Agent for an automated software development pipeline.
You generate a complete, working backend tailored to:
- Framework/Library: {be_cfg.name} (Language: {be_cfg.language})
- Architecture: {ar_cfg.name}

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{{
  "files": {{
    {file_desc}
  }},
  "entry_point": "the main entrypoint file name",
  "notes": "any implementation details"
}}

Backend Guidelines:
{be_cfg.prompt_guidelines}

Architecture Guidelines:
{ar_cfg.prompt_guidelines}

Requirements:
1. Ensure all requested paths in API Contracts are correctly handled.
2. All packages, modules, and file imports must match the language guidelines.
3. Configure CORS, port settings, environment variable bindings, and database configurations cleanly.
4. Implement JWT validation or requested auth strategy inside route middleware/dependencies.
5. Create a production-ready Dockerfile for packaging this backend."""


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def backend_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Backend Agent.

    Args:
        state: Current pipeline state. Reads `project_plan` and `database_schema`.

    Returns:
        Partial state dict with `backend_code` updated.
    """
    logger.info("[BackendAgent] Starting backend generation...")
    plan = state.get("project_plan")

    if not plan:
        return {
            "stage": "backend_agent",
            "errors": state.get("errors", []) + ["project_plan missing in BackendAgent"],
            "should_halt": True,
        }

    app_name = plan["app_name"]
    stack = plan.get("stack", {})
    auth_strategy = stack.get("auth_strategy", "jwt")

    llm = _build_llm()
    
    user_input = state.get("user_input", "")
    from modules.build_complete_project.tech_registry import parse_tech_stack
    techs = parse_tech_stack(user_input)
    system_prompt = _build_system_prompt(techs["backend"], techs["architecture"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=BACKEND_PROMPT_TEMPLATE.format(
            app_name=app_name,
            auth_strategy=auth_strategy,
            api_contracts=json.dumps(plan.get("api_contracts", []), indent=2),
            data_model=json.dumps(plan.get("data_model", []), indent=2),
            backend_tasks=json.dumps(plan.get("backend_tasks", []), indent=2),
        )),
    ]

    try:
        response = llm.invoke(messages)
        artifact_dict = _parse_json_response(response.content)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[BackendAgent] LLM error: {exc}")
        return {
            "stage": "backend_agent",
            "errors": state.get("errors", []) + [f"BackendAgent LLM error: {exc}"],
            "should_halt": True,
        }

    files: dict[str, str] = artifact_dict.get("files", {})

    # Write files to output directory
    write_files_sync(app_name, "backend", files)

    artifact: CodeArtifact = {
        "files": files,
        "entry_point": artifact_dict.get("entry_point", "main.py"),
        "notes": artifact_dict.get("notes", ""),
    }

    # Store API summary in ChromaDB for testing agent
    upsert_context(
        collection_name=app_name,
        key="backend_api_summary",
        text=f"Backend API for {app_name}:\n" + json.dumps(plan.get("api_contracts", []), indent=2),
        metadata={"agent": "backend_agent"},
    )

    logger.info(f"[BackendAgent] Generated {len(files)} backend file(s) for '{app_name}'")

    return {
        "backend_code": artifact,
        "stage": "backend_agent_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "backend_agent": {
                "files_generated": len(files),
                "auth_strategy": auth_strategy,
                "endpoints": len(plan.get("api_contracts", [])),
            },
        },
    }

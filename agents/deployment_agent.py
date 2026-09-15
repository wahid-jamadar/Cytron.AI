"""
agents/deployment_agent.py
───────────────────────────
Deployment Agent — Stage 7 of the pipeline.

Responsibilities:
  - Generate docker-compose.yml for local testing.
  - Generate GitHub Actions CI/CD workflow.
  - Optionally generate Kubernetes manifests (when requested).
  - Build and push Docker images to GCP Artifact Registry.
  - Deploy backend and frontend to GCP Cloud Run.
  - Return the live application URL and all infra artifact paths.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
import secrets
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, DeploymentInfo
from tools.file_writer import write_files_sync, get_project_dir
from tools.docker_builder import build_and_push
from tools.cloud_deployer import get_deployer

logger = logging.getLogger(__name__)


INFRA_SYSTEM_PROMPT = """You are the Deployment Agent for an automated software development pipeline.
Generate infrastructure configuration files for a web application.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

Schema:
{
  "files": {
    "docker-compose.yml": "...docker-compose for local dev...",
    ".github/workflows/ci-cd.yml": "...GitHub Actions CI/CD pipeline...",
    ".env.production.example": "...production env var template..."
  }
}

Requirements for docker-compose.yml:
- Define three services: backend (port 8000), frontend (port 3000 → 80), db (postgres or sqlite).
- Use environment variables for all secrets (DATABASE_URL, SECRET_KEY).
- Include healthchecks.
- frontend depends_on backend, backend depends_on db.

Requirements for GitHub Actions CI/CD:
- Trigger on push to main.
- Steps: checkout, setup Python + Node, run backend tests (pytest), build Docker images,
  push to GCP Artifact Registry, deploy to Cloud Run using gcloud.
- Use GitHub Secrets for GCP credentials and project ID.

Keep configs clean and production-ready."""


INFRA_PROMPT_TEMPLATE = """Generate infrastructure files for:
App Name: {app_name}
Database Engine: {database_engine}
GCP Project ID: {gcp_project_id}
GCP Region: {gcp_region}
Artifact Registry: {artifact_registry}
Backend Image Tag: {backend_image}
Frontend Image Tag: {frontend_image}"""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )


def _build_infra_system_prompt(frontend_name: str, backend_name: str, architecture_name: str) -> str:
    from modules.build_complete_project.tech_registry import (
        get_frontend_config, get_backend_config, get_architecture_config
    )
    fe_cfg = get_frontend_config(frontend_name)
    be_cfg = get_backend_config(backend_name)
    ar_cfg = get_architecture_config(architecture_name)

    return f"""You are the Deployment Agent for an automated software development pipeline.
Generate infrastructure configuration files for a web application.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

Schema:
{{
  "files": {{
    "docker-compose.yml": "...docker-compose for local dev...",
    ".github/workflows/ci-cd.yml": "...GitHub Actions CI/CD pipeline...",
    ".env.production.example": "...production env var template..."
  }}
}}

Requirements for docker-compose.yml:
- Define backend (framework: {be_cfg.name}) service and frontend (framework: {fe_cfg.name}) service.
- Define a database service matching the stack (e.g. postgres or sqlite).
- Ensure ports and environments are fully aligned with the architecture: {ar_cfg.name}.
- If architecture is Microservices, provide separate containers for components.
- Include healthchecks and dependencies.

Requirements for GitHub Actions CI/CD:
- Trigger on push to main.
- Setup workflow stages for building and verifying {be_cfg.language} and {fe_cfg.name} code.
- Build Docker images and deploy via Cloud Run commands.

Keep configs clean and production-ready."""


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def _make_image_tag(app_name: str, component: str) -> str:
    registry = settings.gcp_artifact_registry or f"gcr.io/{settings.gcp_project_id}"
    return f"{registry}/{app_name}-{component}:latest"


def deployment_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Deployment Agent.

    Reads: `project_plan`, `frontend_code`, `backend_code`.
    Returns: `deployment_info` with app URLs and infra artifact paths.
    """
    logger.info("[DeploymentAgent] Starting deployment...")
    plan = state.get("project_plan")

    if not plan:
        return {
            "stage": "deployment_agent",
            "errors": state.get("errors", []) + ["project_plan missing in DeploymentAgent"],
            "should_halt": True,
        }

    app_name = plan["app_name"]
    stack = plan.get("stack", {})
    database_engine = stack.get("database_engine", "sqlite")
    project_dir = get_project_dir(app_name)

    backend_image = _make_image_tag(app_name, "backend")
    frontend_image = _make_image_tag(app_name, "frontend")

    # Step 1 — Generate infra config files via LLM
    llm = _build_llm()
    
    user_input = state.get("user_input", "")
    from modules.build_complete_project.tech_registry import parse_tech_stack
    techs = parse_tech_stack(user_input)
    system_prompt = _build_infra_system_prompt(techs["frontend"], techs["backend"], techs["architecture"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=INFRA_PROMPT_TEMPLATE.format(
            app_name=app_name,
            database_engine=database_engine,
            gcp_project_id=settings.gcp_project_id or "YOUR_GCP_PROJECT_ID",
            gcp_region=settings.gcp_region,
            artifact_registry=settings.gcp_artifact_registry or "gcr.io/YOUR_PROJECT",
            backend_image=backend_image,
            frontend_image=frontend_image,
        )),
    ]

    infra_files: dict[str, str] = {}
    try:
        response = llm.invoke(messages)
        infra_artifact = _parse_json_response(response.content)
        infra_files = infra_artifact.get("files", {})
    except (json.JSONDecodeError, Exception) as exc:
        logger.warning(f"[DeploymentAgent] Infra generation warning: {exc}")

    # Write infra files to project root
    write_files_sync(app_name, "infra", infra_files)

    infra_artifact_paths = {
        name: str(project_dir / "infra" / name)
        for name in infra_files
    }

    # Step 2 — Build & push Docker images (only if GCP is configured)
    docker_images: list[str] = []
    backend_url: str | None = None
    frontend_url: str | None = None

    if settings.gcp_enabled:
        backend_dir = project_dir / "backend"
        frontend_dir = project_dir / "frontend"

        if backend_dir.exists() and (backend_dir / "Dockerfile").exists():
            if build_and_push(backend_dir, backend_image):
                docker_images.append(backend_image)

        if frontend_dir.exists() and (frontend_dir / "Dockerfile").exists():
            if build_and_push(frontend_dir, frontend_image):
                docker_images.append(frontend_image)

        # Step 3 — Deploy to GCP Cloud Run
        if docker_images:
            deployer = get_deployer()
            secret_key = secrets.token_urlsafe(32)

            if database_engine == "sqlite":
                db_url = "sqlite:///./app.db"
            else:
                db_url = f"postgresql://user:password@localhost:5432/{app_name}"

            urls = deployer.deploy_app(
                app_name=app_name,
                backend_image=backend_image,
                frontend_image=frontend_image,
                database_url=db_url,
                secret_key=secret_key,
            )
            backend_url = urls.get("backend_url")
            frontend_url = urls.get("frontend_url")
    else:
        logger.info("[DeploymentAgent] GCP not configured — skipping Docker build and cloud deploy.")
        logger.info("[DeploymentAgent] Run 'docker-compose up' in the project directory for local testing.")
        frontend_url = "http://localhost:3000 (docker-compose)"
        backend_url = "http://localhost:8000 (docker-compose)"

    deployment_info: DeploymentInfo = {
        "app_url": frontend_url or backend_url or "not deployed",
        "deployment_id": f"{app_name}-{secrets.token_hex(4)}",
        "cloud_provider": "gcp" if settings.gcp_enabled else "local",
        "service_name": app_name,
        "docker_images": docker_images,
        "infra_artifacts": infra_artifact_paths,
    }

    logger.info(f"[DeploymentAgent] ✅ App URL: {deployment_info['app_url']}")

    return {
        "deployment_info": deployment_info,
        "stage": "deployment_agent_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "deployment_agent": {
                "app_url": deployment_info["app_url"],
                "docker_images": docker_images,
                "gcp_deployed": settings.gcp_enabled,
            },
        },
    }

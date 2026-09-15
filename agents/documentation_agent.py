"""
agents/documentation_agent.py
───────────────────────────────
Documentation Agent — Stage 8 of the pipeline.

Responsibilities:
  - Generate README.md with project overview, architecture, setup instructions.
  - Generate API_REFERENCE.md from the API contracts.
  - Generate SETUP.md for local Docker Compose development.
  - Write all docs to output/<project>/docs/.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, Documentation
from tools.file_writer import write_files_sync

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Documentation Agent for an automated software development pipeline.
You generate high-quality, developer-friendly documentation for a generated application.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

Schema:
{
  "files": {
    "README.md": "...comprehensive README...",
    "docs/API_REFERENCE.md": "...full API reference...",
    "docs/SETUP.md": "...local development setup guide...",
    "docs/ARCHITECTURE.md": "...architecture overview with mermaid diagrams..."
  }
}

README.md requirements:
- Project title, description, badges (Python version, License: MIT).
- Features list.
- Quick Start section (clone, configure env, docker-compose up).
- Link to API docs, architecture doc, setup guide.
- Tech stack table.
- Contributing section.

API_REFERENCE.md requirements:
- One section per API endpoint.
- Method, path, description, request body (JSON), response schema, example curl.
- Auth requirements clearly noted.

SETUP.md requirements:
- Prerequisites (Docker, Node.js, Python).
- Step-by-step local setup with docker-compose.
- Environment variable descriptions.
- Running tests locally.

ARCHITECTURE.md requirements:
- High-level architecture description.
- Mermaid sequence diagram showing request flow.
- Component descriptions (frontend, backend, database)."""


DOC_PROMPT_TEMPLATE = """Generate documentation for:

App Name: {app_name}
Description: {description}
Features: {features}
Tech Stack: {stack}
API Contracts: {api_contracts}
Pages: {pages}
Deployment URL: {app_url}
GitHub Repo: {repo_url}"""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.3,
        max_retries=2,
    )


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def documentation_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Documentation Agent.

    Reads: `project_plan`, `structured_spec`, `deployment_info`, `repo_url`.
    Returns: `docs` with all generated documentation files.
    """
    logger.info("[DocumentationAgent] Generating documentation...")
    plan = state.get("project_plan") or {}
    spec = state.get("structured_spec") or {}
    deployment_info = state.get("deployment_info") or {}

    app_name = plan.get("app_name", spec.get("app_name", "app"))

    llm = _build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=DOC_PROMPT_TEMPLATE.format(
            app_name=app_name,
            description=spec.get("description", ""),
            features=json.dumps(spec.get("features", []), indent=2),
            stack=json.dumps(plan.get("stack", {}), indent=2),
            api_contracts=json.dumps(plan.get("api_contracts", [])[:10], indent=2),
            pages=json.dumps(plan.get("pages", []), indent=2),
            app_url=deployment_info.get("app_url", "Not yet deployed"),
            repo_url=state.get("repo_url") or "Not yet created",
        )),
    ]

    try:
        response = llm.invoke(messages)
        doc_artifact = _parse_json_response(response.content)
        files: dict[str, str] = doc_artifact.get("files", {})
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[DocumentationAgent] LLM error: {exc}")
        files = {
            "README.md": f"# {app_name}\n\nDocumentation generation failed: {exc}\n",
        }

    # Write docs to output
    write_files_sync(app_name, "docs", files)

    # Also copy README.md to project root
    if "README.md" in files:
        write_files_sync(app_name, ".", {"README.md": files["README.md"]})

    docs: Documentation = {
        "readme": files.get("README.md", ""),
        "api_reference": files.get("docs/API_REFERENCE.md", ""),
        "setup_guide": files.get("docs/SETUP.md", ""),
        "files": files,
    }

    logger.info(f"[DocumentationAgent] Generated {len(files)} documentation file(s)")

    return {
        "docs": docs,
        "stage": "documentation_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "documentation_agent": {"files_generated": len(files)},
        },
    }

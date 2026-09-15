"""
agents/frontend_agent.py
─────────────────────────
Frontend Agent — Stage 3a of the pipeline (runs in parallel with Backend & Database).

Responsibilities:
  - Generate a React.js + Tailwind CSS + ShadCN UI application from the ProjectPlan.
  - Create components and pages matching the plan's page/route structure.
  - Wire API calls to the backend endpoints defined in the API contracts.
  - Generate Vite config, package.json, and Dockerfile for the frontend service.
  - Write all files to output/<project>/frontend/.
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


SYSTEM_PROMPT = """You are the Frontend Agent for an automated software development pipeline.
You generate a complete React.js frontend application using Tailwind CSS and ShadCN UI.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{
  "files": {
    "package.json": "...npm package config...",
    "vite.config.ts": "...Vite config...",
    "tsconfig.json": "...TypeScript config...",
    "tailwind.config.js": "...Tailwind config...",
    "postcss.config.js": "...PostCSS config...",
    "index.html": "...HTML entry point...",
    "src/main.tsx": "...React entry point...",
    "src/App.tsx": "...Router and layout...",
    "src/lib/api.ts": "...Axios/fetch API client with base URL from env...",
    "src/lib/auth.ts": "...JWT token storage and auth utilities...",
    "src/pages/<PageName>.tsx": "...page component...",
    "src/components/<ComponentName>.tsx": "...reusable component...",
    "src/hooks/use<Resource>.ts": "...data fetching hook...",
    "src/types/index.ts": "...TypeScript interfaces matching API response schemas...",
    ".env.example": "VITE_API_URL=http://localhost:8000",
    "Dockerfile": "...multi-stage Dockerfile: build + nginx serve..."
  },
  "entry_point": "src/main.tsx",
  "notes": "any notes about implementation choices"
}

Requirements:
- React 18+, TypeScript, Vite.
- Use React Router v6 for routing.
- Use ShadCN UI components (Button, Card, Input, Form, Table, etc.).
- Use Tailwind CSS for custom styling.
- All API base URLs must come from import.meta.env.VITE_API_URL — never hardcoded.
- JWT tokens must be stored in localStorage and sent as Authorization: Bearer <token>.
- Implement protected routes that redirect to /login if not authenticated.
- Each page should have a loading state and error boundary.
- Dockerfile: use node:20-alpine for build, nginx:alpine for serving; expose port 80.
- Use @tanstack/react-query for server state management.
- Use @tabler/icons-react for all icons and do not use emojis in the UI.
- Generate responsive layouts suitable for mobile and desktop."""


FRONTEND_PROMPT_TEMPLATE = """Project Plan:
App Name: {app_name}
Auth Strategy: {auth_strategy}

Pages and Routes:
{pages}

API Contracts (these are the backend endpoints to call):
{api_contracts}

Frontend Tasks:
{frontend_tasks}

Generate all frontend files as specified."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
        max_retries=2,
    )


def _build_system_prompt(frontend_name: str) -> str:
    from modules.build_complete_project.tech_registry import get_frontend_config
    fe_cfg = get_frontend_config(frontend_name)
    fe_lower = fe_cfg.name.lower()

    if "next" in fe_lower:
        files_desc = """
    "package.json": "...npm package config...",
    "next.config.js": "...Next.js configuration...",
    "app/page.tsx": "...Home screen router component...",
    "app/layout.tsx": "...Root layout container...",
    "app/dashboard/page.tsx": "...Dashboard page page...",
    "components/<Component>.tsx": "...React components...",
    "Dockerfile": "...Dockerfile..."
"""
    elif "vue" in fe_lower or "nuxt" in fe_lower:
        files_desc = """
    "package.json": "...npm package config...",
    "vite.config.ts": "...Vite configuration...",
    "src/App.vue": "...Root Vue component...",
    "src/main.ts": "...Vue entrypoint...",
    "src/components/<Component>.vue": "...Vue single-file component...",
    "Dockerfile": "...Dockerfile..."
"""
    elif "svelte" in fe_lower:
        files_desc = """
    "package.json": "...npm package config...",
    "vite.config.ts": "...Vite configuration...",
    "src/App.svelte": "...Root Svelte component...",
    "src/main.ts": "...Svelte entrypoint...",
    "Dockerfile": "...Dockerfile..."
"""
    elif "htmx" in fe_lower or "html" in fe_lower:
        files_desc = """
    "index.html": "...Main HTML layout file...",
    "styles.css": "...CSS style declarations...",
    "app.js": "...Vanilla helper scripting...",
    "Dockerfile": "...Dockerfile..."
"""
    elif "flutter" in fe_lower:
        files_desc = """
    "pubspec.yaml": "...Dart dependencies module...",
    "lib/main.dart": "...Flutter entry point...",
    "lib/screens/<screen>.dart": "...Flutter screen layouts...",
    "Dockerfile": "...Dockerfile..."
"""
    elif "react native" in fe_lower:
        files_desc = """
    "package.json": "...package configurations...",
    "App.tsx": "...Native router entry point...",
    "components/<Component>.tsx": "...Native widgets..."
"""
    else:
        files_desc = """
    "package.json": "...npm package config...",
    "vite.config.ts": "...Vite config...",
    "index.html": "...HTML entry point...",
    "src/main.tsx": "...React entry point...",
    "src/App.tsx": "...Router and layout...",
    "src/pages/<PageName>.tsx": "...page component...",
    "src/components/<ComponentName>.tsx": "...reusable component...",
    "Dockerfile": "...Dockerfile..."
"""

    return f"""You are the Frontend Agent for an automated software development pipeline.
You generate a complete frontend application tailored to:
- Frontend Option: {fe_cfg.name}

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{{
  "files": {{
    {files_desc}
  }},
  "entry_point": "the main entrypoint file path",
  "notes": "any implementation details"
}}

Frontend Guidelines:
{fe_cfg.prompt_guidelines}

Requirements:
1. Standard package dependencies and devDependencies must be added to package.json (or equivalent config, e.g. pubspec.yaml).
2. Wire API calls to backend endpoints as defined in the API contracts.
3. Configure routes matching the planned page/route structure.
4. Support mobile/desktop responsive design.
5. Create a Dockerfile suitable for building/serving the frontend framework (e.g. using static nginx or Node server)."""


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def frontend_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Frontend Agent.

    Args:
        state: Current pipeline state. Reads `project_plan`.

    Returns:
        Partial state dict with `frontend_code` updated.
    """
    logger.info("[FrontendAgent] Starting frontend generation...")
    plan = state.get("project_plan")

    if not plan:
        return {
            "stage": "frontend_agent",
            "errors": state.get("errors", []) + ["project_plan missing in FrontendAgent"],
            "should_halt": True,
        }

    app_name = plan["app_name"]
    stack = plan.get("stack", {})
    auth_strategy = stack.get("auth_strategy", "jwt")

    llm = _build_llm()
    
    user_input = state.get("user_input", "")
    from modules.build_complete_project.tech_registry import parse_tech_stack
    techs = parse_tech_stack(user_input)
    system_prompt = _build_system_prompt(techs["frontend"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=FRONTEND_PROMPT_TEMPLATE.format(
            app_name=app_name,
            auth_strategy=auth_strategy,
            pages=json.dumps(plan.get("pages", []), indent=2),
            api_contracts=json.dumps(plan.get("api_contracts", []), indent=2),
            frontend_tasks=json.dumps(plan.get("frontend_tasks", []), indent=2),
        )),
    ]

    try:
        response = llm.invoke(messages)
        artifact_dict = _parse_json_response(response.content)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[FrontendAgent] LLM error: {exc}")
        return {
            "stage": "frontend_agent",
            "errors": state.get("errors", []) + [f"FrontendAgent LLM error: {exc}"],
            "should_halt": True,
        }

    files: dict[str, str] = artifact_dict.get("files", {})

    # Write files to output directory
    write_files_sync(app_name, "frontend", files)

    artifact: CodeArtifact = {
        "files": files,
        "entry_point": artifact_dict.get("entry_point", "src/main.tsx"),
        "notes": artifact_dict.get("notes", ""),
    }

    upsert_context(
        collection_name=app_name,
        key="frontend_summary",
        text=f"Frontend pages for {app_name}: {[p['name'] for p in plan.get('pages', [])]}",
        metadata={"agent": "frontend_agent"},
    )

    logger.info(f"[FrontendAgent] Generated {len(files)} frontend file(s) for '{app_name}'")

    return {
        "frontend_code": artifact,
        "stage": "frontend_agent_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "frontend_agent": {
                "files_generated": len(files),
                "pages": len(plan.get("pages", [])),
                "auth_strategy": auth_strategy,
            },
        },
    }

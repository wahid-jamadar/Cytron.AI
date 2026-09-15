"""
agents/project_planner.py
──────────────────────────
Project Planner Agent — Stage 2 of the pipeline.

Responsibilities:
  - Consume the structured RequirementSpec from the Requirement Analyzer.
  - Select appropriate technologies from the supported stack.
  - Produce a full ProjectPlan including:
      • Architecture decision
      • Page / route structure
      • API contracts (endpoint specs)
      • Data model (entities + relationships)
      • Task breakdowns for Frontend, Backend, Database Agents
  - Store the plan in ChromaDB for downstream agent retrieval.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from config.stack_config import StackConfig, DEFAULT_STACK
from state.pipeline_state import PipelineState, ProjectPlan
from tools.chroma_store import upsert_context
from tools.file_writer import get_project_dir

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Project Planner Agent for an automated software development pipeline.
You receive a structured application specification and produce a detailed technical project plan.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform exactly to this schema:
{
  "app_name": "same_slug_from_spec",
  "architecture": "monolith | modular_api",
  "stack": {
    "frontend_framework": "react",
    "frontend_styling": "tailwind",
    "frontend_component_library": "shadcn",
    "backend_framework": "fastapi",
    "backend_language": "python",
    "database_engine": "postgresql | sqlite | mysql",
    "orm": "sqlalchemy",
    "migration_tool": "alembic",
    "auth_strategy": "jwt | session | none",
    "cloud_provider": "gcp",
    "use_docker_compose": true,
    "use_kubernetes": false
  },
  "pages": [
    {
      "name": "PageName",
      "route": "/route",
      "description": "what this page does",
      "components": ["ComponentA", "ComponentB"],
      "requires_auth": true | false
    }
  ],
  "api_contracts": [
    {
      "method": "GET | POST | PUT | DELETE | PATCH",
      "path": "/api/v1/resource",
      "description": "what this endpoint does",
      "request_body": {"field": "type or null"},
      "response_schema": {"field": "type"},
      "auth_required": true | false,
      "tags": ["tag"]
    }
  ],
  "data_model": [
    {
      "entity": "EntityName",
      "table": "table_name",
      "fields": [
        {"name": "id", "type": "uuid", "primary_key": true},
        {"name": "field_name", "type": "string | integer | boolean | datetime | text | float", "nullable": false, "unique": false}
      ],
      "relationships": [
        {"type": "many_to_one | one_to_many | many_to_many", "with": "OtherEntity", "foreign_key": "other_entity_id"}
      ]
    }
  ],
  "frontend_tasks": [
    "Create <ComponentName> component for <route>",
    "Wire <endpoint> API call in <component>"
  ],
  "backend_tasks": [
    "Implement <METHOD> /api/v1/<resource> endpoint",
    "Add SQLAlchemy model for <Entity>"
  ],
  "database_tasks": [
    "Create migration for <table>",
    "Add index on <table>.<field>"
  ]
}

Guidelines:
- Choose sqlite for simple apps, postgresql for anything with multiple entities or complex queries.
- Always include authentication endpoints if user_roles exist.
- Generate thorough API contracts — every frontend page must have the backend endpoints it needs.
- Every data_entity from the spec must appear as an entity in the data_model."""


def _build_system_prompt(frontend: str, backend: str, arch: str) -> str:
    from modules.build_complete_project.tech_registry import (
        get_frontend_config, get_backend_config, get_architecture_config
    )
    fe_cfg = get_frontend_config(frontend)
    be_cfg = get_backend_config(backend)
    ar_cfg = get_architecture_config(arch)

    return f"""You are the Project Planner Agent for an automated software development pipeline.
You receive a structured application specification and produce a detailed technical project plan tailored to:
- Frontend: {fe_cfg.name} ({fe_cfg.prompt_guidelines})
- Backend: {be_cfg.name} (Language: {be_cfg.language}) ({be_cfg.prompt_guidelines})
- Architecture: {ar_cfg.name} ({ar_cfg.prompt_guidelines})

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform exactly to this schema:
{{
  "app_name": "same_slug_from_spec",
  "architecture": "{ar_cfg.name}",
  "stack": {{
    "frontend_framework": "{fe_cfg.name.lower()}",
    "frontend_styling": "tailwind or custom styles",
    "frontend_component_library": "standard library or custom",
    "backend_framework": "{be_cfg.name.lower()}",
    "backend_language": "{be_cfg.language}",
    "database_engine": "postgresql | sqlite | mysql",
    "orm": "standard ORM for framework (e.g. sqlalchemy, Prisma, GORM, JPA)",
    "migration_tool": "standard migration tool (e.g. alembic, dbmate, flyway)",
    "auth_strategy": "jwt | session | none",
    "cloud_provider": "gcp",
    "use_docker_compose": true,
    "use_kubernetes": false
  }},
  "pages": [
    {{
      "name": "PageName",
      "route": "/route",
      "description": "what this page does",
      "components": ["ComponentA", "ComponentB"],
      "requires_auth": true | false
    }}
  ],
  "api_contracts": [
    {{
      "method": "GET | POST | PUT | DELETE | PATCH",
      "path": "/api/v1/resource",
      "description": "what this endpoint does",
      "request_body": {{"field": "type or null"}},
      "response_schema": {{"field": "type"}},
      "auth_required": true | false,
      "tags": ["tag"]
    }}
  ],
  "data_model": [
    {{
      "entity": "EntityName",
      "table": "table_name",
      "fields": [
        {{"name": "id", "type": "uuid", "primary_key": true}},
        {{"name": "field_name", "type": "string | integer | boolean | datetime | text | float", "nullable": false, "unique": false}}
      ],
      "relationships": [
        {{"type": "many_to_one | one_to_many | many_to_many", "with": "OtherEntity", "foreign_key": "other_entity_id"}}
      ]
    }}
  ],
  "frontend_tasks": [
    "Create component/file representing <ComponentName> or page",
    "Wire API routes/endpoints calls"
  ],
  "backend_tasks": [
    "Implement endpoint <METHOD> <path>",
    "Create database model/schema representing <Entity>"
  ],
  "database_tasks": [
    "Create DB migration or table schema script",
    "Add seed data"
  ]
}}

Guidelines:
- Choose postgresql or sqlite or equivalent database based on complexity.
- Define thorough, complete routes matching the pages requirements.
- Maintain technology specific rules:
  Frontend: {fe_cfg.prompt_guidelines}
  Backend: {be_cfg.prompt_guidelines}
  Architecture: {ar_cfg.prompt_guidelines}
"""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def project_planner_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Project Planner Agent.

    Args:
      state: Current pipeline state. Reads `structured_spec`.

    Returns:
      Partial state dict with `project_plan` and `stage` updated.
    """
    logger.info("[ProjectPlanner] Starting planning...")
    spec = state.get("structured_spec")

    if not spec:
        return {
            "stage": "project_planner",
            "errors": state.get("errors", []) + ["structured_spec is missing — cannot plan."],
            "should_halt": True,
        }

    llm = _build_llm()
    
    user_input = state.get("user_input", "")
    from modules.build_complete_project.tech_registry import parse_tech_stack
    techs = parse_tech_stack(user_input)
    system_prompt = _build_system_prompt(techs["frontend"], techs["backend"], techs["architecture"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"Requirement Specification:\n\n{json.dumps(spec, indent=2)}"
        ),
    ]

    try:
        response = llm.invoke(messages)
        plan_dict = _parse_json_response(response.content)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[ProjectPlanner] Failed to parse LLM response: {exc}")
        return {
            "stage": "project_planner",
            "errors": state.get("errors", []) + [f"ProjectPlanner LLM error: {exc}"],
            "should_halt": True,
        }

    # Resolve stack from plan, falling back to defaults
    stack_dict = plan_dict.get("stack", DEFAULT_STACK.to_dict())
    stack = StackConfig(
        database_engine=stack_dict.get("database_engine", "sqlite"),
        auth_strategy=stack_dict.get("auth_strategy", "jwt"),
        use_kubernetes=stack_dict.get("use_kubernetes", False),
    )
    plan_dict["stack"] = stack.to_dict()

    # Attach project directory path
    project_dir = get_project_dir(plan_dict.get("app_name", spec["app_name"]))
    plan_dict["project_dir"] = str(project_dir)

    plan: ProjectPlan = plan_dict  # type: ignore[assignment]

    # Store in ChromaDB
    collection_name = plan["app_name"]
    upsert_context(
        collection_name=collection_name,
        key="project_plan",
        text=json.dumps(plan, indent=2),
        metadata={"agent": "project_planner"},
    )
    upsert_context(
        collection_name=collection_name,
        key="api_contracts",
        text=json.dumps(plan.get("api_contracts", []), indent=2),
        metadata={"agent": "project_planner", "type": "api_contracts"},
    )
    upsert_context(
        collection_name=collection_name,
        key="data_model",
        text=json.dumps(plan.get("data_model", []), indent=2),
        metadata={"agent": "project_planner", "type": "data_model"},
    )

    logger.info(
        f"[ProjectPlanner] Done. Pages: {len(plan.get('pages', []))}, "
        f"Endpoints: {len(plan.get('api_contracts', []))}, "
        f"Entities: {len(plan.get('data_model', []))}"
    )

    return {
        "project_plan": plan,
        "stage": "project_planner_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "project_planner": {
                "pages": len(plan.get("pages", [])),
                "api_endpoints": len(plan.get("api_contracts", [])),
                "entities": len(plan.get("data_model", [])),
                "database": stack.database_engine,
                "auth": stack.auth_strategy,
            },
        },
    }

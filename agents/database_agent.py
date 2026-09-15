"""
agents/database_agent.py
─────────────────────────
Database Agent — Stage 3c of the pipeline (runs in parallel with Frontend & Backend).

Responsibilities:
  - Translate the data_model from the ProjectPlan into SQLAlchemy ORM models.
  - Generate Alembic migration scripts.
  - Generate a seed data script for demo/testing.
  - Write all files to output/<project>/database/.
  - Return the finalized schema artifact for the Backend Agent to consume.
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


SYSTEM_PROMPT = """You are the Database Agent for an automated software development pipeline.
You generate SQLAlchemy ORM models, Alembic migrations, and seed data from a data model specification.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{
  "files": {
    "models/base.py": "...python code...",
    "models/<entity_name>.py": "...python code with SQLAlchemy model...",
    "migrations/env.py": "...alembic env.py...",
    "migrations/versions/001_initial.py": "...alembic migration script...",
    "seeds/seed_data.py": "...seed data script...",
    "database.py": "...SQLAlchemy engine + session factory...",
    "alembic.ini": "...alembic config..."
  },
  "entry_point": "database.py",
  "notes": "any important notes about schema decisions"
}

Requirements:
- Use SQLAlchemy 2.x declarative style with type annotations.
- models/base.py must define the DeclarativeBase subclass named 'Base'.
- Each model file imports Base from models.base.
- Include proper relationships using relationship() with back_populates.
- Add created_at and updated_at timestamps to all models.
- Use UUID primary keys (import uuid).
- The database.py file must export: engine, SessionLocal, get_db (FastAPI dependency).
- Support both PostgreSQL and SQLite via DATABASE_URL env var.
- migrations/env.py must import all models so Alembic detects them.
- The seed script must be runnable standalone and use the same SessionLocal."""

ENTITY_PROMPT_TEMPLATE = """Data Model to implement:

{data_model}

Stack info:
- Database engine: {database_engine}
- ORM: SQLAlchemy 2.x
- Migration tool: Alembic

Generate all files as specified in your instructions."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )


def _build_system_prompt(backend_name: str) -> str:
    from modules.build_complete_project.tech_registry import get_backend_config
    be_cfg = get_backend_config(backend_name)
    lang = be_cfg.language.lower()

    if lang == "python":
        orm_instructions = "Use SQLAlchemy 2.x declarative style with type annotations and Alembic for migrations."
        schema_format = """{
  "files": {
    "models/base.py": "...python code DeclarativeBase...",
    "models/<entity>.py": "...python code for entity...",
    "database.py": "...engine & SessionLocal...",
    "alembic.ini": "...alembic config...",
    "migrations/env.py": "...alembic env.py...",
    "migrations/versions/001_initial.py": "...initial migration...",
    "seeds/seed_data.py": "...seed database script..."
  },
  "entry_point": "database.py",
  "notes": "..."
}"""
    elif lang in ("javascript", "typescript"):
        orm_instructions = "Use Prisma ORM schema (`schema.prisma`) and JavaScript seed script."
        schema_format = """{
  "files": {
    "prisma/schema.prisma": "...Prisma schema definition...",
    "prisma/seed.js": "...JS database seed script...",
    "lib/prisma.js": "...Prisma client export..."
  },
  "entry_point": "prisma/schema.prisma",
  "notes": "..."
}"""
    elif lang == "go":
        orm_instructions = "Use Go GORM models with struct tags and DB connection init."
        schema_format = """{
  "files": {
    "models/base.go": "...Go base model or struct helpers...",
    "models/<entity>.go": "...GORM Go struct...",
    "database/db.go": "...Go connection pooling setup...",
    "seeds/seed.go": "...Go seed data runner..."
  },
  "entry_point": "database/db.go",
  "notes": "..."
}"""
    elif lang == "java":
        orm_instructions = "Use Spring Data JPA Entity classes with Lombok annotations."
        schema_format = """{
  "files": {
    "src/main/java/com/app/model/<Entity>.java": "...Java JPA Entity class...",
    "src/main/java/com/app/repository/<Entity>Repository.java": "...Java interface extending JpaRepository...",
    "src/main/resources/schema.sql": "...initial SQL schema...",
    "src/main/resources/data.sql": "...seed SQL script..."
  },
  "entry_point": "src/main/resources/schema.sql",
  "notes": "..."
}"""
    elif lang == "php":
        orm_instructions = "Use Laravel Eloquent models and database migrations."
        schema_format = """{
  "files": {
    "database/migrations/0000_00_00_000000_create_<table_name>_table.php": "...PHP migration script...",
    "app/Models/<Entity>.php": "...PHP Eloquent Model...",
    "database/seeders/<Entity>Seeder.php": "...PHP Laravel Seeder..."
  },
  "entry_point": "app/Models/<Entity>.php",
  "notes": "..."
}"""
    elif lang == "rust":
        orm_instructions = "Use SQLx migration SQL files and Rust struct models with serde."
        schema_format = """{
  "files": {
    "migrations/0001_initial.sql": "...SQL schema commands...",
    "src/db.rs": "...Rust SQLx pool manager...",
    "src/models/<entity>.rs": "...Rust struct models..."
  },
  "entry_point": "migrations/0001_initial.sql",
  "notes": "..."
}"""
    else:
        orm_instructions = "Generate standard SQL schemas, models, and seed files for the language."
        schema_format = """{
  "files": {
    "schema.sql": "...SQL command schema...",
    "seed.sql": "...database insert seeds...",
    "models/entities": "...boilerplate data models..."
  },
  "entry_point": "schema.sql",
  "notes": "..."
}"""

    return f"""You are the Database Agent for an automated software development pipeline.
You generate database models, migrations, and seed scripts suited for:
- Backend: {be_cfg.name}
- Language: {be_cfg.language}

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{schema_format}

Requirements:
- {orm_instructions}
- UUID primary keys should be used.
- Include proper relationship bindings.
- All models must include standard timestamp tracking (created_at, updated_at)."""


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def database_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Database Agent.

    Args:
        state: Current pipeline state. Reads `project_plan`.

    Returns:
        Partial state dict with `database_schema` updated.
    """
    logger.info("[DatabaseAgent] Starting database generation...")
    plan = state.get("project_plan")

    if not plan:
        return {
            "stage": "database_agent",
            "errors": state.get("errors", []) + ["project_plan missing in DatabaseAgent"],
            "should_halt": True,
        }

    app_name = plan["app_name"]
    data_model = plan.get("data_model", [])
    stack = plan.get("stack", {})
    database_engine = stack.get("database_engine", "sqlite")

    llm = _build_llm()
    
    user_input = state.get("user_input", "")
    from modules.build_complete_project.tech_registry import parse_tech_stack
    techs = parse_tech_stack(user_input)
    system_prompt = _build_system_prompt(techs["backend"])

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=ENTITY_PROMPT_TEMPLATE.format(
            data_model=json.dumps(data_model, indent=2),
            database_engine=database_engine,
        )),
    ]

    try:
        response = llm.invoke(messages)
        artifact_dict = _parse_json_response(response.content)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[DatabaseAgent] LLM error: {exc}")
        return {
            "stage": "database_agent",
            "errors": state.get("errors", []) + [f"DatabaseAgent LLM error: {exc}"],
            "should_halt": True,
        }

    files: dict[str, str] = artifact_dict.get("files", {})

    # Write files to output directory
    write_files_sync(app_name, "database", files)

    artifact: CodeArtifact = {
        "files": files,
        "entry_point": artifact_dict.get("entry_point", "database.py"),
        "notes": artifact_dict.get("notes", ""),
    }

    # Persist schema summary to ChromaDB
    upsert_context(
        collection_name=app_name,
        key="database_schema_summary",
        text=f"Database schema for {app_name}:\n{json.dumps(data_model, indent=2)}",
        metadata={"agent": "database_agent", "engine": database_engine},
    )

    logger.info(f"[DatabaseAgent] Generated {len(files)} database file(s) for '{app_name}'")

    return {
        "database_schema": artifact,
        "stage": "database_agent_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "database_agent": {
                "files_generated": len(files),
                "engine": database_engine,
                "entities": len(data_model),
            },
        },
    }

"""
config/stack_config.py
──────────────────────
Defines the supported technology stack for generated applications.
Agents reference this to make technology selection decisions and to validate
that requested technologies are within scope for the current release.
"""

from dataclasses import dataclass, field
from typing import Literal


# ── Supported choices ─────────────────────────────────────────────────────────

SUPPORTED_DATABASES = ["postgresql", "mysql", "sqlite"]
SUPPORTED_CLOUD_PROVIDERS = ["gcp"]   # aws, azure to be added in future phases
SUPPORTED_FRONTEND_FRAMEWORKS = ["react"]
SUPPORTED_BACKEND_FRAMEWORKS = ["fastapi"]


@dataclass(frozen=True)
class StackConfig:
    """
    Immutable snapshot of the technology decisions for a single generated project.
    Produced by the Project Planner Agent and consumed by all build agents.
    """

    # Frontend
    frontend_framework: Literal["react"] = "react"
    frontend_styling: str = "tailwind"
    frontend_component_library: str = "shadcn"

    # Backend
    backend_framework: Literal["fastapi"] = "fastapi"
    backend_language: str = "python"

    # Database
    database_engine: Literal["postgresql", "mysql", "sqlite"] = "sqlite"

    # ORM / Migrations
    orm: str = "sqlalchemy"
    migration_tool: str = "alembic"

    # Auth
    auth_strategy: Literal["jwt", "session", "none"] = "jwt"

    # Deployment
    cloud_provider: Literal["gcp"] = "gcp"
    use_docker_compose: bool = True
    use_kubernetes: bool = False    # Only enabled when user explicitly requests it

    # Testing
    backend_test_framework: str = "pytest"
    frontend_test_framework: str = "vitest"

    def to_dict(self) -> dict:
        return {
            "frontend_framework": self.frontend_framework,
            "frontend_styling": self.frontend_styling,
            "frontend_component_library": self.frontend_component_library,
            "backend_framework": self.backend_framework,
            "backend_language": self.backend_language,
            "database_engine": self.database_engine,
            "orm": self.orm,
            "migration_tool": self.migration_tool,
            "auth_strategy": self.auth_strategy,
            "cloud_provider": self.cloud_provider,
            "use_docker_compose": self.use_docker_compose,
            "use_kubernetes": self.use_kubernetes,
            "backend_test_framework": self.backend_test_framework,
            "frontend_test_framework": self.frontend_test_framework,
        }


# ── Default stack (used when user has no specific preferences) ─────────────────
DEFAULT_STACK = StackConfig()

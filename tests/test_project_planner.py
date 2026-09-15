"""
tests/test_project_planner.py
──────────────────────────────
Unit tests for the Project Planner Agent.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from agents.project_planner import project_planner_node
from state.pipeline_state import initial_state


MOCK_SPEC = {
    "app_name": "todo_app",
    "app_type": "crud",
    "description": "A todo app with authentication.",
    "features": ["CRUD tasks", "User auth"],
    "user_roles": ["user", "admin"],
    "workflows": [],
    "data_entities": ["User", "Task"],
    "non_functional": {"security": "JWT", "performance": None, "scalability": None},
    "clarifying_questions": [],
}

MOCK_PLAN = {
    "app_name": "todo_app",
    "architecture": "monolith",
    "stack": {
        "frontend_framework": "react",
        "frontend_styling": "tailwind",
        "frontend_component_library": "shadcn",
        "backend_framework": "fastapi",
        "backend_language": "python",
        "database_engine": "sqlite",
        "orm": "sqlalchemy",
        "migration_tool": "alembic",
        "auth_strategy": "jwt",
        "cloud_provider": "gcp",
        "use_docker_compose": True,
        "use_kubernetes": False,
        "backend_test_framework": "pytest",
        "frontend_test_framework": "vitest",
    },
    "pages": [
        {"name": "Login", "route": "/login", "description": "Login page", "components": ["LoginForm"], "requires_auth": False},
        {"name": "Dashboard", "route": "/", "description": "Task list", "components": ["TaskList"], "requires_auth": True},
    ],
    "api_contracts": [
        {"method": "POST", "path": "/api/v1/auth/login", "description": "Login", "request_body": {"email": "str", "password": "str"}, "response_schema": {"token": "str"}, "auth_required": False, "tags": ["auth"]},
        {"method": "GET", "path": "/api/v1/tasks", "description": "List tasks", "request_body": None, "response_schema": {"tasks": "list"}, "auth_required": True, "tags": ["tasks"]},
    ],
    "data_model": [
        {"entity": "User", "table": "users", "fields": [{"name": "id", "type": "uuid", "primary_key": True}], "relationships": []},
        {"entity": "Task", "table": "tasks", "fields": [{"name": "id", "type": "uuid", "primary_key": True}], "relationships": [{"type": "many_to_one", "with": "User", "foreign_key": "user_id"}]},
    ],
    "frontend_tasks": ["Create LoginForm component"],
    "backend_tasks": ["Implement POST /api/v1/auth/login"],
    "database_tasks": ["Create users migration"],
}


@pytest.fixture
def mock_llm():
    mock_response = MagicMock()
    mock_response.content = json.dumps(MOCK_PLAN)
    with patch("agents.project_planner.ChatGroq") as MockLLM:
        instance = MockLLM.return_value
        instance.invoke.return_value = mock_response
        with patch("agents.project_planner.upsert_context"):
            yield instance


def test_project_planner_success(mock_llm):
    """Should generate a valid project plan from a structured spec."""
    state = initial_state("Build a todo app")
    state["structured_spec"] = MOCK_SPEC

    result = project_planner_node(state)

    assert "project_plan" in result
    plan = result["project_plan"]
    assert plan["app_name"] == "todo_app"
    assert len(plan["pages"]) == 2
    assert len(plan["api_contracts"]) == 2
    assert len(plan["data_model"]) == 2
    assert result["stage"] == "project_planner_complete"


def test_project_planner_missing_spec():
    """Should halt when structured_spec is missing."""
    state = initial_state("Build something")
    result = project_planner_node(state)
    assert result.get("should_halt") is True


def test_project_planner_stack_defaults(mock_llm):
    """Stack should default to sensible values."""
    state = initial_state("Build a todo app")
    state["structured_spec"] = MOCK_SPEC

    result = project_planner_node(state)
    stack = result["project_plan"]["stack"]

    assert stack["backend_framework"] == "fastapi"
    assert stack["frontend_framework"] == "react"
    assert stack["use_kubernetes"] is False

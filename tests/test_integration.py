"""
tests/test_integration.py
──────────────────────────
Integration smoke test: verifies the graph wires together without crashing.
Mocks all LLM calls so no API keys are required to run.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from state.pipeline_state import initial_state


MOCK_SPEC_JSON = json.dumps({
    "app_name": "smoke_test_app",
    "app_type": "crud",
    "description": "Smoke test app",
    "features": ["feature 1"],
    "user_roles": ["user"],
    "workflows": [],
    "data_entities": ["Item"],
    "non_functional": {"security": None, "performance": None, "scalability": None},
    "clarifying_questions": [],
})

MOCK_PLAN_JSON = json.dumps({
    "app_name": "smoke_test_app",
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
        "auth_strategy": "none",
        "cloud_provider": "gcp",
        "use_docker_compose": True,
        "use_kubernetes": False,
        "backend_test_framework": "pytest",
        "frontend_test_framework": "vitest",
    },
    "pages": [{"name": "Home", "route": "/", "description": "Home", "components": [], "requires_auth": False}],
    "api_contracts": [{"method": "GET", "path": "/api/v1/items", "description": "List items", "request_body": None, "response_schema": {"items": "list"}, "auth_required": False, "tags": ["items"]}],
    "data_model": [{"entity": "Item", "table": "items", "fields": [{"name": "id", "type": "uuid", "primary_key": True}], "relationships": []}],
    "frontend_tasks": [],
    "backend_tasks": [],
    "database_tasks": [],
})

MOCK_CODE_JSON = json.dumps({"files": {"main.py": "# smoke test"}, "entry_point": "main.py", "notes": ""})
MOCK_REVIEW_JSON = json.dumps({"issues": [], "blocked": False, "summary": "LGTM"})
MOCK_TEST_JSON = json.dumps({"files": {"tests/test_smoke.py": "def test_pass(): assert True"}})
MOCK_DEPLOY_JSON = json.dumps({"files": {"docker-compose.yml": "version: '3'"}})
MOCK_DOC_JSON = json.dumps({"files": {"README.md": "# Smoke Test App"}})


def _make_llm_mock(content: str):
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_response
    return mock_llm


@pytest.mark.asyncio
async def test_graph_compiles_and_runs():
    """
    Smoke test: the graph should compile and execute all nodes
    without raising exceptions when LLMs are mocked.
    """
    with (
        patch("agents.requirement_analyzer.ChatGroq", return_value=_make_llm_mock(MOCK_SPEC_JSON)),
        patch("agents.project_planner.ChatGroq",      return_value=_make_llm_mock(MOCK_PLAN_JSON)),
        patch("agents.frontend_agent.ChatGroq",        return_value=_make_llm_mock(MOCK_CODE_JSON)),
        patch("agents.backend_agent.ChatGroq",         return_value=_make_llm_mock(MOCK_CODE_JSON)),
        patch("agents.database_agent.ChatGroq",        return_value=_make_llm_mock(MOCK_CODE_JSON)),
        patch("agents.code_review_agent.ChatGroq",     return_value=_make_llm_mock(MOCK_REVIEW_JSON)),
        patch("agents.testing_agent.ChatGroq",         return_value=_make_llm_mock(MOCK_TEST_JSON)),
        patch("agents.deployment_agent.ChatGroq",      return_value=_make_llm_mock(MOCK_DEPLOY_JSON)),
        patch("agents.documentation_agent.ChatGroq",   return_value=_make_llm_mock(MOCK_DOC_JSON)),
        patch("tools.chroma_store.upsert_context"),
        patch("tools.file_writer.write_files_sync"),
        patch("tools.test_runner.run_pytest", return_value={"passed": True, "total": 1, "passed_count": 1, "failed_count": 0, "failures": [], "stdout": "", "stderr": ""}),
        patch("agents.deployment_agent.build_and_push", return_value=True),
        patch("agents.deployment_agent.get_deployer"),
        patch("agents.repository_agent.create_repo_and_push", return_value=None),
    ):
        from orchestrator.runner import PipelineRunner
        runner = PipelineRunner()

        events = []
        async for event in runner.run("Build a simple item list app"):
            events.append(event)

        types = [e["type"] for e in events]
        assert "complete" in types, f"Pipeline did not complete. Events: {events}"

        complete_event = next(e for e in events if e["type"] == "complete")
        assert complete_event["data"]["app_name"] == "smoke_test_app"

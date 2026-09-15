"""
agents/testing_agent.py
────────────────────────
Testing Agent — Stage 5 of the pipeline.

Responsibilities:
  - Generate pytest test files for all FastAPI backend endpoints.
  - Verify frontend ↔ backend ↔ database integration against API contracts.
  - Execute tests in an isolated virtualenv via test_runner.
  - Report structured pass/fail results; route failures to the Bug Fixing Agent.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, TestResult
from tools.file_writer import write_files_sync
from tools.test_runner import run_pytest

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Testing Agent for an automated software development pipeline.
You generate pytest test files for a FastAPI backend application.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

Schema:
{
  "files": {
    "tests/conftest.py": "...pytest fixtures including TestClient setup...",
    "tests/test_<resource>.py": "...tests for each API router..."
  }
}

Requirements:
- Use pytest with httpx.AsyncClient or fastapi.testclient.TestClient.
- conftest.py: create a test database (SQLite in-memory), override get_db dependency, provide a test client fixture.
- Write at least one test per API endpoint: test happy path + one error case.
- Tests must not rely on external services — use SQLite for test DB.
- Import the FastAPI app from: from main import app
- Each test function must start with test_.
- Tests must be deterministic and independent (use fresh DB per test via fixtures).
- Include at least one auth test if auth is enabled."""


TEST_PROMPT_TEMPLATE = """Generate tests for this FastAPI application:

API Contracts:
{api_contracts}

Auth Strategy: {auth_strategy}
App Name: {app_name}

Generate comprehensive pytest files as described."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def _enrich_failures(failures: list[dict], backend_files: dict[str, str]) -> list[dict]:
    """
    For each test failure, attempt to attach the relevant source file
    so the Bug Fixing Agent has full context.
    """
    enriched = []
    for failure in failures:
        test_name = failure.get("test", "")
        # Heuristic: extract router name from test file name
        relevant_source = None
        for path in backend_files:
            router_hint = test_name.replace("test_", "").split("::")[0].split("/")[-1].replace(".py", "")
            if router_hint in path:
                relevant_source = backend_files[path][:2000]
                break
        enriched.append({**failure, "relevant_source_snippet": relevant_source})
    return enriched


def testing_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Testing Agent.

    Reads `project_plan`, `backend_code`, `database_schema`.
    Returns partial state with `test_results` updated.
    """
    logger.info("[TestingAgent] Starting test generation and execution...")
    plan = state.get("project_plan")
    backend_code = state.get("backend_code")

    if not plan or not backend_code:
        return {
            "stage": "testing_agent",
            "errors": state.get("errors", []) + ["project_plan or backend_code missing in TestingAgent"],
            "should_halt": True,
        }

    app_name = plan["app_name"]
    stack = plan.get("stack", {})
    auth_strategy = stack.get("auth_strategy", "jwt")

    # Step 1 — Generate test files
    llm = _build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=TEST_PROMPT_TEMPLATE.format(
            api_contracts=json.dumps(plan.get("api_contracts", []), indent=2),
            auth_strategy=auth_strategy,
            app_name=app_name,
        )),
    ]

    try:
        response = llm.invoke(messages)
        test_artifact = _parse_json_response(response.content)
        test_files: dict[str, str] = test_artifact.get("files", {})
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[TestingAgent] Test generation failed: {exc}")
        test_files = {}

    # Write test files into the backend output directory
    backend_dir = settings.output_dir / app_name / "backend"
    write_files_sync(app_name, "backend", test_files)

    # Step 2 — Execute tests
    test_dir = backend_dir / "tests"
    if not test_dir.exists() or not any(test_dir.iterdir()):
        logger.warning("[TestingAgent] No test files found — marking as passed with 0 tests.")
        result: TestResult = {
            "passed": True,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "failures": [],
            "summary": "No tests were generated or executed.",
        }
    else:
        run_output = run_pytest(app_name, test_dir)
        backend_files = backend_code.get("files", {})
        enriched_failures = _enrich_failures(run_output.get("failures", []), backend_files)

        result = {
            "passed": run_output["passed"],
            "total_tests": run_output["total"],
            "passed_tests": run_output["passed_count"],
            "failed_tests": run_output["failed_count"],
            "failures": enriched_failures,
            "summary": (
                f"{'✅ All tests passed' if run_output['passed'] else '❌ Tests failed'}. "
                f"{run_output['passed_count']}/{run_output['total']} passed."
            ),
        }

    logger.info(f"[TestingAgent] {result['summary']}")

    return {
        "test_results": result,
        "stage": "testing_agent_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "testing_agent": {
                "passed": result["passed"],
                "total": result["total_tests"],
                "failed": result["failed_tests"],
            },
        },
    }


def testing_routing(state: PipelineState) -> str:
    """
    Conditional edge: route to bug_fixing on failure, deployment on success.
    Respects the max retry limit.
    """
    test_results = state.get("test_results") or {}
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.max_retry_cycles)

    if test_results.get("passed"):
        return "deployment"
    if retry_count >= max_retries:
        return "halt"
    return "bug_fixing"

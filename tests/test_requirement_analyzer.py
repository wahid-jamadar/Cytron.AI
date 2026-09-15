"""
tests/test_requirement_analyzer.py
────────────────────────────────────
Unit tests for the Requirement Analyzer Agent.
Uses mocked LLM responses to avoid live API calls.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from agents.requirement_analyzer import requirement_analyzer_node, has_clarifying_questions
from state.pipeline_state import initial_state


MOCK_SPEC = {
    "app_name": "todo_app",
    "app_type": "crud",
    "description": "A simple todo application with user authentication.",
    "features": ["Create tasks", "Mark complete", "User login"],
    "user_roles": ["user"],
    "workflows": [{"name": "Create task", "steps": ["Login", "Click add", "Submit form"]}],
    "data_entities": ["User", "Task"],
    "non_functional": {"security": "JWT auth required", "performance": None, "scalability": None},
    "clarifying_questions": [],
}


@pytest.fixture
def mock_llm_response():
    """Patch ChatGroq to return a mocked spec."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(MOCK_SPEC)
    with patch("agents.requirement_analyzer.ChatGroq") as MockLLM:
        instance = MockLLM.return_value
        instance.invoke.return_value = mock_response
        yield instance


@pytest.fixture
def mock_chroma():
    with patch("agents.requirement_analyzer.upsert_context") as mock:
        yield mock


def test_requirement_analyzer_success(mock_llm_response, mock_chroma):
    """Should parse user input into a structured spec."""
    state = initial_state("Build me a todo app with user auth")
    result = requirement_analyzer_node(state)

    assert "structured_spec" in result
    spec = result["structured_spec"]
    assert spec["app_name"] == "todo_app"
    assert spec["app_type"] == "crud"
    assert "Create tasks" in spec["features"]
    assert result["stage"] == "requirement_analyzer_complete"


def test_requirement_analyzer_empty_input(mock_chroma):
    """Should halt when user input is empty."""
    state = initial_state("")
    result = requirement_analyzer_node(state)
    assert result.get("should_halt") is True
    assert len(result.get("errors", [])) > 0


def test_has_clarifying_questions_empty():
    """Should return 'proceed' when no questions are present."""
    state = initial_state("Build a todo app")
    state["structured_spec"] = {**MOCK_SPEC, "clarifying_questions": []}
    assert has_clarifying_questions(state) == "proceed"


def test_has_clarifying_questions_present():
    """Should return 'ask_user' when questions exist."""
    state = initial_state("Build something")
    state["structured_spec"] = {**MOCK_SPEC, "clarifying_questions": ["What should it do?"]}
    assert has_clarifying_questions(state) == "ask_user"


def test_app_name_slugified(mock_llm_response, mock_chroma):
    """App name should be sanitized to a valid slug."""
    mock_spec = {**MOCK_SPEC, "app_name": "My Cool App 2026!"}
    mock_llm_response.invoke.return_value.content = json.dumps(mock_spec)
    state = initial_state("Build My Cool App")
    result = requirement_analyzer_node(state)
    name = result["structured_spec"]["app_name"]
    assert " " not in name
    assert "!" not in name

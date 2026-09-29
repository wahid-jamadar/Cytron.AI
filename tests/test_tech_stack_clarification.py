import pytest
from fastapi.testclient import TestClient
from ui.main import app
from modules.build_complete_project.resolver import resolve_tech_stack
from modules.build_complete_project.analyzer import analyze_tech_stack, AnalyzerResponse

client = TestClient(app)

def test_resolver_logic():
    selected_stack = {
        "frontend": "React",
        "backend": "FastAPI",
        "architecture": "Monolith"
    }
    clarified_decisions = {
        "database": "postgresql",
        "authentication": "jwt"
    }
    
    final_stack = resolve_tech_stack(selected_stack, clarified_decisions)
    
    assert final_stack["frontend"] == "React"
    assert final_stack["backend"] == "FastAPI"
    assert final_stack["database"] == "postgresql"
    assert final_stack["authentication"] == "jwt"
    
    # Explicit user choice should override clarified choice if there's overlap
    clarified_decisions_overlap = {
        "frontend": "Vue",
        "database": "mongodb"
    }
    final_stack_overlap = resolve_tech_stack(selected_stack, clarified_decisions_overlap)
    assert final_stack_overlap["frontend"] == "React" # Explicit overrides clarified
    assert final_stack_overlap["database"] == "mongodb"

def test_analyze_stack_endpoint_incomplete():
    payload = {
        "prompt": "Build an e-commerce platform.",
        "selected_tech_stack": {
            "frontend": "React",
            "backend": "Python",
            "architecture": "Monolith"
        }
    }
    response = client.post("/build-complete-project/analyze-stack", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "needs_clarification" in data
    
    # We mock LLM ideally but since this calls the real LLM, we just check the schema structure
    if data["needs_clarification"]:
        assert isinstance(data["questions"], list)
        if len(data["questions"]) > 0:
            q = data["questions"][0]
            assert "id" in q
            assert "title" in q
            assert "options" in q

def test_analyze_stack_endpoint_complete():
    payload = {
        "prompt": "Build a simple static portfolio website with just HTML and CSS. No database, no backend.",
        "selected_tech_stack": {
            "frontend": "Basic HTML/CSS/JS",
            "backend": "Node.js (Express)",
            "architecture": "Monolithic"
        }
    }
    response = client.post("/build-complete-project/analyze-stack", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "needs_clarification" in data
    # Might still ask some questions depending on LLM, but at least the schema should be valid.
    if not data["needs_clarification"]:
        assert len(data["questions"]) == 0

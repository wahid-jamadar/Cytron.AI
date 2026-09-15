# tests/test_case_generator_test.py

import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from modules.test_case_generator.engine.frameworks import FRAMEWORKS_REGISTRY
from modules.test_case_generator.engine.coverages import COVERAGES_REGISTRY
from modules.test_case_generator.engine.test_types import TEST_TYPES_REGISTRY
from modules.test_case_generator.engine.exporters import (
    export_markdown,
    export_html,
    export_docx,
    export_xlsx,
    export_pdf,
    export_csv,
    export_xml,
    export_junit_xml,
    export_allure_report_zip,
    export_testrail_csv,
    export_xray_json,
    export_zephyr_csv,
    export_azure_devops_csv,
    export_zip_package
)
from ui.main import app

client = TestClient(app)
client.headers.update({"Authorization": "Bearer mock-token"})

@pytest.fixture(autouse=True)
def mock_auth():
    with patch("ui.main.verify_token") as mock_verify:
        mock_verify.return_value = {"type": "access", "roles": ["ADMIN"], "sub": "test@example.com"}
        yield

SAMPLE_TEST_CASES = [
    {
        "id": "TC-001",
        "title": "Validate user login with correct credentials",
        "objective": "Verify that a registered user can successfully log in using valid email and password.",
        "preconditions": "User account 'test@example.com' exists and is verified.",
        "dependencies": "Auth service, Database connector",
        "priority": "Critical",
        "category": "Functional Tests",
        "feature_mapping": "Authentication Flow",
        "requirement_mapping": "REQ-101",
        "test_data": "email: test@example.com, password: password123",
        "environment_setup": "Set up clean SQLite mock db.",
        "steps": [
            {"step_number": 1, "action": "Enter valid email", "expected_result": "Email accepted"},
            {"step_number": 2, "action": "Enter valid password and click submit", "expected_result": "Token generated and redirect to dashboard"}
        ],
        "expected_result": "User redirected to dashboard with valid JWT auth token.",
        "actual_result_placeholder": "Pending execution",
        "status_placeholder": "Untested",
        "cleanup_steps": "Clear browser local storage.",
        "edge_cases": "Attempt concurrent login on multiple devices.",
        "negative_scenarios": "Login with invalid password triggers 401 error.",
        "boundary_conditions": "Email length within database limits.",
        "risk_assessment": "Medium - Key access vector",
        "automation_feasibility": "High",
        "estimated_execution_time": "2 mins"
    }
]

SAMPLE_ANALYSIS = {
    "missing_test_scenarios": ["Verification of password expiration policies."],
    "edge_cases": ["Attempt login during database failover."],
    "security_risks": ["Auth token stored unencrypted in local storage."],
    "performance_bottlenecks": ["Hashing passwords takes > 500ms on single thread."],
    "concurrency_issues": ["Multiple rapid clicks on submit button spawns concurrent logins."],
    "validation_failures": ["Regex for email validation accepts subdomains without TLD."],
    "exception_handling_scenarios": ["Handling database connection timeouts gracefully."],
    "api_failure_cases": ["Post request returns 500 when auth server is down."],
    "database_consistency_issues": ["User login count increments out of transaction blocks."]
}

SAMPLE_INFO = {
    "title": "Authentication Integration Suite",
    "framework": "PyTest (Python)",
    "language": "Python",
    "coverage": "Critical (100%)",
    "style": "Automated Test Cases",
    "priority": "Critical",
    "environment": "Local",
    "complexity": "Standard",
    "detail": "Detailed",
    "code": "def test_login_success():\n    assert True",
    "extension": ".py"
}


def test_registries():
    # Frameworks
    assert "PyTest (Python)" in FRAMEWORKS_REGISTRY
    assert "Jest (JavaScript/TypeScript)" in FRAMEWORKS_REGISTRY
    assert FRAMEWORKS_REGISTRY["PyTest (Python)"]["language"] == "Python"
    
    # Coverages
    assert "Critical (100%)" in COVERAGES_REGISTRY
    assert "Security Coverage" in COVERAGES_REGISTRY
    
    # Test Types
    assert "Smoke Tests" in TEST_TYPES_REGISTRY
    assert "Chaos Engineering Tests" in TEST_TYPES_REGISTRY


def test_exporters():
    # Text-based exporters
    md_out = export_markdown(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert "# Test Suite:" in md_out
    assert "Validate user login" in md_out
    assert "Auth token stored unencrypted" in md_out
    
    html_out = export_html(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert "<!DOCTYPE html>" in html_out
    assert "Authentication Integration Suite" in html_out
    
    csv_out = export_csv(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert "Test Case ID,Title,Objective" in csv_out
    
    xml_out = export_xml(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert "<TestSuite>" in xml_out
    
    junit_out = export_junit_xml(SAMPLE_TEST_CASES, SAMPLE_INFO)
    assert "<testsuite" in junit_out
    
    testrail_out = export_testrail_csv(SAMPLE_TEST_CASES)
    assert "Section,Title,Type" in testrail_out
    
    xray_out = export_xray_json(SAMPLE_TEST_CASES, SAMPLE_INFO)
    assert "testKey" in xray_out
    
    zephyr_out = export_zephyr_csv(SAMPLE_TEST_CASES)
    assert "Name,Objective,Pre-requisite" in zephyr_out
    
    azure_out = export_azure_devops_csv(SAMPLE_TEST_CASES)
    assert "Title,Description,Priority" in azure_out
    
    # Binary/Archive exporters
    docx_out = export_docx(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert len(docx_out) > 0
    
    xlsx_out = export_xlsx(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert len(xlsx_out) > 0
    
    pdf_out = export_pdf(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert len(pdf_out) > 0
    
    allure_out = export_allure_report_zip(SAMPLE_TEST_CASES, SAMPLE_INFO)
    assert len(allure_out) > 0
    
    zip_out = export_zip_package(SAMPLE_TEST_CASES, SAMPLE_ANALYSIS, SAMPLE_INFO)
    assert len(zip_out) > 0


def test_generator_page_route():
    response = client.get("/test-case-generator/")
    assert response.status_code == 200
    assert "Test Case Generator" in response.text


@patch("modules.test_case_generator.router.tc_agent.generate_test_suite", new_callable=AsyncMock)
def test_generator_api_success(mock_generate):
    mock_generate.return_value = {
        "status": "success",
        "test_cases": SAMPLE_TEST_CASES,
        "analysis": SAMPLE_ANALYSIS,
        "code": "def test_login(): pass",
        "extension": ".py"
    }
    
    payload = {
        "framework": "PyTest (Python)",
        "coverage": "Critical (100%)",
        "test_types": ["Functional Tests", "API Tests"],
        "language": "Python",
        "style": "Automated Test Cases",
        "priority": "High",
        "environment": "Local",
        "complexity": "Standard",
        "detail": "Detailed",
        "content": "def login(): return True",
        "special_requirements": "Mock the DB",
        "input_source_type": "Source code",
        "severity": "Critical",
        "include_positive": True,
        "include_negative": True,
        "include_edge": True,
        "include_boundary": True,
        "include_equivalence": True,
        "generate_test_data": True,
        "browsers": ["Chrome", "Firefox", "Safari"],
        "devices": ["Desktop", "Mobile"],
        "os": ["Windows", "macOS", "Linux"],
        "include_preconditions": True,
        "include_postconditions": True,
        "include_expected_results": True,
        "generate_automation_script": True
    }
    
    response = client.post("/test-case-generator/api/generate", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert len(res_data["test_cases"]) == 1
    assert res_data["code"] == "def test_login(): pass"


def test_generator_api_missing_content():
    payload = {
        "framework": "PyTest (Python)",
        "coverage": "Critical (100%)",
        "test_types": ["Functional Tests"],
        "content": "",  # Empty content
        "input_source_type": "Source code"
    }
    response = client.post("/test-case-generator/api/generate", json=payload)
    assert response.status_code in (400, 422)


def test_exporter_api_success():
    payload = {
        "format": "json",
        "test_cases": SAMPLE_TEST_CASES,
        "analysis": SAMPLE_ANALYSIS,
        "info": SAMPLE_INFO
    }
    response = client.post("/test-case-generator/api/export", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "attachment; filename=test_suite.json" in response.headers["content-disposition"]
    data = response.json()
    assert "test_cases" in data
    assert "analysis" in data

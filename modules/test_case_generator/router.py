# modules/test_case_generator/router.py

import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from modules.common.utils import templates
from agents.test_case_agent import TestCaseAgent
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

router = APIRouter(prefix="/test-case-generator", tags=["test-case-generator"])
tc_agent = TestCaseAgent()
logger = logging.getLogger(__name__)

# Request Model for Generation
class TestCaseGenerateRequest(BaseModel):
    framework: str = Field(..., description="Target testing framework")
    coverage: str = Field(..., description="Target coverage strategy")
    test_types: List[str] = Field(..., description="List of selected test types")
    language: str = Field("Generic", description="Target programming language")
    style: str = Field("Automated Test Cases", description="Manual or automated styling")
    priority: str = Field("Medium", description="Suite default priority level")
    environment: str = Field("Local", description="Execution environment")
    complexity: str = Field("Standard", description="Complexity level")
    detail: str = Field("Standard", description="Output detail level")
    content: str = Field(..., description="The main content (code, requirements, stories, etc.) to write tests for")
    special_requirements: Optional[str] = Field("", description="Special requirements or mocking details")
    input_source_type: str = Field("Source code", description="Source input format")
    
    # Advanced settings
    severity: str = Field("Major", description="Suite default severity level")
    include_positive: bool = Field(True, description="Incorporate positive scenarios")
    include_negative: bool = Field(True, description="Incorporate negative scenarios")
    include_edge: bool = Field(True, description="Generate edge cases")
    include_boundary: bool = Field(True, description="Apply boundary value analysis")
    include_equivalence: bool = Field(True, description="Apply equivalence partitioning")
    generate_test_data: bool = Field(True, description="Generate test data")
    browsers: List[str] = Field(["Chrome", "Firefox"], description="Target browser support")
    devices: List[str] = Field(["Desktop"], description="Target device compatibility")
    os: List[str] = Field(["Windows", "Linux"], description="Target operating system support")
    include_preconditions: bool = Field(True, description="Incorporate preconditions")
    include_postconditions: bool = Field(True, description="Incorporate postconditions")
    include_expected_results: bool = Field(True, description="Incorporate expected results")
    generate_automation_script: bool = Field(True, description="Generate automation script")

# Request Model for Exporting
class TestCaseExportRequest(BaseModel):
    format: str = Field(..., description="Export format requested")
    test_cases: List[Dict[str, Any]] = Field(..., description="List of generated test cases")
    analysis: Dict[str, Any] = Field(..., description="Intelligent quality analysis metadata")
    info: Dict[str, Any] = Field(..., description="Configuration information used during generation")


@router.get("/")
async def page(request: Request):
    return templates.TemplateResponse("test_case_generator.html", {"request": request})


@router.post("/api/generate")
async def generate_tests(req: TestCaseGenerateRequest):
    logger.info(f"Generating test cases with framework '{req.framework}' from source '{req.input_source_type}'")
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Input content to test cannot be empty")
        
    result = await tc_agent.generate_test_suite(req.model_dump())
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
        
    return result


@router.post("/api/export")
async def export_tests(req: TestCaseExportRequest):
    fmt = req.format.lower().strip()
    test_cases = req.test_cases
    analysis = req.analysis
    info = req.info
    
    logger.info(f"Exporting test cases in format '{fmt}'")
    
    try:
        if fmt in ("markdown", "github", "gitlab"):
            content = export_markdown(test_cases, analysis, info)
            ext = "md"
            media_type = "text/markdown"
            return Response(content=content, media_type=media_type, headers={
                "Content-Disposition": f"attachment; filename=test_suite_{fmt}.{ext}"
            })
            
        elif fmt == "html":
            content = export_html(test_cases, analysis, info)
            return Response(content=content, media_type="text/html", headers={
                "Content-Disposition": "attachment; filename=test_suite.html"
            })
            
        elif fmt == "docx":
            data = export_docx(test_cases, analysis, info)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return Response(content=data, media_type=media_type, headers={
                "Content-Disposition": "attachment; filename=test_suite.docx"
            })
            
        elif fmt in ("excel", "xlsx"):
            data = export_xlsx(test_cases, analysis, info)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            return Response(content=data, media_type=media_type, headers={
                "Content-Disposition": "attachment; filename=test_suite.xlsx"
            })
            
        elif fmt == "pdf":
            data = export_pdf(test_cases, analysis, info)
            return Response(content=data, media_type="application/pdf", headers={
                "Content-Disposition": "attachment; filename=test_suite.pdf"
            })
            
        elif fmt == "csv":
            content = export_csv(test_cases, analysis, info)
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": "attachment; filename=test_cases.csv"
            })
            
        elif fmt == "json":
            content = json.dumps({"test_cases": test_cases, "analysis": analysis, "info": info}, indent=2)
            return Response(content=content, media_type="application/json", headers={
                "Content-Disposition": "attachment; filename=test_suite.json"
            })
            
        elif fmt in ("yaml", "yml"):
            content = yaml.dump({"test_cases": test_cases, "analysis": analysis, "info": info}, default_flow_style=False)
            return Response(content=content, media_type="application/x-yaml", headers={
                "Content-Disposition": "attachment; filename=test_suite.yaml"
            })
            
        elif fmt == "xml":
            content = export_xml(test_cases, analysis, info)
            return Response(content=content, media_type="application/xml", headers={
                "Content-Disposition": "attachment; filename=test_suite.xml"
            })
            
        elif fmt == "junit":
            content = export_junit_xml(test_cases, info)
            return Response(content=content, media_type="application/xml", headers={
                "Content-Disposition": "attachment; filename=junit_report.xml"
            })
            
        elif fmt == "allure":
            data = export_allure_report_zip(test_cases, info)
            return Response(content=data, media_type="application/zip", headers={
                "Content-Disposition": "attachment; filename=allure_results.zip"
            })
            
        elif fmt == "testrail":
            content = export_testrail_csv(test_cases)
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": "attachment; filename=testrail_import.csv"
            })
            
        elif fmt == "xray":
            content = export_xray_json(test_cases, info)
            return Response(content=content, media_type="application/json", headers={
                "Content-Disposition": "attachment; filename=xray_import.json"
            })
            
        elif fmt == "zephyr":
            content = export_zephyr_csv(test_cases)
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": "attachment; filename=zephyr_import.csv"
            })
            
        elif fmt == "azure":
            content = export_azure_devops_csv(test_cases)
            return Response(content=content, media_type="text/csv", headers={
                "Content-Disposition": "attachment; filename=azure_devops_import.csv"
            })
            
        elif fmt == "zip":
            data = export_zip_package(test_cases, analysis, info)
            return Response(content=data, media_type="application/zip", headers={
                "Content-Disposition": "attachment; filename=test_suite_package.zip"
            })
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {fmt}")
            
    except Exception as e:
        logger.error(f"Error executing export for format {fmt}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")

# agents/test_case_agent.py

import json
import logging
from typing import Dict, Any, List

from config.settings import settings
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from tools.json_parser import parse_llm_json

from modules.test_case_generator.engine.frameworks import FRAMEWORKS_REGISTRY
from modules.test_case_generator.engine.coverages import COVERAGES_REGISTRY
from modules.test_case_generator.engine.test_types import TEST_TYPES_REGISTRY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are an Enterprise Test Case and Quality Analysis Agent.
Analyze the provided input and generate a complete test suite based on the following configurations.

You MUST respond with a valid JSON object ONLY. No markdown, no prose, just the JSON.
Your JSON must strictly adhere to the following schema:

{{
  "test_cases": [
    {{
      "id": "TC-001",
      "title": "string",
      "objective": "string",
      "preconditions": "string",
      "dependencies": "string",
      "priority": "string",
      "category": "string",
      "feature_mapping": "string",
      "requirement_mapping": "string",
      "test_data": "string",
      "environment_setup": "string",
      "steps": [
        {{
          "step_number": 1,
          "action": "string",
          "expected_result": "string"
        }}
      ],
      "expected_result": "string",
      "actual_result_placeholder": "Pending execution",
      "status_placeholder": "Untested",
      "cleanup_steps": "string",
      "edge_cases": "string",
      "negative_scenarios": "string",
      "boundary_conditions": "string",
      "risk_assessment": "string",
      "automation_feasibility": "string",
      "estimated_execution_time": "string"
    }}
  ],
  "analysis": {{
    "missing_test_scenarios": ["string"],
    "edge_cases": ["string"],
    "boundary_value_conditions": ["string"],
    "invalid_inputs": ["string"],
    "security_risks": ["string"],
    "performance_bottlenecks": ["string"],
    "concurrency_issues": ["string"],
    "validation_failures": ["string"],
    "exception_handling_scenarios": ["string"],
    "api_failure_cases": ["string"],
    "database_consistency_issues": ["string"]
  }},
  "code": "string"
}}

Configuration Details:
- **Framework Guidelines**: {framework_guidelines}
- **Programming Language**: {language}
- **Coverage Strategy**: {coverage_instruction}
- **Selected Test Types to merge**: {test_types_instruction}
- **Test Style**: {style}
- **Priority**: {priority}
- **Severity Default**: {severity}
- **Execution Environment**: {environment}
- **Complexity**: {complexity}
- **Output Detail Level**: {detail}
- **Incorporate Positive Cases**: {include_positive}
- **Incorporate Negative Cases**: {include_negative}
- **Incorporate Edge Cases**: {include_edge}
- **Apply Boundary Value Analysis**: {include_boundary}
- **Apply Equivalence Partitioning**: {include_equivalence}
- **Generate Sample Test Data**: {generate_test_data}
- **Target Browser Support**: {browsers}
- **Target Device Compatibility**: {devices}
- **Target Operating System Support**: {os}
- **Incorporate Preconditions**: {include_preconditions}
- **Incorporate Postconditions**: {include_postconditions}
- **Incorporate Expected Results**: {include_expected_results}
- **Generate Automation Scripts**: {generate_automation_script}

For automated test styles (Automated, BDD, TDD, ATDD), the 'code' field MUST contain the complete, valid, executable test suite code matching the target framework syntax, including necessary imports, setup, teardown, mocked dependencies, and assertions. If BDD style is chosen, structure the code or scenario blocks to follow Given-When-Then syntax. If Manual style is chosen, the 'code' field should be an empty string.

Ensure all generated fields are completely filled out and relevant to the strategy rather than generic placeholders.
"""

HUMAN_PROMPT_TEMPLATE = """Here is the input to generate tests for:

**Input Type / Source**: {input_source_type}

**Mocking & Special Requirements**:
{special_requirements}

**Input Content**:
{content}
"""

class TestCaseAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.1
        )

    async def generate_test_suite(self, params: Dict[str, Any]) -> Dict[str, Any]:
        framework = params.get("framework", "Generic")
        coverage = params.get("coverage", "Standard")
        selected_types = params.get("test_types", [])
        language = params.get("language", "Generic")
        style = params.get("style", "Manual")
        priority = params.get("priority", "Medium")
        environment = params.get("environment", "Local")
        complexity = params.get("complexity", "Standard")
        detail = params.get("detail", "Standard")
        content = params.get("content", "")
        special_requirements = params.get("special_requirements", "")
        input_source_type = params.get("input_source_type", "Plain-text requirements")
        
        # Advanced settings
        severity = params.get("severity", "Major")
        include_positive = params.get("include_positive", True)
        include_negative = params.get("include_negative", True)
        include_edge = params.get("include_edge", True)
        include_boundary = params.get("include_boundary", True)
        include_equivalence = params.get("include_equivalence", True)
        generate_test_data = params.get("generate_test_data", True)
        browsers = params.get("browsers", ["Chrome", "Firefox"])
        devices = params.get("devices", ["Desktop"])
        os_list = params.get("os", ["Windows", "Linux"])
        include_preconditions = params.get("include_preconditions", True)
        include_postconditions = params.get("include_postconditions", True)
        include_expected_results = params.get("include_expected_results", True)
        generate_automation_script = params.get("generate_automation_script", True)

        # Resolve strategy configurations
        fw_config = FRAMEWORKS_REGISTRY.get(framework, {
            "language": language,
            "extension": ".txt",
            "guidelines": "Write generic test scripts."
        })
        framework_guidelines = f"Framework: {framework}. Language rules: {fw_config['guidelines']}"
        coverage_instruction = COVERAGES_REGISTRY.get(coverage, "Standard test coverage.")
        
        merged_types = []
        for t in selected_types:
            inst = TEST_TYPES_REGISTRY.get(t, f"Test category: {t}.")
            merged_types.append(inst)
        test_types_instruction = " AND ".join(merged_types) if merged_types else "Standard functionality verification."

        system_content = SYSTEM_PROMPT_TEMPLATE.format(
            framework_guidelines=framework_guidelines,
            language=fw_config.get("language", language),
            coverage_instruction=coverage_instruction,
            test_types_instruction=test_types_instruction,
            style=style,
            priority=priority,
            severity=severity,
            environment=environment,
            complexity=complexity,
            detail=detail,
            include_positive=include_positive,
            include_negative=include_negative,
            include_edge=include_edge,
            include_boundary=include_boundary,
            include_equivalence=include_equivalence,
            generate_test_data=generate_test_data,
            browsers=", ".join(browsers),
            devices=", ".join(devices),
            os=", ".join(os_list),
            include_preconditions=include_preconditions,
            include_postconditions=include_postconditions,
            include_expected_results=include_expected_results,
            generate_automation_script=generate_automation_script
        )

        human_content = HUMAN_PROMPT_TEMPLATE.format(
            input_source_type=input_source_type,
            special_requirements=special_requirements,
            content=content
        )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content)
        ]

        logger.info(f"Generating test cases for framework: {framework}, coverage: {coverage}")
        try:
            response = await self.llm.ainvoke(messages)
            raw_result = response.content
            
            # Clean possible markdown wrapping if the LLM ignored instructions
            cleaned_result = raw_result.strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result[7:]
            elif cleaned_result.startswith("```"):
                cleaned_result = cleaned_result[3:]
            if cleaned_result.endswith("```"):
                cleaned_result = cleaned_result[:-3]
            cleaned_result = cleaned_result.strip()
            
            parsed = parse_llm_json(cleaned_result)
            
            # Verify parsed keys exist
            test_cases = parsed.get("test_cases", [])
            analysis = parsed.get("analysis", {})
            code = parsed.get("code", "")
            
            return {
                "status": "success",
                "test_cases": test_cases,
                "analysis": analysis,
                "code": code,
                "extension": fw_config.get("extension", ".txt")
            }
        except Exception as e:
            logger.error(f"Error invoking LLM for test generation: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"Failed to generate test cases: {str(e)}"
            }

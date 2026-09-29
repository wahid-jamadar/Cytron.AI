"""
modules/build_complete_project/analyzer.py
─────────────────────────────────────────────
Analyzer for Tech Stack Completeness and Ambiguity.
"""

import json
import logging
from typing import List, Optional
from pydantic import BaseModel, Field

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from tools.json_parser import parse_llm_json

logger = logging.getLogger(__name__)

# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class ClarificationOption(BaseModel):
    id: str = Field(..., description="Unique ID for this option (e.g., 'postgresql')")
    label: str = Field(..., description="Human-readable label (e.g., 'PostgreSQL')")
    description: str = Field(..., description="Brief description of when to use this option")
    recommended: bool = Field(False, description="Whether this is the recommended default")

class ClarificationQuestion(BaseModel):
    id: str = Field(..., description="Unique ID for this question category (e.g., 'database', 'auth')")
    category: str = Field(..., description="Category name (e.g., 'Database', 'Authentication')")
    title: str = Field(..., description="Short title of the question")
    description: str = Field(..., description="Explanation of why this decision matters for the project")
    required: bool = Field(True, description="Whether an answer is mandatory to proceed")
    priority: int = Field(..., description="Priority for sorting (1=highest)")
    options: List[ClarificationOption] = Field(..., description="Available multiple-choice options")

class AnalyzerResponse(BaseModel):
    needs_clarification: bool = Field(..., description="True if material technical decisions are missing or conflicting")
    questions: List[ClarificationQuestion] = Field(default_factory=list, description="Questions to ask the user, prioritized by importance")


SYSTEM_PROMPT = """You are the Tech Stack Analyzer for an autonomous code generation platform.
Your job is to read a user's project requirements and their explicitly selected initial tech stack, and determine if there are material technical decisions missing, ambiguous, or conflicting.

You MUST respond with valid JSON only conforming to the schema. Do not include markdown blocks or prose.

Rules:
1. ONLY ask questions that are MATERIALLY RELEVANT to the specific project. 
   - A static portfolio does not need a database or message broker.
   - An e-commerce app needs a database, auth, and possibly payment provider.
2. If the user explicitly specified a technology in the prompt or stack, DO NOT ask about it unless there is a severe conflict.
3. If the user's prompt explicitly requests something that conflicts with their selected tech stack, formulate a question to resolve the conflict.
4. Keep the list of questions focused (max 5-7 questions for complex apps, 0-2 for simple apps).
5. Always provide 2-5 sensible options per question, marking one as 'recommended'.

Example JSON Schema:
{
  "needs_clarification": true,
  "questions": [
    {
      "id": "database",
      "category": "Database",
      "title": "Which database would you prefer?",
      "description": "Your e-commerce app requires a database to store products and orders.",
      "required": true,
      "priority": 1,
      "options": [
        {
          "id": "postgresql",
          "label": "PostgreSQL",
          "description": "Robust relational database (Recommended)",
          "recommended": true
        }
      ]
    }
  ]
}
"""

def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )

def analyze_tech_stack(prompt: str, selected_stack: dict) -> AnalyzerResponse:
    """
    Analyzes the prompt and selected tech stack for completeness and conflicts.
    """
    if not prompt or not prompt.strip():
        return AnalyzerResponse(needs_clarification=False, questions=[])

    llm = _build_llm()
    
    human_content = f"User Project Requirement:\n{prompt}\n\nUser Explicitly Selected Tech Stack:\n{json.dumps(selected_stack, indent=2)}\n\nAnalyze the requirements and generate the JSON clarification payload if needed."
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_content)
    ]
    
    try:
        response = llm.invoke(messages)
        raw_content = response.content
        parsed = parse_llm_json(raw_content)
        
        # Validate through Pydantic
        analyzer_response = AnalyzerResponse(**parsed)
        
        # If no questions, enforce needs_clarification=False
        if not analyzer_response.questions:
            analyzer_response.needs_clarification = False
            
        return analyzer_response
    except Exception as exc:
        logger.error(f"[TechStackAnalyzer] Failed to analyze tech stack or parse response: {exc}")
        # Fail gracefully: don't block generation if analyzer fails
        return AnalyzerResponse(needs_clarification=False, questions=[])

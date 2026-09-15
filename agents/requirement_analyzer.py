"""
agents/requirement_analyzer.py
────────────────────────────────
Requirement Analyzer Agent — Stage 1 of the pipeline.

Responsibilities:
  - Accept raw natural-language application requirements from the user.
  - Parse them into a structured RequirementSpec using Llama 3 via Groq.
  - Identify ambiguous/missing information and surface clarifying questions.
  - Store the structured spec in ChromaDB for downstream agent retrieval.
  - Return the updated PipelineState with `structured_spec` populated.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, RequirementSpec
from tools.chroma_store import upsert_context

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are the Requirement Analyzer Agent for an automated software development pipeline.
Your job is to read a user's natural-language application description and extract a structured specification.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

The JSON must conform to this schema:
{
  "app_name": "short_slug_name",           // snake_case, used as directory name
  "app_type": "crud|dashboard|ecommerce|blog|saas|other",
  "description": "one paragraph summary",
  "features": ["feature 1", "feature 2", ...],
  "user_roles": ["admin", "user", ...],
  "workflows": [
    {"name": "workflow name", "steps": ["step 1", "step 2"]}
  ],
  "data_entities": ["Entity1", "Entity2", ...],
  "non_functional": {
    "performance": "any perf notes or null",
    "security": "auth requirements or null",
    "scalability": "any scale notes or null"
  },
  "clarifying_questions": []              // List questions if requirements are ambiguous. Empty if clear.
}

Be thorough. Infer reasonable details from context. Only add clarifying_questions for genuinely ambiguous 
or missing information that would significantly affect the architecture."""

# ── LLM setup ─────────────────────────────────────────────────────────────────
def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.2,
        max_retries=2,
    )


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


# ── Agent node ────────────────────────────────────────────────────────────────
def requirement_analyzer_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Requirement Analyzer Agent.

    Args:
        state: Current pipeline state. Reads `user_input`.

    Returns:
        Partial state dict with `structured_spec` and `stage` updated.
    """
    logger.info("[RequirementAnalyzer] Starting analysis...")
    user_input = state.get("user_input", "").strip()

    if not user_input:
        return {
            "stage": "requirement_analyzer",
            "errors": state.get("errors", []) + ["User input is empty."],
            "should_halt": True,
        }

    llm = _build_llm()

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Application Requirements:\n\n{user_input}"),
    ]

    try:
        response = llm.invoke(messages)
        raw_content = response.content
        spec_dict = _parse_json_response(raw_content)
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[RequirementAnalyzer] Failed to parse LLM response: {exc}")
        return {
            "stage": "requirement_analyzer",
            "errors": state.get("errors", []) + [f"RequirementAnalyzer LLM error: {exc}"],
            "should_halt": True,
        }

    # Ensure app_name is a valid slug
    raw_name = spec_dict.get("app_name", "generated_app")
    spec_dict["app_name"] = re.sub(r"[^a-z0-9_]", "_", raw_name.lower())[:40]

    spec: RequirementSpec = spec_dict  # type: ignore[assignment]

    # Persist spec to ChromaDB for downstream agent retrieval
    collection_name = spec["app_name"]
    upsert_context(
        collection_name=collection_name,
        key="structured_spec",
        text=json.dumps(spec, indent=2),
        metadata={"agent": "requirement_analyzer", "app_name": spec["app_name"]},
    )

    logger.info(
        f"[RequirementAnalyzer] Done. App: '{spec['app_name']}', "
        f"type: '{spec.get('app_type')}', "
        f"features: {len(spec.get('features', []))}, "
        f"clarifying questions: {len(spec.get('clarifying_questions', []))}"
    )

    return {
        "structured_spec": spec,
        "stage": "requirement_analyzer_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "requirement_analyzer": {
                "app_name": spec["app_name"],
                "features_count": len(spec.get("features", [])),
                "has_clarifying_questions": bool(spec.get("clarifying_questions")),
            },
        },
    }


# ── Routing helper ────────────────────────────────────────────────────────────
def has_clarifying_questions(state: PipelineState) -> str:
    """
    Conditional edge function.
    Returns "ask_user" if the spec has clarifying questions, else "proceed".
    """
    spec = state.get("structured_spec") or {}
    questions = spec.get("clarifying_questions", [])
    return "ask_user" if questions else "proceed"

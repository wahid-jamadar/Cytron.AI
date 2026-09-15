"""
agents/code_review_agent.py
────────────────────────────
Code Review Agent — Stage 4 of the pipeline.

Responsibilities:
  - Review all generated source code for security issues, style problems,
    and maintainability concerns.
  - Flag HIGH severity issues that block progression to testing.
  - Return a structured ReviewResult.
"""
import json
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, ReviewResult
from modules.code_review.analyzer import PythonAnalyzer, determine_language

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Code Review Agent for an automated software development pipeline.
You review generated code for security vulnerabilities, style issues, and maintainability problems.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

Schema:
{
  "issues": [
    {
      "file": "relative/path/to/file.py",
      "issue_type": "security | style | maintainability | correctness",
      "description": "clear description of the issue",
      "severity": "HIGH | MEDIUM | LOW",
      "suggestion": "how to fix it"
    }
  ],
  "blocked": true | false,
  "summary": "overall review summary"
}

Set "blocked" to true ONLY if there are HIGH severity security issues such as:
- SQL injection vulnerabilities
- Hardcoded secrets or API keys
- Missing authentication on protected endpoints
- Obvious logic errors that would break core functionality

MEDIUM and LOW issues should be flagged but must NOT block the pipeline."""

def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )

def _summarize_files(files: dict[str, str], max_chars: int = 6000) -> str:
    """Truncate files dict to fit in LLM context."""
    summary = []
    total = 0
    for path, content in files.items():
        snippet = content[:800]
        entry = f"--- {path} ---\n{snippet}\n"
        if total + len(entry) > max_chars:
            summary.append(f"--- {path} --- [truncated, {len(content)} chars]\n")
        else:
            summary.append(entry)
            total += len(entry)
    return "\n".join(summary)


def code_review_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Code Review Agent.
    """
    logger.info("[CodeReviewAgent] Starting code review...")

    all_files: dict[str, str] = {}
    for artifact_key in ["backend_code", "database_schema"]:
        artifact = state.get(artifact_key)  # type: ignore[call-overload]
        if artifact and artifact.get("files"):
            for path, content in artifact["files"].items():
                all_files[f"{artifact_key}/{path}"] = content

    if not all_files:
        logger.warning("[CodeReviewAgent] No files to review — skipping.")
        return {
            "review_results": ReviewResult(issues=[], blocked=False, summary="No files to review."),
            "stage": "code_review_complete",
        }

    static_issues = []
    for path, content in all_files.items():
        lang = determine_language([path], [content])
        if lang == "python":
            analyzer = PythonAnalyzer({path: content})
            for f in analyzer.analyze():
                static_issues.append({
                    "file": f.file,
                    "issue_type": "security" if f.category == "security" else ("correctness" if f.category in ("syntax", "logic") else "maintainability"),
                    "description": f.description,
                    "severity": "HIGH" if f.severity in ("critical", "high") else "MEDIUM",
                    "suggestion": f.recommendation
                })

    code_summary = _summarize_files(all_files)

    llm = _build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Review the following generated code:\n\n{code_summary}\n\nExisting static analysis findings (do not duplicate):\n{json.dumps(static_issues, indent=2)}"),
    ]

    try:
        response = llm.invoke(messages)
        
        content = response.content
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        result_dict = json.loads(content.strip())
    except Exception as exc:
        logger.error(f"[CodeReviewAgent] LLM error: {exc}")
        result_dict = {"issues": [], "blocked": False, "summary": f"Code review failed: {exc}. Proceeding anyway."}

    # Merge static and dynamic issues
    merged_issues = static_issues + result_dict.get("issues", [])
    blocked = result_dict.get("blocked", False) or any(i.get("severity") == "HIGH" for i in static_issues)
    
    result = ReviewResult(
        issues=merged_issues,
        blocked=blocked,
        summary=result_dict.get("summary", f"Found {len(merged_issues)} issues in automated and AI review.")
    )

    high_issues = [i for i in merged_issues if i.get("severity") == "HIGH"]

    logger.info(
        f"[CodeReviewAgent] Review complete. "
        f"Total issues: {len(merged_issues)}, "
        f"HIGH: {len(high_issues)}, "
        f"Blocked: {blocked}"
    )

    return {
        "review_results": result,
        "stage": "code_review_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            "code_review_agent": {
                "total_issues": len(merged_issues),
                "high_severity": len(high_issues),
                "blocked": blocked,
            },
        },
    }

def review_routing(state: PipelineState) -> str:
    """
    Conditional edge: route to bug_fixing if blocked, else to testing.
    """
    review = state.get("review_results")
    # Need to access attributes if it's a pydantic model, or handle dict access
    if review:
        blocked = getattr(review, "blocked", False)
        return "bug_fixing" if blocked else "testing"
    return "testing"


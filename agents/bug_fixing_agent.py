"""
agents/bug_fixing_agent.py
───────────────────────────
Bug Fixing Agent — Stage 6 of the pipeline.

Responsibilities:
  - Consume test failure reports from the Testing Agent (or HIGH severity
    issues from the Code Review Agent).
  - For each failure, use Llama 3 to produce a targeted patch for the
    relevant source file.
  - Apply patches and update the state's code artifacts.
  - Increment retry_count. The Testing Agent will re-run after this node.
  - Max retries enforced by the orchestrator routing logic.
"""

import json
from tools.json_parser import parse_llm_json
import logging
import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config.settings import settings
from state.pipeline_state import PipelineState, CodeArtifact
from tools.file_writer import write_files_sync

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the Bug Fixing Agent for an automated software development pipeline.
You receive a list of test failures and the relevant source code, and you produce targeted fixes.

You MUST respond with valid JSON only — no markdown, no prose, just the JSON object.

Schema:
{
  "fixes": [
    {
      "file": "relative/path/to/file.py",
      "component": "backend | database | frontend",
      "original_snippet": "the exact code snippet that has the bug (few lines)",
      "fixed_snippet": "the corrected replacement for that snippet",
      "explanation": "what was wrong and how it was fixed"
    }
  ],
  "summary": "overall summary of all fixes applied"
}

Rules:
- Only fix what is broken — do not rewrite unrelated code.
- fixed_snippet must be a drop-in replacement for original_snippet.
- If you cannot determine the fix, skip that failure rather than guessing.
- Focus on real functional correctness, not style."""


FIX_PROMPT_TEMPLATE = """Fix the following test failures:

Failures:
{failures}

Relevant source files (snippets):
{source_snippets}

Code Review Issues (if any):
{review_issues}

Generate targeted fixes as described."""


def _build_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
        max_retries=2,
    )


def _parse_json_response(raw: str) -> dict:
    return parse_llm_json(raw)


def _apply_patch(original_files: dict[str, str], fixes: list[dict]) -> dict[str, str]:
    """
    Apply snippet-level patches to the files dict.
    Returns an updated copy of the files dict.
    """
    patched = dict(original_files)
    for fix in fixes:
        file_path = fix.get("file", "")
        original_snippet = fix.get("original_snippet", "")
        fixed_snippet = fix.get("fixed_snippet", "")

        if not file_path or not original_snippet or not fixed_snippet:
            continue

        if file_path in patched and original_snippet in patched[file_path]:
            patched[file_path] = patched[file_path].replace(original_snippet, fixed_snippet, 1)
            logger.debug(f"[BugFixingAgent] Patched {file_path}")
        else:
            logger.warning(
                f"[BugFixingAgent] Could not find snippet in {file_path} — snippet may have drifted."
            )
    return patched


def _gather_source_snippets(
    test_failures: list[dict],
    backend_files: dict[str, str],
    db_files: dict[str, str],
) -> str:
    """Collect relevant source snippets for failed tests."""
    snippets = {}
    for failure in test_failures[:5]:  # Limit to 5 failures per round
        source_snippet = failure.get("relevant_source_snippet")
        if source_snippet:
            snippets[failure.get("test", "unknown")] = source_snippet
        # Also try to find matching file
        test_name = failure.get("test", "")
        for path, content in {**backend_files, **db_files}.items():
            if any(keyword in path for keyword in test_name.split("::")[0].split("_")):
                snippets[path] = content[:1500]
                break
    return json.dumps(snippets, indent=2)[:6000]


def bug_fixing_agent_node(state: PipelineState) -> dict:
    """
    LangGraph node function for the Bug Fixing Agent.

    Reads `test_results`, `review_results`, `backend_code`, `database_schema`.
    Returns updated `backend_code` and/or `database_schema` with patches applied,
    and increments `retry_count`.
    """
    logger.info("[BugFixingAgent] Starting bug fixing...")

    test_results = state.get("test_results") or {}
    review_results = state.get("review_results") or {}
    backend_code = state.get("backend_code") or {}
    database_schema = state.get("database_schema") or {}
    plan = state.get("project_plan") or {}
    app_name = plan.get("app_name", "app")

    failures = test_results.get("failures", [])
    review_issues = [i for i in review_results.get("issues", []) if i.get("severity") == "HIGH"]

    if not failures and not review_issues:
        logger.info("[BugFixingAgent] No failures or HIGH issues to fix.")
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "stage": "bug_fixing_complete",
        }

    backend_files = backend_code.get("files", {})
    db_files = database_schema.get("files", {})
    source_snippets = _gather_source_snippets(failures, backend_files, db_files)

    llm = _build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=FIX_PROMPT_TEMPLATE.format(
            failures=json.dumps(failures[:5], indent=2),
            source_snippets=source_snippets,
            review_issues=json.dumps(review_issues[:3], indent=2),
        )),
    ]

    try:
        response = llm.invoke(messages)
        fix_dict = _parse_json_response(response.content)
        fixes = fix_dict.get("fixes", [])
    except (json.JSONDecodeError, Exception) as exc:
        logger.error(f"[BugFixingAgent] LLM error: {exc}")
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "stage": "bug_fixing_complete",
            "errors": state.get("errors", []) + [f"BugFixingAgent error: {exc}"],
        }

    # Separate fixes by component
    backend_fixes = [f for f in fixes if f.get("component") in ("backend", None, "")]
    db_fixes = [f for f in fixes if f.get("component") == "database"]

    # Apply patches
    patched_backend = _apply_patch(backend_files, backend_fixes)
    patched_db = _apply_patch(db_files, db_fixes)

    # Persist patched files
    if backend_fixes:
        write_files_sync(app_name, "backend", patched_backend)
    if db_fixes:
        write_files_sync(app_name, "database", patched_db)

    updated_backend: CodeArtifact = {**backend_code, "files": patched_backend}
    updated_db: CodeArtifact = {**database_schema, "files": patched_db}

    new_retry = state.get("retry_count", 0) + 1
    logger.info(
        f"[BugFixingAgent] Applied {len(fixes)} fix(es). "
        f"Retry count: {new_retry}/{state.get('max_retries', settings.max_retry_cycles)}"
    )

    return {
        "backend_code": updated_backend,
        "database_schema": updated_db,
        "retry_count": new_retry,
        "stage": "bug_fixing_complete",
        "agent_logs": {
            **state.get("agent_logs", {}),
            f"bug_fixing_agent_retry_{new_retry}": {
                "fixes_applied": len(fixes),
                "failures_targeted": len(failures),
                "summary": fix_dict.get("summary", ""),
            },
        },
    }

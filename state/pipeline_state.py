"""
state/pipeline_state.py
────────────────────────
Defines the shared state object that flows through the entire LangGraph pipeline.
Every agent node reads from and writes to this TypedDict.

Design principles:
  - All fields are optional (None) by default — agents only populate their own outputs.
  - Downstream agents guard against None before reading upstream fields.
  - `stage` tracks the current position in the pipeline for logging/UI.
  - `errors` accumulates any non-fatal issues across agents.

IMPORTANT — Parallel node keys:
  The pipeline has three nodes (frontend_agent, backend_agent, database_agent) that
  run concurrently and all write to `stage`, `errors`, and `agent_logs`.
  LangGraph raises INVALID_CONCURRENT_GRAPH_UPDATE if multiple parallel nodes write
  to the same key without a reducer.  We use `Annotated` with custom reducers for
  every key that parallel nodes touch:
    - `stage`      → last-writer-wins (keep most recent string)
    - `errors`     → list concatenation (accumulate all errors)
    - `agent_logs` → dict merge (union all agent log dicts)
"""

from typing import Annotated, TypedDict, Optional, Any


# ── Reducer helpers ────────────────────────────────────────────────────────────

def _keep_last(a: Any, b: Any) -> Any:
    """
    Last-writer-wins reducer.
    When multiple parallel nodes emit a value, keep the last (most recent) one.
    Used for scalar fields like `stage` and `should_halt`.
    """
    return b if b is not None else a


def _merge_lists(a: list, b: list) -> list:
    """
    List concatenation reducer.
    Combines error lists from parallel nodes without losing any entry.
    """
    a = a or []
    b = b or []
    return a + b


def _merge_dicts(a: dict, b: dict) -> dict:
    """
    Shallow dict merge reducer.
    Merges per-agent log dicts from parallel nodes.
    """
    a = a or {}
    b = b or {}
    return {**a, **b}


# ── Sub-TypeDicts (unchanged) ─────────────────────────────────────────────────

class RequirementSpec(TypedDict, total=False):
    """Structured output of the Requirement Analyzer Agent."""
    app_name: str
    app_type: str                          # e.g. "crud", "dashboard", "ecommerce"
    description: str
    features: list[str]
    user_roles: list[str]
    workflows: list[dict]                  # [{name, steps[]}]
    data_entities: list[str]
    non_functional: dict                   # {performance, security, ...}
    clarifying_questions: list[str]        # Non-empty means user Q&A needed
    raw_answers: str                       # Appended answers from user


class ProjectPlan(TypedDict, total=False):
    """Structured output of the Project Planner Agent."""
    app_name: str
    architecture: str                      # "monolith" | "modular_api"
    stack: dict                            # StackConfig.to_dict()
    pages: list[dict]                      # [{name, route, components[]}]
    api_contracts: list[dict]              # [{method, path, request, response}]
    data_model: list[dict]                 # [{entity, fields[], relationships[]}]
    frontend_tasks: list[str]
    backend_tasks: list[str]
    database_tasks: list[str]
    project_dir: str                       # Absolute path to output/<app_name>/


class CodeArtifact(TypedDict, total=False):
    """Generic structure for a set of generated source files."""
    files: dict[str, str]                  # {relative_path: file_content}
    entry_point: str                       # Main file to run / index file
    notes: str                             # Agent-level notes about the generation


class ReviewResult(TypedDict, total=False):
    """Output of the Code Review Agent."""
    issues: list[dict]                     # [{file, issue_type, description, severity}]
    blocked: bool                          # True if HIGH severity issues block progression
    summary: str


class TestResult(TypedDict, total=False):
    """Output of the Testing Agent."""
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    failures: list[dict]                   # [{test_name, file, error_message, relevant_source_file}]
    summary: str


class DeploymentInfo(TypedDict, total=False):
    """Output of the Deployment Agent."""
    app_url: str
    deployment_id: str
    cloud_provider: str
    service_name: str
    docker_images: list[str]
    infra_artifacts: dict[str, str]        # {artifact_name: file_path}


class Documentation(TypedDict, total=False):
    """Output of the Documentation Agent."""
    readme: str
    api_reference: str
    setup_guide: str
    files: dict[str, str]                  # {filename: content}


# ── Main pipeline state ───────────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    """
    The single shared state object for the entire LangGraph pipeline.
    Passed to every agent node; each agent reads relevant fields and
    returns a partial dict with only the fields it updates.

    Keys written by parallel nodes (frontend_agent, backend_agent, database_agent)
    MUST use Annotated reducers to avoid INVALID_CONCURRENT_GRAPH_UPDATE errors.
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    user_input: str                                  # Raw natural-language requirement

    # ── Agent Outputs (populated progressively) ───────────────────────────────
    # These are written by exactly ONE node each → no reducer needed
    structured_spec: Optional[RequirementSpec]
    project_plan:    Optional[ProjectPlan]
    frontend_code:   Optional[CodeArtifact]
    backend_code:    Optional[CodeArtifact]
    database_schema: Optional[CodeArtifact]
    review_results:  Optional[ReviewResult]
    test_results:    Optional[TestResult]
    deployment_info: Optional[DeploymentInfo]
    docs:            Optional[Documentation]
    repo_url:        Optional[str]

    # ── Control Flow ──────────────────────────────────────────────────────────
    # `stage` and `should_halt` are written by ALL parallel nodes → use reducer
    stage:       Annotated[str, _keep_last]          # Current pipeline stage label
    should_halt: Annotated[bool, _keep_last]         # Set True to abort gracefully
    retry_count: int                                  # Number of bug-fix retry cycles
    max_retries: int                                  # Max allowed (from settings)

    # ── Diagnostics ───────────────────────────────────────────────────────────
    # `errors` and `agent_logs` are written by ALL parallel nodes → use reducers
    errors:     Annotated[list[str], _merge_lists]   # Non-fatal errors accumulated
    agent_logs: Annotated[dict[str, Any], _merge_dicts]  # Per-agent structured logs


def initial_state(user_input: str, max_retries: int = 3) -> PipelineState:
    """
    Factory function — creates a clean initial PipelineState for a new run.
    Call this from the orchestrator runner before invoking the graph.
    """
    return PipelineState(
        user_input=user_input,
        structured_spec=None,
        project_plan=None,
        frontend_code=None,
        backend_code=None,
        database_schema=None,
        review_results=None,
        test_results=None,
        deployment_info=None,
        docs=None,
        repo_url=None,
        stage="start",
        retry_count=0,
        max_retries=max_retries,
        should_halt=False,
        errors=[],
        agent_logs={},
    )

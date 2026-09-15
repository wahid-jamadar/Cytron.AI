"""
orchestrator/graph.py
──────────────────────
Defines the LangGraph pipeline graph.

Wires all agent nodes together with sequential, parallel fan-out/fan-in,
and conditional routing edges. This is the authoritative definition of
the pipeline's execution order and branching logic.

Graph topology:
  requirement_analyzer
        │
        ▼
   project_planner
        │
    ┌───┴───────────────────┐
    ▼           ▼           ▼
 frontend    backend    database
    └───────────┬───────────┘
           fan-in (all 3 done)
                │
                ▼
          code_review  ─── blocked? ──→ bug_fixing
                │                           │
               pass                    re-entry
                │                           ▼
                └──────────────────→ testing_agent
                                          │
                              passed? ────┼──── failed & retries < max?
                                 │                        │
                                 ▼                        ▼
                           deployment              bug_fixing
                                 │
                                 ▼
                           documentation
                                 │
                                 ▼
                           repository
                                 │
                                 ▼
                               END
"""

import logging
import asyncio
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state.pipeline_state import PipelineState
from agents.requirement_analyzer import requirement_analyzer_node, has_clarifying_questions
from agents.project_planner import project_planner_node
from agents.frontend_agent import frontend_agent_node
from agents.backend_agent import backend_agent_node
from agents.database_agent import database_agent_node
from agents.code_review_agent import code_review_agent_node, review_routing
from agents.testing_agent import testing_agent_node, testing_routing
from agents.bug_fixing_agent import bug_fixing_agent_node
from agents.deployment_agent import deployment_agent_node
from agents.documentation_agent import documentation_agent_node
from agents.repository_agent import repository_agent_node
from modules.common.logger import log_agent_execution

logger = logging.getLogger(__name__)

def wrap_node_logging(node_name: str, node_func):
    async def wrapped_node(state: PipelineState) -> dict:
        async with log_agent_execution(node_name):
            if asyncio.iscoroutinefunction(node_func):
                return await node_func(state)
            else:
                return await asyncio.to_thread(node_func, state)
    return wrapped_node


# ── Halt node ─────────────────────────────────────────────────────────────────
def halt_node(state: PipelineState) -> dict:
    """
    Terminal node reached when max retries are exceeded.
    Marks the pipeline as halted with a descriptive error.
    """
    test_results = state.get("test_results") or {}
    failures = test_results.get("failures", [])
    retry_count = state.get("retry_count", 0)

    error_msg = (
        f"Pipeline halted after {retry_count} retry cycles. "
        f"Remaining test failures: {len(failures)}. "
        f"Manual intervention required."
    )
    logger.error(f"[Orchestrator] {error_msg}")
    return {
        "should_halt": True,
        "stage": "halted",
        "errors": state.get("errors", []) + [error_msg],
    }


# ── Fan-in merge ───────────────────────────────────────────────────────────────
def build_agents_fanin(state: PipelineState) -> dict:
    """
    Merge node after the parallel frontend/backend/database build.
    Simply passes state through — the three parallel nodes write their outputs
    independently; this node confirms all three are done before code review.
    """
    logger.info("[Orchestrator] Fan-in: all build agents complete.")
    return {"stage": "build_agents_complete"}


def build_graph(use_checkpointing: bool = True) -> StateGraph:
    """
    Construct and compile the full pipeline LangGraph.

    Args:
        use_checkpointing: If True, attach an in-memory checkpointer for
                           state persistence across interruptions.

    Returns:
        A compiled LangGraph application ready to invoke.
    """
    builder = StateGraph(PipelineState)

    # ── Register all nodes ────────────────────────────────────────────────────
    builder.add_node("requirement_analyzer", wrap_node_logging("Requirement Analyzer", requirement_analyzer_node))
    builder.add_node("project_planner", wrap_node_logging("Project Planner", project_planner_node))
    builder.add_node("frontend_agent", wrap_node_logging("Frontend Agent", frontend_agent_node))
    builder.add_node("backend_agent", wrap_node_logging("Backend Agent", backend_agent_node))
    builder.add_node("database_agent", wrap_node_logging("Database Agent", database_agent_node))
    builder.add_node("build_fanin", wrap_node_logging("Build Fan-in", build_agents_fanin))
    builder.add_node("code_review", wrap_node_logging("Code Review Agent", code_review_agent_node))
    builder.add_node("testing_agent", wrap_node_logging("Testing Agent", testing_agent_node))
    builder.add_node("bug_fixing", wrap_node_logging("Bug Fixing Agent", bug_fixing_agent_node))
    builder.add_node("deployment", wrap_node_logging("Deployment Agent", deployment_agent_node))
    builder.add_node("documentation", wrap_node_logging("Documentation Agent", documentation_agent_node))
    builder.add_node("repository", wrap_node_logging("Repository Agent", repository_agent_node))
    builder.add_node("halt", wrap_node_logging("Halt Node", halt_node))

    # ── Entry point ───────────────────────────────────────────────────────────
    builder.set_entry_point("requirement_analyzer")

    # ── Sequential: analyzer → planner ───────────────────────────────────────
    builder.add_edge("requirement_analyzer", "project_planner")

    # ── Parallel fan-out: planner → 3 build agents ───────────────────────────
    builder.add_edge("project_planner", "frontend_agent")
    builder.add_edge("project_planner", "backend_agent")
    builder.add_edge("project_planner", "database_agent")

    # ── Fan-in: all 3 build agents → merge node ───────────────────────────────
    builder.add_edge("frontend_agent", "build_fanin")
    builder.add_edge("backend_agent", "build_fanin")
    builder.add_edge("database_agent", "build_fanin")

    # ── Code review ───────────────────────────────────────────────────────────
    builder.add_edge("build_fanin", "code_review")
    builder.add_conditional_edges(
        "code_review",
        review_routing,
        {"bug_fixing": "bug_fixing", "testing": "testing_agent"},
    )

    # ── Testing with retry loop ───────────────────────────────────────────────
    builder.add_conditional_edges(
        "testing_agent",
        testing_routing,
        {
            "deployment": "deployment",
            "bug_fixing": "bug_fixing",
            "halt": "halt",
        },
    )

    # ── Bug fixing → back to testing ──────────────────────────────────────────
    builder.add_edge("bug_fixing", "testing_agent")

    # ── Deployment → documentation → repository → END ─────────────────────────
    builder.add_edge("deployment", "documentation")
    builder.add_edge("documentation", "repository")
    builder.add_edge("repository", END)

    # ── Halt is a terminal node ───────────────────────────────────────────────
    builder.add_edge("halt", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    checkpointer = MemorySaver() if use_checkpointing else None
    return builder.compile(checkpointer=checkpointer)

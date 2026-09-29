"""
modules/build_complete_project/resolver.py
─────────────────────────────────────────────
Tech Stack Resolver for Cytron.AI.
Merges explicit user selections with clarified selections into a final configuration.
"""

from typing import Dict, Any

def resolve_tech_stack(selected_stack: Dict[str, Any], clarified_decisions: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the final canonical tech-stack configuration.
    Priority:
      1. Explicit user selections (selected_stack)
      2. User selections made through clarification (clarified_decisions)
    """
    # Start with a normalized base structure
    final_stack = {
        "frontend": "React",
        "backend": "FastAPI",
        "architecture": "Monolithic",
    }
    
    # 1. Merge clarified decisions (lowest priority overrides default, but explicit beats clarified)
    # We apply them first so explicit can override if there happens to be an overlap.
    for key, value in clarified_decisions.items():
        if value:
            final_stack[key] = value

    # 2. Merge explicit selected stack
    for key, value in selected_stack.items():
        if value:
            final_stack[key] = value

    return final_stack

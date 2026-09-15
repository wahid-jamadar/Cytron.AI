"""
tools/file_writer.py
─────────────────────
Utility for writing generated code artifacts to the output directory.
All agents use this to persist generated files, ensuring consistent
path handling and logging across the pipeline.
"""

import aiofiles
from pathlib import Path
from config.settings import settings
from modules.common.logger import platform_logger
logger = platform_logger


async def write_files(project_name: str, component: str, files: dict[str, str]) -> Path:
    """
    Write a dict of {relative_path: content} files into the project output directory.

    Args:
        project_name: The app/project slug (e.g. "my_todo_app").
        component: Sub-directory label (e.g. "frontend", "backend", "database", "tests").
        files: Dict mapping relative file paths to their string contents.

    Returns:
        The component directory path where files were written.

    Example:
        await write_files("todo_app", "backend", {
            "main.py": "from fastapi import FastAPI\\napp = FastAPI()",
            "routers/tasks.py": "...",
        })
    """
    component_dir = settings.output_dir / project_name / component
    component_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for rel_path, content in files.items():
        import re
        if re.search(r'[*?"<>|]', str(rel_path)):
            logger.warning(f"[FileWriter] Skipping invalid filename from LLM: {rel_path}")
            continue
        abs_path = component_dir / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            if isinstance(content, list) and all(isinstance(i, str) for i in content):
                content = "\n".join(content)
            else:
                import json
                content = json.dumps(content, indent=2)
        async with aiofiles.open(abs_path, "w", encoding="utf-8") as f:
            await f.write(content)
        written.append(str(rel_path))

    logger.file_system(
        f"Wrote {len(written)} file(s) to {component_dir} — {written[:5]}{'...' if len(written) > 5 else ''}",
        path=component_dir
    )
    return component_dir


def write_files_sync(project_name: str, component: str, files: dict[str, str]) -> Path:
    """
    Synchronous variant of write_files for use in non-async contexts.
    """
    component_dir = settings.output_dir / project_name / component
    component_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for rel_path, content in files.items():
        import re
        if re.search(r'[*?"<>|]', str(rel_path)):
            logger.warning(f"[FileWriter] Skipping invalid filename from LLM: {rel_path}")
            continue
        abs_path = component_dir / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if not isinstance(content, str):
            if isinstance(content, list) and all(isinstance(i, str) for i in content):
                content = "\n".join(content)
            else:
                import json
                content = json.dumps(content, indent=2)
        abs_path.write_text(content, encoding="utf-8")
        written.append(str(rel_path))

    logger.file_system(
        f"Wrote {len(written)} file(s) to {component_dir} — {written[:5]}{'...' if len(written) > 5 else ''}",
        path=component_dir
    )
    return component_dir


def get_project_dir(project_name: str) -> Path:
    """Return the root output directory for a given project."""
    return settings.output_dir / project_name


def list_generated_files(project_name: str) -> list[str]:
    """Return a flat list of all generated files for a project."""
    project_dir = get_project_dir(project_name)
    if not project_dir.exists():
        return []
    return [
        str(p.relative_to(project_dir))
        for p in project_dir.rglob("*")
        if p.is_file()
    ]

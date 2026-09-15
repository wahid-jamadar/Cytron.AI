"""
tools/test_runner.py
─────────────────────
Executes generated test suites in an isolated subprocess.
Supports pytest (backend) and vitest (frontend).
Returns structured pass/fail results to the Testing Agent.
"""

import logging
import subprocess
import sys
import venv
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)


def _create_venv(project_name: str) -> Path:
    """Create (or reuse) a Python virtualenv inside the project output directory."""
    venv_dir = settings.output_dir / project_name / ".venv"
    if not venv_dir.exists():
        logger.info(f"[TestRunner] Creating venv at {venv_dir}")
        venv.create(str(venv_dir), with_pip=True)
    return venv_dir


def _venv_python(venv_dir: Path) -> str:
    if sys.platform == "win32":
        return str(venv_dir / "Scripts" / "python.exe")
    return str(venv_dir / "bin" / "python")


def _install_deps(venv_dir: Path, project_name: str) -> bool:
    """Install backend requirements inside the venv."""
    req_file = settings.output_dir / project_name / "backend" / "requirements.txt"
    if not req_file.exists():
        logger.warning("[TestRunner] No backend requirements.txt found — skipping dep install.")
        return True

    python = _venv_python(venv_dir)
    result = subprocess.run(
        [python, "-m", "pip", "install", "-r", str(req_file), "pytest", "httpx", "pytest-asyncio"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        logger.error(f"[TestRunner] pip install failed:\n{result.stderr}")
        return False
    return True


def run_pytest(project_name: str, test_dir: Path) -> dict:
    """
    Run pytest on the given test directory inside a project virtualenv.

    Returns:
        {
            "passed": bool,
            "total": int,
            "passed_count": int,
            "failed_count": int,
            "failures": [{"test": str, "error": str}],
            "stdout": str,
            "stderr": str,
        }
    """
    venv_dir = _create_venv(project_name)
    _install_deps(venv_dir, project_name)

    python = _venv_python(venv_dir)
    backend_dir = settings.output_dir / project_name / "backend"

    result = subprocess.run(
        [
            python, "-m", "pytest",
            str(test_dir),
            "--tb=short",
            "--json-report",
            "--json-report-file=/dev/null",
            "-v",
            "--no-header",
        ],
        capture_output=True, text=True, timeout=180,
        cwd=str(backend_dir),
        env={
            **_clean_env(),
            "PYTHONPATH": str(backend_dir),
            "DATABASE_URL": f"sqlite:///{settings.output_dir / project_name / 'test.db'}",
        },
    )

    return _parse_pytest_output(result)


def _parse_pytest_output(result: subprocess.CompletedProcess) -> dict:
    """Parse pytest stdout into a structured result dict."""
    stdout = result.stdout or ""
    stderr = result.stderr or ""

    passed_count = 0
    failed_count = 0
    failures = []

    for line in stdout.splitlines():
        if " passed" in line:
            try:
                passed_count = int(line.strip().split()[0])
            except (ValueError, IndexError):
                pass
        if " failed" in line:
            try:
                failed_count = int(line.strip().split()[0])
            except (ValueError, IndexError):
                pass
        if line.startswith("FAILED "):
            test_name = line.replace("FAILED ", "").split(" - ")[0].strip()
            error_msg = line.split(" - ", 1)[-1].strip() if " - " in line else "See output"
            failures.append({"test": test_name, "error": error_msg})

    total = passed_count + failed_count
    passed = result.returncode == 0

    return {
        "passed": passed,
        "total": total,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "failures": failures,
        "stdout": stdout[-3000:],   # Trim to last 3000 chars
        "stderr": stderr[-1000:],
    }


def _clean_env() -> dict:
    """Return a minimal clean environment for subprocess execution."""
    import os
    safe_keys = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP", "APPDATA"}
    return {k: v for k, v in os.environ.items() if k in safe_keys}

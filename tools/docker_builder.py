"""
tools/docker_builder.py
────────────────────────
Builds and optionally pushes Docker images for generated application components.
Used by the Deployment Agent.
"""

import logging
import subprocess
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)


def build_image(
    context_dir: Path,
    image_tag: str,
    dockerfile: str = "Dockerfile",
    build_args: dict[str, str] | None = None,
) -> bool:
    """
    Build a Docker image from a given context directory.

    Args:
        context_dir: Directory containing the Dockerfile.
        image_tag: Full image tag (e.g. "us-central1-docker.pkg.dev/proj/repo/app:latest").
        dockerfile: Dockerfile filename (default: "Dockerfile").
        build_args: Optional dict of --build-arg KEY=VALUE pairs.

    Returns:
        True if build succeeded, False otherwise.
    """
    cmd = ["docker", "build", "-t", image_tag, "-f", dockerfile, "."]
    if build_args:
        for key, value in build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

    logger.info(f"[DockerBuilder] Building image: {image_tag}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(context_dir), timeout=300)

    if result.returncode == 0:
        logger.info(f"[DockerBuilder] Built: {image_tag}")
        return True
    else:
        logger.error(f"[DockerBuilder] Build failed:\n{result.stderr[-2000:]}")
        return False


def push_image(image_tag: str) -> bool:
    """
    Push a Docker image to a container registry.

    Args:
        image_tag: Full image tag to push.

    Returns:
        True if push succeeded, False otherwise.
    """
    logger.info(f"[DockerBuilder] Pushing image: {image_tag}")
    result = subprocess.run(
        ["docker", "push", image_tag],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode == 0:
        logger.info(f"[DockerBuilder] Pushed: {image_tag}")
        return True
    else:
        logger.error(f"[DockerBuilder] Push failed:\n{result.stderr[-2000:]}")
        return False


def build_and_push(
    context_dir: Path,
    image_tag: str,
    dockerfile: str = "Dockerfile",
) -> bool:
    """Convenience method: build then push."""
    if not build_image(context_dir, image_tag, dockerfile):
        return False
    return push_image(image_tag)

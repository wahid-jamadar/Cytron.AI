"""
tools/cloud_deployer.py
────────────────────────
GCP Cloud Run deployment strategy.
Deploys the validated application to GCP Cloud Run as separate services
(frontend Nginx container + backend Uvicorn container).

Extensible: add AzureDeployer / AWSDeployer here in future phases.
"""

import logging
import subprocess
import json
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)


class GCPDeployer:
    """
    Deploys frontend and backend containers to GCP Cloud Run.

    Prerequisites:
      - gcloud CLI installed and authenticated.
      - settings.gcp_project_id configured.
      - Docker images already built and pushed to Artifact Registry.
    """

    def __init__(self):
        self.project_id = settings.gcp_project_id
        self.region = settings.gcp_region

    def _run_gcloud(self, args: list[str], timeout: int = 120) -> tuple[bool, str]:
        cmd = ["gcloud"] + args + ["--project", self.project_id, "--format=json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        return success, output

    def deploy_service(
        self,
        service_name: str,
        image_tag: str,
        port: int = 8000,
        env_vars: dict[str, str] | None = None,
        allow_unauthenticated: bool = True,
    ) -> str | None:
        """
        Deploy a single container image as a Cloud Run service.

        Returns:
            The service URL if deployment succeeded, None otherwise.
        """
        logger.info(f"[GCPDeployer] Deploying '{service_name}' to Cloud Run...")

        cmd = [
            "run", "deploy", service_name,
            "--image", image_tag,
            "--region", self.region,
            "--port", str(port),
            "--platform", "managed",
        ]

        if allow_unauthenticated:
            cmd.append("--allow-unauthenticated")

        if env_vars:
            env_str = ",".join(f"{k}={v}" for k, v in env_vars.items())
            cmd.extend(["--set-env-vars", env_str])

        success, output = self._run_gcloud(cmd, timeout=300)

        if not success:
            logger.error(f"[GCPDeployer] Deploy failed for '{service_name}':\n{output}")
            return None

        try:
            data = json.loads(output)
            url = data.get("status", {}).get("url") or data.get("url", "")
            logger.info(f"[GCPDeployer] Deployed '{service_name}' → {url}")
            return url
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"[GCPDeployer] Could not parse URL from gcloud output.")
            return output.strip()

    def deploy_app(
        self,
        app_name: str,
        backend_image: str,
        frontend_image: str,
        database_url: str,
        secret_key: str = "change-me-in-production",
    ) -> dict[str, str | None]:
        """
        Deploy both backend and frontend services.

        Returns:
            dict with "backend_url" and "frontend_url".
        """
        backend_url = self.deploy_service(
            service_name=f"{app_name}-backend",
            image_tag=backend_image,
            port=8000,
            env_vars={
                "DATABASE_URL": database_url,
                "SECRET_KEY": secret_key,
                "ENVIRONMENT": "production",
            },
        )

        # Pass the backend URL to the frontend as its API base
        frontend_url = self.deploy_service(
            service_name=f"{app_name}-frontend",
            image_tag=frontend_image,
            port=80,
            env_vars={"VITE_API_URL": backend_url or ""},
        )

        return {"backend_url": backend_url, "frontend_url": frontend_url}


def get_deployer() -> GCPDeployer:
    """Factory function — returns the appropriate deployer based on settings."""
    return GCPDeployer()

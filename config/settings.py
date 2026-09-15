"""
config/settings.py
──────────────────
Loads all environment variables from .env and exposes them as a typed
Settings object. All other modules import from here — never read os.environ
directly elsewhere in the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API key for Llama 3 inference")
    groq_model: str = Field("llama3-70b-8192", description="Groq model name")

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token: str = Field("", description="GitHub PAT for repo creation")
    github_org: str = Field("", description="GitHub org/user to create repos under")
    github_default_visibility: str = Field("private", description="'private' or 'public'")

    # ── GCP ──────────────────────────────────────────────────────────────────
    gcp_project_id: str = Field("", description="GCP project ID")
    gcp_region: str = Field("us-central1", description="GCP region for deployments")
    gcp_artifact_registry: str = Field("", description="Artifact Registry repo URL")
    google_application_credentials: str = Field("", description="Path to GCP service account JSON")

    # ── Storage ───────────────────────────────────────────────────────────────
    output_dir: Path = Field(Path("./output"), description="Root dir for generated projects")
    chroma_path: Path = Field(Path("./memory/chroma_db"), description="ChromaDB local persistence path")
    chroma_api_key: str = Field("", description="ChromaDB API key")
    chroma_tenant: str = Field("", description="ChromaDB tenant name or ID")
    chroma_database: str = Field("", description="ChromaDB database name")
    database_url: str = Field("mysql+pymysql://root:wahid5104@127.0.0.1:3306/eto_agent", description="MySQL connection URL")

    # ── Security & Session ───────────────────────────────────────────────────
    jwt_secret: str = Field("eto-agent-secure-secret-key-2026", description="JWT signing key")
    jwt_algorithm: str = Field("HS256", description="JWT hash algorithm")
    access_token_expire_minutes: int = Field(30, description="Expiry duration for JWT Access Token")
    refresh_token_expire_days: int = Field(7, description="Expiry duration for JWT Refresh Token")

    # ── Pipeline ──────────────────────────────────────────────────────────────
    max_retry_cycles: int = Field(3, description="Max bug-fix retry cycles")
    pipeline_timeout_seconds: int = Field(600, description="Hard timeout per pipeline run")
    log_level: str = Field("INFO", description="Logging level")

    # ── Web UI ────────────────────────────────────────────────────────────────
    ui_host: str = Field("0.0.0.0", description="Host for the orchestrator web UI")
    ui_port: int = Field(8000, description="Port for the orchestrator web UI")

    @property
    def github_enabled(self) -> bool:
        """Returns True only if a GitHub token has been configured."""
        return bool(self.github_token)

    @property
    def gcp_enabled(self) -> bool:
        """Returns True only if GCP credentials have been configured."""
        return bool(self.gcp_project_id)


# Singleton instance — import this everywhere
settings = Settings()

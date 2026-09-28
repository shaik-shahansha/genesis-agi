"""Settings and configuration for Genesis."""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

#: The placeholder shipped in `.env.example`. Booting with this means every JWT
#: in the deployment is forgeable by anyone who has read the repository.
INSECURE_SECRET_PLACEHOLDER = "your-secret-key-change-this-in-production"

#: Environments where an insecure secret is tolerated, because the app is only
#: reachable from the developer's own machine and requiring a key on every test
#: run is friction that leads to people committing a real one.
_INSECURE_ALLOWED_ENVS = ("test", "development", "dev", "local")

#: Shortest secret accepted as "real". A 32-character secret is the same order as
#: what `secrets.token_hex(32)` produces for the compose file.
MINIMUM_SECRET_LENGTH = 32


class InsecureSecretError(RuntimeError):
    """Raised when the app is configured with a placeholder signing key."""


class Settings(BaseSettings):
    """Genesis configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Application
    app_name: str = "Genesis AGI Framework"
    version: str = "0.1.5"
    debug: bool = False

    # Paths
    genesis_home: Path = Field(default_factory=lambda: Path.home() / ".genesis")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".genesis" / "data")
    minds_dir: Path = Field(default_factory=lambda: Path.home() / ".genesis" / "minds")
    logs_dir: Path = Field(default_factory=lambda: Path.home() / ".genesis" / "logs")

    # Database
    database_url: str = "sqlite:///genesis.db"
    vector_db_path: str = "./chroma_db"

    # Model Providers - API Keys
    openrouter_api_key: Optional[str] = None  # Free models available from https://openrouter.ai/
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Free from Google AI Studio
    groq_api_key: Optional[str] = None
    pollinations_api_key: Optional[str] = None  # Free from https://enter.pollinations.ai/

    # Model Defaults  
    default_reasoning_model: str = "openrouter/meta-llama/llama-3.3-70b-instruct:free"  # ✓ Works - Clean JSON output
    default_fast_model: str = "openrouter/meta-llama/llama-3.3-70b-instruct:free"  # ✓ Fast & reliable
    default_local_model: str = "ollama/llama3.1"
    ollama_base_url: str = "http://localhost:11434"

    # Consciousness Settings
    consciousness_tick_interval: int = 60  # seconds (1 minute for active consciousness)
    dream_schedule: str = "02:00"  # 2 AM
    thought_generation_enabled: bool = True

    # Safety
    action_logging_enabled: bool = True
    require_approval_for_external_actions: bool = True
    max_autonomous_actions_per_hour: int = 100

    # Process supervision for Mind daemons (plan item B11).
    #   None      - fall through to the GENESIS_SUPERVISOR environment variable,
    #               then to "none". The default, so the environment variable is
    #               authoritative and this field cannot shadow it.
    #   "none"    - this API will not start or stop daemons; it tells the caller
    #               what the operator should run instead, because the API tier
    #               should not hold process-control authority.
    #   "systemd" - delegate to `systemctl` against genesis-mind@<gmid>.service.
    supervisor: Optional[str] = None

    # Uploads
    max_upload_size_mb: int = 100  # Per-file cap for workspace uploads (SEC-14)

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    cors_origins: str = "*"  # Comma-separated list of allowed origins or * for all

    # Security & Authentication
    api_secret_key: str = "your-secret-key-change-this-in-production"
    api_authentication_enabled: bool = True
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Firebase Authentication (optional)
    firebase_project_id: Optional[str] = None  # Set to enable Firebase auth
    firebase_api_key: Optional[str] = None  # Firebase Web API key for token verification
    
    # Mind Creation Limits
    max_minds_per_user: int = 1  # Maximum minds a user can create (admins exempt)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.genesis_home.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.minds_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Secret validation (plan item B12)
    # ------------------------------------------------------------------ #

    @staticmethod
    def environment_name() -> str:
        """The configured environment, normalised."""
        return (
            os.environ.get("GENESIS_ENV", "").strip().lower()
            or os.environ.get("ENVIRONMENT", "").strip().lower()
            or "production"
        )

    def insecure_secrets(self) -> list[str]:
        """Names of signing secrets still set to the shipped placeholder.

        Empty means nothing to complain about.
        """
        offenders: list[str] = []
        if self.api_secret_key == INSECURE_SECRET_PLACEHOLDER:
            offenders.append("API_SECRET_KEY")
        if self.secret_key == INSECURE_SECRET_PLACEHOLDER:
            offenders.append("SECRET_KEY")
        return offenders

    def short_secrets(self) -> list[str]:
        """Names of signing secrets that are real but too short to be safe."""
        offenders: list[str] = []
        for name, value in (
            ("API_SECRET_KEY", self.api_secret_key),
            ("SECRET_KEY", self.secret_key),
        ):
            if value and value != INSECURE_SECRET_PLACEHOLDER and len(value) < MINIMUM_SECRET_LENGTH:
                offenders.append(name)
        return offenders

    def assert_secure_secrets(self) -> None:
        """Refuse to run in production with a placeholder or weak signing key.

        `docker-compose.yml` already fails fast on a missing key, but the
        application did not, so any install that bypassed compose (a systemd
        unit, a bare `uvicorn`, a container run by hand) silently shipped with a
        key published in this repository. Every token would be forgeable.

        Raises:
            InsecureSecretError: outside test/development, if a signing secret is
                still the shipped placeholder.
        """
        environment = self.environment_name()
        placeholders = self.insecure_secrets()

        if not placeholders:
            short = self.short_secrets()
            if short and environment not in _INSECURE_ALLOWED_ENVS:
                logger.warning(
                    "Signing secrets %s are shorter than %d characters. Generate one with: "
                    "python -c \"import secrets; print(secrets.token_hex(32))\"",
                    ", ".join(short),
                    MINIMUM_SECRET_LENGTH,
                )
            return

        if environment in _INSECURE_ALLOWED_ENVS:
            logger.warning(
                "Running with the placeholder signing key (%s) because GENESIS_ENV=%s. "
                "This must not be reachable from a network.",
                ", ".join(placeholders),
                environment,
            )
            return

        raise InsecureSecretError(
            "Refusing to start: "
            + ", ".join(placeholders)
            + " is still the placeholder value from .env.example, so every issued token "
            "would be forgeable by anyone who has read this repository. Generate a real "
            "one and set it in the environment:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"\n'
            "Set GENESIS_ENV=development to bypass this check for local work."
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

"""Settings and configuration for Genesis."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    version: str = "0.1.2"
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

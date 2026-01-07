"""Intelligence configuration for Genesis Minds."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Intelligence(BaseModel):
    """Intelligence configuration for a Mind."""

    # Model selection
    reasoning_model: Optional[str] = Field(
        default=None,
        description="Model for complex reasoning tasks (REQUIRED - must be set during Mind creation)",
    )

    fast_model: Optional[str] = Field(
        default=None,
        description="Model for quick responses (defaults to reasoning_model if not set)"
    )

    vision_model: Optional[str] = Field(
        default=None, description="Model for image understanding"
    )

    local_model: Optional[str] = Field(
        default="ollama/llama3.1", description="Local model via Ollama"
    )

    # Routing
    auto_route: bool = Field(
        default=True, description="Automatically select best model for task"
    )

    cost_optimize: bool = Field(
        default=True, description="Optimize for cost when possible"
    )

    prefer_local: bool = Field(
        default=False, description="Prefer local models when available"
    )

    # Generation parameters
    default_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=2000, ge=1)  # Increased for DeepSeek R1 reasoning models
    max_tokens: int = Field(default=8000, ge=1, description="Maximum tokens for generation (default: 8000)")

    # Capabilities
    multimodal_enabled: bool = Field(default=False, description="Enable vision/audio")
    code_execution_enabled: bool = Field(default=False, description="Execute code")
    web_search_enabled: bool = Field(default=True, description="Search the web")

    # API Keys (stored with Mind, not from environment)
    api_keys: Optional[dict[str, str]] = Field(
        default=None,
        description="API keys for model providers (e.g., {'groq': 'gsk_...', 'openai': 'sk-...'})"
    )

    @model_validator(mode='after')
    def sync_and_validate_models(self) -> 'Intelligence':
        """Ensure fast_model defaults to reasoning_model and validate required fields."""
        # CRITICAL: reasoning_model is REQUIRED
        if not self.reasoning_model:
            raise ValueError(
                "reasoning_model is REQUIRED. Mind cannot be created without a model. "
                "Please specify a model like 'groq/llama-3.1-70b-versatile' or 'openai/gpt-4o'"
            )
        
        # If fast_model not set (None), default to reasoning_model
        # IMPORTANT: Only set if None, never overwrite existing values
        if self.fast_model is None:
            self.fast_model = self.reasoning_model
            print(f"[Intelligence] fast_model not specified, defaulting to reasoning_model: {self.fast_model}")
        
        return self

    def get_model_for_task(self, task_type: str) -> str:
        """Get the appropriate model for a task type."""
        if not self.auto_route:
            return self.reasoning_model

        task_map = {
            "reasoning": self.reasoning_model,
            "quick": self.fast_model,
            "vision": self.vision_model or self.reasoning_model,
            "local": self.local_model or self.fast_model,
        }

        return task_map.get(task_type, self.reasoning_model)

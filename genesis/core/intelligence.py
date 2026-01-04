"""Intelligence configuration for Genesis Minds."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class Intelligence(BaseModel):
    """Intelligence configuration for a Mind."""

    # Model selection
    reasoning_model: str = Field(
        default="openrouter/meta-llama/llama-3.3-70b-instruct:free",
        description="Model for complex reasoning tasks",
    )

    fast_model: str = Field(
        default="openrouter/meta-llama/llama-3.3-70b-instruct:free",
        description="Model for quick responses"
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

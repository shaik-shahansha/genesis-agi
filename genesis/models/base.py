"""Base classes for model providers."""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum


class ModelType(str, Enum):
    """Model capability types."""

    REASONING = "reasoning"  # Complex reasoning tasks
    FAST = "fast"  # Quick responses
    VISION = "vision"  # Image understanding
    LOCAL = "local"  # Local models via Ollama


@dataclass
class ModelResponse:
    """Response from a language model."""

    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    latency_ms: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any):
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate a response from the model."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate responses from the model."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

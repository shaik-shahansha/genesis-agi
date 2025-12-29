"""OpenAI model provider."""

import time
from typing import Any, Optional

from openai import AsyncOpenAI

from genesis.models.base import ModelProvider, ModelResponse


class OpenAIProvider(ModelProvider):
    """OpenAI model provider."""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any):
        super().__init__(api_key, **kwargs)
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return self.client is not None

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from OpenAI."""
        if not self.is_available():
            raise ValueError("OpenAI API key not configured")

        start_time = time.time()

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000

        return ModelResponse(
            content=response.choices[0].message.content or "",
            model=model,
            provider="openai",
            tokens_used=response.usage.total_tokens if response.usage else None,
            latency_ms=latency_ms,
            metadata={"finish_reason": response.choices[0].finish_reason},
        )

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate from OpenAI."""
        if not self.is_available():
            raise ValueError("OpenAI API key not configured")

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

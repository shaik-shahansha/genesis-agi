"""Anthropic (Claude) model provider."""

import time
from typing import Any, Optional

from anthropic import AsyncAnthropic

from genesis.models.base import ModelProvider, ModelResponse


class AnthropicProvider(ModelProvider):
    """Anthropic (Claude) model provider."""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any):
        super().__init__(api_key, **kwargs)
        self.client = AsyncAnthropic(api_key=api_key) if api_key else None

    def is_available(self) -> bool:
        """Check if Anthropic is available."""
        return self.client is not None

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from Claude."""
        if not self.is_available():
            raise ValueError("Anthropic API key not configured")

        start_time = time.time()

        # Convert messages format for Anthropic
        system_message = None
        formatted_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        response = await self.client.messages.create(
            model=model,
            messages=formatted_messages,
            system=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return ModelResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            latency_ms=latency_ms,
            metadata={"stop_reason": response.stop_reason},
        )

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate from Claude."""
        if not self.is_available():
            raise ValueError("Anthropic API key not configured")

        # Convert messages format
        system_message = None
        formatted_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        async with self.client.messages.stream(
            model=model,
            messages=formatted_messages,
            system=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

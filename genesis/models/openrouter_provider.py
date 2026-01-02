"""OpenRouter model provider for accessing multiple AI models."""

import ssl
import time
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from genesis.models.base import ModelProvider, ModelResponse


class OpenRouterProvider(ModelProvider):
    """OpenRouter model provider - unified access to multiple AI models with many free options."""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any):
        super().__init__(api_key, **kwargs)
        if api_key:
            # Create HTTP client with SSL context that uses system certificates
            http_client = httpx.AsyncClient(
                verify=ssl.create_default_context(),
                timeout=60.0  # Longer timeout for free models
            )
            # OpenRouter uses OpenAI-compatible API
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                http_client=http_client
            )
        else:
            self.client = None

    def is_available(self) -> bool:
        """Check if OpenRouter is available."""
        return self.client is not None

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek/deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from OpenRouter."""
        if not self.is_available():
            raise ValueError("OpenRouter API key not configured")

        start_time = time.time()

        # Convert 'functions' to 'tools' format if present
        if 'functions' in kwargs:
            functions = kwargs.pop('functions')
            # Convert to tools format
            kwargs['tools'] = [
                {
                    'type': 'function',
                    'function': func
                }
                for func in functions
            ]

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        latency_ms = (time.time() - start_time) * 1000

        # Check if response has tool calls (function calls)
        message = response.choices[0].message
        
        # Handle DeepSeek R1 reasoning models - they put output in 'reasoning' field
        # when finish_reason is 'length' and content is empty
        content = message.content or ""
        if not content and hasattr(message, 'reasoning') and message.reasoning:
            # DeepSeek R1 hit token limit during reasoning, use reasoning as content
            print(f"[DEBUG OpenRouter] Using reasoning field as content (model: {model})")
            content = message.reasoning
        
        # Debug logging for empty responses
        if not content:
            print(f"[WARNING OpenRouter] Empty content received!")
            print(f"[WARNING OpenRouter] Model: {model}")
            print(f"[WARNING OpenRouter] Finish reason: {response.choices[0].finish_reason}")
            if hasattr(message, 'tool_calls'):
                print(f"[WARNING OpenRouter] Has tool calls: {bool(message.tool_calls)}")
            if hasattr(message, 'reasoning'):
                print(f"[WARNING OpenRouter] Has reasoning: {bool(message.reasoning)}")
                print(f"[WARNING OpenRouter] Reasoning length: {len(message.reasoning) if message.reasoning else 0}")
        
        model_response = ModelResponse(
            content=content,
            model=model,
            provider="openrouter",
            tokens_used=response.usage.total_tokens if response.usage else None,
            latency_ms=latency_ms,
            metadata={"finish_reason": response.choices[0].finish_reason},
        )
        
        # Add function_call if present (convert from tool_calls)
        if hasattr(message, 'tool_calls') and message.tool_calls:
            tool_call = message.tool_calls[0]
            model_response.function_call = {
                'name': tool_call.function.name,
                'arguments': tool_call.function.arguments
            }
        
        return model_response

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek/deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate from OpenRouter."""
        if not self.is_available():
            raise ValueError("OpenRouter API key not configured")

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

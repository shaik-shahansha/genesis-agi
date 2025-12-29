"""Ollama provider for local models."""

import time
from typing import Any, Optional

import httpx

from genesis.models.base import ModelProvider, ModelResponse


class OllamaProvider(ModelProvider):
    """Ollama provider for local models."""

    def __init__(self, base_url: str = "http://localhost:11434", **kwargs: Any):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            import httpx

            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "llama3.1",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from Ollama."""
        start_time = time.time()

        # Format messages for Ollama
        prompt = self._format_messages(messages)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        try:
            response = await self.client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()

            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=result.get("response", ""),
                model=model,
                provider="ollama",
                latency_ms=latency_ms,
                metadata={"done": result.get("done", False)},
            )
        except Exception as e:
            raise ValueError(f"Ollama generation failed: {str(e)}")

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str = "llama3.1",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate from Ollama."""
        prompt = self._format_messages(messages)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        try:
            async with self.client.stream(
                "POST", f"{self.base_url}/api/generate", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json

                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
        except Exception as e:
            raise ValueError(f"Ollama streaming failed: {str(e)}")

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        """Format messages into a prompt for Ollama."""
        formatted = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
        return "\n\n".join(formatted) + "\n\nAssistant:"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

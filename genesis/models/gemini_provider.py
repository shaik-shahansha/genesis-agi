"""Google Gemini model provider."""

import time
from typing import Any, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from genesis.models.base import ModelProvider, ModelResponse


class GeminiProvider(ModelProvider):
    """Google Gemini model provider."""

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any):
        super().__init__(api_key, **kwargs)
        self.client = None
        if api_key and GEMINI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.client = genai

    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return self.client is not None and GEMINI_AVAILABLE

    def _convert_messages_to_gemini_format(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, list[dict[str, str]]]:
        """Convert messages to Gemini format.

        Gemini expects a system instruction separately and a history of user/model messages.
        """
        system_instruction = ""
        chat_history = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                # Gemini uses system_instruction parameter
                system_instruction = content
            elif role == "user":
                chat_history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                chat_history.append({"role": "model", "parts": [content]})

        return system_instruction, chat_history

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "gemini-1.5-pro",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from Gemini."""
        if not self.is_available():
            raise ValueError(
                "Gemini API not available. Install google-generativeai: "
                "pip install google-generativeai"
            )

        start_time = time.time()

        # Convert messages to Gemini format
        system_instruction, chat_history = self._convert_messages_to_gemini_format(
            messages
        )

        # Create model with configuration
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        # Add system instruction if present
        model_kwargs = {"model_name": model, "generation_config": generation_config}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        gemini_model = genai.GenerativeModel(**model_kwargs)

        # If we have chat history, use chat mode
        if len(chat_history) > 1:
            # Separate the last user message from history
            history = chat_history[:-1]
            last_message = chat_history[-1]["parts"][0]

            chat = gemini_model.start_chat(history=history)
            response = await chat.send_message_async(last_message)
        else:
            # Single message - use generate_content
            prompt = chat_history[0]["parts"][0] if chat_history else ""
            response = await gemini_model.generate_content_async(prompt)

        latency_ms = (time.time() - start_time) * 1000

        # Extract token usage if available
        tokens_used = None
        if hasattr(response, "usage_metadata"):
            tokens_used = (
                response.usage_metadata.prompt_token_count
                + response.usage_metadata.candidates_token_count
            )

        return ModelResponse(
            content=response.text,
            model=model,
            provider="gemini",
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            metadata={
                "finish_reason": (
                    response.candidates[0].finish_reason.name
                    if response.candidates
                    else None
                ),
                "safety_ratings": (
                    [
                        {
                            "category": rating.category.name,
                            "probability": rating.probability.name,
                        }
                        for rating in response.candidates[0].safety_ratings
                    ]
                    if response.candidates and response.candidates[0].safety_ratings
                    else []
                ),
            },
        )

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str = "gemini-1.5-pro",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate from Gemini."""
        if not self.is_available():
            raise ValueError(
                "Gemini API not available. Install google-generativeai: "
                "pip install google-generativeai"
            )

        # Convert messages to Gemini format
        system_instruction, chat_history = self._convert_messages_to_gemini_format(
            messages
        )

        # Create model with configuration
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        # Add system instruction if present
        model_kwargs = {"model_name": model, "generation_config": generation_config}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction

        gemini_model = genai.GenerativeModel(**model_kwargs)

        # If we have chat history, use chat mode
        if len(chat_history) > 1:
            # Separate the last user message from history
            history = chat_history[:-1]
            last_message = chat_history[-1]["parts"][0]

            chat = gemini_model.start_chat(history=history)
            response_stream = await chat.send_message_async(last_message, stream=True)
        else:
            # Single message - use generate_content
            prompt = chat_history[0]["parts"][0] if chat_history else ""
            response_stream = await gemini_model.generate_content_async(
                prompt, stream=True
            )

        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text

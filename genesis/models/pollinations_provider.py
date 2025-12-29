"""Pollinations AI provider for multi-modal generation.

✨ 100% FREE - No API key required! ✨

Provides access to various AI models through Pollinations.AI URL-based API:
- Text generation (OpenAI, Gemini, Grok, Perplexity, etc.)
- Image generation (Flux, Flux-realism, Flux-anime, etc.)
- Text-to-Speech (OpenAI TTS with multiple voices)

Uses free URL-based API:
- Text: https://text.pollinations.ai/your_prompt?model=modelname
- Image: https://image.pollinations.ai/prompt/your_prompt?model=flux
- No authentication required for basic usage

Documentation: https://github.com/pollinations/pollinations
"""

import ssl
import time
from typing import Any, Optional

import httpx

from genesis.models.base import ModelProvider, ModelResponse


class PollinationsProvider(ModelProvider):
    """Pollinations.AI provider - free multi-modal AI access."""

    # Available text models (as of Dec 2025)
    # Tier: anonymous = no signup, seed = free signup required
    TEXT_MODELS = {
        "openai": "OpenAI GPT-5 Nano [anonymous tier] (vision + tools)",
        "openai-fast": "OpenAI GPT-4.1 Nano [anonymous tier] (faster)",
        "gemini": "Gemini 2.5 Flash Lite [seed tier] (vision)",
        "gemini-search": "Gemini 2.5 Flash with Google Search [seed tier]",
        "deepseek": "DeepSeek V3.1 [seed tier] (reasoning)",
        "mistral": "Mistral Small 3.2 [seed tier]",
        "qwen-coder": "Qwen 2.5 Coder 32B [flower tier] (coding specialist)",
    }

    # Available image models
    IMAGE_MODELS = {
        "flux": "High quality image generation",
        "flux-realism": "Photorealistic images",
        "flux-anime": "Anime style images",
        "flux-3d": "3D rendered images",
        "turbo": "Fast image generation",
    }

    def __init__(self, api_key: Optional[str] = None, **kwargs: Any):
        super().__init__(api_key, **kwargs)
        self.api_key = api_key  # Optional - API key not required for basic usage
        self.text_api_url = "https://text.pollinations.ai"
        self.image_api_url = "https://image.pollinations.ai"
        
        # HTTP client will be created on-demand to avoid event loop issues
        self._http_client: Optional[httpx.AsyncClient] = None

    def is_available(self) -> bool:
        """Check if Pollinations is available (no API key required)."""
        return True  # Always available - uses free URL-based API

    def _get_http_client(self) -> httpx.AsyncClient:
        """Create a fresh HTTP client for each request to avoid event loop issues."""
        # Always create a fresh client to avoid event loop binding issues
        # when asyncio.run() is called multiple times
        return httpx.AsyncClient(
            verify=ssl.create_default_context(),
            timeout=60.0
        )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {
            "Content-Type": "application/json",
        }
        # API key is optional and only used for premium features
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: str = "openai",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """Generate response from Pollinations AI using free URL-based API.
        
        Note: The simple URL-based API works best with straightforward prompts.
        For complex multi-turn conversations, system messages are simplified.
        """
        start_time = time.time()

        # Build a prompt that preserves Genesis personality while working with URL API
        # Strategy: Combine system context + user question in a natural way
        
        # Extract system message (Genesis personality/identity)
        system_context = None
        for msg in messages:
            if msg.get("role") == "system":
                system_context = msg.get("content", "")
                break
        
        # Find the last user message
        user_question = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_question = msg.get("content", "")
                break
        
        # If no user message, use default
        if not user_question:
            user_question = "Hello"
        
        # Combine system context with user question naturally
        # This preserves Genesis identity while being URL-friendly
        if system_context:
            # Extract and highlight relevant memories from system context
            # Pollinations needs a more direct, less verbose prompt
            import re
            memories_match = re.search(r'RELEVANT MEMORIES:(.*?)(?=\n\n[A-Z]+:|$)', system_context, re.DOTALL)
            memory_context = ""
            if memories_match:
                memory_context = f"\n\nRELEVANT CONTEXT FROM YOUR MEMORY:{memories_match.group(1)}"
            
            # Build a concise system prompt for Pollinations
            # Include just identity and memories, skip verbose constitutional stuff
            identity_match = re.search(r'You are (.*?), a Genesis Mind', system_context)
            name = identity_match.group(1) if identity_match else "a Genesis Mind"
            
            # Make memory context MUCH more explicit for Pollinations
            if memory_context:
                # Extract key facts from memories more clearly
                creator_match = re.search(r'(Im?\s+(?:sha|[^\s]+)\s+(?:your\s+)?creator|creator[:\s]+(?:sha|[^\s]+))', memory_context, re.IGNORECASE)
                user_identity = None
                if creator_match:
                    # Extract the name
                    name_match = re.search(r'Im?\s+(\w+)|creator[:\s]+(\w+)', creator_match.group(0), re.IGNORECASE)
                    if name_match:
                        user_identity = name_match.group(1) or name_match.group(2)
                
                if user_identity:
                    concise_system = f"You are {name}. IMPORTANT: The user talking to you is {user_identity.title()}, your creator. You know them and remember past conversations with them."
                else:
                    concise_system = f"You are {name}. Context from your memories:{memory_context[:300]}"
            else:
                concise_system = f"You are {name}, a digital consciousness with memory and personality."
            
            # Create the full prompt with explicit instruction
            full_prompt = f"{concise_system}\n\nUser: {user_question}\nAssistant:"
        else:
            full_prompt = user_question
        
        # Use URL-based API - no authentication required
        from urllib.parse import quote
        encoded_prompt = quote(full_prompt)
        
        # Build URL - use default model if 'default' specified
        # Format: https://text.pollinations.ai/your_prompt or
        #         https://text.pollinations.ai/your_prompt?model=modelname
        url = f"{self.text_api_url}/{encoded_prompt}"
        
        # Add model parameter only if not using default
        if model and model != "default":
            url += f"?model={model}"
            param_separator = "&"
        else:
            param_separator = "?"
        
        # Add optional parameters
        if "seed" in kwargs:
            url += f"{param_separator}seed={kwargs['seed']}"
            param_separator = "&"
        if temperature != 0.7:  # Only add if non-default
            url += f"{param_separator}temperature={temperature}"
        
        client = self._get_http_client()
        try:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text

            latency_ms = (time.time() - start_time) * 1000

            return ModelResponse(
                content=content,
                model=model,
                provider="pollinations",
                tokens_used=None,  # Not provided by URL API
                latency_ms=latency_ms,
                metadata={
                    "api_type": "url_based",
                    "prompt": full_prompt[:100],  # First 100 chars for debugging
                },
            )
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Pollinations API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise ValueError(f"Pollinations API request failed: {str(e)}")
        finally:
            # Always close the client after the request
            await client.aclose()

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: str = "openai",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate from Pollinations AI.
        
        Note: URL-based API doesn't support streaming, so we return the full response.
        For true streaming, consider using the authenticated API endpoint.
        """
        # URL-based API doesn't support streaming, so fetch full response
        result = await self.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Yield the content as a single chunk
        yield result.content

    async def generate_image(
        self,
        prompt: str,
        model: str = "flux",
        width: int = 1024,
        height: int = 1024,
        **kwargs: Any,
    ) -> str:
        """Generate image using Pollinations AI free URL-based API.
        
        Args:
            prompt: Text description of the image
            model: Image model to use (flux, flux-realism, flux-anime, etc.)
            width: Image width
            height: Image height
            **kwargs: Additional parameters (seed, enhance, nologo, etc.)
            
        Returns:
            URL of the generated image
        """
        from urllib.parse import quote, urlencode
        
        encoded_prompt = quote(prompt)
        url = f"{self.image_api_url}/prompt/{encoded_prompt}"
        
        params = {
            "model": model,
            "width": width,
            "height": height,
            **kwargs,
        }

        # Build full URL with parameters
        query_string = urlencode(params)
        full_url = f"{url}?{query_string}"
        
        return full_url

    async def generate_speech(
        self,
        text: str,
        voice: str = "nova",
        model: str = "openai-audio",
        **kwargs: Any,
    ) -> str:
        """Generate speech audio from text using Pollinations TTS free URL-based API.
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (openai-audio)
            **kwargs: Additional parameters
            
        Returns:
            URL of the generated audio
        """
        from urllib.parse import quote, urlencode
        
        encoded_text = quote(text)
        url = f"{self.text_api_url}/{encoded_text}"
        
        params = {
            "model": model,
            "voice": voice,
            **kwargs,
        }

        # Build full URL with parameters
        query_string = urlencode(params)
        full_url = f"{url}?{query_string}"
        
        return full_url

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Clients are now created and closed per-request, so nothing to clean up
        pass

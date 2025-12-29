"""Model orchestrator for intelligent routing across providers."""

from typing import Any, Optional

from genesis.config import get_settings
from genesis.models.base import ModelProvider, ModelResponse, ModelType
from genesis.models.openai_provider import OpenAIProvider
from genesis.models.anthropic_provider import AnthropicProvider
from genesis.models.groq_provider import GroqProvider
from genesis.models.ollama_provider import OllamaProvider
from genesis.models.gemini_provider import GeminiProvider
from genesis.models.pollinations_provider import PollinationsProvider


class ModelOrchestrator:
    """
    Orchestrates multiple model providers and intelligently routes requests.

    Supports:
    - OpenAI (GPT-4, etc.)
    - Anthropic (Claude)
    - Google Gemini (Gemini 1.5 Pro/Flash)
    - Groq (fast inference)
    - Pollinations AI (multi-model access: OpenAI, Gemini, Grok, Perplexity, etc.)
    - Ollama (local models)
    """

    def __init__(self, api_keys: Optional[dict[str, str]] = None):
        """
        Initialize the orchestrator.
        
        Args:
            api_keys: Optional dict of API keys by provider name (e.g., {'groq': 'gsk_...', 'openai': 'sk-...'})
                     If not provided, will fall back to settings/environment variables.
        """
        self.settings = get_settings()
        self.api_keys = api_keys or {}
        self.providers: dict[str, ModelProvider] = {}

        # Initialize providers (prefer passed api_keys over settings)
        openai_key = self.api_keys.get('openai') or self.settings.openai_api_key
        if openai_key:
            self.providers["openai"] = OpenAIProvider(api_key=openai_key)

        anthropic_key = self.api_keys.get('anthropic') or self.settings.anthropic_api_key
        if anthropic_key:
            self.providers["anthropic"] = AnthropicProvider(api_key=anthropic_key)

        gemini_key = self.api_keys.get('gemini') or self.settings.gemini_api_key
        if gemini_key:
            self.providers["gemini"] = GeminiProvider(api_key=gemini_key)

        groq_key = self.api_keys.get('groq') or self.settings.groq_api_key
        if groq_key:
            self.providers["groq"] = GroqProvider(api_key=groq_key)

        # Pollinations AI - always available, no API key required!
        self.providers["pollinations"] = PollinationsProvider(
            api_key=getattr(self.settings, 'pollinations_api_key', None)
        )

        # Always try to initialize Ollama (local)
        ollama = OllamaProvider(base_url=self.settings.ollama_base_url)
        if ollama.is_available():
            self.providers["ollama"] = ollama

    def parse_model_string(self, model: str) -> tuple[str, str]:
        """
        Parse model string like 'provider/model-name' or just 'model-name'.

        Examples:
            'openai/gpt-4' -> ('openai', 'gpt-4')
            'groq/llama-3.3-70b-versatile' -> ('groq', 'llama-3.3-70b-versatile')
            'gemini/gemini-1.5-pro' -> ('gemini', 'gemini-1.5-pro')
            'gpt-4' -> ('openai', 'gpt-4')  # defaults to openai
            'gemini-1.5-flash' -> ('gemini', 'gemini-1.5-flash')  # defaults to gemini
        """
        if "/" in model:
            provider, model_name = model.split("/", 1)
            return provider, model_name
        else:
            # Default providers for common models
            if model.startswith("gpt"):
                return "openai", model
            elif model.startswith("claude"):
                return "anthropic", model
            elif model.startswith("gemini"):
                return "gemini", model
            elif model.startswith("llama") or model.startswith("mistral"):
                return "ollama", model
            elif model in ["grok", "perplexity", "perplexity-fast", "flux"]:
                return "pollinations", model
            else:
                # Default to first available provider
                if self.providers:
                    return list(self.providers.keys())[0], model
                raise ValueError("No providers available")

    async def generate(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> ModelResponse:
        """
        Generate a response using the specified model or auto-select.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model string (e.g., 'openai/gpt-4', 'groq/llama-3.1-70b')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        # Use default if no model specified
        if model is None:
            model = self.settings.default_fast_model

        provider_name, model_name = self.parse_model_string(model)

        if provider_name not in self.providers:
            raise ValueError(
                f"Provider '{provider_name}' not available. "
                f"Available: {list(self.providers.keys())}"
            )

        provider = self.providers[provider_name]
        return await provider.generate(
            messages=messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def stream_generate(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ):
        """Stream generate responses."""
        if model is None:
            model = self.settings.default_fast_model

        provider_name, model_name = self.parse_model_string(model)

        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not available")

        provider = self.providers[provider_name]
        async for chunk in provider.stream_generate(
            messages=messages,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield chunk

    def get_available_providers(self) -> list[str]:
        """Get list of available providers."""
        return list(self.providers.keys())

    def is_provider_available(self, provider: str) -> bool:
        """Check if a specific provider is available."""
        return provider in self.providers

    async def health_check(self) -> dict[str, bool]:
        """Check health of all providers."""
        health = {}
        for name, provider in self.providers.items():
            try:
                health[name] = provider.is_available()
            except Exception:
                health[name] = False
        return health

    async def test_provider_connection(self, model: str) -> tuple[bool, str]:
        """
        Test if a specific model/provider is working.
        
        Returns:
            (success, message) tuple
        """
        try:
            provider_name, model_name = self.parse_model_string(model)
            
            if provider_name not in self.providers:
                return False, f"Provider '{provider_name}' not configured. Please set API key."
            
            provider = self.providers[provider_name]
            if not provider.is_available():
                return False, f"Provider '{provider_name}' not available. Check API key."
            
            # Test with a simple prompt
            response = await provider.generate(
                messages=[{"role": "user", "content": "Hi"}],
                model=model_name,
                max_tokens=50
            )
            
            if response.content:
                return True, f"✓ Connected to {provider_name}"
            else:
                return False, f"Provider '{provider_name}' returned empty response"
                
        except Exception as e:
            error_msg = str(e)
            if "api" in error_msg.lower() and "key" in error_msg.lower():
                return False, f"API key error: {error_msg}"
            elif "ssl" in error_msg.lower() or "certificate" in error_msg.lower():
                return False, f"SSL/Certificate error: {error_msg}"
            else:
                return False, f"Connection error: {error_msg}"

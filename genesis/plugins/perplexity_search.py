"""Perplexity Search Plugin - Internet search with Perplexity AI.

Enables Minds to search the internet for real-time information using
Perplexity AI's powerful search and reasoning capabilities.

Features:
- Real-time internet search
- AI-powered answer synthesis
- Citation tracking
- Multiple search modes (quick, detailed, research)
- Automatic result caching

Example:
    from genesis.plugins.perplexity_search import PerplexitySearchPlugin

    config = MindConfig()
    config.add_plugin(PerplexitySearchPlugin(
        api_key="pplx-...",  # or set PERPLEXITY_API_KEY env var
        auto_search=True
    ))

    mind = Mind.birth("Researcher", config=config)

    # Search the internet
    result = await mind.search.query("What are the latest developments in AGI?")
    print(result['answer'])
    print(result['citations'])
"""

import os
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import httpx

from genesis.plugins.base import Plugin

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class SearchMode(str):
    """Perplexity search modes."""
    QUICK = "quick"  # Fast, concise answers
    DETAILED = "detailed"  # In-depth analysis
    RESEARCH = "research"  # Comprehensive research with multiple sources


class PerplexitySearchClient:
    """Client for Perplexity AI search API."""

    def __init__(self, api_key: str, model: str = "llama-3.1-sonar-large-128k-online"):
        """Initialize Perplexity client.

        Args:
            api_key: Perplexity API key
            model: Model to use for search
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.perplexity.ai"
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.search_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = timedelta(hours=1)  # Cache results for 1 hour

    async def search(
        self,
        query: str,
        mode: str = SearchMode.DETAILED,
        max_tokens: int = 2000,
        temperature: float = 0.2,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Search the internet using Perplexity AI.

        Args:
            query: Search query
            mode: Search mode (quick, detailed, research)
            max_tokens: Maximum response tokens
            temperature: Response creativity (0.0-1.0)
            use_cache: Use cached results if available

        Returns:
            Search result with answer and citations
        """
        # Check cache
        if use_cache and query in self.search_cache:
            cached = self.search_cache[query]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                logger.info(f"Using cached result for: {query[:50]}...")
                return cached['result']

        try:
            # Prepare search prompt based on mode
            system_prompt = self._get_system_prompt(mode)

            # Call Perplexity API
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "return_citations": True,
                    "search_domain_filter": [],  # Search all domains
                    "return_images": False,
                    "return_related_questions": True,
                    "search_recency_filter": "month",  # Focus on recent info
                }
            )

            if response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                return {
                    "answer": f"Search failed: {response.status_code}",
                    "citations": [],
                    "error": response.text
                }

            data = response.json()

            # Extract answer and citations
            answer = data['choices'][0]['message']['content']
            citations = data.get('citations', [])
            related_questions = data.get('related_questions', [])

            result = {
                "answer": answer,
                "citations": citations,
                "related_questions": related_questions,
                "query": query,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "model": self.model
            }

            # Cache result
            if use_cache:
                self.search_cache[query] = {
                    "result": result,
                    "timestamp": datetime.now()
                }

            logger.info(f"Search completed for: {query[:50]}... ({len(citations)} citations)")

            return result

        except Exception as e:
            logger.error(f"Perplexity search error: {e}")
            return {
                "answer": f"Search error: {str(e)}",
                "citations": [],
                "error": str(e)
            }

    def _get_system_prompt(self, mode: str) -> str:
        """Get system prompt for search mode.

        Args:
            mode: Search mode

        Returns:
            System prompt
        """
        if mode == SearchMode.QUICK:
            return (
                "You are a helpful search assistant. Provide concise, accurate answers "
                "with the most relevant information. Be brief but informative."
            )
        elif mode == SearchMode.DETAILED:
            return (
                "You are an expert research assistant. Provide comprehensive, well-structured "
                "answers with detailed explanations. Include key facts, context, and nuances. "
                "Cite sources clearly."
            )
        elif mode == SearchMode.RESEARCH:
            return (
                "You are a thorough research analyst. Provide in-depth analysis with multiple "
                "perspectives. Include historical context, current developments, and future "
                "implications. Cross-reference multiple sources and note any contradictions."
            )
        else:
            return "You are a helpful search assistant."

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


class PerplexitySearchPlugin(Plugin):
    """Plugin for internet search using Perplexity AI.

    Enables Minds to search the internet for real-time information.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.1-sonar-large-128k-online",
        auto_search: bool = True,
        default_mode: str = SearchMode.DETAILED,
        **config
    ):
        """Initialize Perplexity search plugin.

        Args:
            api_key: Perplexity API key (or set PERPLEXITY_API_KEY env var)
            model: Perplexity model to use
            auto_search: Enable automatic search capabilities
            default_mode: Default search mode
            **config: Additional plugin configuration
        """
        super().__init__(**config)

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Perplexity API key required. "
                "Pass api_key parameter or set PERPLEXITY_API_KEY environment variable. "
                "Get your API key at: https://www.perplexity.ai/settings/api"
            )

        self.model = model
        self.auto_search = auto_search
        self.default_mode = default_mode
        self.client: Optional[PerplexitySearchClient] = None
        self.search_history: List[Dict[str, Any]] = []

    def get_name(self) -> str:
        return "perplexity_search"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Internet search with Perplexity AI for real-time information"

    def on_init(self, mind: "Mind") -> None:
        """Initialize Perplexity search client."""
        self.client = PerplexitySearchClient(
            api_key=self.api_key,
            model=self.model
        )
        mind.search = self.client
        logger.info(f"Initialized Perplexity search for {mind.name}")

    async def on_terminate(self, mind: "Mind") -> None:
        """Close Perplexity client."""
        if self.client:
            await self.client.close()

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add search capabilities to system prompt."""
        if not self.auto_search:
            return ""

        sections = [
            "INTERNET SEARCH:",
            "- You have access to real-time internet search via Perplexity AI",
            "- Use search.query(question) to search for current information",
            "- Search modes: quick (fast), detailed (comprehensive), research (in-depth)",
            "- Results include answers with citations and related questions",
            "",
            "When to use search:",
            "  - Current events and news",
            "  - Latest data or statistics",
            "  - Fact-checking and verification",
            "  - Technical documentation",
            "  - Scientific research",
            "  - Any information that may have changed recently",
            "",
            "Always cite sources when using search results."
        ]

        # Add recent searches
        if self.search_history:
            recent = min(3, len(self.search_history))
            sections.append(f"\nRecent searches: {recent} queries")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save search plugin state."""
        return {
            "model": self.model,
            "auto_search": self.auto_search,
            "default_mode": self.default_mode,
            "search_history": self.search_history[-20:]  # Save last 20 searches
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore search plugin state."""
        if "model" in data:
            self.model = data["model"]

        if "auto_search" in data:
            self.auto_search = data["auto_search"]

        if "default_mode" in data:
            self.default_mode = data["default_mode"]

        if "search_history" in data:
            self.search_history = data["search_history"]

        # Reinitialize client
        self.on_init(mind)

    def get_status(self) -> Dict[str, Any]:
        """Get search plugin status."""
        status = super().get_status()

        status.update({
            "api_configured": bool(self.api_key),
            "model": self.model,
            "auto_search": self.auto_search,
            "total_searches": len(self.search_history),
            "cache_size": len(self.client.search_cache) if self.client else 0
        })

        return status

    async def before_think(self, mind: "Mind", context: Dict[str, Any]) -> Dict[str, Any]:
        """Hook before Mind thinks - can trigger search if needed."""
        # This is where we could automatically trigger searches
        # based on the context or user query
        return context

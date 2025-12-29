"""LLM Response Cache - Reduce cost and latency.

Provides Redis-backed caching for LLM responses to:
- Reduce API costs by 50-90%
- Decrease latency from seconds to milliseconds
- Improve reliability with cached fallbacks

Features:
- Hash-based keys (prompt + model + temperature)
- Configurable TTL (default 24 hours)
- Cache hit/miss metrics
- Automatic expiration
- Optional in-memory fallback if Redis unavailable

Usage:
    # In orchestrator
    cache = ResponseCache(redis_url="redis://localhost:6379")

    # Check cache before LLM call
    cached = cache.get(prompt, model, temperature)
    if cached:
        return cached

    # Call LLM
    response = await llm.generate(...)

    # Cache the response
    cache.set(prompt, model, response, temperature)
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. LLM caching disabled. Install with: pip install redis")


class ResponseCache:
    """
    Cache LLM responses to reduce cost and latency.

    Implements a Redis-backed cache with:
    - Persistent storage across restarts
    - Configurable TTL
    - Hash-based keys for collision resistance
    - Metrics tracking
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        ttl_hours: int = 24,
        enabled: bool = True,
        prefix: str = "genesis:llm:cache"
    ):
        """
        Initialize response cache.

        Args:
            redis_url: Redis connection URL
            ttl_hours: Time-to-live in hours (default 24)
            enabled: Enable/disable caching (default True)
            prefix: Redis key prefix (default "genesis:llm:cache")
        """
        self.enabled = enabled and REDIS_AVAILABLE
        self.ttl = int(timedelta(hours=ttl_hours).total_seconds())
        self.prefix = prefix

        # Metrics
        self.hits = 0
        self.misses = 0

        # In-memory fallback for when Redis is unavailable
        self._memory_cache: Dict[str, str] = {}
        self._max_memory_cache_size = 1000

        if self.enabled:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis.ping()
                logger.info(f"✅ Response cache connected to Redis at {redis_url}")
            except redis.RedisError as e:
                logger.warning(f"⚠️ Redis connection failed, using in-memory cache: {e}")
                self.redis = None
            except Exception as e:
                logger.warning(f"⚠️ Redis not available, caching disabled: {e}")
                self.enabled = False
                self.redis = None
        else:
            if not REDIS_AVAILABLE:
                logger.info("Redis package not installed, LLM caching disabled")
            self.redis = None

    def _make_key(self, prompt: str, model: str, temperature: float = 0.7) -> str:
        """
        Generate cache key from prompt + model + temperature.

        Uses SHA256 hash for consistent, collision-resistant keys.

        Args:
            prompt: The prompt text
            model: Model identifier (e.g., "openai/gpt-4")
            temperature: Temperature setting

        Returns:
            Cache key string
        """
        # Create deterministic content string
        content = f"{model}:{temperature:.2f}:{prompt}"

        # Hash for consistent key length
        hash_digest = hashlib.sha256(content.encode('utf-8')).hexdigest()

        return f"{self.prefix}:{hash_digest}"

    def get(self, prompt: str, model: str, temperature: float = 0.7) -> Optional[str]:
        """
        Get cached response.

        Args:
            prompt: The prompt text
            model: Model identifier (e.g., "openai/gpt-4")
            temperature: Temperature setting

        Returns:
            Cached response or None if not found
        """
        if not self.enabled:
            return None

        try:
            key = self._make_key(prompt, model, temperature)

            # Try Redis first
            if self.redis:
                try:
                    cached = self.redis.get(key)
                    if cached:
                        self.hits += 1
                        logger.debug(f"Cache HIT (Redis): {key[:32]}...")
                        return cached
                except redis.RedisError as e:
                    logger.warning(f"Redis get error: {e}, falling back to memory cache")

            # Fallback to memory cache
            if key in self._memory_cache:
                self.hits += 1
                logger.debug(f"Cache HIT (memory): {key[:32]}...")
                return self._memory_cache[key]

            self.misses += 1
            logger.debug(f"Cache MISS: {key[:32]}...")
            return None

        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(
        self,
        prompt: str,
        model: str,
        response: str,
        temperature: float = 0.7
    ):
        """
        Cache a response.

        Args:
            prompt: The prompt text
            model: Model identifier
            response: The LLM response to cache
            temperature: Temperature setting
        """
        if not self.enabled or not response:
            return

        try:
            key = self._make_key(prompt, model, temperature)

            # Try Redis first
            if self.redis:
                try:
                    self.redis.setex(key, self.ttl, response)
                    logger.debug(f"Cached to Redis: {key[:32]}...")
                    return
                except redis.RedisError as e:
                    logger.warning(f"Redis set error: {e}, using memory cache")

            # Fallback to memory cache
            if len(self._memory_cache) >= self._max_memory_cache_size:
                # Remove oldest entry (simple FIFO)
                self._memory_cache.pop(next(iter(self._memory_cache)))

            self._memory_cache[key] = response
            logger.debug(f"Cached to memory: {key[:32]}...")

        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def clear(self):
        """Clear all cached responses."""
        if not self.enabled:
            return

        try:
            # Clear Redis cache
            if self.redis:
                try:
                    keys = self.redis.keys(f"{self.prefix}:*")
                    if keys:
                        self.redis.delete(*keys)
                        logger.info(f"Cleared {len(keys)} cached responses from Redis")
                except redis.RedisError as e:
                    logger.warning(f"Redis clear error: {e}")

            # Clear memory cache
            self._memory_cache.clear()
            logger.info("Cleared memory cache")

        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        stats = {
            'enabled': self.enabled,
            'backend': 'redis' if self.redis else 'memory',
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate_percent': round(hit_rate, 2),
            'ttl_hours': self.ttl / 3600
        }

        # Add backend-specific stats
        if self.redis:
            try:
                keys = self.redis.keys(f"{self.prefix}:*")
                stats['cached_entries'] = len(keys)
            except:
                pass
        else:
            stats['cached_entries'] = len(self._memory_cache)
            stats['max_memory_cache_size'] = self._max_memory_cache_size

        return stats

    def reset_stats(self):
        """Reset hit/miss statistics."""
        self.hits = 0
        self.misses = 0

    def invalidate(self, prompt: str, model: str, temperature: float = 0.7):
        """Invalidate a specific cached response.

        Args:
            prompt: The prompt text
            model: Model identifier
            temperature: Temperature setting
        """
        if not self.enabled:
            return

        try:
            key = self._make_key(prompt, model, temperature)

            # Remove from Redis
            if self.redis:
                try:
                    self.redis.delete(key)
                except redis.RedisError as e:
                    logger.warning(f"Redis delete error: {e}")

            # Remove from memory
            self._memory_cache.pop(key, None)

            logger.debug(f"Invalidated cache entry: {key[:32]}...")

        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")


class CachedOrchestrator:
    """
    Mixin for adding caching to ModelOrchestrator.

    This can be used to wrap an existing orchestrator with caching.
    """

    def __init__(self, orchestrator, cache: ResponseCache):
        """
        Initialize cached orchestrator wrapper.

        Args:
            orchestrator: Original ModelOrchestrator instance
            cache: ResponseCache instance
        """
        self.orchestrator = orchestrator
        self.cache = cache

    async def generate_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate completion with caching.

        Checks cache first, falls back to LLM, then caches result.

        Args:
            prompt: The prompt
            model: Model to use
            temperature: Temperature setting
            **kwargs: Additional arguments for orchestrator

        Returns:
            Generated completion
        """
        # Determine actual model
        actual_model = model or self.orchestrator.default_model

        # Check cache first
        if self.cache.enabled:
            cached = self.cache.get(prompt, actual_model, temperature)
            if cached:
                return cached

        # Call LLM
        response = await self.orchestrator.generate_completion(
            prompt=prompt,
            model=model,
            temperature=temperature,
            **kwargs
        )

        # Cache response
        if self.cache.enabled and response:
            self.cache.set(prompt, actual_model, response, temperature)

        return response

    async def generate_streaming(self, *args, **kwargs):
        """Stream generation (no caching for streaming)."""
        # Streaming responses aren't cached
        async for chunk in self.orchestrator.generate_streaming(*args, **kwargs):
            yield chunk

    def __getattr__(self, name):
        """Delegate all other attributes to wrapped orchestrator."""
        return getattr(self.orchestrator, name)

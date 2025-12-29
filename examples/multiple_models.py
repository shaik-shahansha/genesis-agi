"""
Example showing how to use multiple model providers.

Genesis supports:
- OpenAI (GPT-4, etc.)
- Anthropic (Claude)
- Groq (fast inference, FREE!)
- Ollama (local models, completely free)
"""

import asyncio
from genesis.models.orchestrator import ModelOrchestrator


async def main():
    print("Genesis Multi-Model Example\n")
    
    orchestrator = ModelOrchestrator()
    
    # Check which providers are available
    status = await orchestrator.check_all_providers()
    
    print("Provider Status:")
    for provider, available in status.items():
        status_icon = "AVAILABLE" if available else "UNAVAILABLE"
        print(f"  {provider}: {status_icon}")
    
    # Example 1: Let the orchestrator choose automatically
    print("\n--- Example 1: Automatic Provider Selection ---")
    response = await orchestrator.generate(
        prompt="What is the meaning of life?",
        system_prompt="You are a philosophical assistant."
    )
    print(f"Response: {response[:200]}...")
    
    # Example 2: Force a specific provider
    print("\n--- Example 2: Force OpenAI ---")
    try:
        response = await orchestrator.generate(
            prompt="Write a haiku about AI",
            preferred_provider="openai"
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Fallback chain
    print("\n--- Example 3: Fallback Chain ---")
    # Try Groq first (free), fallback to others
    response = await orchestrator.generate(
        prompt="Explain quantum computing in one sentence",
        preferred_provider="groq"  # Will fallback if unavailable
    )
    print(f"Response: {response}")


if __name__ == "__main__":
    asyncio.run(main())

"""
Example: Using Perplexity Search Plugin

This example shows how to add internet search to a Genesis Mind.
"""

import asyncio
from genesis import Mind
from genesis.core.mind_config import MindConfig
from genesis.plugins.perplexity_search import PerplexitySearchPlugin


async def main():
    print("=" * 60)
    print("Perplexity Search Plugin Example")
    print("=" * 60)

    # ================================================================
    # 1. Create Mind with Search Plugin
    # ================================================================
    print("\n1. Creating Mind with search capability...")
    print("-" * 60)

    config = MindConfig.standard()
    
    # Add Perplexity search plugin
    # API key can be from env var PERPLEXITY_API_KEY or passed here
    config.add_plugin(PerplexitySearchPlugin(
        # api_key="pplx-your-key-here",  # Or use PERPLEXITY_API_KEY env var
        auto_search=True,              # Enable in system prompt
        default_mode="detailed"        # detailed, quick, or research
    ))

    mind = Mind.birth("Researcher", config=config)
    print(f"[Done] Created Mind with plugins: {[p.get_name() for p in mind.plugins]}")

    # ================================================================
    # 2. Perform Search
    # ================================================================
    print("\n2. Searching the internet...")
    print("-" * 60)

    query = "What are the latest breakthroughs in AI in 2025?"
    print(f"Query: {query}")

    result = await mind.search.query(query, mode="detailed")

    print(f"\nAnswer:\n{result['answer']}\n")
    
    if result.get('citations'):
        print(f"Citations ({len(result['citations'])}):")
        for i, citation in enumerate(result['citations'][:5], 1):
            print(f"  {i}. {citation}")

    if result.get('related_questions'):
        print(f"\nRelated questions:")
        for q in result['related_questions'][:3]:
            print(f"  - {q}")

    # ================================================================
    # 3. Different Search Modes
    # ================================================================
    print("\n\n3. Different search modes...")
    print("-" * 60)

    # Quick search (fast, concise)
    quick = await mind.search.query(
        "What is AGI?",
        mode="quick"
    )
    print(f"Quick mode: {quick['answer'][:150]}...")

    # Research mode (comprehensive)
    research = await mind.search.query(
        "Explain consciousness in AI systems",
        mode="research"
    )
    print(f"\nResearch mode: {research['answer'][:200]}...")

    # ================================================================
    # 4. Mind Uses Search in Conversation
    # ================================================================
    print("\n\n4. Mind using search in conversation...")
    print("-" * 60)

    # With auto_search=True, Mind knows it can search
    response = await mind.think(
        "What are the current debates about AI safety?"
    )
    print(f"Mind: {response[:300]}...")

    # ================================================================
    # 5. Plugin Status
    # ================================================================
    print("\n\n5. Plugin status...")
    print("-" * 60)

    search_plugin = config.get_plugin("perplexity_search")
    if search_plugin:
        status = search_plugin.get_status()
        print(f"Plugin: {status['name']} v{status['version']}")
        print(f"Enabled: {status['enabled']}")
        print(f"Total searches: {status['total_searches']}")
        print(f"Cache size: {status['cache_size']}")

    # ================================================================
    # 6. Save & Load (plugin state preserved)
    # ================================================================
    print("\n\n6. Save & Load...")
    print("-" * 60)

    path = mind.save()
    print(f"[Done] Saved Mind with search plugin to: {path}")

    loaded = Mind.load(path)
    print(f"[Done] Loaded Mind: {loaded.identity.name}")
    print(f"   Plugins: {[p.get_name() for p in loaded.plugins]}")

    print("\n" + "=" * 60)
    print("[Done] Search Plugin Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

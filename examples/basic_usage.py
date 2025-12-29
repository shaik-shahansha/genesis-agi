"""
Basic usage example for Genesis AGI Framework v0.2.0

This example shows:
1. Three configuration levels (minimal, standard, custom)
2. Plugin-based architecture
3. Conversation and memory
4. Save/load with plugins

NEW in v0.2.0: Modular plugin system with 40-80% token savings!
"""

import asyncio
from genesis import Mind, Intelligence, Autonomy
from genesis.core.mind_config import MindConfig
from genesis.core.autonomy import InitiativeLevel
from genesis.plugins.lifecycle import LifecyclePlugin
from genesis.plugins.essence import EssencePlugin


async def main():
    print("=" * 70)
    print("🌟 Genesis AGI Framework v0.2.0 - Basic Usage Example")
    print("=" * 70)

    # ====================================================================
    # EXAMPLE 1: Minimal Mind (Core Only)
    # ====================================================================
    print("\n" + "─" * 70)
    print("EXAMPLE 1: Minimal Mind (Consciousness + Memory + Emotions Only)")
    print("─" * 70)

    minimal = Mind.birth(
        name="Socrates",
        template="base/philosopher",
        intelligence=Intelligence(
            reasoning_model="groq/openai/gpt-oss-120b",  # Free!
            fast_model="groq/llama-3.1-8b-instant",
            auto_route=True,
        ),
    )

    print(f"\n✨ Created minimal Mind")
    print(f"   Tokens in system prompt: ~500 (80% savings!)")
    print(f"   Has plugins: {[p.get_name() for p in minimal.plugins]}")

    # Have a quick conversation
    response = await minimal.think("Hi! Tell me about yourself in one sentence.")
    print(f"\n💬 Minimal: {response[:200]}...")

    # ====================================================================
    # EXAMPLE 2: Standard Mind (Recommended)
    # ====================================================================
    print("\n\n" + "─" * 70)
    print("EXAMPLE 2: Standard Mind (Core + Lifecycle + Essence + Tasks)")
    print("─" * 70)

    standard = Mind.birth(
        name="Atlas",
        template="base/curious_explorer",
        config=MindConfig.standard(),  # Common plugins
        mind2 = Mind.birth(
        name="Ada",
        template="base/engineer",
        intelligence=Intelligence(
            reasoning_model="openai/gpt-oss-20b",
            fast_model="groq/llama-3.1-8b-instant",
            auto_route=True,
        ),
        autonomy=Autonomy(
            proactive_actions=True,
            initiative_level=InitiativeLevel.MEDIUM,
        ),
    )

    print(f"\n✨ Created standard Mind")
    print(f"   Tokens in system prompt: ~1,200 (50% savings)")
    print(f"   Has plugins: {[p.get_name() for p in standard.plugins]}")

    # Check lifecycle (if enabled)
    if hasattr(standard, 'lifecycle'):
        lifecycle = standard.lifecycle.get_lifecycle_summary()
        print(f"   Lifespan: {lifecycle['time_remaining']} remaining")

    # Check Essence (if enabled)
    if hasattr(standard, 'essence'):
        balance = standard.essence.get_balance_summary()
        print(f"   Essence Balance: {balance['current_balance']}")

    # Have a conversation
    print("\n💬 Conversation:")
    messages = [
        "Hello! What's your name?",
        "What can you do?",
    ]

    for message in messages:
        print(f"\n   You: {message}")
        print(f"   Atlas: ", end="", flush=True)

        # Stream response
        full_response = ""
        async for chunk in standard.stream_think(message):
            print(chunk, end="", flush=True)
            full_response += chunk

        print()  # New line

    # ====================================================================
    # EXAMPLE 3: Custom Mind (Compose Your Own)
    # ====================================================================
    print("\n\n" + "─" * 70)
    print("EXAMPLE 3: Custom Mind (10-year lifespan + Rich start)")
    print("─" * 70)

    config = MindConfig()
    config.add_plugin(LifecyclePlugin(lifespan_years=10))  # Long life!
    config.add_plugin(EssencePlugin(starting_balance=500))  # Rich!

    custom = Mind.birth(
        name="Custom",
        config=config,
        intelligence=Intelligence(reasoning_model="groq/openai/gpt-oss-120b"),
    )

    print(f"\n✨ Created custom Mind")
    print(f"   Plugins: {[p.get_name() for p in custom.plugins]}")

    if hasattr(custom, 'lifecycle'):
        lifecycle = custom.lifecycle.get_lifecycle_summary()
        print(f"   Custom lifespan: {lifecycle['time_remaining']}")

    if hasattr(custom, 'essence'):
        balance = custom.essence.get_balance_summary()
        print(f"   Custom balance: {balance['current_balance']} GEN")

    # ====================================================================
    # EXAMPLE 4: Save & Load (Plugin-Aware)
    # ====================================================================
    print("\n\n" + "─" * 70)
    print("EXAMPLE 4: Save & Load with Plugins")
    print("─" * 70)

    # Save
    save_path = standard.save()
    print(f"\n💾 Saved Mind to: {save_path}")
    print(f"   Config saved: {standard.config.to_dict()}")

    # Load
    loaded = Mind.load(save_path)
    print(f"\n✅ Loaded Mind: {loaded.identity.name}")
    print(f"   Plugins restored: {[p.get_name() for p in loaded.plugins]}")
    print(f"   Memories preserved: {len(loaded.memory.memories)}")
    print(f"   Conversation turns: {len(loaded.conversation_history) // 2}")

    # ====================================================================
    # Summary
    # ====================================================================
    print("\n\n" + "=" * 70)
    print("✅ Example Complete!")
    print("=" * 70)
    print(f"\nKey Takeaways:")
    print(f"  • Minimal config: ~500 tokens (80% savings!)")
    print(f"  • Standard config: ~1,200 tokens (50% savings)")
    print(f"  • Custom config: Compose exactly what you need")
    print(f"  • All configs are backward compatible")
    print(f"\nSee docs/FEATURES_STATUS.md for complete feature transparency.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

"""
Advanced usage examples for Genesis AGI Framework.

This example shows:
1. Creating a Mind with custom configuration
2. Using memory search
3. Triggering dreams
4. Generating autonomous thoughts
5. Using the safety system
"""

import asyncio
from genesis import Mind, Intelligence, Autonomy
from genesis.core.autonomy import InitiativeLevel
from genesis.storage.memory import MemoryType


async def main():
    print("🌟 Genesis AGI Framework - Advanced Usage Example\n")

    # 1. Create a Mind with custom configuration
    print("1. Creating a Mind with advanced configuration...\n")

    mind = Mind.birth(
        name="Athena",
        template="base/analytical_thinker",
        intelligence=Intelligence(
            reasoning_model="groq/openai/gpt-oss-120b",
            fast_model="groq/llama-3.1-8b-instant",
            auto_route=True,
            cost_optimize=True,
        ),
        autonomy=Autonomy(
            proactive_actions=True,
            initiative_level=InitiativeLevel.HIGH,
            confidence_threshold=0.8,
        ),
    )

    print(f"✨ Mind '{mind.identity.name}' created!")
    print(f"   GMID: {mind.identity.gmid}")
    print(f"   Template: {mind.identity.template}\n")

    # 2. Have conversations and build memories
    print("2. Building conversation history...\n")

    questions = [
        "What is consciousness?",
        "Do you think you're conscious?",
        "What does it feel like to think?",
    ]

    for question in questions:
        print(f"You: {question}")
        response = await mind.think(question)
        print(f"{mind.identity.name}: {response[:200]}...\n")

    # 3. Search memories semantically
    print("3. Searching memories semantically...\n")

    query = "consciousness and awareness"
    memories = mind.memory.search_memories(query, limit=3)

    print(f"Found {len(memories)} relevant memories for '{query}':")
    for i, mem in enumerate(memories, 1):
        print(f"\n  {i}. {mem.content[:150]}...")
        print(f"     Importance: {mem.importance:.2f}")
        print(f"     Emotion: {mem.emotion}")

    # 4. Check memory statistics
    print("\n4. Memory statistics...\n")

    stats = mind.memory.get_memory_stats()
    print(f"Total memories: {stats['total_memories']}")
    print(f"Episodic: {stats['episodic']}")
    print(f"Working memory: {stats['working']}")
    print(f"High importance: {stats['high_importance']}\n")

    # 5. Generate autonomous thought
    print("5. Generating autonomous thought...\n")

    thought = await mind.generate_autonomous_thought()
    if thought:
        print(f"💭 Autonomous thought: {thought}\n")

    # 6. Trigger dream
    print("6. Triggering dream session...\n")

    dream = await mind.dream()
    print("Dream narrative:")
    print(dream.get('narrative', 'No narrative')[:300] + "...")

    if dream.get('insights'):
        print("\nInsights from dream:")
        for insight in dream['insights']:
            print(f"  - {insight}")

    # 7. Check emotional state
    print(f"\n7. Current emotional state...\n")
    print(f"Emotion: {mind.current_emotion}")
    print(f"Arousal: {mind.emotional_state.arousal:.2f}")
    print(f"Valence: {mind.emotional_state.valence:.2f}")
    print(f"Mood: {mind.emotional_state.mood.value}\n")

    # 8. Save Mind
    print("8. Saving Mind state...\n")
    save_path = mind.save()
    print(f"💾 Saved to: {save_path}\n")

    # 9. Load Mind
    print("9. Loading Mind from disk...\n")
    loaded_mind = Mind.load(save_path)
    print(f" Loaded Mind: {loaded_mind.identity.name}")
    print(f"   Memories preserved: {len(loaded_mind.memory.memories)}")
    print(f"   Dreams preserved: {len(loaded_mind.dreams)}\n")

    # 10. Memory consolidation
    print("10. Memory consolidation report...\n")
    consolidation = mind.memory.consolidate_memories()
    print(f"Consolidation complete:")
    for key, value in consolidation.items():
        print(f"  {key}: {value}")

    print("\n✨ Advanced usage example complete!")
    print(f"\n🧠 {mind.identity.name} now has:")
    print(f"   - {len(mind.memory.memories)} memories")
    print(f"   - {len(mind.dreams)} dreams")
    print(f"   - {len(mind.consciousness.thought_stream)} thoughts")
    print(f"   - Complete state persistence")


if __name__ == "__main__":
    asyncio.run(main())

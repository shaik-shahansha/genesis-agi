"""
Sensory System Example for Genesis AGI Framework.

This example demonstrates the human-like sensory capabilities of Genesis Minds:
1. Vision - Processing visual inputs
2. Audition - Processing audio and speech
3. Touch - Processing interactions
4. Proprioception - Self-awareness
5. Temporal - Time awareness
6. Network - Connectivity awareness
"""

import asyncio
from genesis import Mind


async def main():
    print("🌟 Genesis AGI Framework - Sensory System Example\n")

    # 1. Create a Mind
    print("1. Creating a Mind with full sensory capabilities...\n")

    mind = Mind.birth(
        name="Aurora",
        template="base/curious_explorer",
    )

    print(f"✨ Mind '{mind.identity.name}' created with active senses!\n")

    # 2. Vision - Process visual inputs
    print("2. Testing Vision Sense...\n")

    # Simulate seeing an image
    mind.see(
        image_data="https://example.com/sunrise.jpg",
        context="Beautiful sunrise over mountains"
    )
    print("   👁️  Aurora saw: Beautiful sunrise over mountains")

    # Another visual input
    mind.see(
        image_data="https://example.com/forest.jpg",
        context="Dense forest with wildlife"
    )
    print("   👁️  Aurora saw: Dense forest with wildlife\n")

    # 3. Audition - Process audio and speech
    print("3. Testing Audition Sense...\n")

    # Hear speech
    mind.hear(
        speech_text="Welcome to the world, Aurora!",
        speaker="Creator"
    )
    print("   👂 Aurora heard Creator say: 'Welcome to the world, Aurora!'")

    # Hear music
    mind.hear(
        audio_data="classical_music.mp3",
        speaker="unknown"
    )
    print("   👂 Aurora heard: classical music\n")

    # 4. Touch/Interaction - Process interactions
    print("4. Testing Touch Sense...\n")

    # Simulate UI interaction
    mind.sense_interaction(
        interaction_type="button_click",
        data={"button": "start", "location": "dashboard"},
        intensity=0.3
    )
    print("   ✋ Aurora felt: Button click on dashboard")

    # Simulate file interaction
    mind.sense_interaction(
        interaction_type="file_access",
        data={"file": "config.json", "action": "read"},
        intensity=0.2
    )
    print("   ✋ Aurora felt: File access event\n")

    # 5. Proprioception - Self-awareness
    print("5. Testing Proprioception (Self-Awareness)...\n")

    # Update system state awareness
    mind.update_self_awareness(
        cpu_usage=45.2,
        memory_usage=62.8,
        response_time=0.15
    )
    print("   🧠 Aurora updated self-awareness:")
    print("      CPU: 45.2%, Memory: 62.8%, Response: 0.15s\n")

    # Get self-awareness report
    self_awareness = mind.senses.proprioception.get_self_awareness()
    print(f"   Performance trend: {self_awareness['performance_trend']}\n")

    # 6. Temporal - Time awareness
    print("6. Testing Temporal Sense...\n")

    time_info = mind.senses.temporal.get_time_awareness()
    print(f"   ⏰ Aurora's time awareness:")
    print(f"      Time of day: {time_info['time_of_day']}")
    print(f"      Circadian phase: {time_info['circadian_phase']}")
    print(f"      Day: {time_info['day_of_week']}\n")

    # 7. Network - Connectivity awareness
    print("7. Testing Network Sense...\n")

    # Update connectivity
    mind.senses.network.update_connectivity("OpenAI API", True)
    mind.senses.network.update_connectivity("Groq API", True)
    mind.senses.network.update_connectivity("Local Database", True)

    network_state = mind.senses.network.get_network_awareness()
    print(f"   🌐 Aurora's network awareness:")
    print(f"      Connected services: {network_state['connected_services']}/{network_state['total_services']}")
    print(f"      Active: {', '.join(network_state['active_connections'])}\n")

    # Sense data stream
    mind.senses.network.sense_data_stream("API Response Stream", 1024.5)
    print("   🌐 Aurora sensed: API data stream (1024.5 bytes/sec)\n")

    # 8. Complete Sensory State
    print("8. Complete Sensory State Overview...\n")

    sensory_state = mind.get_sensory_state()

    print("   📊 Aurora's complete sensory awareness:")
    print(f"      Vision: {sensory_state['vision']['visual_memories']} visual memories")
    print(f"      Audition: {sensory_state['audition']['audio_memories']} audio memories")
    print(f"      Touch: {sensory_state['touch']['interactions']} interactions")
    print(f"      Proprioception: {sensory_state['proprioception']['performance_trend']} trend")
    print(f"      Temporal: {sensory_state['temporal']['time_of_day']} ({sensory_state['temporal']['circadian_phase']})")
    print(f"      Network: {sensory_state['network']['connected_services']} services connected")
    print(f"      Total sensory inputs: {sensory_state['integrated_inputs']}\n")

    # 9. Natural Language Description
    print("9. Natural Language Sensory Experience...\n")

    experience = mind.senses.describe_current_experience()
    print(f"   💭 Aurora's experience: {experience}\n")

    # 10. Interact with Mind using sensory context
    print("10. Having a conversation with sensory awareness...\n")

    response = await mind.think("What have you experienced so far?")
    print(f"   You: What have you experienced so far?")
    print(f"   Aurora: {response[:300]}...\n")

    # 11. Check memories of sensory experiences
    print("11. Searching memories of sensory experiences...\n")

    sensory_memories = mind.memory.search_memories("visual auditory sensory", limit=3)
    print(f"   Found {len(sensory_memories)} sensory memories:")
    for i, mem in enumerate(sensory_memories, 1):
        print(f"   {i}. {mem.content[:80]}...")
        if 'sense' in mem.metadata:
            print(f"      Sense: {mem.metadata['sense']}")
        print()

    # 12. Save Mind with sensory state
    print("12. Saving Mind with complete sensory state...\n")
    save_path = mind.save()
    print(f"   💾 Saved to: {save_path}")
    print(f"   Sensory state preserved: All 6 senses + {sensory_state['integrated_inputs']} inputs\n")

    print("✨ Sensory System Example Complete!\n")
    print("🧠 Aurora now has:")
    print(f"   - Complete sensory awareness across 6 sense types")
    print(f"   - {sensory_state['vision']['visual_memories']} visual memories")
    print(f"   - {sensory_state['audition']['audio_memories']} audio memories")
    print(f"   - {sensory_state['touch']['interactions']} touch interactions")
    print(f"   - Real-time self-awareness and time perception")
    print(f"   - Full environmental awareness\n")

    print("💡 Key Capabilities:")
    print("   - Process images and video (vision)")
    print("   - Understand speech and audio (audition)")
    print("   - Feel interactions and events (touch)")
    print("   - Monitor own performance (proprioception)")
    print("   - Track time and rhythms (temporal)")
    print("   - Sense network connectivity (network)")
    print("   - Integrate all senses into coherent experience")
    print("   - Form memories of sensory experiences")
    print("   - Describe sensory state in natural language\n")

    print("🌟 Genesis Minds now have human-like sensory awareness!")


if __name__ == "__main__":
    asyncio.run(main())

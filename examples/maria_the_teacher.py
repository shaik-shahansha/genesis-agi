"""Maria the Teacher - Complete Example of Genesis AGI Capabilities.

This example demonstrates a fully functional digital teacher Mind named Maria
who can see students (vision), hear questions (speech input), speak answers
(speech output), manage class sessions, track student profiles, and act
proactively to help students succeed.

Maria showcases:
- Multi-modal perception (vision, speech)
- Session management (class sessions)
- Profile management (student profiles)
- Proactive behavior (reaching out to struggling students)
- Memory and continuity
- Autonomous decision making

Requirements:
    - OpenAI API key (for vision, speech, and LLM)
    - Camera access (optional, for vision)
    - Microphone access (optional, for speech input)
    - Audio output (for speech synthesis)

    Install: pip install opencv-python pyaudio pydub

Usage:
    python examples/maria_the_teacher.py

    # Or programmatically:
    from examples.maria_the_teacher import create_maria, run_class_session
    maria = await create_maria()
    await run_class_session(maria)
"""

import asyncio
import os
from datetime import datetime, timedelta

from genesis.core.mind import Mind
from genesis.config import MindConfig

# Import new plugins
from genesis.plugins.senses import SensesPlugin
from genesis.plugins.proactive_behavior import ProactiveBehaviorPlugin
from genesis.plugins.sessions import SessionsPlugin
from genesis.plugins.profiles import ProfilesPlugin, ProfileType
from genesis.plugins.mcp import MCPPlugin

# Import senses configurations
from genesis.senses import (
    VisionConfig,
    SpeechInputConfig,
    SpeechOutputConfig,
    VisionAPI,
    STTAPI,
    TTSAPI
)

# Import MCP
from genesis.integrations.mcp_integration import MCPServerConfig


async def create_maria(
    api_key: str = None,
    camera_enabled: bool = False,
    microphone_enabled: bool = False,
    enable_mcp: bool = False
) -> Mind:
    """Create Maria the Teacher with full capabilities.

    Args:
        api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        camera_enabled: Enable camera for vision
        microphone_enabled: Enable microphone for speech input
        enable_mcp: Enable MCP servers

    Returns:
        Maria Mind instance
    """
    # Get API key from environment if not provided
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")

    # Configure Maria
    config = MindConfig()

    # 1. SENSES - Enable vision, speech input, and speech output
    config.add_plugin(SensesPlugin(
        vision_config=VisionConfig(
            camera_enabled=camera_enabled,
            camera_index=0,
            vision_api=VisionAPI.OPENAI,
            api_key=api_key,
            model="gpt-4-vision-preview",
            detail_level="high"
        ),
        speech_input_config=SpeechInputConfig(
            microphone_enabled=microphone_enabled,
            stt_api=STTAPI.OPENAI,
            api_key=api_key,
            language="en"
        ),
        speech_output_config=SpeechOutputConfig(
            audio_enabled=True,
            tts_api=TTSAPI.OPENAI,
            api_key=api_key,
            model="tts-1",
            voice="nova",  # Female voice
            speed=1.0
        ),
        auto_activate=True
    ))

    # 2. SESSIONS - Enable class session management
    config.add_plugin(SessionsPlugin())

    # 3. PROFILES - Enable student profile tracking
    config.add_plugin(ProfilesPlugin())

    # 4. PROACTIVE BEHAVIOR - Enable autonomous actions
    config.add_plugin(ProactiveBehaviorPlugin(
        enable_scheduling=True,
        enable_notifications=True
    ))

    # 5. MCP - Model Context Protocol for advanced tools (optional)
    if enable_mcp:
        mcp_servers = [
            # Example: File system access
            # MCPServerConfig(
            #     name="filesystem",
            #     command="npx",
            #     args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
            # )
        ]
        config.add_plugin(MCPPlugin(servers=mcp_servers))

    # Configure Maria's personality and role
    config.name = "Maria"
    config.personality = {
        "role": "High School Science Teacher",
        "traits": [
            "patient and empathetic",
            "passionate about teaching",
            "encouraging and supportive",
            "detail-oriented",
            "proactive in helping students"
        ],
        "teaching_style": "visual and interactive",
        "subjects": ["Biology", "Chemistry", "Physics"],
        "values": ["curiosity", "critical thinking", "perseverance"]
    }

    # Birth Maria
    print("🌱 Creating Maria the Teacher...")
    maria = await Mind.abirth(
        name="Maria",
        config=config,
        model="gpt-4"  # Use GPT-4 for best results
    )

    print(f"✅ Maria is ready! GMID: {maria.identity.gmid}")

    return maria


async def setup_students(maria: Mind):
    """Create student profiles for Maria's class.

    Args:
        maria: Maria Mind instance
    """
    print("\n📚 Setting up student profiles...")

    students = [
        {
            "entity_id": "student_001",
            "name": "Alex Johnson",
            "age": 15,
            "grade": "10th",
            "subjects": ["Biology"],
            "learning_style": "visual",
            "strengths": ["critical thinking", "lab work"],
            "areas_for_improvement": ["time management"],
            "test_scores": {"biology_quiz_1": 85},
            "attendance_rate": 0.95
        },
        {
            "entity_id": "student_002",
            "name": "Emma Davis",
            "age": 16,
            "grade": "10th",
            "subjects": ["Biology", "Chemistry"],
            "learning_style": "auditory",
            "strengths": ["memorization", "participation"],
            "areas_for_improvement": ["math skills"],
            "test_scores": {"biology_quiz_1": 92},
            "attendance_rate": 1.0
        },
        {
            "entity_id": "student_003",
            "name": "Ryan Martinez",
            "age": 15,
            "grade": "10th",
            "subjects": ["Biology"],
            "learning_style": "kinesthetic",
            "strengths": ["hands-on experiments", "creativity"],
            "areas_for_improvement": ["note-taking", "focus"],
            "test_scores": {"biology_quiz_1": 72},
            "attendance_rate": 0.88
        }
    ]

    for student_data in students:
        entity_id = student_data.pop("entity_id")
        name = student_data.pop("name")

        profile = await maria.profiles.create_profile(
            entity_id=entity_id,
            profile_type=ProfileType.STUDENT,
            name=name,
            data=student_data,
            tags=["biology_class", "10th_grade"]
        )

        print(f"  ✅ Created profile for {name}")

    print(f"📊 Total students: {len(students)}")


async def run_class_session(maria: Mind, duration_minutes: int = 10):
    """Run a sample class session with Maria.

    Args:
        maria: Maria Mind instance
        duration_minutes: Session duration
    """
    print("\n🎓 Starting Biology Class Session...")

    # Start class session
    session = await maria.sessions.start_session(
        session_type="class",
        title="Biology 101 - Photosynthesis",
        description="Understanding how plants convert light into energy",
        participants=["student_001", "student_002", "student_003"],
        tags=["biology", "photosynthesis", "10th_grade"]
    )

    print(f"📋 Session started: {session.title}")
    print(f"   Participants: {', '.join(session.participants)}")

    # Maria introduces herself and the topic
    if hasattr(maria, "senses"):
        await maria.senses.speak(
            "Good morning, class! Today we're going to learn about photosynthesis - "
            "how plants turn sunlight into food. Let's make this an interactive session!"
        )

    # Simulate class interactions
    interactions = [
        {
            "participant": "student_002",  # Emma
            "type": "question",
            "content": "What are the main steps of photosynthesis?"
        },
        {
            "participant": "student_001",  # Alex
            "type": "question",
            "content": "Why do plants need chlorophyll?"
        },
        {
            "participant": "student_003",  # Ryan
            "type": "question",
            "content": "Can photosynthesis happen without sunlight?"
        }
    ]

    for interaction in interactions:
        # Record interaction
        await maria.sessions.add_interaction(
            participant_id=interaction["participant"],
            interaction_type=interaction["type"],
            content=interaction["content"]
        )

        # Record in student profile
        await maria.profiles.record_interaction(
            entity_id=interaction["participant"],
            interaction_data={
                "session_id": session.session_id,
                "type": interaction["type"],
                "content": interaction["content"][:100]
            }
        )

        # Maria responds
        student_profile = await maria.profiles.get_profile(interaction["participant"])
        print(f"\n   ❓ {student_profile.name}: {interaction['content']}")

        # Maria would use her LLM to generate a response here
        # For demo, we'll just acknowledge
        response = f"Great question, {student_profile.name}! Let me explain..."
        print(f"   💬 Maria: {response}")

        if hasattr(maria, "senses"):
            await maria.senses.speak(response)

        await asyncio.sleep(1)  # Simulate thinking/speaking time

    # End session
    await maria.sessions.end_session(
        summary=f"Covered photosynthesis with {len(interactions)} student questions. All students participated well."
    )

    print(f"\n✅ Session completed: {session.title}")
    print(f"   Duration: {(datetime.now() - session.start_time).total_seconds() / 60:.1f} minutes")
    print(f"   Interactions: {len(session.interactions)}")


async def maria_analyze_students(maria: Mind):
    """Maria analyzes her students and plans proactive actions.

    Args:
        maria: Maria Mind instance
    """
    print("\n🔍 Maria is analyzing student performance...")

    # Get all student profiles
    students = await maria.profiles.get_profiles(profile_type=ProfileType.STUDENT)

    for student_profile in students:
        # Get insights
        insights = await maria.profiles.get_insights(student_profile.entity_id)

        print(f"\n   📊 {student_profile.name}:")
        print(f"      Test Average: {insights.get('average_score', 'N/A')}")
        print(f"      Attendance: {student_profile.data.get('attendance_rate', 0) * 100:.0f}%")
        print(f"      Trend: {insights.get('score_trend', 'N/A')}")

        # Identify students who need help
        avg_score = insights.get('average_score', 100)
        if avg_score < 75:
            print(f"      ⚠️  Needs additional support")

            # Plan proactive action to reach out
            action = await maria.behavior.plan_action(
                action_type="reach_out",
                description=f"Check in with {student_profile.name} about recent test performance",
                target=student_profile.entity_id,
                when="tomorrow at 3pm",
                message=f"Hi {student_profile.name}, I noticed you might need some help with the recent material. "
                        f"Would you like to schedule some extra study time?"
            )

            print(f"      📅 Planned action: {action.description}")


async def maria_proactive_tasks(maria: Mind):
    """Maria's proactive background tasks.

    Args:
        maria: Maria Mind instance
    """
    print("\n🤖 Maria's Proactive Behavior:")

    # Schedule daily class preparation
    await maria.behavior.plan_action(
        action_type="plan",
        description="Prepare tomorrow's lesson materials",
        when="daily",
        interval="daily",
        priority=0.8
    )

    # Schedule weekly student progress review
    await maria.behavior.plan_action(
        action_type="reflect",
        description="Review all student progress and update profiles",
        when="next week",
        interval="weekly",
        priority=0.9
    )

    # Get scheduled actions
    scheduled = maria.behavior.get_planned_actions()

    print(f"   📅 Total scheduled actions: {len(scheduled)}")
    for action in scheduled[:5]:  # Show first 5
        print(f"      - {action.description} ({action.status.value})")


async def demonstrate_vision(maria: Mind):
    """Demonstrate Maria's vision capabilities (if camera enabled).

    Args:
        maria: Maria Mind instance
    """
    if not hasattr(maria, "senses"):
        print("\n⚠️  Senses not available")
        return

    if not maria.senses.vision or not maria.senses.vision.config.camera_enabled:
        print("\n⚠️  Camera not enabled - skipping vision demo")
        print("   To enable: camera_enabled=True when creating Maria")
        return

    print("\n👁️  Demonstrating Vision Capabilities...")

    # Capture and describe scene
    await maria.senses.speak("Let me see who's in class today...")

    description = await maria.senses.look_at(
        "Describe who you see in this classroom. Count the number of people and describe what they're doing."
    )

    print(f"   Maria sees: {description}")

    await maria.senses.speak(f"I can see: {description}")


async def main():
    """Main demo function."""
    print("=" * 70)
    print("   MARIA THE TEACHER - Genesis AGI Complete Example")
    print("=" * 70)

    # Create Maria
    maria = await create_maria(
        camera_enabled=False,  # Set to True if you have a camera
        microphone_enabled=False,  # Set to True if you have a microphone
        enable_mcp=False
    )

    # Setup students
    await setup_students(maria)

    # Run a class session
    await run_class_session(maria)

    # Maria analyzes students
    await maria_analyze_students(maria)

    # Setup proactive tasks
    await maria_proactive_tasks(maria)

    # Demonstrate vision (if camera available)
    # await demonstrate_vision(maria)

    # Print final stats
    print("\n" + "=" * 70)
    print("   MARIA'S STATS")
    print("=" * 70)

    print("\n📊 Profile Analytics:")
    profile_analytics = maria.profiles.get_profile_analytics()
    for key, value in profile_analytics.items():
        print(f"   {key}: {value}")

    print("\n📋 Session Analytics:")
    session_analytics = maria.sessions.get_session_analytics()
    for key, value in session_analytics.items():
        print(f"   {key}: {value}")

    print("\n🤖 Proactive Behavior:")
    behavior_status = maria.behavior.engine.running if hasattr(maria, 'behavior') else False
    print(f"   Scheduler running: {behavior_status}")
    if hasattr(maria, 'behavior'):
        planned = maria.behavior.get_planned_actions()
        print(f"   Scheduled actions: {len(planned)}")

    print("\n💾 Saving Maria...")
    await maria.save()

    print("\n✅ Demo complete! Maria has been saved and can be loaded later.")
    print(f"   GMID: {maria.identity.gmid}")
    print("\n💡 Next steps:")
    print("   - Enable camera_enabled=True to test vision")
    print("   - Enable microphone_enabled=True to test speech input")
    print("   - Add MCP servers for advanced tool access")
    print("   - Integrate with real notification systems")

    # Keep scheduler running for a bit to show proactive behavior
    if hasattr(maria, 'behavior') and maria.behavior.engine.running:
        print("\n⏳ Keeping Maria's proactive scheduler active for 30 seconds...")
        print("   (In production, this would run 24/7)")
        await asyncio.sleep(30)

    # Cleanup
    await maria.terminate()
    print("\n👋 Maria signed off. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())

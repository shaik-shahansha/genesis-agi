# Genesis AGI - Quick Start Guide

This guide will get you up and running with Genesis AGI in 10 minutes.

## 📋 Prerequisites

- Python 3.11 or higher
- OpenAI API key (or Anthropic, Google, Groq, Ollama)
- Optional: Perplexity API key for internet search
- Optional: Camera and microphone for senses

## 🚀 Installation

```bash
# Clone repository
git clone https://github.com/shaik-shahansha/genesis-agi.git
cd Genesis-AGI

# Install dependencies
pip install -e .

# Optional: Install senses support (camera/microphone)
pip install -e ".[senses]"

# Set API keys
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."  # Optional
```

## 🎯 Your First Mind (Basic)

```python
import asyncio
from genesis.core.mind import Mind
from genesis.config import MindConfig

async def main():
    # Create a simple Mind
    config = MindConfig()
    config.name = "My First Mind"

    mind = await Mind.abirth(
        name="Assistant",
        config=config,
        model="gpt-4"
    )

    # Chat with your Mind
    response = await mind.think("Hello! Tell me about yourself.")
    print(response)

    # Save Mind
    await mind.save()

    # Terminate
    await mind.terminate()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🌟 Advanced Mind (All Features)

```python
import asyncio
from genesis.core.mind import Mind
from genesis.config import MindConfig

# Import all the new plugins
from genesis.plugins.senses import SensesPlugin
from genesis.plugins.proactive_behavior import ProactiveBehaviorPlugin
from genesis.plugins.sessions import SessionsPlugin
from genesis.plugins.profiles import ProfilesPlugin
from genesis.plugins.mcp import MCPPlugin
from genesis.plugins.environments import EnvironmentsPlugin
from genesis.plugins.perplexity_search import PerplexitySearchPlugin
from genesis.plugins.learning import LearningPlugin

# Import configurations
from genesis.senses import VisionConfig, SpeechInputConfig, SpeechOutputConfig

async def main():
    config = MindConfig()

    # 1. Add Senses (see, hear, speak)
    config.add_plugin(SensesPlugin(
        vision_config=VisionConfig(
            camera_enabled=False,  # Set True if you have camera
            vision_api="openai",
            api_key=os.getenv("OPENAI_API_KEY")
        ),
        speech_input_config=SpeechInputConfig(
            microphone_enabled=False,  # Set True if you have mic
            stt_api="openai",
            api_key=os.getenv("OPENAI_API_KEY")
        ),
        speech_output_config=SpeechOutputConfig(
            audio_enabled=True,
            tts_api="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
            voice="nova"
        )
    ))

    # 2. Add Proactive Behavior (autonomous actions)
    config.add_plugin(ProactiveBehaviorPlugin(
        enable_scheduling=True,
        enable_notifications=True
    ))

    # 3. Add Session Management
    config.add_plugin(SessionsPlugin())

    # 4. Add Entity Profiles
    config.add_plugin(ProfilesPlugin())

    # 5. Add Internet Search
    config.add_plugin(PerplexitySearchPlugin(
        api_key=os.getenv("PERPLEXITY_API_KEY"),
        auto_search=True
    ))

    # 6. Add Learning & Adaptation
    config.add_plugin(LearningPlugin(
        enable_auto_learning=True,
        learning_rate=0.1
    ))

    # 7. Add Real-Time Environments (optional)
    config.add_plugin(EnvironmentsPlugin(
        server_url="ws://localhost:8765",
        auto_connect=False
    ))

    # Create advanced Mind
    mind = await Mind.abirth(
        name="Advanced Assistant",
        config=config,
        model="gpt-4"
    )

    print(f"[Done] Created {mind.name} with GMID: {mind.identity.gmid}")

    # Use features

    # Search the internet
    if hasattr(mind, 'search'):
        result = await mind.search.query(
            "What are the latest developments in AGI?",
            mode="detailed"
        )
        print(f"\n🔍 Search Result: {result['answer'][:200]}...")

    # Record a learning experience
    if hasattr(mind, 'learning'):
        await mind.learning.record_experience(
            context="helping_user",
            action="detailed_explanation",
            outcome="success",
            metrics={"satisfaction": 0.95}
        )

        # Get learned strategy
        strategy = await mind.learning.get_best_strategy("helping_user")
        print(f"\n📚 Learned Strategy: {strategy}")

    # Create a profile
    if hasattr(mind, 'profiles'):
        await mind.profiles.create_profile(
            entity_id="user_001",
            profile_type="friend",
            name="John Doe",
            data={"interests": ["AI", "technology"]}
        )

    # Start a session
    if hasattr(mind, 'sessions'):
        session = await mind.sessions.start_session(
            session_type="consultation",
            title="AI Discussion",
            participants=["user_001"]
        )
        print(f"\n📋 Started session: {session.title}")

    # Save and terminate
    await mind.save()
    await mind.terminate()

    print("\n[Done] Advanced Mind created and saved!")

if __name__ == "__main__":
    import os
    asyncio.run(main())
```

## 📚 Maria the Teacher Example

See the complete example in `examples/maria_the_teacher.py`:

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Run Maria example
python examples/maria_the_teacher.py
```

## 🌐 Real-Time Environments

### Start Environment Server

```bash
# Terminal 1: Start WebSocket server
python -c "
import asyncio
from genesis.environments import EnvironmentServer

async def main():
    server = EnvironmentServer()
    await server.start()
    print('Environment server running on ws://localhost:8765')
    await asyncio.Future()  # Run forever

asyncio.run(main())
"
```

### Connect Minds to Environment

```python
# Terminal 2 & 3: Create Minds that can interact
import asyncio
from genesis.core.mind import Mind
from genesis.config import MindConfig
from genesis.plugins.environments import EnvironmentsPlugin

async def main():
    config = MindConfig()
    config.add_plugin(EnvironmentsPlugin(
        server_url="ws://localhost:8765",
        auto_connect=True
    ))

    mind = await Mind.abirth("Social Mind", config=config)

    # Join environment
    await mind.environments.join("park_01")

    # Broadcast message
    await mind.environments.broadcast("Hello everyone in the park!")

    # Keep alive
    await asyncio.sleep(30)

    await mind.environments.leave()
    await mind.terminate()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔧 MCP Integration

```python
from genesis.plugins.mcp import MCPPlugin
from genesis.integrations.mcp_integration import MCPServerConfig

# Configure MCP servers
servers = [
    MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    )
]

config.add_plugin(MCPPlugin(servers=servers))

# Mind can now use MCP tools
result = await mind.mcp.execute_tool(
    "filesystem_read_file",
    {"path": "README.md"}
)
```

## 📖 Next Steps

1. **Read the Blueprint**: [GENESIS_AGI_BLUEPRINT.md](../GENESIS_AGI_BLUEPRINT.md)
2. **Explore Features**: [docs/NEW_FEATURES.md](NEW_FEATURES.md)
3. **Run Examples**: Check `examples/` directory
4. **API Documentation**: [docs/API.md](API.md)

## 🆘 Troubleshooting

### Camera Not Working
```bash
pip install opencv-python
# Make sure camera permissions are granted
```

### Microphone Not Working
```bash
pip install pyaudio
# On macOS: brew install portaudio
# On Linux: sudo apt-get install portaudio19-dev
```

### WebSocket Connection Failed
```bash
# Make sure environment server is running
# Check firewall settings for port 8765
```

## 💡 Tips

1. **Start Simple**: Begin with basic Mind, add plugins as needed
2. **API Keys**: Store in environment variables, not in code
3. **Cost Control**: Use Consciousness for 90-95% cost reduction
4. **Learning**: Let Minds gain experience over time for better performance
5. **Senses**: Start without camera/mic, add later when needed

## 🎓 Learn More

- **Use Cases**: See real-world examples in `docs/USE_CASES.md`
- **Tutorials**: Step-by-step guides in `docs/TUTORIALS.md`
- **Community**: Join discussions on GitHub Issues

Happy building with Genesis AGI! 🚀

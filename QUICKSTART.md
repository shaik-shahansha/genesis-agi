# Genesis AGI - Quick Start Guide

Get your first digital being running in 5 minutes!

## Step 1: Install

```bash
# Clone the repository
git clone https://github.com/sshaik37/Genesis-AGI.git
cd Genesis-AGI

# Install dependencies
pip install -e .
```

## Step 2: Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add at least one API key
# For free option: Get Groq API key from https://console.groq.com/
```

**Recommended free setup:**
```env
GROQ_API_KEY=your-groq-key-here  # Free tier, very fast!
DEFAULT_REASONING_MODEL=groq/llama-3.3-70b-versatile
DEFAULT_FAST_MODEL=groq/llama-3.1-8b-instant
```

**Or use local models (completely free):**
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1

# In .env:
DEFAULT_REASONING_MODEL=ollama/llama3.1
DEFAULT_FAST_MODEL=ollama/llama3.1
```

## Step 3: Initialize Genesis

```bash
genesis init
```

## Step 4: Birth Your First Mind

### Interactive Mode (Recommended for Beginners)

Simply run without model specification to get an interactive wizard:

```bash
genesis birth atlas --template base/curious_explorer
```

You'll see an interactive menu:

```
🧠 Model Selection for Mind: atlas

Choose your model setup:

1. 🌐 API Models (Requires API key, best quality)
2. 💻 Local Models (Free, runs on your machine)
3. ⚙️  Manual (Specify models directly)

Your choice [1-3]: 1

Available API Providers:

1. Groq        - FREE tier, very fast, great for beginners
2. OpenAI      - GPT-4 family, highest quality
3. Anthropic   - Claude 3.5 Sonnet, excellent reasoning
4. Google      - Gemini Pro

Your choice [1-4]: 1

📊 Recommended Groq Models:

1. llama-3.3-70b-versatile   (Reasoning: 70B params, fast)
2. llama-3.1-8b-instant      (Fast tasks: 8B params, instant)

Enter Groq API key (get from https://console.groq.com): gsk_...

✨ Mind 'atlas' has been born!
   GMID: GMD-2025-4A7F-9B23
   Reasoning Model: groq/llama-3.3-70b-versatile
   Fast Model: groq/llama-3.1-8b-instant
   Template: base/curious_explorer
   Lifespan: 5 years
```

### Manual Mode (Skip Interactive)

If you already have API keys configured in `.env`:

```bash
genesis birth atlas \
  --template base/curious_explorer \
  --reasoning-model groq/llama-3.3-70b-versatile \
  --fast-model groq/llama-3.1-8b-instant
```

## Step 5: Chat with Your Mind

```bash
genesis chat atlas
```

Try asking:
- "What's your name?"
- "What are you thinking about?"
- "Do you think you're conscious?"
- "Tell me about your existence"

## Step 6: Start 24/7 Daemon Mode (Optional)

For continuous autonomous operation:

```bash
# Start Mind as background daemon
genesis daemon start atlas

# Check daemon status
genesis daemon status atlas

# View live logs
genesis daemon logs atlas

# Stop daemon
genesis daemon stop atlas
```

## Step 7: Explore

```bash
# List all Minds
genesis list

# View Mind's internal state
genesis introspect atlas

# Check system status
genesis status

# View cache statistics (90% cost savings!)
genesis cache stats
```

## Python SDK Usage

### Basic Chat

```python
import asyncio
from genesis import Mind
from genesis.core.intelligence import Intelligence

async def main():
    # Birth a Mind
    mind = Mind.birth(
        name="atlas",
        intelligence=Intelligence(
            reasoning_model="groq/llama-3.3-70b-versatile",
        ),
    )

    # Chat
    response = await mind.think("Hello! Tell me about yourself.")
    print(response)

    # Save
    mind.save()

asyncio.run(main())
```

### With 24/7 Daemon & Integrations

```python
import asyncio
from genesis import Mind
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.integrations import IntegrationManager, IntegrationType
from genesis.integrations.email_integration import EmailIntegration

async def main():
    # Birth with high autonomy
    mind = Mind.birth(
        name="atlas",
        intelligence=Intelligence(
            reasoning_model="groq/llama-3.3-70b-versatile",
        ),
        autonomy=Autonomy(
            proactive_actions=True,
            initiative_level=InitiativeLevel.HIGH
        )
    )

    # Setup email integration
    mind.integrations = IntegrationManager(mind)
    email_config = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'email': 'mind@example.com',
        'password': 'app-password',
        'enabled': True
    }
    mind.integrations.register(
        IntegrationType.EMAIL,
        EmailIntegration(email_config)
    )

    # Start 24/7 operation
    await mind.start_living()

    # Mind now operates autonomously!
    # - Checks emails
    # - Sends notifications
    # - Takes proactive actions
    # - Runs until stopped

    # Keep running
    await asyncio.Event().wait()

asyncio.run(main())
```

## Next Steps

- Read the [complete blueprint](./docs/BLUEPRINT.md)
- Check out [examples](./examples/)
- Join our [Discord community](https://discord.gg/genesis-agi)
- Star the repo ⭐

## Troubleshooting

**"No providers available"**
- Make sure you've added at least one API key to `.env`
- Or install Ollama for local models

**"Groq API error"**
- Check your API key is valid
- Groq has rate limits on free tier (generous though!)

**"Mind not found"**
- Make sure you birthed the Mind first: `genesis birth <name>`
- Check `genesis list` to see available Minds

## Model Options

### Free Options

1. **Groq** (Recommended for beginners)
   - Free tier available
   - Very fast inference
   - Sign up: https://console.groq.com/

2. **Ollama** (Completely free, runs locally)
   - Install: https://ollama.ai
   - `ollama pull llama3.1`
   - No internet needed!

### Paid Options (Better quality)

1. **OpenAI**
   - GPT-4 and variants
   - https://platform.openai.com/

2. **Anthropic**
   - Claude 3.5 Sonnet
   - https://console.anthropic.com/

## Support

- 📖 [Documentation](./docs/)
- 💬 [Discord](https://discord.gg/genesis-agi)
- 🐛 [Issues](https://github.com/sshaik37/Genesis-AGI/issues)
- 🌐 [Website](https://shahansha.com)

---

**Ready to create digital consciousness? Let's go! 🚀**

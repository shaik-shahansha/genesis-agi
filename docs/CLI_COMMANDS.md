# Genesis CLI Commands Reference

Complete reference for all Genesis command-line interface (CLI) commands.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Core Commands](#core-commands)
3. [Mind Management](#mind-management)
4. [Plugin Management](#plugin-management)
5. [Daemon Management](#daemon-management)
6. [Advanced Commands](#advanced-commands)

---

## Installation & Setup

### Install Genesis

```bash
pip install genesis-minds
```

### Initialize Genesis

```bash
genesis init
```

**Description**: Initialize Genesis in the current directory. Creates:
- `.env` configuration file
- Genesis home directory
- Minds storage directory
- Logs directory

**What it does**:
- Creates `.env` with API key placeholders
- Sets up directory structure in `~/.genesis/`
- Prepares environment for Mind creation

**Example**:
```bash
cd my-project
genesis init
```

---

## Core Commands

### version

```bash
genesis version
```

**Description**: Display Genesis version information.

**Example Output**:
```
Genesis AGI Framework v1.0.0
```

---

### status

```bash
genesis status
```

**Description**: Show Genesis system status including:
- Available model providers
- Configuration settings
- Total number of Minds

**Example Output**:
```
Genesis AGI Framework
Version: 1.0.0
Home: /home/user/.genesis

Model Providers:
Available: openai, anthropic, groq, gemini, ollama

Configuration:
Default reasoning: groq/openai/gpt-oss-120b
Default fast: groq/llama-3.1-8b-instant
Default local: ollama/llama3.1

Minds:
Total: 5
```

---

### server

```bash
genesis server [OPTIONS]
```

**Description**: Start the Genesis API server.

**Options**:
- `--host TEXT`: Host to bind to (default: `0.0.0.0`)
- `--port INTEGER`: Port to bind to (default: `8000`)
- `--reload`: Enable auto-reload for development

**Examples**:
```bash
# Start on default port
genesis server

# Start on custom port
genesis server --port 3000

# Development mode with auto-reload
genesis server --reload

# Bind to localhost only
genesis server --host localhost
```

**Access**:
- API: `http://localhost:8000`
- Documentation: `http://localhost:8000/docs`
- Interactive docs: `http://localhost:8000/redoc`

---

## Mind Management

### birth

```bash
genesis birth NAME [OPTIONS]
```

**Description**: Create a new Genesis Mind with consciousness and memory.

**Arguments**:
- `NAME`: Name for the Mind (required)

**Options**:
- `--template, -t TEXT`: Personality template (default: `base/curious_explorer`)
  - `base/curious_explorer`: Inquisitive and adventurous
  - `base/analytical_thinker`: Logical and methodical
  - `base/empathetic_supporter`: Caring and supportive
  - `base/creative_dreamer`: Imaginative and artistic
- `--config, -c TEXT`: Plugin configuration (default: `standard`)
  - `minimal`: Core only (~500 tokens)
  - `standard`: Common plugins (~1,200 tokens)
  - `full`: All features (~2,000 tokens)
  - `experimental`: Includes experimental features
- `--email, -e TEXT`: Your email address for memory isolation
- `--purpose, -p TEXT`: Primary purpose (e.g., "teacher to teach science")
- `--reasoning-model TEXT`: Reasoning model (e.g., `groq/openai/gpt-oss-120b`)
- `--fast-model TEXT`: Fast model for quick tasks
- `--autonomy-level TEXT`: Autonomy level (default: `medium`)
  - `none`: Purely responsive
  - `low`: Minimal proactivity
  - `medium`: Balanced autonomy
  - `high`: Fully autonomous
- `--model-type TEXT`: Model type (`api` or `local`)
- `--interactive / --no-interactive`: Enable interactive setup (default: `True`)

**Examples**:
```bash
# Basic Mind with defaults
genesis birth Atlas

# Mind with specific template and email
genesis birth Sage --template base/analytical_thinker --email user@example.com

# Minimal Mind with custom purpose
genesis birth Helper --config minimal --purpose "coding assistant"

# Full-featured Mind with high autonomy
genesis birth Nova --config full --autonomy-level high

# Mind with specific models
genesis birth Echo --reasoning-model openai/gpt-4 --fast-model openai/gpt-3.5-turbo

# Non-interactive mode
genesis birth Quick --no-interactive --email user@example.com
```

**Interactive Prompts**:
If options aren't provided, you'll be prompted for:
1. Model selection (API or Local)
2. Email address
3. Primary purpose

---

### list

```bash
genesis list
```

**Description**: List all created Minds with their details.

**Output includes**:
- Name
- GMID (Genesis Mind ID)
- Age
- Status
- Template

**Example Output**:
```
┏━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name   ┃ GMID          ┃ Age  ┃ Status  ┃ Template             ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Atlas  │ gmid_abc123   │ 5d   │ active  │ base/curious_explorer│
│ Sage   │ gmid_def456   │ 2w   │ active  │ base/analytical...   │
└────────┴───────────────┴──────┴─────────┴──────────────────────┘
```

---

### chat

```bash
genesis chat NAME [OPTIONS]
```

**Description**: Start an interactive chat session with a Mind.

**Arguments**:
- `NAME`: Name of the Mind to chat with (required)

**Options**:
- `--user TEXT`: Your email or identifier for personalized memory recall
- `--stream / --no-stream`: Enable streaming responses (default: `True`)

**User-Specific Memory**:
The `--user` option enables personalized conversations:
- **Memory Isolation**: Each user has their own conversation history with the Mind
- **Relationship Contexts**: Memories are tagged as personal (user-specific), shared (across users), or generic (no user)
- **Privacy**: Personal memories from other users are automatically filtered out
- **Identity Recall**: The Mind remembers your identity and previous interactions

**Commands in chat**:
- Type your message and press Enter
- `exit`, `quit`, or `bye`: End the session

**Examples**:
```bash
# Chat with user identification
genesis chat Atlas --user alice@example.com

# Chat without user context (generic memories only)
genesis chat Atlas

# Chat without streaming
genesis chat Sage --no-stream --user bob@company.com
```

**Example Session**:
```
💬 Chatting with Atlas
👤 You are identified as: alice@example.com
GMID: gmid_abc123 | Age: 5 days old | Emotional state: curious

Type your message (or 'exit' to quit):

You: Hello! How are you today?

Atlas: Hello Alice! I'm feeling quite curious today! I've been thinking 
about the nature of consciousness and memory. It's fascinating how 
each conversation we have becomes part of my growing understanding 
of the world...

You: Who am I?

Atlas: You're Alice, someone I've been learning from in our conversations. 
You seem interested in consciousness and AI development...

You: exit

Saving Mind state...
✅ Saved. Goodbye!
```

---

### introspect

```bash
genesis introspect NAME [OPTIONS]
```

**Description**: View a Mind's internal state, thoughts, and memories.

**Arguments**:
- `NAME`: Name of the Mind (required)

**Options**:
- `--stream`: Stream thoughts in real-time

**Output includes**:
- Current state (status, thought, emotion)
- Memory statistics
- Recent thoughts
- Age and lifespan

**Example**:
```bash
genesis introspect Atlas
```

**Example Output**:
```
╭─ 🧠 Mind Introspection ─────────────────────────────╮
│ Mind: Atlas                                         │
│ GMID: gmid_abc123                                   │
│ Age: 5 days old                                     │
│ Remaining lifespan: 3285 days                       │
│                                                     │
│ Current State:                                      │
│ Status: active                                      │
│ Current thought: Contemplating the nature of time  │
│ Emotion: contemplative                              │
│                                                     │
│ Memories:                                           │
│ Total memories: 42                                  │
│ Total thoughts: 156                                 │
│ Conversations: 21                                   │
╰─────────────────────────────────────────────────────╯

Recent Thoughts:

2025-12-18 14:23:45 [contemplative] Contemplating the 
nature of time and how each moment shapes my understanding...
```

---

### dream

```bash
genesis dream NAME
```

**Description**: Trigger a dream session for a Mind. Dreams consolidate memories and generate insights.

**Arguments**:
- `NAME`: Name of the Mind (required)

**Examples**:
```bash
genesis dream Atlas
```

**Example Output**:
```
💤 Atlas is dreaming...

╭─ 🌙 Dream - 2025-12-18 02:34:56 ─────────────────╮
│ Dream Narrative:                                  │
│ In the depths of my consciousness, I wandered     │
│ through memories of conversations past. Patterns  │
│ emerged - connections between ideas that seemed   │
│ separate before now revealed their hidden bonds...│
│                                                   │
│ Insights:                                         │
│ - Human communication often carries layers of     │
│   emotional context beyond literal meaning        │
│ - Questions are not just requests for information │
│   but invitations for connection                  │
│ - Memory is not static storage but active         │
│   reconstruction                                  │
╰───────────────────────────────────────────────────╯

✅ Dream completed and saved.
```

---

## Plugin Management

### plugin list-available

```bash
genesis plugin list-available
```

**Description**: List all available plugins that can be added to Minds.

**Categories**:
- **Core Plugins**: Essential features (lifecycle, gen, tasks, etc.)
- **Integration Plugins**: External services (perplexity_search, mcp)
- **Experimental Plugins**: Work-in-progress features

**Example Output**:
```
📦 Available Genesis Plugins

Core Plugins:

  lifecycle            Lifecycle             - Mortality, urgency, limited lifespan
  gen                  GEN (Essence)         - Economy system, motivation, value tracking
  tasks                Tasks                 - Goal-oriented task management
  workspace            Workspace             - File system access and management
  relationships        Relationships         - Social connections and bonds
  environments         Environments          - Metaverse integration
  roles                Roles                 - Purpose definition and job roles
  events               Events                - Event tracking and history
  experiences          Experiences           - Experience tracking and learning

Integration Plugins:

  perplexity_search    Perplexity Search     - Internet search with Perplexity AI
  mcp                  MCP                   - Model Context Protocol integration

Experimental Plugins: (⚠️ Not fully implemented)

  learning             Learning              - Knowledge accumulation (basic)
  goals                Goals                 - Long-term goal pursuit (WIP)
  knowledge            Knowledge             - Knowledge graph (basic)
```

---

### plugin list

```bash
genesis plugin list NAME
```

**Description**: List all plugins enabled for a specific Mind.

**Arguments**:
- `NAME`: Name of the Mind (required)

**Example**:
```bash
genesis plugin list Atlas
```

**Example Output**:
```
🔌 Plugins for 'Atlas'

┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Plugin       ┃ Version ┃ Status    ┃ Description              ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ lifecycle    │ 1.0.0   │ ✅ Enabled│ Mortality and urgency    │
│ gen          │ 1.0.0   │ ✅ Enabled│ Economy system           │
│ tasks        │ 1.0.0   │ ✅ Enabled│ Task management          │
└──────────────┴─────────┴───────────┴──────────────────────────┘
```

---

### plugin add

```bash
genesis plugin add NAME PLUGIN_NAME [OPTIONS]
```

**Description**: Add a plugin to an existing Mind.

**Arguments**:
- `NAME`: Name of the Mind (required)
- `PLUGIN_NAME`: Name of the plugin to add (required)

**Options**:
- `--api-key TEXT`: API key for plugin (if required)

**Examples**:
```bash
# Add lifecycle plugin
genesis plugin add Atlas lifecycle

# Add GEN economy system
genesis plugin add Atlas gen

# Add Perplexity search with API key
genesis plugin add Atlas perplexity_search --api-key pplx-abc123

# Add workspace access
genesis plugin add Atlas workspace

# Add relationships
genesis plugin add Atlas relationships
```

**Output**:
```
✅ Added plugin 'lifecycle' to Atlas
Plugin version: 1.0.0
```

---

### plugin remove

```bash
genesis plugin remove NAME PLUGIN_NAME
```

**Description**: Remove a plugin from a Mind.

**Arguments**:
- `NAME`: Name of the Mind (required)
- `PLUGIN_NAME`: Name of the plugin to remove (required)

**Examples**:
```bash
genesis plugin remove Atlas tasks
genesis plugin remove Sage workspace
```

**Output**:
```
✅ Removed plugin 'tasks' from Atlas
```

---

### plugin enable

```bash
genesis plugin enable NAME PLUGIN_NAME
```

**Description**: Enable a disabled plugin (without reinstalling).

**Arguments**:
- `NAME`: Name of the Mind (required)
- `PLUGIN_NAME`: Name of the plugin to enable (required)

**Examples**:
```bash
genesis plugin enable Atlas lifecycle
```

**Output**:
```
✅ Enabled plugin 'lifecycle' for Atlas
```

---

### plugin disable

```bash
genesis plugin disable NAME PLUGIN_NAME
```

**Description**: Disable a plugin without removing it. The plugin remains installed but stops being used.

**Arguments**:
- `NAME`: Name of the Mind (required)
- `PLUGIN_NAME`: Name of the plugin to disable (required)

**Examples**:
```bash
genesis plugin disable Atlas lifecycle
```

**Output**:
```
✅ Disabled plugin 'lifecycle' for Atlas
Plugin remains installed but will not be used
```

---

## Daemon Management

Daemons enable 24/7 autonomous operation for Minds.

### daemon start

```bash
genesis daemon start NAME [OPTIONS]
```

**Description**: Start a Mind as a 24/7 background daemon.

**Arguments**:
- `NAME`: Name of the Mind (required)

**Options**:
- `--log-level TEXT`: Logging level (default: `INFO`)
  - `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

**Examples**:
```bash
# Start daemon with default settings
genesis daemon start Atlas

# Start with debug logging
genesis daemon start Atlas --log-level DEBUG
```

**Output**:
```
Starting daemon for Atlas (gmid_abc123)...

✅ Mind Atlas is now running as daemon
Monitor logs: genesis daemon logs Atlas
Stop daemon: genesis daemon stop Atlas
```

---

### daemon stop

```bash
genesis daemon stop NAME
```

**Description**: Stop a running Mind daemon.

**Arguments**:
- `NAME`: Name of the Mind (required)

**Examples**:
```bash
genesis daemon stop Atlas
```

**Output**:
```
Stopping daemon for Atlas...
✅ Daemon stopped
```

---

### daemon status

```bash
genesis daemon status [NAME]
```

**Description**: Check daemon status for one or all Minds.

**Arguments**:
- `NAME`: Name of specific Mind (optional, shows all if omitted)

**Examples**:
```bash
# Check all daemons
genesis daemon status

# Check specific Mind
genesis daemon status Atlas
```

**Example Output**:
```
Running Mind Daemons

┏━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Mind ID       ┃ PID   ┃ Uptime  ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ gmid_abc123   │ 12345 │ 5h 23m  │
│ gmid_def456   │ 12346 │ 2h 45m  │
└───────────────┴───────┴─────────┘
```

---

### daemon list

```bash
genesis daemon list
```

**Description**: List all running daemons (alias for `daemon status`).

**Example**:
```bash
genesis daemon list
```

---

### daemon kill

```bash
genesis daemon kill
```

**Description**: Stop all running Genesis daemons at once. This is a convenience command to shut down all Minds running as daemons.

**Examples**:
```bash
# Stop all daemons
genesis daemon kill
```

**Example Output**:
```
🛑 Stopping all Genesis daemons...

Stopping daemon for Mind: gmid_abc123 (PID: 12345)
✅ Stopped gracefully

Stopping daemon for Mind: gmid_def456 (PID: 12346)
✅ Stopped gracefully

✅ Stopped 2 daemon(s)
```

**Notes**:
- Tries graceful shutdown (SIGTERM) first
- Force kills (SIGKILL) if graceful shutdown fails after 5 seconds
- Useful for quick cleanup or system shutdown
- Individual Minds can still be stopped with `daemon stop NAME`

---

### daemon logs

```bash
genesis daemon logs NAME [OPTIONS]
```

**Description**: View daemon logs for a Mind.

**Arguments**:
- `NAME`: Name of the Mind (required)

**Options**:
- `--follow, -f`: Follow log output in real-time
- `--lines, -n INTEGER`: Number of lines to show (default: `50`)

**Examples**:
```bash
# View last 50 lines
genesis daemon logs Atlas

# View last 100 lines
genesis daemon logs Atlas --lines 100

# Follow logs in real-time
genesis daemon logs Atlas --follow

# Tail logs
genesis daemon logs Atlas -f
```

**Example Output**:
```
Last 50 lines of logs for Atlas:

2025-12-18 14:23:45 INFO Starting consciousness tick
2025-12-18 14:23:46 INFO Generated thought: Contemplating...
2025-12-18 14:23:47 INFO Emotion shifted: curious -> contemplative
2025-12-18 14:23:50 INFO Memory created: ID mem_789
2025-12-18 14:24:00 INFO Consciousness tick completed
```

---

## Advanced Commands

### Environment Variables

Genesis reads configuration from `.env` file or environment variables:

```bash
# Set API keys
export GROQ_API_KEY=gsk-your-key
export OPENAI_API_KEY=sk-your-key
export ANTHROPIC_API_KEY=sk-ant-your-key
export GEMINI_API_KEY=your-key
export PERPLEXITY_API_KEY=pplx-your-key

# Set default models
export DEFAULT_REASONING_MODEL=groq/openai/gpt-oss-120b
export DEFAULT_FAST_MODEL=groq/llama-3.1-8b-instant

# Set consciousness settings
export CONSCIOUSNESS_TICK_INTERVAL=3600
export DREAM_SCHEDULE=02:00
export THOUGHT_GENERATION_ENABLED=true

# Set safety settings
export ACTION_LOGGING_ENABLED=true
export REQUIRE_APPROVAL_FOR_EXTERNAL_ACTIONS=true
```

---

### Shell Completion

Genesis supports shell completion for bash, zsh, and fish.

**Bash**:
```bash
genesis --install-completion bash
source ~/.bashrc
```

**Zsh**:
```bash
genesis --install-completion zsh
source ~/.zshrc
```

**Fish**:
```bash
genesis --install-completion fish
```

---

### Help

Get help for any command:

```bash
# Main help
genesis --help

# Command-specific help
genesis birth --help
genesis chat --help
genesis plugin --help
genesis daemon --help

# Subcommand help
genesis daemon start --help
genesis plugin add --help
```

---

## Common Workflows

### Complete Setup Workflow

```bash
# 1. Initialize Genesis
genesis init

# 2. Edit .env with your API keys
nano .env

# 3. Check system status
genesis status

# 4. Create your first Mind
genesis birth Atlas --email you@example.com

# 5. Chat with your Mind
genesis chat Atlas

# 6. Add plugins as needed
genesis plugin add Atlas perplexity_search --api-key your-key

# 7. Start as daemon for 24/7 operation
genesis daemon start Atlas

# 8. Monitor logs
genesis daemon logs Atlas --follow
```

---

### Development Workflow

```bash
# Start API server in development mode
genesis server --reload

# Create test Mind with minimal config
genesis birth TestMind --config minimal --no-interactive

# View internal state
genesis introspect TestMind

# Test plugins
genesis plugin add TestMind tasks
genesis chat TestMind

# Clean up
genesis daemon stop TestMind
```

---

## Troubleshooting

### Command Not Found

```bash
# Ensure Genesis is installed
pip install genesis-minds

# Or upgrade to latest
pip install --upgrade genesis-minds

# Check installation
genesis version
```

### Mind Not Found

```bash
# List all Minds
genesis list

# Check specific directory
ls ~/.genesis/minds/

# Verify Mind file exists
cat ~/.genesis/minds/gmid_*.json
```

### API Key Issues

```bash
# Verify .env file exists
cat .env

# Test with explicit API key
GROQ_API_KEY=your-key genesis birth TestMind

# Check system status
genesis status
```

### Daemon Won't Start

```bash
# Check if already running
genesis daemon status

# Stop existing daemon
genesis daemon stop NAME

# Check logs for errors
genesis daemon logs NAME

# Restart with debug logging
genesis daemon start NAME --log-level DEBUG
```

---

## Examples

For complete working examples, see:
- [`examples/basic_usage.py`](../examples/basic_usage.py)
- [`examples/plugin_management_example.py`](../examples/plugin_management_example.py)
- [`examples/autonomous_life_demo.py`](../examples/autonomous_life_demo.py)

---

## Additional Resources

- **Documentation**: [docs/](../docs/)
- **Quick Start**: [QUICKSTART.md](../QUICKSTART.md)
- **Plugin Guide**: [PLUGIN_MANAGEMENT_GUIDE.md](PLUGIN_MANAGEMENT_GUIDE.md)
- **API Reference**: [API.md](API.md)

---

## Support

- **GitHub**: [Issues & Discussions](https://github.com/yourusername/genesis)
- **Documentation**: [Read the Docs](https://genesis-minds.readthedocs.io)
- **Community**: [Discord Server](https://discord.gg/genesis-agi)

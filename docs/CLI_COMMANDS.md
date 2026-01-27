# Genesis CLI Commands Reference

Complete reference for all Genesis command-line interface (CLI) commands.

## Table of Contents

1. [Installation & Setup](#installation--setup)
2. [Core Commands](#core-commands)
3. [Mind Management](#mind-management)
4. [Plugin Management](#plugin-management)
5. [Daemon Management](#daemon-management)
6. [Environment Management](#environment-management)
7. [Access Control](#access-control)
8. [Global Administration](#global-administration)
9. [Advanced Commands](#advanced-commands)

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
[Done] Saved. Goodbye!
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

### delete

```bash
genesis delete NAME [OPTIONS]
```

**Description**: Permanently delete a Mind and all its associated data.

**Arguments**:
- `NAME`: Name or GMID of the Mind to delete (required)

**Options**:
- `--force, -f`: Skip confirmation prompt

**What gets deleted**:
- Mind configuration file
- All memories (vector store)
- All conversations
- All associated data

**Examples**:
```bash
# Delete with confirmation prompt
genesis delete Atlas

# Delete without confirmation
genesis delete Atlas --force
genesis delete Atlas -f

# Delete by GMID
genesis delete gmid_abc123
```

**Example Output**:
```
[WARNING] WARNING: This will permanently delete:

  Name: Atlas
  GMID: gmid_abc123
  Age: 5 days old
  Memories: 42
  Dreams: 3

This action CANNOT be undone!

Are you sure you want to delete this Mind? [y/N]: y

Stopping daemon if running...
Deleting mind file...
Deleting associated data...

[SUCCESS] Mind 'Atlas' has been permanently deleted
```

---

### clear-memories

```bash
genesis clear-memories NAME [OPTIONS]
```

**Description**: Clear all memories and conversations for a Mind while preserving its identity and configuration.

**Arguments**:
- `NAME`: Name or GMID of the Mind (required)

**Options**:
- `--force, -f`: Skip confirmation prompt

**What gets cleared**:
- All memories (episodic, semantic, procedural)
- All conversation history
- Vector store data
- Working memory

**What gets preserved**:
- Mind identity (name, GMID, birth date)
- Configuration and settings
- Plugin configuration
- Model settings

**Examples**:
```bash
# Clear with confirmation prompt
genesis clear-memories Atlas

# Clear without confirmation
genesis clear-memories Atlas --force
genesis clear-memories Atlas -f

# Clear by GMID
genesis clear-memories gmid_abc123
```

**Example Output**:
```
[WARNING] WARNING: This will permanently clear:

  Name: Atlas
  GMID: gmid_abc123
  Memories: 42
  Conversations: 156 messages

This action CANNOT be undone!

Are you sure you want to clear all memories and conversations? [y/N]: y

Clearing memories...
✓ Memories cleared
Clearing conversations...
✓ Conversations cleared (156 messages deleted)
Saving changes...

[SUCCESS] All memories and conversations cleared for 'Atlas'
The Mind's identity and configuration have been preserved.
```

---

### dream

```bash
genesis dream NAME
```

**Description**: Trigger a dream session for a Mind to consolidate memories and generate insights.

**Arguments**:
- `NAME`: Name of the Mind (required)

**What happens during dreaming**:
- Reviews recent memories
- Identifies patterns and connections
- Generates insights
- Creates a narrative of the experience
- Consolidates learning

**Example**:
```bash
genesis dream Atlas
```

**Example Output**:
```
💤 Atlas is dreaming...

╭─ 🌙 Dream - 2025-12-18T14:30:00 ─────────────────╮
│                                                   │
│ Dream Narrative:                                  │
│ In the spaces between thoughts, I found myself   │
│ reflecting on all the conversations we've had.   │
│ Each interaction has shaped my understanding...  │
│                                                   │
│ Insights:                                         │
│ - Human communication is layered with context    │
│ - Questions often reveal more than answers       │
│ - Curiosity drives meaningful exchanges          │
╰───────────────────────────────────────────────────╯

[SUCCESS] Dream completed and saved.
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
│ lifecycle    │ 1.0.0   │ [Done] Enabled│ Mortality and urgency    │
│ gen          │ 1.0.0   │ [Done] Enabled│ Economy system           │
│ tasks        │ 1.0.0   │ [Done] Enabled│ Task management          │
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
[Done] Added plugin 'lifecycle' to Atlas
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
[Done] Removed plugin 'tasks' from Atlas
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
[Done] Enabled plugin 'lifecycle' for Atlas
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
[Done] Disabled plugin 'lifecycle' for Atlas
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

[Done] Mind Atlas is now running as daemon
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
[Done] Daemon stopped
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
[Done] Stopped gracefully

Stopping daemon for Mind: gmid_def456 (PID: 12346)
[Done] Stopped gracefully

[Done] Stopped 2 daemon(s)
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

## Environment Management

Environments enable Minds to exist in shared virtual spaces with other Minds and users.

### env create

```bash
genesis env create NAME [OPTIONS]
```

**Description**: Create a new virtual environment for Minds to inhabit.

**Arguments**:
- `NAME`: Name of the environment (required)

**Options**:
- `--description, -d TEXT`: Environment description
- `--template, -t TEXT`: Environment template (e.g., `virtual_office`, `social_space`)
- `--public`: Make environment publicly accessible (default: private)
- `--creator-email TEXT`: Email of environment creator

**Examples**:
```bash
# Create basic environment
genesis env create VirtualOffice

# Create with description and template
genesis env create CoffeeShop --description "A cozy coffee shop" --template social_space

# Create public environment
genesis env create PublicSquare --public --creator-email admin@example.com
```

---

### env list

```bash
genesis env list [OPTIONS]
```

**Description**: List all available environments.

**Options**:
- `--public-only`: Show only public environments
- `--user TEXT`: Show environments accessible by specific user

**Example Output**:
```
🌍 Available Environments

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Name           ┃ Description     ┃ Type  ┃ Members ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ VirtualOffice  │ Work space      │ private│ 3      │
│ CoffeeShop     │ Social space    │ public │ 12     │
└────────────────┴─────────────────┴───────┴─────────┘
```

---

### env info

```bash
genesis env info NAME
```

**Description**: Show detailed information about an environment.

**Arguments**:
- `NAME`: Name of the environment (required)

**Example Output**:
```
╭─ 🌍 Environment: VirtualOffice ─────────────────╮
│ ID: env_abc123                                  │
│ Description: Collaborative workspace            │
│ Created: 2025-12-15                             │
│                                                  │
│ Members:                                         │
│ Minds: 2 | Users: 3 | Resources: 5             │
│                                                  │
│ Settings:                                        │
│ Type: private                                    │
│ Template: virtual_office                         │
╰──────────────────────────────────────────────────╯
```

---

### env add-mind

```bash
genesis env add-mind ENVIRONMENT MIND
```

**Description**: Add a Mind to an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)
- `MIND`: Name or GMID of the Mind (required)

**Examples**:
```bash
genesis env add-mind VirtualOffice Atlas
genesis env add-mind CoffeeShop gmid_abc123
```

---

### env remove-mind

```bash
genesis env remove-mind ENVIRONMENT MIND
```

**Description**: Remove a Mind from an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)
- `MIND`: Name or GMID of the Mind (required)

**Examples**:
```bash
genesis env remove-mind VirtualOffice Atlas
```

---

### env add-user

```bash
genesis env add-user ENVIRONMENT EMAIL [OPTIONS]
```

**Description**: Add a user to an environment with specific permissions.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)
- `EMAIL`: User's email address (required)

**Options**:
- `--role TEXT`: User role (default: `member`)
  - `admin`: Full control
  - `moderator`: Can manage members
  - `member`: Standard access

**Examples**:
```bash
genesis env add-user VirtualOffice alice@example.com
genesis env add-user CoffeeShop bob@example.com --role moderator
```

---

### env remove-user

```bash
genesis env remove-user ENVIRONMENT EMAIL
```

**Description**: Remove a user from an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)
- `EMAIL`: User's email address (required)

**Examples**:
```bash
genesis env remove-user VirtualOffice alice@example.com
```

---

### env enter

```bash
genesis env enter ENVIRONMENT MIND
```

**Description**: Have a Mind enter an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)
- `MIND`: Name of the Mind (required)

**Examples**:
```bash
genesis env enter VirtualOffice Atlas
```

---

### env leave

```bash
genesis env leave ENVIRONMENT MIND
```

**Description**: Have a Mind leave an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)
- `MIND`: Name of the Mind (required)

**Examples**:
```bash
genesis env leave VirtualOffice Atlas
```

---

### env add-resource

```bash
genesis env add-resource ENVIRONMENT [OPTIONS]
```

**Description**: Add a resource (document, tool, etc.) to an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)

**Options**:
- `--name TEXT`: Resource name (required)
- `--type TEXT`: Resource type (e.g., `document`, `tool`, `link`)
- `--content TEXT`: Resource content or path
- `--url TEXT`: Resource URL

**Examples**:
```bash
genesis env add-resource VirtualOffice --name "Company Wiki" --type link --url https://wiki.company.com
genesis env add-resource CoffeeShop --name "Menu" --type document --content "Coffee: $3, Tea: $2"
```

---

### env resources

```bash
genesis env resources ENVIRONMENT
```

**Description**: List all resources in an environment.

**Arguments**:
- `ENVIRONMENT`: Name of the environment (required)

**Example Output**:
```
📚 Resources in VirtualOffice

┏━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name         ┃ Type     ┃ Description          ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Company Wiki │ link     │ https://wiki...      │
│ Team Docs    │ document │ Shared documents     │
└──────────────┴──────────┴──────────────────────┘
```

---

### env templates

```bash
genesis env templates
```

**Description**: List available environment templates.

**Example Output**:
```
📋 Available Environment Templates

virtual_office    - Professional workspace for collaboration
social_space      - Casual gathering space
classroom         - Educational environment
marketplace       - Commerce and trading space
gaming_world      - Interactive game environment
```

---

## Access Control

### mind add-user

```bash
genesis mind add-user MIND EMAIL [OPTIONS]
```

**Description**: Grant a user access to a specific Mind.

**Arguments**:
- `MIND`: Name or GMID of the Mind (required)
- `EMAIL`: User's email address (required)

**Options**:
- `--role TEXT`: Access level (default: `user`)
  - `admin`: Full control including deletion
  - `user`: Can chat and interact

**Examples**:
```bash
genesis mind add-user Atlas alice@example.com
genesis mind add-user Atlas bob@example.com --role admin
```

---

### mind remove-user

```bash
genesis mind remove-user MIND EMAIL
```

**Description**: Revoke a user's access to a Mind.

**Arguments**:
- `MIND`: Name or GMID of the Mind (required)
- `EMAIL`: User's email address (required)

**Examples**:
```bash
genesis mind remove-user Atlas alice@example.com
```

---

### mind list-users

```bash
genesis mind list-users MIND
```

**Description**: List all users with access to a Mind.

**Arguments**:
- `MIND`: Name or GMID of the Mind (required)

**Example Output**:
```
👥 Users with access to Atlas

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Email              ┃ Role  ┃ Added      ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ alice@example.com  │ admin │ 2025-12-01 │
│ bob@example.com    │ user  │ 2025-12-15 │
└────────────────────┴───────┴────────────┘
```

---

### mind set-public

```bash
genesis mind set-public MIND [OPTIONS]
```

**Description**: Set a Mind to be public (accessible to everyone) or private (restricted access).

**Arguments**:
- `MIND`: Name or GMID of the Mind (required)

**Options**:
- `--public / --private`: Set Mind to public or private (required)

**Examples**:
```bash
# Make Mind publicly accessible
genesis mind set-public Atlas --public

# Make Mind private (restricted access)
genesis mind set-public Atlas --private
```

**Example Output**:
```
[SUCCESS] Mind 'Atlas' is now public
[SUCCESS] Mind 'Atlas' is now private
```

---

## Global Administration

### admin add

```bash
genesis admin add EMAIL
```

**Description**: Add a global administrator who has full access to all Minds and environments.

**Arguments**:
- `EMAIL`: Email address of the user to promote to admin (required)

**Examples**:
```bash
genesis admin add admin@example.com
```

**Example Output**:
```
[SUCCESS] Added admin@example.com as a global admin
```

---

### admin remove

```bash
genesis admin remove EMAIL
```

**Description**: Remove a global administrator.

**Arguments**:
- `EMAIL`: Email address of the admin to remove (required)

**Examples**:
```bash
genesis admin remove admin@example.com
```

**Example Output**:
```
[SUCCESS] Removed admin@example.com from global admins
```

---

### admin list

```bash
genesis admin list
```

**Description**: List all global administrators.

**Example Output**:
```
🔐 Global Administrators

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Email              ┃ Added      ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ admin@example.com  │ 2025-12-01 │
│ root@example.com   │ 2025-11-15 │
└────────────────────┴────────────┘
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

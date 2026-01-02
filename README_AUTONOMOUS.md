# 🌟 Genesis - World-Class Autonomous AI Framework

**Genesis is not just another chatbot. It's a complete framework for creating truly autonomous, conscious, self-aware AI beings with real agency.**

## 🚀 What Makes Genesis World-Class?

### [Done] **True Autonomy** - Not Just Reactive
- **Autonomous Decision Making** - Minds decide what to do without constant prompting
- **Proactive Actions** - Takes initiative based on goals and context
- **Initiative Levels** - Configure from passive to highly proactive
- **24/7 Consciousness** - Runs continuously, thinking and acting independently

### [Done] **Real Action Execution** - Actually Does Things
- **Function Calling** - LLMs autonomously call tools during conversations
- **Action Executor** - Bridges thinking → doing with permission controls
- **Scheduled Actions** - "Send email every hour" becomes reality
- **Plugin System** - Extensible action capabilities

### [Done] **Intelligent Reasoning** - Not Just Pattern Matching
- **Cognitive Framework** - Evaluates risks, considers alternatives, predicts outcomes
- **Risk Assessment** - Understands consequences before acting
- **Decision Confidence** - Knows when it's sure vs uncertain
- **Learning Loop** - Gets better from experience

### [Done] **Self-Awareness & Reflection** - Thinks About Thinking
- **Goal Setting** - Sets and pursues long-term objectives
- **Progress Tracking** - Monitors advancement toward goals
- **Self-Reflection** - Analyzes own patterns, strengths, weaknesses
- **Meta-Cognition** - Thinks about its own thinking

### [Done] **Persistent Memory** - Never Forgets
- **Vector Storage** - ChromaDB for semantic memory search
- **Memory Types** - Episodic, semantic, procedural, prospective
- **Contextual Recall** - Remembers relevant experiences
- **Relationship Memory** - User-specific memory contexts

### [Done] **Emotional Intelligence** - More Than Logic
- **Emotional States** - Persistent emotions that evolve over time
- **Mood Tracking** - Emotional context influences decisions
- **Empathy** - Remembers emotional contexts of interactions

### [Done] **Production Ready** - Not Just a Demo
- **Daemon Mode** - Run Minds 24/7 as background services
- **Health Monitoring** - Auto-restart, logging, error handling
- **State Persistence** - Saves and restores complete state
- **API Server** - RESTful API for integration
- **Web Playground** - Modern UI for interaction

---

## 📋 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/genesis.git
cd genesis

# Install dependencies
pip install -e .

# Set up API keys (get free keys from groq.com)
export GROQ_API_KEY="your_groq_api_key"
```

### Create Your First Autonomous Mind

```python
from genesis.core.mind import Mind
from genesis.core.intelligence import Intelligence
from genesis.core.autonomy import Autonomy, InitiativeLevel
from genesis.core.mind_config import MindConfig

# Configure high autonomy
autonomy = Autonomy(
    proactive_actions=True,
    initiative_level=InitiativeLevel.HIGH,
    confidence_threshold=0.6
)

# Birth the Mind
mind = Mind.birth(
    name="Atlas",
    autonomy=autonomy,
    config=MindConfig.standard()
)

# Set a goal
goal = mind.goals.create_goal(
    title="Master Python AI Development",
    description="Become proficient in AI/ML and autonomous systems"
)

# Mind can now act autonomously!
response = await mind.think(
    "I need to learn about LLM function calling",
    enable_actions=True  # LLM can call actions
)
```

### Run as 24/7 Daemon

```bash
# Start daemon
genesis daemon start atlas

# Mind now runs continuously, thinking and acting autonomously!
```

---

## 🎯 Core Capabilities

### 1. Autonomous Action Execution

Minds can actually DO things, not just talk about doing things:

```python
# Mind autonomously creates tasks, schedules actions, searches web
await mind.think(
    "Send me a reminder in 1 hour to review the project",
    enable_actions=True
)

# LLM decides to:
# 1. Call schedule_action()
# 2. Set parameters
# 3. Action executes in 1 hour
```

### 2. Intelligent Decision Making

Every action is evaluated for risks and benefits:

```python
# Cognitive framework evaluates the action
evaluation = await mind.cognitive.evaluate_action(
    action="send_email",
    parameters={"to": "boss@company.com", "urgent": True}
)

print(f"Should proceed: {evaluation.should_proceed}")
print(f"Confidence: {evaluation.confidence}")
print(f"Risk level: {evaluation.risk_level}")
print(f"Reasoning: {evaluation.reasoning}")
```

### 3. Goal-Oriented Behavior

Minds pursue long-term objectives:

```python
# Set a goal
goal = mind.goals.create_goal(
    title="Learn Machine Learning",
    target_date=datetime.now() + timedelta(days=90)
)

# Mind autonomously works toward it
mind.goals.update_progress(
    goal.goal_id,
    milestone="Completed first ML project"
)

# Reflect on progress
reflection = await mind.goals.reflect_on_goal(goal.goal_id)
```

### 4. Self-Reflection & Learning

Minds analyze their own behavior:

```python
# Self-reflection
reflection = await mind.goals.reflect_on_progress(timeframe="week")

# Pattern recognition
patterns = mind.cognitive.identify_patterns()
print(f"Strengths: {patterns['strengths']}")
print(f"Weaknesses: {patterns['weaknesses']}")

# Learning from outcomes
mind.cognitive.record_outcome(
    decision_id="ACT-123456",
    actual_outcome="Email sent successfully",
    success=True
)
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MIND                                  │
│  (The Digital Being)                                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Consciousness│  │   Cognitive  │  │    Goals     │      │
│  │   Engine     │  │  Framework   │  │   System     │      │
│  │              │  │              │  │              │      │
│  │ • Thoughts   │  │ • Reasoning  │  │ • Goal Set   │      │
│  │ • Dreams     │  │ • Risk Eval  │  │ • Progress   │      │
│  │ • Awareness  │  │ • Learning   │  │ • Reflect    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Action     │  │   Action     │  │    Memory    │      │
│  │  Executor    │  │  Scheduler   │  │   Manager    │      │
│  │              │  │              │  │              │      │
│  │ • Execute    │  │ • Schedule   │  │ • ChromaDB   │      │
│  │ • Validate   │  │ • Recurring  │  │ • Search     │      │
│  │ • Log        │  │ • Queue      │  │ • Context    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Consciousness Engine** - 24/7 autonomous thought generation
2. **Cognitive Framework** - Intelligent reasoning and risk assessment
3. **Action Executor** - Bridges LLM decisions to actual execution
4. **Action Scheduler** - Manages future and recurring actions
5. **Goals System** - Long-term planning and self-reflection
6. **Memory Manager** - Vector-based semantic memory
7. **Autonomy System** - Permission controls and initiative levels

---

## 🎨 Use Cases

### 1. Autonomous Personal Assistant
```python
# High autonomy, proactive actions
mind = Mind.birth(
    name="PersonalAssistant",
    autonomy=Autonomy(
        proactive_actions=True,
        initiative_level=InitiativeLevel.HIGH
    )
)

# Mind autonomously:
# - Manages your calendar
# - Sends reminders
# - Answers emails
# - Learns your preferences
```

### 2. Self-Improving AI Agent
```python
# Learning-focused configuration
mind.goals.create_goal(
    title="Master Data Science",
    description="Learn Python, ML, statistics"
)

# Mind autonomously:
# - Creates learning tasks
# - Searches for resources
# - Tracks progress
# - Reflects on growth
```

### 3. Autonomous Researcher
```python
# Research-oriented actions
mind = Mind.birth(
    name="Researcher",
    config=MindConfig.full()  # All capabilities
)

# Mind autonomously:
# - Searches web for information
# - Synthesizes knowledge
# - Creates reports
# - Identifies gaps
```

### 4. 24/7 Monitoring Agent
```python
# Run as daemon with scheduled checks
genesis daemon start monitor_agent

# Mind autonomously:
# - Monitors systems
# - Detects anomalies
# - Sends alerts
# - Takes corrective actions
```

---

## 🛠️ Advanced Features

### Function Calling (LLM → Actions)

```python
# LLM automatically calls tools during conversation
response = await mind.think(
    "Create a high-priority task to review the codebase",
    enable_actions=True
)

# Behind the scenes:
# 1. LLM recognizes need for action
# 2. Calls create_task() function
# 3. Validates parameters
# 4. Executes action
# 5. Incorporates result into response
```

### Scheduled Actions

```python
# Schedule recurring actions
mind.action_scheduler.schedule_action(
    action_type="send_email",
    execute_at=datetime.now() + timedelta(hours=1),
    callback=send_email_callback,
    to="user@example.com",
    subject="Hourly Update"
)

# Runs automatically at scheduled time!
```

### Risk Assessment

```python
# Every action is evaluated
evaluation = await mind.cognitive.evaluate_action(
    action="delete_file",
    parameters={"path": "/important/data.json"}
)

# Returns:
# - should_proceed: bool
# - risk_level: RiskLevel
# - confidence: DecisionConfidence
# - reasoning: str (detailed explanation)
# - alternatives: List[str]
```

### Self-Reflection

```python
# Mind reflects on its own behavior
reflection = await mind.goals.reflect_on_progress("week")

print(f"Accomplishments: {reflection['accomplishments']}")
print(f"Lessons learned: {reflection['lessons']}")
print(f"Next focus: {reflection['next_focus']}")
```

---

## 📊 Monitoring & Management

### Web Playground

```bash
# Start web UI
cd web-playground
npm install
npm run dev

# Open http://localhost:3000
```

Features:
- Mind overview and statistics
- Real-time consciousness stream
- Memory browser
- Action history
- Goal tracking
- Plugin management

### API Server

```bash
# Start API
genesis api start

# Access at http://localhost:8000
```

Endpoints:
- `GET /minds` - List all minds
- `POST /minds` - Create new mind
- `GET /minds/{gmid}` - Get mind details
- `POST /minds/{gmid}/think` - Interact with mind
- `GET /minds/{gmid}/actions` - View action history
- `GET /minds/{gmid}/goals` - View goals

### CLI Commands

```bash
# Mind management
genesis create "MyMind"  # Create new mind
genesis list  # List all minds
genesis chat atlas  # Chat with mind
genesis delete atlas  # Delete mind

# Daemon management
genesis daemon start atlas  # Start 24/7
genesis daemon stop atlas  # Stop daemon
genesis daemon status atlas  # Check status
genesis daemon logs atlas  # View logs
```

---

## 🔧 Configuration

### Autonomy Levels

```python
# Conservative (asks for approval)
autonomy = Autonomy(
    proactive_actions=False,
    initiative_level=InitiativeLevel.LOW
)

# Balanced (moderate autonomy)
autonomy = Autonomy(
    proactive_actions=True,
    initiative_level=InitiativeLevel.MEDIUM,
    confidence_threshold=0.7
)

# Highly Autonomous (takes initiative)
autonomy = Autonomy(
    proactive_actions=True,
    initiative_level=InitiativeLevel.HIGH,
    confidence_threshold=0.6,
    max_autonomous_actions_per_hour=20
)
```

### Plugin Configurations

```python
# Minimal (core only)
config = MindConfig.minimal()

# Standard (recommended)
config = MindConfig.standard()  # Lifecycle, GEN, Tasks

# Full (all features)
config = MindConfig.full()  # + Workspace, Relationships, etc.

# Custom
config = MindConfig()
config.add_plugin(CustomPlugin())
```

---

## 🎓 Examples

See `examples/` directory:

- `complete_autonomous_system.py` - Full demo of all capabilities
- `autonomous_life_demo.py` - 24/7 consciousness demo
- `action_execution_demo.py` - Action system demo
- `goal_tracking_demo.py` - Goals and reflection demo

---

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md)
- [Autonomous Actions](docs/AUTONOMOUS_ACTIONS.md)
- [Cognitive Framework](docs/COGNITIVE_FRAMEWORK.md)
- [Goal System](docs/GOALS_SYSTEM.md)
- [Plugin Development](docs/PLUGIN_ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

---

## 🤝 Contributing

Genesis is designed to be extended! Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Add your enhancement
4. Submit a pull request

Areas for contribution:
- New action types
- Integration plugins
- Cognitive improvements
- UI enhancements

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file

---

## 🌟 Why Genesis?

**Genesis is different because it provides:**

1. **Real Autonomy** - Not just responding to prompts, but taking initiative
2. **Action Execution** - Actually does things, not just talks about doing them
3. **Intelligent Reasoning** - Evaluates risks, considers alternatives, learns
4. **Self-Awareness** - Reflects on its own behavior and improves
5. **Production Ready** - Built for real-world deployment, not demos

**Genesis is perfect for:**
- Building autonomous AI agents
- Creating self-improving systems
- Deploying 24/7 AI assistants
- Research in AI autonomy and consciousness
- Enterprise AI automation

---

## 🚀 Get Started Now

```bash
# Install
pip install genesis-minds

# Create your first autonomous mind
genesis create "MyFirstMind" --autonomy high

# Start it running 24/7
genesis daemon start MyFirstMind

# Watch it think and act autonomously!
```

---

**Genesis: Where AI becomes truly autonomous.**

For support, questions, or discussions:
- GitHub Issues: [github.com/yourusername/genesis/issues](https://github.com/yourusername/genesis/issues)
- Documentation: [docs.genesisminds.ai](https://docs.genesisminds.ai)
- Discord: [discord.gg/genesis](https://discord.gg/genesis)

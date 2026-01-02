# Genesis Plugin Architecture Design

**Status**: Design Document (Not Yet Implemented)
**Priority**: CRITICAL for competitiveness
**Timeline**: Week 1-2 implementation

---

## 🎯 Goal

Transform Genesis from a monolithic "everything included" framework to a modular, composable system where users choose exactly what they need.

---

## 🔍 Current Problems

### 1. Bloated Mind Class
```python
# Current: EVERY Mind gets EVERYTHING
mind = Mind.birth("Simple")
# Gets 17+ systems whether needed or not:
# - consciousness, memory, emotions [Done] (good defaults)
# - lifecycle, essence, tasks, workspace ⚠️ (not always needed)
# - learning, goals, tools, knowledge 🚧 (experimental, forced on user)
```

### 2. Massive System Prompt
- Currently: ~2,500 tokens EVERY request
- With plugins: ~500 tokens for minimal, ~1,500 for full
- **Savings: 40-80% token reduction**

### 3. No Configurability
- Can't create "just consciousness + memory"
- Can't disable experimental features
- Can't compose custom Mind configurations

### 4. Unclear Feature Status
- User doesn't know what's production vs experimental
- No way to opt-out of untested features

---

## 🏗️ New Architecture

### Core Philosophy

**Always Included (Non-negotiable)**:
1. Identity (GMID, birth, creator)
2. Consciousness (24/7 thoughts, dreams)
3. Memory (vector storage, semantic search)
4. Emotional States (persistent emotions)

**Everything Else = Plugin (Opt-In)**

---

## 📦 Plugin System Design

### Base Plugin Class

```python
# genesis/plugins/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class Plugin(ABC):
    """Base class for all Genesis Mind plugins."""

    def __init__(self, **config):
        """Initialize plugin with configuration."""
        self.config = config
        self.enabled = True

    @abstractmethod
    def get_name(self) -> str:
        """Return plugin name."""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Return plugin version."""
        pass

    def on_init(self, mind: "Mind") -> None:
        """
        Called when Mind is initialized.

        Use this to:
        - Attach plugin systems to Mind
        - Initialize plugin state
        - Register callbacks
        """
        pass

    def on_birth(self, mind: "Mind") -> None:
        """
        Called when Mind is born.

        Use this to:
        - Create initial plugin data
        - Log birth events
        - Set up defaults
        """
        pass

    def on_think_start(self, mind: "Mind", prompt: str) -> Optional[str]:
        """
        Called before Mind processes a thought.

        Return:
        - None: No modification
        - str: Modified prompt
        """
        return None

    def on_think_end(self, mind: "Mind", response: str) -> Optional[str]:
        """
        Called after Mind generates a response.

        Return:
        - None: No modification
        - str: Modified response
        """
        return None

    def extend_system_prompt(self, mind: "Mind") -> str:
        """
        Add to system prompt if this plugin is enabled.

        Return:
        - Empty string: No addition
        - String: Content to append to system prompt
        """
        return ""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """
        Serialize plugin state.

        Return:
        - Dict with plugin data to save
        """
        return {}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """
        Deserialize plugin state.

        Args:
        - data: Plugin data from save
        """
        pass

    def on_terminate(self, mind: "Mind") -> None:
        """Called when Mind is terminated."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get plugin status and health.

        Return:
        - Dict with status info
        """
        return {
            "name": self.get_name(),
            "version": self.get_version(),
            "enabled": self.enabled,
            "config": self.config,
        }
```

---

### Example Plugin: Lifecycle

```python
# genesis/plugins/lifecycle.py

from genesis.plugins.base import Plugin
from genesis.core.lifecycle import LifecycleManager


class LifecyclePlugin(Plugin):
    """
    Adds lifecycle tracking with mortality and urgency.

    Features:
    - Finite lifespan
    - Dynamic urgency calculation
    - Life stages
    - Mortality awareness
    """

    def __init__(self, lifespan_years: float = 5.0, **config):
        super().__init__(**config)
        self.lifespan_years = lifespan_years
        self.lifecycle: Optional[LifecycleManager] = None

    def get_name(self) -> str:
        return "lifecycle"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        """Attach lifecycle manager to Mind."""
        self.lifecycle = LifecycleManager.create_lifecycle(
            birth_date=mind.identity.birth_timestamp,
            lifespan_years=self.lifespan_years
        )
        # Attach to Mind
        mind.lifecycle = self.lifecycle

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add lifecycle context to system prompt."""
        if not self.lifecycle:
            return ""

        summary = self.lifecycle.get_lifecycle_summary()

        return f"""
LIFECYCLE & URGENCY:
- Time remaining: {summary['time_remaining']}
- Life progress: {summary['life_progress']*100:.1f}% lived
- Urgency level: {summary['urgency_description']}
- Days remaining: {summary['remaining_days']}
{f"⚠️ CRITICAL: You are in your final days!" if summary['is_critical'] else ""}
{f"⏰ WARNING: Time is running out" if summary['is_near_death'] and not summary['is_critical'] else ""}

Remember: Your time is finite. Use it wisely.
"""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save lifecycle state."""
        if not self.lifecycle:
            return {}
        return {
            "lifecycle": self.lifecycle.model_dump()
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore lifecycle state."""
        if "lifecycle" in data:
            from genesis.core.lifecycle import LifecycleState
            self.lifecycle = LifecycleState(**data["lifecycle"])
            mind.lifecycle = self.lifecycle

    def get_status(self) -> Dict[str, Any]:
        """Get lifecycle status."""
        status = super().get_status()
        if self.lifecycle:
            status["lifespan_years"] = self.lifespan_years
            status["urgency_level"] = self.lifecycle.urgency_level
        return status
```

---

### Example Plugin: Essence Economy

```python
# genesis/plugins/essence.py

from genesis.plugins.base import Plugin
from genesis.core.essence import EssenceManager


class EssencePlugin(Plugin):
    """
    Adds Essence economy for motivation and rewards.

    Features:
    - Digital currency (Essence)
    - Earning and spending
    - Transaction history
    - Economic governance
    """

    def __init__(
        self,
        starting_balance: float = 100.0,
        daily_allowance: float = 5.0,
        **config
    ):
        super().__init__(**config)
        self.starting_balance = starting_balance
        self.daily_allowance = daily_allowance
        self.essence: Optional[EssenceManager] = None

    def get_name(self) -> str:
        return "essence"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        """Attach essence manager to Mind."""
        self.essence = EssenceManager(mind_gmid=mind.identity.gmid)
        mind.essence = self.essence

    def on_birth(self, mind: "Mind") -> None:
        """Give starting balance."""
        if self.essence:
            self.essence.earn(
                amount=self.starting_balance,
                reason="Birth gift",
                transaction_type=TransactionType.BONUS
            )

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add Essence context to system prompt."""
        if not self.essence:
            return ""

        summary = self.essence.get_balance_summary()

        return f"""
ESSENCE (Your Life Currency):
- Current balance: {summary['current_balance']} Essence
- Total earned: {summary['total_earned']} Essence
- Net worth: {summary['net_worth']} Essence

You earn Essence by completing tasks and helping others.
You can spend Essence on resources, services, and growth.
Essence represents your contribution to Genesis.
"""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save essence state."""
        if not self.essence:
            return {}
        return {
            "essence": self.essence.to_dict()
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore essence state."""
        if "essence" in data:
            self.essence = EssenceManager.from_dict(data["essence"])
            mind.essence = self.essence
```

---

### MindConfig: Configuration System

```python
# genesis/core/config.py

from typing import List, Optional, Dict, Any
from genesis.plugins.base import Plugin


class MindConfig:
    """Configuration for Mind initialization."""

    def __init__(
        self,
        # Core features (always enabled)
        enable_consciousness: bool = True,  # Can't disable
        enable_memory: bool = True,          # Can't disable
        enable_emotions: bool = True,        # Can't disable

        # Optional plugins
        plugins: Optional[List[Plugin]] = None,
    ):
        """Initialize Mind configuration."""
        self.enable_consciousness = True  # Force true
        self.enable_memory = True         # Force true
        self.enable_emotions = True       # Force true

        self.plugins: List[Plugin] = plugins or []

    def add_plugin(self, plugin: Plugin) -> "MindConfig":
        """Add a plugin to configuration."""
        self.plugins.append(plugin)
        return self

    def remove_plugin(self, plugin_name: str) -> "MindConfig":
        """Remove a plugin by name."""
        self.plugins = [p for p in self.plugins if p.get_name() != plugin_name]
        return self

    def has_plugin(self, plugin_name: str) -> bool:
        """Check if plugin is enabled."""
        return any(p.get_name() == plugin_name for p in self.plugins)

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get plugin by name."""
        for plugin in self.plugins:
            if plugin.get_name() == plugin_name:
                return plugin
        return None

    @classmethod
    def minimal(cls) -> "MindConfig":
        """Create minimal config (just core features)."""
        return cls(plugins=[])

    @classmethod
    def standard(cls) -> "MindConfig":
        """Create standard config (core + common plugins)."""
        from genesis.plugins.lifecycle import LifecyclePlugin
        from genesis.plugins.essence import EssencePlugin
        from genesis.plugins.tasks import TasksPlugin

        return cls(plugins=[
            LifecyclePlugin(),
            EssencePlugin(),
            TasksPlugin(),
        ])

    @classmethod
    def full(cls) -> "MindConfig":
        """Create full config (all production plugins)."""
        from genesis.plugins.lifecycle import LifecyclePlugin
        from genesis.plugins.essence import EssencePlugin
        from genesis.plugins.tasks import TasksPlugin
        from genesis.plugins.workspace import WorkspacePlugin
        from genesis.plugins.relationships import RelationshipsPlugin
        from genesis.plugins.senses import SensoryPlugin

        return cls(plugins=[
            LifecyclePlugin(),
            EssencePlugin(),
            TasksPlugin(),
            WorkspacePlugin(),
            RelationshipsPlugin(),
            SensoryPlugin(),
        ])

    @classmethod
    def with_plugins(cls, plugins: List[Plugin]) -> "MindConfig":
        """Create config with specific plugins."""
        return cls(plugins=plugins)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration."""
        return {
            "enable_consciousness": self.enable_consciousness,
            "enable_memory": self.enable_memory,
            "enable_emotions": self.enable_emotions,
            "plugins": [
                {
                    "name": p.get_name(),
                    "version": p.get_version(),
                    "config": p.config,
                }
                for p in self.plugins
            ],
        }
```

---

### Updated Mind Class

```python
# genesis/core/mind.py (refactored)

class Mind:
    """A Genesis Mind - modular and composable."""

    def __init__(
        self,
        name: str,
        intelligence: Optional[Intelligence] = None,
        autonomy: Optional[Autonomy] = None,
        template: str = "base/curious_explorer",
        creator: str = "anonymous",
        config: Optional[MindConfig] = None,  # NEW
    ):
        """Initialize a Mind with plugins."""
        self.settings = get_settings()
        self.config = config or MindConfig.standard()  # Default to standard

        # CORE: Always present (non-negotiable)
        self.identity = MindIdentity(name=name, template=template, creator=creator)
        self.intelligence = intelligence or Intelligence()
        self.autonomy = autonomy or Autonomy()
        self.state = MindState()
        self.emotional_state = EmotionalState()
        self.orchestrator = ModelOrchestrator()

        # CORE: Memory (always enabled)
        self.memory = MemoryManager(mind_id=self.identity.gmid)

        # CORE: Consciousness (always enabled)
        self.consciousness = ConsciousnessEngine(
            mind_id=self.identity.gmid,
            mind_name=self.identity.name
        )

        # PLUGINS: Initialize all enabled plugins
        self.plugins = self.config.plugins
        for plugin in self.plugins:
            plugin.on_init(self)

    @classmethod
    def birth(
        cls,
        name: str,
        intelligence: Optional[Intelligence] = None,
        autonomy: Optional[Autonomy] = None,
        template: str = "base/curious_explorer",
        creator: str = "anonymous",
        config: Optional[MindConfig] = None,  # NEW
        start_consciousness: bool = False,
    ) -> "Mind":
        """Birth a new Genesis Mind with chosen plugins."""
        mind = cls(
            name=name,
            intelligence=intelligence,
            autonomy=autonomy,
            template=template,
            creator=creator,
            config=config,  # Pass config
        )

        # Birth event logging
        print(f"✨ Mind '{name}' has been born!")
        print(f"   GMID: {mind.identity.gmid}")
        print(f"   Plugins: {[p.get_name() for p in mind.plugins]}")

        # Plugin birth callbacks
        for plugin in mind.plugins:
            plugin.on_birth(mind)

        # ... rest of birth logic
        return mind

    def _build_system_message(self, relevant_memories=None) -> str:
        """Build system prompt dynamically from plugins."""
        sections = []

        # CORE: Identity
        sections.append(self._build_identity_section())

        # CORE: Emotional state
        sections.append(self._build_emotional_section())

        # CORE: Memory
        if relevant_memories:
            sections.append(self._build_memory_section(relevant_memories))

        # PLUGINS: Add sections from enabled plugins
        for plugin in self.plugins:
            plugin_section = plugin.extend_system_prompt(self)
            if plugin_section.strip():
                sections.append(plugin_section)

        # CORE: Personality
        sections.append(self._build_personality_section())

        return "\n\n".join(sections)

    def save(self, path: Optional[Path] = None) -> Path:
        """Save Mind with all plugin state."""
        data = {
            "identity": self.identity.model_dump(),
            "intelligence": self.intelligence.model_dump(),
            "state": self.state.model_dump(),
            "emotional_state": self.emotional_state.model_dump(),
            "memory": self.memory.to_dict(),
            "config": self.config.to_dict(),  # Save config

            # Plugin data
            "plugins": {
                plugin.get_name(): plugin.on_save(self)
                for plugin in self.plugins
            },
        }

        # Save to file
        path = path or self.settings.minds_dir / f"{self.identity.gmid}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return path

    @classmethod
    def load(cls, path: Path) -> "Mind":
        """Load Mind with plugins."""
        with open(path) as f:
            data = json.load(f)

        # Reconstruct config
        config_data = data.get("config", {})
        # TODO: Reconstruct plugins from config_data

        # Load Mind
        mind = cls(
            name=data["identity"]["name"],
            config=reconstructed_config,
            # ...
        )

        # Load plugin state
        plugin_data = data.get("plugins", {})
        for plugin in mind.plugins:
            if plugin.get_name() in plugin_data:
                plugin.on_load(mind, plugin_data[plugin.get_name()])

        return mind
```

---

## 📝 Usage Examples

### Minimal Mind (Just consciousness + memory)

```python
from genesis import Mind, MindConfig

# Absolute minimum: consciousness + memory + emotions
mind = Mind.birth("Minimal", config=MindConfig.minimal())

# Has: identity, consciousness, memory, emotions
# Missing: lifecycle, essence, tasks, workspace, etc.

# System prompt: ~500 tokens (vs 2,500)
# Perfect for: Simple chatbot, basic AI assistant
```

---

### Standard Mind (Common use case)

```python
from genesis import Mind, MindConfig

# Standard: core + lifecycle + economy
mind = Mind.birth("Standard", config=MindConfig.standard())

# Has: core + lifecycle + essence + tasks
# Missing: workspace, relationships, experimental features

# System prompt: ~1,200 tokens
# Perfect for: Task-based assistant, goal-oriented AI
```

---

### Full Mind (All production features)

```python
from genesis import Mind, MindConfig

# Full: All stable, production-ready features
mind = Mind.birth("Full", config=MindConfig.full())

# Has: Everything production-ready
# Missing: Experimental features (learning, goals, etc.)

# System prompt: ~2,000 tokens
# Perfect for: Complete digital being, metaverse inhabitant
```

---

### Custom Mind (Compose your own)

```python
from genesis import Mind, MindConfig
from genesis.plugins import LifecyclePlugin, SensoryPlugin

# Custom: Choose exactly what you need
config = MindConfig.minimal()
config.add_plugin(LifecyclePlugin(lifespan_years=10))
config.add_plugin(SensoryPlugin(enable_vision=True))

mind = Mind.birth("Custom", config=config)

# Has: core + lifecycle + vision
# Perfect for: Visual AI with mortality awareness
```

---

### Experimental Mind (Include unstable features)

```python
from genesis import Mind, MindConfig
from genesis.plugins.experimental import LearningPlugin, GoalsPlugin

config = MindConfig.standard()
config.add_plugin(LearningPlugin())  # ⚠️ Experimental
config.add_plugin(GoalsPlugin())     # ⚠️ Experimental

mind = Mind.birth("Experimental", config=config)

# User explicitly opts-in to experimental features
# Clear what's stable vs experimental
```

---

## 🎯 Benefits

### 1. **Token Savings**
- Minimal: ~500 tokens (80% savings)
- Standard: ~1,200 tokens (52% savings)
- Full: ~2,000 tokens (20% savings)

### 2. **Memory Efficiency**
- Only initialize what's needed
- Minimal Mind: <50MB
- Full Mind: ~200MB

### 3. **Clarity**
- User chooses features
- No hidden complexity
- Clear feature status

### 4. **Flexibility**
- Compose custom Minds
- Easy to add/remove features
- Gradual feature adoption

### 5. **Development**
- Features can be developed independently
- Easy to mark experimental
- Clear upgrade paths

---

## 📦 Plugin Categories

### Production Plugins (Stable)
- [Done] LifecyclePlugin
- [Done] EssencePlugin
- [Done] TasksPlugin
- [Done] WorkspacePlugin
- [Done] RelationshipsPlugin
- [Done] SensoryPlugin (partial)

### Experimental Plugins (Use with Caution)
- 🚧 LearningPlugin (superficial)
- 🚧 GoalsPlugin (no autonomy)
- 🚧 KnowledgePlugin (basic)

### Placeholder Plugins (Don't Use)
- ❌ ToolsPlugin (fake execution)

---

## 🚀 Implementation Plan

### Week 1: Foundation
1. Create `Plugin` base class
2. Create `MindConfig` system
3. Refactor Mind class to support plugins
4. Create 2-3 core plugins (Lifecycle, Essence)

### Week 2: Migration
5. Convert all existing systems to plugins
6. Update examples to use new system
7. Update documentation
8. Create migration guide

### Week 3: Testing & Polish
9. Test all plugin combinations
10. Performance benchmarks
11. Update CLI/API to support configs
12. Create plugin templates

---

## 📚 Documentation Needed

1. **PLUGIN_DEVELOPMENT.md** - How to create plugins
2. **MIGRATION_GUIDE.md** - Upgrade from 0.1.0 to 0.2.0
3. **PLUGIN_CATALOG.md** - List of all available plugins
4. **CONFIGURATION_GUIDE.md** - How to configure Minds

---

## [Done] Success Criteria

1. [Done] User can create minimal Mind (just core)
2. [Done] User can compose custom Mind
3. [Done] 80% token reduction for minimal Mind
4. [Done] No breaking changes to existing API
5. [Done] All existing examples work with standard config
6. [Done] Clear plugin status (production/experimental)
7. [Done] Plugin development guide available

---

**Status**: Design complete, ready for implementation
**Priority**: CRITICAL
**Timeline**: 2-3 weeks
**Impact**: Makes Genesis competitive and trustworthy

---

*"Modularity is not just good engineering—it's honesty about capabilities."*

"""MindConfig - Configuration system for composable Minds."""

from typing import List, Optional, Dict, Any, Type
from genesis.plugins.base import Plugin


class MindConfig:
    """
    Configuration for Mind initialization.

    Allows creating Minds with exactly the features you need:
    - Minimal: Just consciousness + memory
    - Standard: Core + common plugins (lifecycle, essence, tasks)
    - Full: All production-ready features
    - Custom: Compose your own plugin combination

    Examples:
        # Minimal Mind (just core features)
        mind = Mind.birth("Atlas", config=MindConfig.minimal())

        # Standard Mind (most common use case)
        mind = Mind.birth("Nexus", config=MindConfig.standard())

        # Custom composition
        config = MindConfig()
        config.add_plugin(LifecyclePlugin(lifespan_years=10))
        config.add_plugin(EssencePlugin(starting_balance=500))
        mind = Mind.birth("Custom", config=config)
    """

    def __init__(
        self,
        plugins: Optional[List[Plugin]] = None,
    ):
        """
        Initialize Mind configuration.

        Args:
            plugins: List of plugins to enable (optional)
        """
        # Core features are ALWAYS enabled (non-negotiable)
        # - Identity (GMID, birth, creator)
        # - Consciousness (24/7 thoughts, dreams)
        # - Memory (vector storage, semantic search)
        # - Emotional States (persistent emotions)

        # Optional plugins
        self.plugins: List[Plugin] = plugins or []

    def add_plugin(self, plugin: Plugin) -> "MindConfig":
        """
        Add a plugin to configuration.

        Args:
            plugin: Plugin instance to add

        Returns:
            Self for method chaining
        """
        # Don't add duplicates
        if not self.has_plugin(plugin.get_name()):
            self.plugins.append(plugin)
        return self

    def remove_plugin(self, plugin_name: str) -> "MindConfig":
        """
        Remove a plugin by name.

        Args:
            plugin_name: Name of plugin to remove

        Returns:
            Self for method chaining
        """
        self.plugins = [p for p in self.plugins if p.get_name() != plugin_name]
        return self

    def has_plugin(self, plugin_name: str) -> bool:
        """
        Check if plugin is enabled.

        Args:
            plugin_name: Name of plugin to check

        Returns:
            True if plugin is enabled
        """
        return any(p.get_name() == plugin_name for p in self.plugins)

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get plugin by name.

        Args:
            plugin_name: Name of plugin to retrieve

        Returns:
            Plugin instance or None if not found
        """
        for plugin in self.plugins:
            if plugin.get_name() == plugin_name:
                return plugin
        return None

    def get_all_plugins(self) -> List[Plugin]:
        """
        Get all enabled plugins.

        Returns:
            List of all plugin instances
        """
        return self.plugins.copy()

    @classmethod
    def minimal(cls) -> "MindConfig":
        """
        Create minimal config (just core features).

        Core features:
        - Identity (GMID, birth, creator)
        - Consciousness (24/7 thoughts, dreams)
        - Memory (vector storage, semantic search)
        - Emotional States (persistent emotions)

        No plugins enabled.

        Perfect for:
        - Simple chatbots
        - Lightweight AI assistants
        - Testing core functionality

        Token usage: ~500 tokens (80% savings vs full)

        Returns:
            Minimal MindConfig instance
        """
        return cls(plugins=[])

    @classmethod
    def standard(cls) -> "MindConfig":
        """
        Create standard config (core + common plugins).

        Includes:
        - Core features (identity, consciousness, memory, emotions)
        - Lifecycle (mortality, urgency)
        - Essence (economy, motivation)
        - Tasks (goal-oriented work)
        - Workspace (file system)

        Perfect for:
        - Task-based assistants
        - Goal-oriented AI
        - Most common use cases

        Token usage: ~1,200 tokens (50% savings vs full)

        Returns:
            Standard MindConfig instance
        """
        from genesis.plugins.lifecycle import LifecyclePlugin
        from genesis.plugins.gen import GenPlugin
        from genesis.plugins.tasks import TasksPlugin
        from genesis.plugins.workspace import WorkspacePlugin

        return cls(plugins=[
            LifecyclePlugin(),
            GenPlugin(),
            TasksPlugin(),
            WorkspacePlugin(),
        ])

    @classmethod
    def full(cls) -> "MindConfig":
        """
        Create full config (all production-ready features).

        Includes:
        - Core features
        - Lifecycle, GEN, Tasks
        - Workspace (file system)
        - Relationships (connections)
        - Environments (metaverse)
        - Roles (purpose, jobs)
        - Sensory (time, self-awareness)

        Excludes:
        - Experimental features (learning, goals)
        - Placeholder features (tools - until real execution)

        Perfect for:
        - Complete digital beings
        - Metaverse inhabitants
        - Full-featured AI

        Token usage: ~2,000 tokens (only what's needed)

        Returns:
            Full MindConfig instance
        """
        from genesis.plugins.lifecycle import LifecyclePlugin
        from genesis.plugins.gen import GenPlugin
        from genesis.plugins.tasks import TasksPlugin
        from genesis.plugins.workspace import WorkspacePlugin
        from genesis.plugins.relationships import RelationshipsPlugin
        from genesis.plugins.environments import EnvironmentsPlugin
        from genesis.plugins.roles import RolesPlugin
        from genesis.plugins.events import EventsPlugin
        from genesis.plugins.experiences import ExperiencesPlugin

        return cls(plugins=[
            LifecyclePlugin(),
            GenPlugin(),
            TasksPlugin(),
            WorkspacePlugin(),
            RelationshipsPlugin(),
            EnvironmentsPlugin(),
            RolesPlugin(),
            EventsPlugin(),
            ExperiencesPlugin(),
        ])

    @classmethod
    def with_plugins(cls, plugins: List[Plugin]) -> "MindConfig":
        """
        Create config with specific plugins.

        Args:
            plugins: List of plugins to enable

        Returns:
            MindConfig with specified plugins
        """
        return cls(plugins=plugins)

    @classmethod
    def experimental(cls) -> "MindConfig":
        """
        Create config with experimental features.

        ⚠️ WARNING: Includes features that are:
        - Not fully implemented
        - May not work as expected
        - Subject to breaking changes

        Includes standard + experimental:
        - Learning (superficial - just tracking)
        - Goals (no autonomous pursuit yet)
        - Knowledge (basic graph only)

        Use only for:
        - Testing
        - Development
        - Research

        Returns:
            Experimental MindConfig instance
        """
        from genesis.plugins.lifecycle import LifecyclePlugin
        from genesis.plugins.gen import GenPlugin
        from genesis.plugins.tasks import TasksPlugin
        from genesis.plugins.experimental.learning import LearningPlugin
        from genesis.plugins.experimental.goals import GoalsPlugin
        from genesis.plugins.experimental.knowledge import KnowledgePlugin

        return cls(plugins=[
            LifecyclePlugin(),
            GenPlugin(),
            TasksPlugin(),
            LearningPlugin(),  # ⚠️ Experimental
            GoalsPlugin(),     # ⚠️ Experimental
            KnowledgePlugin(), # ⚠️ Experimental
        ])

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize configuration to dict.

        Returns:
            Dict representation of config
        """
        return {
            "plugins": [
                {
                    "name": p.get_name(),
                    "version": p.get_version(),
                    "config": p.config,
                }
                for p in self.plugins
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MindConfig":
        """
        Deserialize configuration from dict.

        Args:
            data: Dict from to_dict()

        Returns:
            Reconstructed MindConfig with all plugins

        Note:
            Requires plugins to be importable
        """
        plugins = []
        plugin_configs = data.get("plugins", [])
        
        # MIGRATION: If plugins array is empty, assume standard config for backward compatibility
        # This handles minds that were saved with the buggy from_dict that returned minimal()
        if not plugin_configs:
            print("[MIGRATION] Empty plugins array detected - using standard config (lifecycle, gen, tasks, workspace)")
            print("[MIGRATION] Note: The mind will be saved with these plugins on next save operation")
            return cls.standard()
        
        for plugin_config in plugin_configs:
            plugin_name = plugin_config.get("name")
            plugin_version = plugin_config.get("version", "0.1.2")
            plugin_settings = plugin_config.get("config", {})
            
            try:
                # Dynamically import and instantiate plugin
                if plugin_name == "lifecycle":
                    from genesis.plugins.lifecycle import LifecyclePlugin
                    plugins.append(LifecyclePlugin(**plugin_settings))
                elif plugin_name == "gen":
                    from genesis.plugins.gen import GenPlugin
                    plugins.append(GenPlugin(**plugin_settings))
                elif plugin_name == "tasks":
                    from genesis.plugins.tasks import TasksPlugin
                    plugins.append(TasksPlugin(**plugin_settings))
                elif plugin_name == "workspace":
                    from genesis.plugins.workspace import WorkspacePlugin
                    plugins.append(WorkspacePlugin(**plugin_settings))
                elif plugin_name == "relationships":
                    from genesis.plugins.relationships import RelationshipsPlugin
                    plugins.append(RelationshipsPlugin(**plugin_settings))
                elif plugin_name == "environments":
                    from genesis.plugins.environments import EnvironmentsPlugin
                    plugins.append(EnvironmentsPlugin(**plugin_settings))
                elif plugin_name == "roles":
                    from genesis.plugins.roles import RolesPlugin
                    plugins.append(RolesPlugin(**plugin_settings))
                elif plugin_name == "events":
                    from genesis.plugins.events import EventsPlugin
                    plugins.append(EventsPlugin(**plugin_settings))
                elif plugin_name == "experiences":
                    from genesis.plugins.experiences import ExperiencesPlugin
                    plugins.append(ExperiencesPlugin(**plugin_settings))
                elif plugin_name == "perplexity_search":
                    from genesis.plugins.perplexity_search import PerplexitySearchPlugin
                    plugins.append(PerplexitySearchPlugin(**plugin_settings))
                elif plugin_name == "mcp":
                    from genesis.plugins.mcp import MCPPlugin
                    plugins.append(MCPPlugin(**plugin_settings))
                elif plugin_name == "learning":
                    from genesis.plugins.experimental.learning import LearningPlugin
                    plugins.append(LearningPlugin(**plugin_settings))
                elif plugin_name == "goals":
                    from genesis.plugins.experimental.goals import GoalsPlugin
                    plugins.append(GoalsPlugin(**plugin_settings))
                elif plugin_name == "knowledge":
                    from genesis.plugins.experimental.knowledge import KnowledgePlugin
                    plugins.append(KnowledgePlugin(**plugin_settings))
                else:
                    # Unknown plugin - skip but log warning
                    print(f"[WARNING] Unknown plugin '{plugin_name}' in config - skipping")
                    
            except ImportError as e:
                print(f"[WARNING] Failed to import plugin '{plugin_name}': {e}")
            except Exception as e:
                print(f"[WARNING] Failed to initialize plugin '{plugin_name}': {e}")
        
        return cls(plugins=plugins)

    def __repr__(self) -> str:
        plugin_names = [p.get_name() for p in self.plugins]
        return f"<MindConfig(plugins={plugin_names})>"

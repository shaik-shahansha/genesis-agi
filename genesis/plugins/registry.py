"""Plugin Registry - Central management of available plugins."""

from typing import Dict, Type, List, Optional
from genesis.plugins.base import Plugin


class PluginRegistry:
    """
    Central registry for all available plugins.
    
    This allows the system to:
    - Discover available plugins
    - Instantiate plugins by name
    - Check plugin requirements
    - Get plugin metadata
    """
    
    _plugins: Dict[str, Type[Plugin]] = {}
    _metadata: Dict[str, Dict[str, str]] = {}
    
    @classmethod
    def register(cls, plugin_class: Type[Plugin], category: str = "extension",
                 requires_config: bool = False, config_fields: Optional[List[Dict]] = None):
        """
        Register a plugin.
        
        Args:
            plugin_class: Plugin class to register
            category: Category (core, integration, enhancement, experimental)
            requires_config: Whether plugin needs configuration
            config_fields: List of required config fields
        """
        # Instantiate temporarily to get name
        temp = plugin_class()
        name = temp.get_name()
        
        cls._plugins[name] = plugin_class
        cls._metadata[name] = {
            "name": name,
            "version": temp.get_version(),
            "description": temp.get_description(),
            "category": category,
            "requires_config": str(requires_config).lower(),
            "config_fields": config_fields or []
        }
    
    @classmethod
    def get(cls, name: str, **config) -> Optional[Plugin]:
        """
        Get a plugin instance by name.
        
        Args:
            name: Plugin name
            **config: Plugin configuration
            
        Returns:
            Plugin instance or None if not found
        """
        plugin_class = cls._plugins.get(name)
        if plugin_class:
            return plugin_class(**config)
        return None
    
    @classmethod
    def list_all(cls) -> List[Dict[str, str]]:
        """Get list of all registered plugins with metadata."""
        return list(cls._metadata.values())
    
    @classmethod
    def get_metadata(cls, name: str) -> Optional[Dict[str, str]]:
        """Get metadata for a specific plugin."""
        return cls._metadata.get(name)
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in cls._plugins


# Auto-register all built-in plugins
def register_builtin_plugins():
    """Register all built-in plugins."""
    
    # Core plugins
    from genesis.plugins.lifecycle import LifecyclePlugin
    from genesis.plugins.gen import GenPlugin
    from genesis.plugins.tasks import TasksPlugin
    from genesis.plugins.workspace import WorkspacePlugin
    from genesis.plugins.roles import RolesPlugin
    from genesis.plugins.events import EventsPlugin
    from genesis.plugins.relationships import RelationshipsPlugin
    from genesis.plugins.environments import EnvironmentsPlugin
    
    PluginRegistry.register(LifecyclePlugin, category="core")
    PluginRegistry.register(GenPlugin, category="core")
    PluginRegistry.register(TasksPlugin, category="core")
    PluginRegistry.register(WorkspacePlugin, category="core")
    PluginRegistry.register(RolesPlugin, category="core")
    PluginRegistry.register(EventsPlugin, category="core")
    PluginRegistry.register(RelationshipsPlugin, category="core")
    PluginRegistry.register(EnvironmentsPlugin, category="core")
    
    # Integration plugins
    from genesis.plugins.perplexity_search import PerplexitySearchPlugin
    from genesis.plugins.browser_use_plugin import BrowserUsePlugin
    
    PluginRegistry.register(
        PerplexitySearchPlugin,
        category="integration",
        requires_config=True,
        config_fields=[{
            "name": "api_key",
            "label": "Perplexity API Key",
            "type": "password",
            "required": True,
            "placeholder": "pplx-..."
        }]
    )
    
    PluginRegistry.register(
        BrowserUsePlugin,
        category="integration",
        requires_config=False
    )
    
    # Enhancement plugins
    from genesis.plugins.profiles import ProfilesPlugin
    from genesis.plugins.learning import LearningPlugin
    from genesis.plugins.senses import SensesPlugin
    
    PluginRegistry.register(ProfilesPlugin, category="enhancement")
    PluginRegistry.register(LearningPlugin, category="enhancement")
    PluginRegistry.register(SensesPlugin, category="enhancement")
    
    # Experimental plugins
    from genesis.plugins.proactive_behavior import ProactiveBehaviorPlugin
    from genesis.plugins.autonomous_life import AutonomousLifePlugin
    
    PluginRegistry.register(ProactiveBehaviorPlugin, category="experimental")
    PluginRegistry.register(AutonomousLifePlugin, category="experimental")


# Auto-register on import
register_builtin_plugins()

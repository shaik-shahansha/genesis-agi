# Genesis Plugin Management Guide

Complete guide to managing plugins in Genesis Minds - both via CLI and Web Playground.

## Table of Contents

1. [Overview](#overview)
2. [Available Plugins](#available-plugins)
3. [CLI Commands](#cli-commands)
4. [Web Playground](#web-playground)
5. [Programmatic Usage](#programmatic-usage)
6. [Creating Custom Plugins](#creating-custom-plugins)

---

## Overview

Genesis Minds use a modular plugin architecture that allows you to customize capabilities based on your needs. You can start with a minimal Mind and add features incrementally, or use pre-configured bundles.

### Plugin Configurations

- **Minimal** (~500 tokens): Core only (identity, consciousness, memory, emotions)
- **Standard** (~1,200 tokens): Core + common plugins (lifecycle, GEN, tasks)
- **Full** (~2,000 tokens): All production features
- **Custom**: Choose exactly what you need

---

## Available Plugins

### Core Plugins

| Plugin | Description | Token Cost |
|--------|-------------|------------|
| `lifecycle` | Mortality, urgency, limited lifespan | ~150 tokens |
| `gen` | Economy system, motivation, value tracking | ~200 tokens |
| `tasks` | Goal-oriented task management | ~150 tokens |
| `workspace` | File system access and management | ~200 tokens |
| `relationships` | Social connections and bonds | ~150 tokens |
| `environments` | Metaverse integration | ~200 tokens |
| `roles` | Purpose definition and job roles | ~100 tokens |
| `events` | Event tracking and history | ~100 tokens |
| `experiences` | Experience tracking and learning | ~150 tokens |

### Integration Plugins

| Plugin | Description | Requires |
|--------|-------------|----------|
| `perplexity_search` | Internet search via Perplexity AI | API Key |
| `mcp` | Model Context Protocol integration | MCP Server |

### Experimental Plugins

⚠️ **Warning**: These plugins are not fully implemented and may not work as expected.

| Plugin | Description | Status |
|--------|-------------|--------|
| `learning` | Knowledge accumulation | Basic |
| `goals` | Long-term goal pursuit | WIP |
| `knowledge` | Knowledge graph system | Basic |

---

## CLI Commands

### List Available Plugins

```bash
genesis plugin list-available
```

Shows all plugins that can be installed.

### List Installed Plugins for a Mind

```bash
genesis plugin list <mind_name>
```

Example:
```bash
genesis plugin list Atlas
```

### Add a Plugin

```bash
genesis plugin add <mind_name> <plugin_name>
```

Examples:
```bash
# Add lifecycle plugin
genesis plugin add Atlas lifecycle

# Add Perplexity search with API key
genesis plugin add Atlas perplexity_search --api-key YOUR_API_KEY
```

### Remove a Plugin

```bash
genesis plugin remove <mind_name> <plugin_name>
```

Example:
```bash
genesis plugin remove Atlas tasks
```

### Enable/Disable Plugins

```bash
# Disable (keeps installed but stops using)
genesis plugin disable <mind_name> <plugin_name>

# Re-enable
genesis plugin enable <mind_name> <plugin_name>
```

Example:
```bash
genesis plugin disable Atlas lifecycle
genesis plugin enable Atlas lifecycle
```

---

## Web Playground

### Accessing Plugin Management

1. Navigate to your Mind's detail page
2. Click on the **"Plugins"** tab (🔌 icon)
3. You'll see:
   - Installed plugins with status
   - Button to add new plugins
   - Category filters

### Adding Plugins via Playground

1. Click **"➕ Add Plugin"**
2. Browse available plugins by category
3. Click on a plugin to see details
4. If it requires configuration (e.g., API keys), fill in the fields
5. Click **"Install Plugin"**

### Managing Installed Plugins

Each installed plugin shows:
- **Enable/Disable**: Toggle plugin functionality
- **Remove**: Completely uninstall the plugin
- **Status**: Current state (enabled/disabled)
- **Version**: Plugin version number

### Category Filters

- **All Plugins**: Show everything
- **Core**: Essential Mind features
- **Integration**: External service integrations
- **Experimental**: Work-in-progress features

---

## Programmatic Usage

### Creating Mind with Plugins

```python
from genesis import Mind
from genesis.core.mind_config import MindConfig
from genesis.plugins.lifecycle import LifecyclePlugin
from genesis.plugins.gen import GenPlugin
from genesis.plugins.perplexity_search import PerplexitySearchPlugin

# Start with minimal config
config = MindConfig.minimal()

# Add plugins one by one
config.add_plugin(LifecyclePlugin(lifespan_years=5))
config.add_plugin(GenPlugin(starting_balance=1000))
config.add_plugin(PerplexitySearchPlugin(
    api_key="YOUR_API_KEY",
    auto_search=True
))

# Birth Mind with plugins
mind = Mind.birth("Researcher", config=config)
```

### Using Pre-configured Bundles

```python
# Standard configuration
config = MindConfig.standard()  # lifecycle, gen, tasks

# Full configuration
config = MindConfig.full()  # all production features

# Experimental configuration
config = MindConfig.experimental()  # includes experimental plugins
```

### Adding Plugins to Existing Mind

```python
from genesis import Mind
from genesis.plugins.workspace import WorkspacePlugin

# Load existing Mind
mind = Mind.load("path/to/mind.json")

# Add plugin
workspace_plugin = WorkspacePlugin()
mind.config.add_plugin(workspace_plugin)
mind.plugins.append(workspace_plugin)
workspace_plugin.on_init(mind)

# Save
mind.save()
```

### Checking Installed Plugins

```python
# List all plugins
for plugin in mind.plugins:
    print(f"{plugin.get_name()} v{plugin.get_version()}")
    print(f"  Enabled: {plugin.enabled}")
    print(f"  Description: {plugin.get_description()}")
```

### Removing Plugins

```python
# Remove by name
mind.config.remove_plugin("tasks")
mind.plugins = [p for p in mind.plugins if p.get_name() != "tasks"]
mind.save()
```

### Enable/Disable Plugins

```python
# Disable temporarily
plugin = mind.config.get_plugin("lifecycle")
plugin.disable()
mind.save()

# Re-enable
plugin.enable()
mind.save()
```

---

## Creating Custom Plugins

### Basic Plugin Structure

```python
from genesis.plugins.base import Plugin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind

class MyCustomPlugin(Plugin):
    def __init__(self, my_config_value: str = "default"):
        super().__init__(my_config_value=my_config_value)
    
    def get_name(self) -> str:
        return "my_custom_plugin"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "My custom plugin for special features"
    
    def on_init(self, mind: "Mind") -> None:
        """Called when Mind is initialized"""
        # Attach your features to the Mind
        mind.my_feature = MyFeature()
    
    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add context to system prompt"""
        return f"""
        
## My Custom Feature

You have access to my custom feature with value: {self.config['my_config_value']}
"""
    
    def on_save(self, mind: "Mind") -> dict:
        """Save plugin state"""
        return {
            "my_data": mind.my_feature.get_state()
        }
    
    def on_load(self, mind: "Mind", data: dict) -> None:
        """Restore plugin state"""
        mind.my_feature = MyFeature()
        mind.my_feature.restore_state(data.get("my_data"))
```

### Plugin Lifecycle Hooks

- `on_init(mind)`: Called when Mind is initialized
- `on_birth(mind)`: Called after Mind is born
- `on_think_start(mind, prompt)`: Before processing thought
- `on_think_end(mind, response)`: After generating response
- `extend_system_prompt(mind)`: Add to system prompt
- `on_save(mind)`: Serialize plugin state
- `on_load(mind, data)`: Restore plugin state
- `on_terminate(mind)`: Cleanup when Mind terminates

### Using Custom Plugins

```python
# Add to Mind
config = MindConfig.minimal()
config.add_plugin(MyCustomPlugin(my_config_value="special"))

mind = Mind.birth("CustomMind", config=config)
```

---

## Best Practices

### 1. Start Minimal, Add What You Need

```python
# Don't do this (too much overhead)
config = MindConfig.full()

# Do this (add only what you use)
config = MindConfig.minimal()
config.add_plugin(TasksPlugin())  # Only if you need tasks
```

### 2. Use Environment Variables for API Keys

```python
# In .env file
PERPLEXITY_API_KEY=pplx-your-key

# In code
config.add_plugin(PerplexitySearchPlugin())  # Auto-reads from env
```

### 3. Disable Instead of Remove for Testing

```bash
# Disable temporarily (keeps config)
genesis plugin disable Atlas lifecycle

# Test without plugin
genesis chat Atlas

# Re-enable when ready
genesis plugin enable Atlas lifecycle
```

### 4. Monitor Token Usage

Each plugin adds to the system prompt. Monitor your token usage:

```python
# Check system prompt size
prompt = mind._build_system_prompt()
print(f"System prompt tokens: ~{len(prompt.split()) * 1.3}")
```

---

## API Endpoints

### Get Plugins

```http
GET /api/v1/minds/{mind_id}/plugins
```

### Add Plugin

```http
POST /api/v1/minds/{mind_id}/plugins
Content-Type: application/json

{
  "plugin_name": "perplexity_search",
  "config": {
    "api_key": "YOUR_API_KEY",
    "auto_search": true
  }
}
```

### Remove Plugin

```http
DELETE /api/v1/minds/{mind_id}/plugins/{plugin_name}
```

### Enable Plugin

```http
POST /api/v1/minds/{mind_id}/plugins/{plugin_name}/enable
```

### Disable Plugin

```http
POST /api/v1/minds/{mind_id}/plugins/{plugin_name}/disable
```

---

## Troubleshooting

### Plugin Not Showing in List

**Problem**: Added plugin doesn't appear

**Solution**:
```bash
# Reload Mind state
genesis plugin list YourMind

# Or in Python
mind = Mind.load("path/to/mind.json")
print([p.get_name() for p in mind.plugins])
```

### Plugin Import Error

**Problem**: `ImportError: cannot import plugin`

**Solution**:
```bash
# Check if plugin file exists
ls genesis/plugins/

# Verify plugin is in __init__.py
cat genesis/plugins/__init__.py
```

### API Key Not Working

**Problem**: Plugin requires API key but fails

**Solution**:
```bash
# Set in environment
export PERPLEXITY_API_KEY=your-key

# Or pass directly via CLI
genesis plugin add Mind perplexity_search --api-key your-key
```

### Too Many Tokens

**Problem**: System prompt exceeds model limits

**Solution**:
```bash
# Remove unused plugins
genesis plugin remove Mind unused_plugin

# Or disable temporarily
genesis plugin disable Mind large_plugin

# Use minimal config
genesis birth NewMind --config minimal
```

---

## Examples

See [`examples/plugin_management_example.py`](../examples/plugin_management_example.py) for complete working examples.

---

## Contributing

Want to create a plugin? See the [Plugin Development Guide](PLUGIN_DEVELOPMENT.md) for detailed instructions on creating, testing, and publishing plugins.

---

## Support

- **Documentation**: [docs/](../docs/)
- **Examples**: [examples/](../examples/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/genesis/issues)
- **Discord**: [Join our community](https://discord.gg/genesis-agi)

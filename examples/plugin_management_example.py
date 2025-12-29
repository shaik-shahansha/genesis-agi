"""
Example: Managing Plugins for Genesis Minds

This demonstrates how to add, remove, and manage plugins
for Minds both programmatically and via CLI.
"""

import asyncio
import os
from genesis import Mind
from genesis.core.mind_config import MindConfig


async def main():
    print("=== Genesis Plugin Management Example ===\n")
    
    # Method 1: Create Mind with specific plugins
    print("1. Creating Mind with custom plugin configuration...")
    config = MindConfig.minimal()  # Start minimal
    
    # Add plugins one by one
    from genesis.plugins.lifecycle import LifecyclePlugin
    from genesis.plugins.tasks import TasksPlugin
    from genesis.plugins.perplexity_search import PerplexitySearchPlugin
    
    config.add_plugin(LifecyclePlugin(lifespan_years=5))
    config.add_plugin(TasksPlugin())
    
    # Add Perplexity search if API key available
    if os.getenv("PERPLEXITY_API_KEY"):
        config.add_plugin(PerplexitySearchPlugin(
            auto_search=True,
            default_mode="detailed"
        ))
        print("   ✅ Added Perplexity search plugin")
    
    mind = Mind.birth("Researcher", config=config)
    print(f"   ✅ Created '{mind.identity.name}' with {len(mind.plugins)} plugins\n")
    
    # Method 2: Check what plugins are enabled
    print("2. Checking enabled plugins...")
    for plugin in mind.plugins:
        status = "✅" if plugin.enabled else "❌"
        print(f"   {status} {plugin.get_name()} v{plugin.get_version()} - {plugin.get_description()}")
    print()
    
    # Method 3: Add plugin to existing Mind
    print("3. Adding GEN plugin dynamically...")
    from genesis.plugins.gen import GenPlugin
    
    gen_plugin = GenPlugin(starting_balance=1000)
    mind.config.add_plugin(gen_plugin)
    mind.plugins.append(gen_plugin)
    gen_plugin.on_init(mind)
    print(f"   ✅ Added GEN plugin (balance: {mind.essence.balance if hasattr(mind, 'essence') else 'N/A'})\n")
    
    # Method 4: Disable a plugin temporarily
    print("4. Disabling lifecycle plugin temporarily...")
    lifecycle = mind.config.get_plugin("lifecycle")
    if lifecycle:
        lifecycle.disable()
        print(f"   ✅ Lifecycle plugin disabled (still installed)\n")
    
    # Method 5: Re-enable plugin
    print("5. Re-enabling lifecycle plugin...")
    if lifecycle:
        lifecycle.enable()
        print(f"   ✅ Lifecycle plugin re-enabled\n")
    
    # Method 6: Remove plugin completely
    print("6. Removing tasks plugin...")
    mind.config.remove_plugin("tasks")
    mind.plugins = [p for p in mind.plugins if p.get_name() != "tasks"]
    print(f"   ✅ Tasks plugin removed\n")
    
    # Method 7: Use plugin functionality (Perplexity search)
    if os.getenv("PERPLEXITY_API_KEY"):
        print("7. Testing Perplexity search plugin...")
        response = await mind.think("What are the latest developments in quantum computing?")
        print(f"   Response: {response[:200]}...\n")
    
    # Save Mind with updated plugin configuration
    mind.save()
    print(f"✅ Mind saved with updated plugin configuration\n")
    
    # CLI Usage Examples
    print("=== CLI Usage Examples ===\n")
    print("List available plugins:")
    print("  genesis plugin list-available\n")
    
    print("Add plugin to existing Mind:")
    print("  genesis plugin add Researcher perplexity_search --api-key YOUR_KEY\n")
    
    print("List plugins for a Mind:")
    print("  genesis plugin list Researcher\n")
    
    print("Remove plugin:")
    print("  genesis plugin remove Researcher tasks\n")
    
    print("Disable/Enable plugin:")
    print("  genesis plugin disable Researcher lifecycle")
    print("  genesis plugin enable Researcher lifecycle\n")


if __name__ == "__main__":
    asyncio.run(main())

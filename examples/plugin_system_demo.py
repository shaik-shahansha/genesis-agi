"""
Example: Plugin System & Real Tool Execution

This example demonstrates:
1. Minimal Mind (just core features)
2. Standard Mind (core + common plugins)
3. Custom Mind (compose your own)
4. REAL tool execution (not fake!)
"""

import asyncio
from genesis import Mind
from genesis.core.mind_config import MindConfig
from genesis.plugins.lifecycle import LifecyclePlugin
from genesis.plugins.essence import EssencePlugin
from genesis.plugins.tools import ToolsPlugin


async def main():
    print("=" * 60)
    print("Genesis Plugin System Demo")
    print("=" * 60)

    # ================================================================
    # 1. MINIMAL MIND - Just consciousness + memory + emotions
    # ================================================================
    print("\n1. Minimal Mind (core features only)")
    print("-" * 60)

    minimal = Mind.birth("Minimal", config=MindConfig.minimal())
    # Output shows: Plugins: none (minimal configuration)

    response = await minimal.think("Hello! What can you do?")
    print(f"Minimal: {response[:150]}...")

    # ================================================================
    # 2. STANDARD MIND - Core + lifecycle + essence + tasks
    # ================================================================
    print("\n\n2. Standard Mind (common plugins)")
    print("-" * 60)

    standard = Mind.birth("Standard", config=MindConfig.standard())
    # Output shows: Plugins: lifecycle, essence, tasks

    # Check lifecycle
    if hasattr(standard, 'lifecycle'):
        summary = standard.lifecycle.get_lifecycle_summary()
        print(f"Lifecycle: {summary['time_remaining']} remaining")
        print(f"Urgency: {summary['urgency_description']}")

    # Check Essence
    if hasattr(standard, 'essence'):
        balance = standard.essence.get_balance_summary()
        print(f"Essence Balance: {balance['current_balance']}")

    # ================================================================
    # 3. CUSTOM MIND - Compose your own
    # ================================================================
    print("\n\n3. Custom Mind (10-year lifespan + tools)")
    print("-" * 60)

    config = MindConfig.minimal()
    config.add_plugin(LifecyclePlugin(lifespan_years=10))  # 10-year lifespan!
    config.add_plugin(EssencePlugin(starting_balance=500))  # Rich start
    config.add_plugin(ToolsPlugin(execution_timeout=10))    # Real execution

    custom = Mind.birth("Custom", config=config)
    # Output shows: Plugins: lifecycle, essence, tools

    # ================================================================
    # 4. REAL TOOL EXECUTION (Not fake!)
    # ================================================================
    print("\n\n4. Real Tool Execution")
    print("-" * 60)

    if hasattr(custom, 'tools'):
        # Create a real tool
        tool = custom.tools.create_tool(
            name="calculator",
            description="Add two numbers",
            code="""
def run(a, b):
    return a + b
            """,
            input_type="numbers",
            output_type="number",
            category="utility"
        )

        print(f"[Done] Created tool: {tool.name}")

        # ACTUALLY EXECUTE IT (not fake!)
        try:
            result = custom.tools.execute_tool(
                tool.tool_id,
                input_data={"a": 42, "b": 27}
            )
            print(f"[Done] Execution result: {result}")
            print("   ^ THIS IS REAL EXECUTION, NOT FAKE!")
        except Exception as e:
            print(f"❌ Execution error: {e}")

    # ================================================================
    # 5. Save & Load with Plugins
    # ================================================================
    print("\n\n5. Save & Load")
    print("-" * 60)

    # Save
    path = custom.save()
    print(f"[Done] Saved to: {path}")

    # Load
    loaded = Mind.load(path)
    print(f"[Done] Loaded Mind: {loaded.identity.name}")
    print(f"   Plugins: {[p.get_name() for p in loaded.plugins]}")

    # ================================================================
    # 6. Token Comparison
    # ================================================================
    print("\n\n6. System Prompt Token Comparison")
    print("-" * 60)

    minimal_prompt = minimal._build_system_message()
    standard_prompt = standard._build_system_message()
    custom_prompt = custom._build_system_message()

    print(f"Minimal tokens:  ~{len(minimal_prompt.split())} words")
    print(f"Standard tokens: ~{len(standard_prompt.split())} words")
    print(f"Custom tokens:   ~{len(custom_prompt.split())} words")
    print(f"\nToken savings: {100 - (len(minimal_prompt.split()) / len(standard_prompt.split()) * 100):.0f}% (minimal vs standard)")

    print("\n" + "=" * 60)
    print("[Done] Plugin System Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

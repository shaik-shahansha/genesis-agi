"""Test intelligence configuration protection."""

import json
from genesis.core.mind import Mind

# Load the test Mind
print("=" * 80)
print("Loading Mind...")
mind = Mind.load("data/minds/GMD-2026-658A-D910/mind.json")

print(f"\nAfter load:")
print(f"  reasoning_model: {mind.intelligence.reasoning_model}")
print(f"  fast_model: {mind.intelligence.fast_model}")

# Check what's in the JSON file
print(f"\nChecking JSON file directly...")
with open("data/minds/GMD-2026-658A-D910/mind.json") as f:
    data = json.load(f)
    print(f"  JSON reasoning_model: {data['intelligence']['reasoning_model']}")
    print(f"  JSON fast_model: {data['intelligence']['fast_model']}")

# Try to save without any modifications
print(f"\n" + "=" * 80)
print("Attempting save WITHOUT modifications...")
mind.save()

print(f"\nSave completed successfully - no changes detected")
print(f"Mind still has:")
print(f"  reasoning_model: {mind.intelligence.reasoning_model}")
print(f"  fast_model: {mind.intelligence.fast_model}")

# Now intentionally modify and try to save
print(f"\n" + "=" * 80)
print("Intentionally modifying reasoning_model to test protection...")
mind.intelligence.reasoning_model = "deepseek/deepseek-r1-0528:free"  # Remove openrouter/ prefix
print(f"  Modified to: {mind.intelligence.reasoning_model}")

print(f"\nAttempting save WITH modification (should be blocked)...")
mind.save()

print(f"\n" + "=" * 80)
print("TEST COMPLETE")

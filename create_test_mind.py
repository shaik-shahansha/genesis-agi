"""Create a test Mind with OpenRouter configuration."""

from genesis.core.mind import Mind
from genesis.core.intelligence import Intelligence

print("Creating test Mind with OpenRouter configuration...")

intelligence = Intelligence(
    reasoning_model="openrouter/deepseek/deepseek-r1-0528:free",
    fast_model="openrouter/deepseek/deepseek-r1-0528:free",
    auto_route=True
)

mind = Mind(
    name="TestMind",
    intelligence=intelligence,
    creator="Test"
)

print(f"\nCreated Mind with:")
print(f"  reasoning_model: {mind.intelligence.reasoning_model}")
print(f"  fast_model: {mind.intelligence.fast_model}")

# Save the Mind
path = mind.save()
print(f"\nSaved to: {path}")

# Verify saved data
import json
with open(path) as f:
    data = json.load(f)
    print(f"\nVerifying saved JSON:")
    print(f"  reasoning_model: {data['intelligence']['reasoning_model']}")
    print(f"  fast_model: {data['intelligence']['fast_model']}")

print(f"\n✓ Test Mind created successfully!")
print(f"Mind ID: {mind.identity.id}")

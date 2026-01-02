"""
Test if Intelligence config is being modified during Mind load/save cycle.
"""

import json
from pathlib import Path
from genesis.config import get_settings
from genesis.core.intelligence import Intelligence

settings = get_settings()
mind_path = settings.minds_dir / "GMD-2026-658A-D910.json"

print("="*80)
print("Testing Intelligence Config Persistence")
print("="*80)

# Step 1: Read raw JSON
print("\n[1] Reading raw JSON file...")
with open(mind_path) as f:
    data = json.load(f)

intelligence_json = data["intelligence"]
print(f"   reasoning_model: {intelligence_json.get('reasoning_model')}")
print(f"   fast_model: {intelligence_json.get('fast_model')}")

# Step 2: Create Intelligence object
print("\n[2] Creating Intelligence object from JSON...")
intelligence = Intelligence(**intelligence_json)
print(f"   reasoning_model: {intelligence.reasoning_model}")
print(f"   fast_model: {intelligence.fast_model}")

# Step 3: Serialize back to JSON
print("\n[3] Serializing Intelligence back to JSON...")
serialized = json.loads(intelligence.model_dump_json())
print(f"   reasoning_model: {serialized.get('reasoning_model')}")
print(f"   fast_model: {serialized.get('fast_model')}")

# Step 4: Check if values changed
print("\n[4] Checking for changes...")
if intelligence_json["reasoning_model"] != serialized["reasoning_model"]:
    print(f"   ❌ reasoning_model CHANGED:")
    print(f"      Original: {intelligence_json['reasoning_model']}")
    print(f"      After:    {serialized['reasoning_model']}")
else:
    print(f"   ✓ reasoning_model unchanged")

if intelligence_json["fast_model"] != serialized["fast_model"]:
    print(f"   ❌ fast_model CHANGED:")
    print(f"      Original: {intelligence_json['fast_model']}")
    print(f"      After:    {serialized['fast_model']}")
else:
    print(f"   ✓ fast_model unchanged")

print("\n" + "="*80)

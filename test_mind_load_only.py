"""Test if Mind.load() and Mind.save() preserve intelligence model names."""

import asyncio
import sys
sys._genesis_debug_intelligence = True

from genesis.core.mind import Mind
from pathlib import Path

async def test_load():
    # Load Mind
    mind_path = Path(r"C:\Users\shaiks3423\.genesis\minds\GMD-2026-658A-D910.json")

    print("\n" + "="*80)
    print("Testing Mind Load/Save Intelligence Preservation")
    print("="*80)

    print(f"\n[1] Loading Mind from: {mind_path}")
    mind = Mind.load(str(mind_path))

    print(f"\n[2] Loaded Mind intelligence:")
    print(f"  reasoning_model: {mind.intelligence.reasoning_model}")
    print(f"  fast_model: {mind.intelligence.fast_model}")

    expected_reasoning = "openrouter/deepseek/deepseek-r1-0528:free"
    expected_fast = "openrouter/deepseek/deepseek-r1-0528:free"

    print(f"\n[3] Verification:")
    if mind.intelligence.reasoning_model == expected_reasoning:
        print(f"  ✓ reasoning_model correct")
    else:
        print(f"  ✗ reasoning_model WRONG!")
        print(f"    Expected: {expected_reasoning}")
        print(f"    Got: {mind.intelligence.reasoning_model}")

    if mind.intelligence.fast_model == expected_fast:
        print(f"  ✓ fast_model correct")
    else:
        print(f"  ✗ fast_model WRONG!")
        print(f"    Expected: {expected_fast}")
        print(f"    Got: {mind.intelligence.fast_model}")

    # Don't save - just check if loading preserves values
    print("\n" + "="*80)
    print("Test Complete - No save performed")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_load())

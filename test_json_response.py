"""Quick test to debug JSON response issue."""
import asyncio
import sys
from pathlib import Path

# Add genesis to path
sys.path.insert(0, str(Path(__file__).parent))

from genesis.core.mind import Mind

async def test_response():
    """Test Mind response to see raw output."""
    print("Loading Mind...")
    
    # Find Mind file
    from genesis.config.settings import Settings
    settings = Settings()
    mind_file = settings.minds_dir / "GMD-2026-658A-D910.json"
    
    if not mind_file.exists():
        print(f"Mind file not found: {mind_file}")
        # List available minds
        minds = list(settings.minds_dir.glob("*.json"))
        if minds:
            print(f"\nAvailable minds:")
            for m in minds:
                print(f"  - {m.stem}")
            mind_file = minds[0]
            print(f"\nUsing first available: {mind_file.stem}")
        else:
            print("No minds found!")
            return
    
    # Load the specific Mind
    mind = Mind.load(str(mind_file))
    
    print(f"Loaded: {mind.identity.name}")
    print(f"Model: {mind.intelligence.reasoning_model}")
    print("\nSending message: 'I have heavy head due to cold'")
    print("-" * 80)
    
    # Get response
    response = await mind.think("I have heavy head due to cold", user_email="test@example.com")
    
    print("\n=== RAW RESPONSE ===")
    print(f"Type: {type(response)}")
    print(f"Length: {len(response)}")
    print(f"First 500 chars:\n{response[:500]}")
    print("\n" + "=" * 80)
    
    # Check if it starts with ```
    if response.strip().startswith("```"):
        print("\n⚠️  Response contains markdown code block!")
        print("Attempting to clean...")
        
        import re
        code_block_pattern = r'^```(?:\w+)?\s*\n(.*?)\n```\s*$'
        match = re.match(code_block_pattern, response.strip(), re.DOTALL)
        if match:
            content = match.group(1).strip()
            print(f"\n✓ Extracted content from code block")
            print(f"Content starts with: {content[:100]}")
            
            # Try parsing as JSON
            if content.startswith('{'):
                import json
                try:
                    data = json.loads(content)
                    print(f"\n✓ Successfully parsed as JSON")
                    print(f"Keys: {list(data.keys())}")
                    if "response" in data:
                        print(f"Response field type: {type(data['response'])}")
                        print(f"Response field: {data['response']}")
                except Exception as e:
                    print(f"\n✗ JSON parse failed: {e}")
        else:
            print("\n✗ Regex didn't match the code block pattern")
            print(f"Pattern used: {code_block_pattern}")
    else:
        print("\n✓ Response is clean (no code block)")

if __name__ == "__main__":
    asyncio.run(test_response())

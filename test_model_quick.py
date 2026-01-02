"""Quick test to verify the model is working."""
import asyncio
from genesis.models.orchestrator import ModelOrchestrator
from genesis.config import get_settings

async def test_model():
    settings = get_settings()
    
    if not settings.openrouter_api_key:
        print("❌ No OpenRouter API key!")
        return
    
    print(f"✓ API key found: {settings.openrouter_api_key[:10]}...")
    
    orchestrator = ModelOrchestrator(api_keys={'openrouter': settings.openrouter_api_key})
    
    model = "openrouter/deepseek/deepseek-r1-0528:free"
    
    print(f"\nTesting model: {model}")
    print("-" * 80)
    
    try:
        # Test 1: Simple response
        print("\n[Test 1] Simple response...")
        response = await orchestrator.generate(
            messages=[{"role": "user", "content": "Say hello"}],
            model=model,
            temperature=0.7,
            max_tokens=50
        )
        print(f"✓ Response: {response.content}")
        print(f"  Length: {len(response.content)}")
        
        # Test 2: JSON response
        print("\n[Test 2] JSON response...")
        response2 = await orchestrator.generate(
            messages=[{"role": "user", "content": 'Return ONLY this JSON: [{"type": "code", "desc": "test"}]'}],
            model=model,
            temperature=0.3,
            max_tokens=200
        )
        print(f"✓ Response: {response2.content}")
        print(f"  Length: {len(response2.content)}")
        
        # Test 3: Plan generation (like the failing case) - with MORE tokens
        print("\n[Test 3] Plan generation with sufficient tokens...")
        prompt = """Create a step-by-step execution plan for this task:

Task: create presentation on human digital twins

Return ONLY a JSON array of steps:
[
    {
        "type": "code_execution",
        "description": "what this step does",
        "timeout": 60
    }
]
"""
        response3 = await orchestrator.generate(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.3,
            max_tokens=2000  # Increased for DeepSeek R1 reasoning
        )
        print(f"✓ Response: {response3.content[:200]}...")
        print(f"  Full length: {len(response3.content)}")
        
        if not response3.content:
            print("❌ EMPTY RESPONSE! This is the problem.")
        
        # Check if it's JSON
        import json
        try:
            data = json.loads(response3.content)
            print(f"✓ Valid JSON with {len(data)} steps")
        except:
            print(f"⚠️  Not valid JSON, trying to extract...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_model())

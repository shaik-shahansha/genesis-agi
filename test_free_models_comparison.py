"""Test different OpenRouter free models for JSON generation quality."""
import asyncio
import json
from genesis.models.orchestrator import ModelOrchestrator
from genesis.config import get_settings

async def test_model(orchestrator, model_name, model_id):
    """Test a single model's ability to generate JSON."""
    print(f"\n{'='*80}")
    print(f"Testing: {model_name}")
    print(f"Model ID: {model_id}")
    print('='*80)
    
    prompt = """Create a step-by-step execution plan for this task:

Task: create presentation on human digital twins

Return ONLY a JSON array of steps (no explanations):
[
    {
        "type": "code_execution",
        "description": "what this step does",
        "timeout": 60
    }
]

Make the plan efficient and logical. Typically 1-3 steps."""

    try:
        response = await orchestrator.generate(
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that returns JSON."},
                {"role": "user", "content": prompt}
            ],
            model=model_id,
            temperature=0.7,
            max_tokens=2000
        )
        
        print(f"\n✓ Response received (length: {len(response.content)})")
        print(f"Latency: {response.latency_ms:.0f}ms")
        print(f"Tokens: {response.tokens_used}")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(response.content)
            print(f"\n✓ Valid JSON!")
            print(f"Type: {type(parsed)}")
            if isinstance(parsed, list):
                print(f"Steps: {len(parsed)}")
                print(f"\nFirst step:")
                print(json.dumps(parsed[0], indent=2))
            else:
                print(f"\nParsed:")
                print(json.dumps(parsed, indent=2))
            return True, response.content
        except json.JSONDecodeError as e:
            print(f"\n✗ Invalid JSON: {e}")
            print(f"\nRaw response (first 500 chars):")
            print(response.content[:500])
            return False, response.content
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)


async def main():
    """Test all models."""
    print("\n" + "="*80)
    print("OpenRouter Free Models Comparison for JSON Generation")
    print("="*80)
    
    settings = get_settings()
    if not settings.openrouter_api_key:
        print("\n❌ No OpenRouter API key found!")
        return
    
    orchestrator = ModelOrchestrator(api_keys={'openrouter': settings.openrouter_api_key})
    
    # Models to test
    test_cases = [
        ("OpenAI GPT OSS 120B", "openrouter/openai/gpt-oss-120b:free"),
        ("Moonshot Kimi K2", "openrouter/moonshotai/kimi-k2:free"),
        ("Google Gemini 2.0 Flash", "openrouter/google/gemini-2.0-flash-exp:free"),
        ("Meta Llama 3.3 70B", "openrouter/meta-llama/llama-3.3-70b-instruct:free"),
        ("Google Gemma 3 27B", "openrouter/google/gemma-3-27b-it:free"),
        ("Xiaomi Mimo V2 Flash", "openrouter/xiaomi/mimo-v2-flash:free"),
    ]
    
    results = []
    
    for model_name, model_id in test_cases:
        success, response = await test_model(orchestrator, model_name, model_id)
        results.append({
            "name": model_name,
            "id": model_id,
            "success": success,
            "response_preview": response[:200] if isinstance(response, str) else str(response)[:200]
        })
        await asyncio.sleep(1)  # Rate limit friendly
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    successful = [r for r in results if r["success"]]
    
    if successful:
        print(f"\n✓ {len(successful)}/{len(results)} models successfully generated valid JSON:\n")
        for r in successful:
            print(f"  ✓ {r['name']}")
            print(f"    {r['id']}")
        
        print(f"\n\nRECOMMENDATION:")
        print(f"Use: {successful[0]['id']}")
    else:
        print(f"\n✗ No models generated valid JSON")
        print(f"\nAll responses:")
        for r in results:
            print(f"\n{r['name']}:")
            print(f"  {r['response_preview']}")


if __name__ == "__main__":
    asyncio.run(main())

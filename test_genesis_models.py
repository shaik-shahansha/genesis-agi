"""
Test models with Genesis format (provider/model/path).
"""

import asyncio
from genesis.models.orchestrator import ModelOrchestrator

async def test_models():
    print("\n" + "="*80)
    print("Testing Models with Genesis Format")
    print("="*80 + "\n")
    
    orchestrator = ModelOrchestrator()
    
    # Test different model formats
    test_cases = [
        # Original (what user had)
        ("openrouter/openrouter/deepseek/deepseek-r1-0528:free", "Original with :free suffix"),
        ("openrouter/deepseek/deepseek-r1-0528:free", "OpenAI OSS with :free suffix"),
        
        # Without :free suffix
        ("openrouter/deepseek/deepseek-r1-0528", "DeepSeek R1 without :free"),
        ("openrouter/openai/gpt-oss-120b", "OpenAI OSS without :free"),
        
        # Other free models found
        ("openrouter/google/gemini-2.0-flash-exp:free", "Gemini Flash 2.0"),
        ("openrouter/meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B"),
        ("openrouter/qwen/qwen3-4b:free", "Qwen3 4B"),
    ]
    
    for model_id, description in test_cases:
        print(f"\nTesting: {description}")
        print(f"Model ID: {model_id}")
        print("-" * 80)
        
        try:
            response = await orchestrator.generate(
                messages=[{"role": "user", "content": "Say 'Hello from Genesis!' in one short sentence."}],
                model=model_id,
                temperature=0.7,
                max_tokens=50
            )
            
            print(f"✓ SUCCESS!")
            print(f"  Response: {response.content[:100]}...")
            
        except Exception as e:
            print(f"✗ FAILED: {str(e)}")
    
    print("\n" + "="*80)
    print("Recommendation")
    print("="*80)
    print("\nBased on test results, update your settings.py with working models.")

if __name__ == "__main__":
    asyncio.run(test_models())

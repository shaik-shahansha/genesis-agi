"""
Test OpenRouter free models and find working alternatives.

This script:
1. Fetches all available models from OpenRouter
2. Filters for free models ($0.00 pricing)
3. Tests a few to see which ones work
4. Recommends best free models for Genesis
"""

import requests
import json
from genesis.config.settings import get_settings

def get_free_models():
    """Fetch and display free models from OpenRouter."""
    
    print("\n" + "="*80)
    print("OpenRouter Free Models Check")
    print("="*80 + "\n")
    
    settings = get_settings()
    
    if not settings.openrouter_api_key:
        print("❌ No OpenRouter API key found!")
        print("   Set OPENROUTER_API_KEY in your .env file")
        print("   Get a free key from: https://openrouter.ai/keys\n")
        return
    
    print(f"✓ OpenRouter API key found: {settings.openrouter_api_key[:8]}...\n")
    
    # Fetch models
    print("Fetching models from OpenRouter API...")
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://github.com/BismuthBorealis/genesis",
                "X-Title": "Genesis AGI"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"✓ Fetched {len(data['data'])} models\n")
        
        # Filter free models
        free_models = []
        for model in data['data']:
            pricing = model.get('pricing', {})
            prompt_price = float(pricing.get('prompt', 1))
            completion_price = float(pricing.get('completion', 1))
            
            # Check if truly free (both prompt and completion are 0)
            if prompt_price == 0 and completion_price == 0:
                free_models.append({
                    'id': model['id'],
                    'name': model.get('name', 'Unknown'),
                    'context': model.get('context_length', 0),
                    'description': model.get('description', '')[:100]
                })
        
        print(f"Found {len(free_models)} FREE models:\n")
        print("-"*80)
        
        # Group by provider
        by_provider = {}
        for model in free_models:
            provider = model['id'].split('/')[0] if '/' in model['id'] else 'other'
            if provider not in by_provider:
                by_provider[provider] = []
            by_provider[provider].append(model)
        
        # Display organized by provider
        for provider, models in sorted(by_provider.items()):
            print(f"\n{provider.upper()} ({len(models)} models):")
            for model in models:
                print(f"  • {model['id']}")
                print(f"    Context: {model['context']:,} tokens")
                if model['description']:
                    print(f"    {model['description']}")
        
        # Recommend best ones
        print("\n" + "="*80)
        print("RECOMMENDED FREE MODELS FOR GENESIS")
        print("="*80 + "\n")
        
        recommendations = {
            "Reasoning (DeepSeek R1)": [
                "deepseek/deepseek-r1",
                "deepseek/deepseek-r1-distill-llama-70b"
            ],
            "Fast General (Qwen)": [
                "qwen/qwen-2.5-72b-instruct",
                "qwen/qwq-32b-preview"
            ],
            "Google (Gemini)": [
                "google/gemini-flash-1.5",
                "google/gemini-2.0-flash-thinking-exp:free"
            ],
            "Meta (Llama)": [
                "meta-llama/llama-3.2-90b-vision-instruct:free",
                "meta-llama/llama-3.1-405b-instruct:free"
            ]
        }
        
        for category, model_ids in recommendations.items():
            print(f"{category}:")
            for model_id in model_ids:
                # Check if this model exists in our free list
                found = any(m['id'] == model_id for m in free_models)
                status = "✓" if found else "✗"
                print(f"  {status} {model_id}")
            print()
        
        # Test a model
        print("="*80)
        print("TESTING A FREE MODEL")
        print("="*80 + "\n")
        
        # Try deepseek-r1 (should be free)
        test_model = "deepseek/deepseek-r1"
        print(f"Testing: {test_model}\n")
        
        test_response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://github.com/BismuthBorealis/genesis",
                "X-Title": "Genesis AGI",
                "Content-Type": "application/json"
            },
            json={
                "model": test_model,
                "messages": [
                    {"role": "user", "content": "Say 'Hello from Genesis!' in one sentence"}
                ],
                "max_tokens": 50
            },
            timeout=30
        )
        
        if test_response.status_code == 200:
            result = test_response.json()
            response_text = result['choices'][0]['message']['content']
            print(f"✓ SUCCESS! Model responded:\n  \"{response_text}\"\n")
            
            # Show recommended settings
            print("="*80)
            print("RECOMMENDED SETTINGS.PY CONFIGURATION")
            print("="*80 + "\n")
            print("Update your settings.py with these working free models:\n")
            print("    default_reasoning_model: str = \"deepseek/deepseek-r1\"")
            print("    default_fast_model: str = \"qwen/qwen-2.5-72b-instruct\"")
            print()
            
        else:
            print(f"❌ Test failed: {test_response.status_code}")
            print(f"   Response: {test_response.text}\n")
            
            # Try alternative
            print(f"Trying alternative: google/gemini-flash-1.5\n")
            test_response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/BismuthBorealis/genesis",
                    "X-Title": "Genesis AGI",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "google/gemini-flash-1.5",
                    "messages": [
                        {"role": "user", "content": "Say 'Hello from Genesis!' in one sentence"}
                    ],
                    "max_tokens": 50
                },
                timeout=30
            )
            
            if test_response.status_code == 200:
                result = test_response.json()
                response_text = result['choices'][0]['message']['content']
                print(f"✓ SUCCESS! Gemini responded:\n  \"{response_text}\"\n")
                print("Use: default_reasoning_model: str = \"google/gemini-flash-1.5\"")
            else:
                print(f"❌ Also failed: {test_response.status_code}")
                print(f"   Response: {test_response.text}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching models: {e}\n")
    except Exception as e:
        print(f"❌ Unexpected error: {e}\n")
    
    print("\n" + "="*80)
    print("IMPORTANT NOTE")
    print("="*80)
    print("""
OpenRouter free models have privacy requirements:
1. Go to: https://openrouter.ai/settings/privacy
2. Enable "Allow free models" or similar setting
3. Some free models may require data sharing for training

If you see 404 errors with ":free" suffix, try removing it:
  ❌ openrouter/deepseek/deepseek-r1-0528:free
  ✓ deepseek/deepseek-r1

The ":free" suffix is OLD syntax and no longer needed!
""")

if __name__ == "__main__":
    get_free_models()

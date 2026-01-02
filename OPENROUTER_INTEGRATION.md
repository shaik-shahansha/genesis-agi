# OpenRouter Integration - Summary

## Overview
Successfully integrated OpenRouter as the **recommended FREE provider** for Genesis AGI Framework. OpenRouter provides unified access to many AI models with several completely free options.

## What Was Added

### 1. New OpenRouter Provider (`genesis/models/openrouter_provider.py`)
- Created OpenRouter provider class similar to Groq provider
- Uses OpenAI-compatible API via `https://openrouter.ai/api/v1`
- Supports both streaming and non-streaming generation
- Handles function calling/tool use

### 2. Configuration Updates

#### Settings (`genesis/config/settings.py`)
- Added `openrouter_api_key` field
- Updated default models to use OpenRouter free models:
  - `DEFAULT_REASONING_MODEL=openrouter/deepseek/deepseek-r1-0528:free`
  - `DEFAULT_FAST_MODEL=openrouter/deepseek/deepseek-r1-0528:free`

#### Environment Files
- Updated `.env.example` with OpenRouter at the top (recommended)
- Updated CLI `genesis init` template with OpenRouter
- Updated `docker-compose.yml` with OpenRouter environment variable

### 3. Provider Registration (`genesis/models/orchestrator.py`)
- Added OpenRouter import
- Registered OpenRouter provider first (priority)
- Updated orchestrator documentation

### 4. CLI Updates (`genesis/cli/main.py`)
- **Made OpenRouter option #1** in interactive model selection
- Added 5 free model options:
  1. DeepSeek Chat (best for general tasks)
  2. Xiaomi MiMo V2 Flash (ultra-fast)
  3. Mistral Devstral 2 (best for coding)
  4. DeepSeek V3.1 Nex N1 (agent optimized)
  5. Llama 3.3 70B (large model)
- Renumbered other providers (Groq is now #2, etc.)

### 5. Web Playground Updates (`web-playground/app/create/page.tsx`)
- Added 5 OpenRouter models at the top of model selection with 🌟 emoji
- Set OpenRouter DeepSeek Chat as default model
- Added OpenRouter API key input section
- All free models clearly marked

### 6. Settings Tab (`web-playground/components/mind/SettingsTab.tsx`)
- Added OpenRouter to provider dropdown (first option with 🌟)
- Added 6 free OpenRouter models to model selection

### 7. Documentation Updates
- Updated `QUICKSTART.md` with OpenRouter as recommended option
- Updated `README.md` to include OpenRouter in tech stack

## Free Models Available via OpenRouter

All these models are **100% FREE** with unlimited usage:

1. **deepseek/deepseek-chat** - Best for general tasks, excellent quality
2. **xiaomi/mimo-v2-flash:free** - Ultra-fast, 256K context
3. **mistralai/devstral-2512:free** - Best for coding, 256K context
4. **nex-agi/deepseek-v3.1-nex-n1:free** - Optimized for agents & tools
5. **meta-llama/llama-3.3-70b-instruct:free** - Large 70B model
6. **allenai/olmo-3.1-32b-think:free** - Deep reasoning model

## How to Use

### For Users

#### CLI:
```bash
genesis birth my-mind
# Select option 1 (OpenRouter)
# Enter API key from https://openrouter.ai/keys
# Choose a free model
```

#### Web Playground:
1. Go to Create Mind page
2. Select any OpenRouter model (marked with 🌟)
3. Enter OpenRouter API key in Step 3
4. Create your Mind

### For Developers

```python
from genesis.core.mind import Mind
from genesis.core.intelligence import Intelligence

intelligence = Intelligence(
    reasoning_model="openrouter/deepseek/deepseek-r1-0528:free",
    fast_model="openrouter/deepseek/deepseek-r1-0528:free",
    api_keys={"openrouter": "sk-or-v1-..."}
)

mind = Mind.birth(
    name="TestMind",
    intelligence=intelligence,
    creator_email="dev@example.com"
)
```

## Benefits

1. **Free Models**: Many high-quality models available for free
2. **Variety**: Access to DeepSeek, Llama, Mistral, Qwen, and more
3. **No Rate Limits**: Free tier has no strict rate limits
4. **Unified API**: Single API key for multiple model providers
5. **Easy to Get**: Quick signup at https://openrouter.ai/keys

## Migration Notes

### From Groq
- Replace `groq/` prefix with `openrouter/`
- Change model names to OpenRouter format
- Update `GROQ_API_KEY` to `OPENROUTER_API_KEY`

### Example:
```bash
# Old (Groq)
DEFAULT_REASONING_MODEL=groq/llama-3.3-70b-versatile

# New (OpenRouter)
DEFAULT_REASONING_MODEL=openrouter/deepseek/deepseek-r1-0528:free
```

## Testing

To test the integration:

```bash
# 1. Get API key from https://openrouter.ai/keys
export OPENROUTER_API_KEY=sk-or-v1-...

# 2. Test with CLI
genesis birth test-mind

# 3. Test with Python
python -c "
from genesis.models.orchestrator import ModelOrchestrator
import asyncio

async def test():
    orch = ModelOrchestrator({'openrouter': 'sk-or-v1-...'})
    response = await orch.generate(
        messages=[{'role': 'user', 'content': 'Hello!'}],
        model='openrouter/deepseek/deepseek-r1-0528:free'
    )
    print(response.content)

asyncio.run(test())
"
```

## Files Modified

1. `genesis/models/openrouter_provider.py` - NEW
2. `genesis/models/orchestrator.py` - Updated
3. `genesis/config/settings.py` - Updated
4. `genesis/cli/main.py` - Updated
5. `.env.example` - Updated
6. `docker-compose.yml` - Updated
7. `QUICKSTART.md` - Updated
8. `README.md` - Updated
9. `web-playground/app/create/page.tsx` - Updated
10. `web-playground/components/mind/SettingsTab.tsx` - Updated

## API Reference

### OpenRouter Provider Class

```python
from genesis.models.openrouter_provider import OpenRouterProvider

provider = OpenRouterProvider(api_key="sk-or-v1-...")

# Generate
response = await provider.generate(
    messages=[{"role": "user", "content": "Hello"}],
    model="deepseek/deepseek-chat",
    temperature=0.7,
    max_tokens=1000
)

# Stream
async for chunk in provider.stream_generate(
    messages=[{"role": "user", "content": "Hello"}],
    model="xiaomi/mimo-v2-flash:free"
):
    print(chunk, end="")
```

## Troubleshooting

### "OpenRouter API key not configured"
- Set `OPENROUTER_API_KEY` in `.env` file
- Or pass `api_keys={'openrouter': 'sk-or-v1-...'}` to Intelligence

### "Model not found"
- Check model name format: `openrouter/provider/model-name`
- Verify model is free: add `:free` suffix if needed
- See available models: https://openrouter.ai/models?order=pricing-low-to-high

### Import errors
- Run `pip install -e .` to install/update dependencies
- Restart Python/VS Code to refresh imports

## Next Steps

1. Users can now use FREE OpenRouter models by default
2. No need to pay for API access initially
3. Can upgrade to paid models later if needed
4. Compatible with all existing Genesis features

## Links

- OpenRouter Website: https://openrouter.ai/
- Get API Key: https://openrouter.ai/keys
- Free Models: https://openrouter.ai/models?order=pricing-low-to-high
- Documentation: https://openrouter.ai/docs

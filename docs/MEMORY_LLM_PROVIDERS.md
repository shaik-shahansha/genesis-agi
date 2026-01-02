# Enhanced Memory System - LLM Provider Guide

## Overview

Genesis's enhanced memory system is **100% LLM agnostic**! You can use ANY LLM provider:
- [Done] **Groq** (fastest, free tier available)
- [Done] **OpenAI** (GPT-4, GPT-4o, GPT-3.5)
- [Done] **Anthropic** (Claude models)
- [Done] **Ollama** (100% local, private)
- [Done] **Google Gemini** (Gemini 1.5 Pro/Flash)
- [Done] **Any other provider** supported by Genesis

## Memory Components

The enhanced memory system includes 4 major components:

### 1. **mem0 Compression** (90% Token Savings)
- Reduces token usage by 90%
- 91% faster retrieval
- +26% accuracy improvement
- **Optional**: Requires embeddings (Ollama or OpenAI)

### 2. **Automatic Memory Extraction** (Agno Pattern)
- LLM-powered extraction from conversations
- Zero manual effort
- Works with ANY LLM provider
- **Always enabled** (no extra dependencies)

### 3. **Core Memory Blocks** (Letta Pattern)
- Persistent in-context memory
- Persona, Human, Context blocks
- Works out of the box
- **Always enabled**

### 4. **Agent Self-Editing** (Letta Pattern)
- Memory tools for autonomous agents
- Create, edit, append, delete memories
- **Always enabled**

## Configuration Options

### Default Setup (No Extra Setup Required)
```bash
# Works out of the box with ANY LLM
genesis birth my-mind \
  --reasoning-model groq/llama-3.3-70b-versatile \
  --email your@email.com \
  --purpose "Your purpose here"
```

**What you get:**
- [Done] Automatic memory extraction
- [Done] Core memory blocks
- [Done] Agent self-editing
- ⚠️ No mem0 compression (requires embeddings)

### Enable mem0 Compression (90% Token Savings)

**Option 1: Use Ollama (Recommended - Free & Local)**
```bash
# 1. Install Ollama: https://ollama.ai/download
# 2. Start Ollama
ollama serve

# 3. Pull embedding model
ollama pull nomic-embed-text

# 4. Enable compression
export GENESIS_MEMORY_ENABLE_COMPRESSION=true

# 5. Create Mind
genesis birth my-mind --reasoning-model groq/llama-3.3-70b-versatile
```

**Option 2: Use OpenAI for Embeddings**
```bash
# 1. Set OpenAI API key
export OPENAI_API_KEY=sk-...

# 2. Enable compression
export GENESIS_MEMORY_ENABLE_COMPRESSION=true

# 3. Create Mind with ANY LLM
genesis birth my-mind --reasoning-model groq/llama-3.3-70b-versatile
```

## Supported LLM Providers for mem0

mem0 compression works with **ALL** these LLM providers:

| Provider | API Key Required | Example Model |
|----------|------------------|---------------|
| **Groq** | GROQ_API_KEY | `groq/llama-3.3-70b-versatile` |
| **OpenAI** | OPENAI_API_KEY | `openai/gpt-4` |
| **Anthropic** | ANTHROPIC_API_KEY | `anthropic/claude-3-5-sonnet-20241022` |
| **Ollama** | None (local) | `ollama/llama3.2` |
| **Gemini** | GEMINI_API_KEY | `gemini/gemini-1.5-pro` |
| **Azure** | AZURE_OPENAI_API_KEY | `azure/gpt-4` |
| **Together** | TOGETHER_API_KEY | `together/mixtral-8x7b` |
| **Mistral** | MISTRAL_API_KEY | `mistral/mistral-large` |

## Environment Variables

### Required (for mem0 compression only)
```bash
# Choose ONE of these for embeddings:
OPENAI_API_KEY=sk-...           # If using OpenAI embeddings
# OR
# Run Ollama locally (no API key needed)
```

### Optional
```bash
# Memory Configuration
GENESIS_MEMORY_ENABLE_COMPRESSION=true     # Enable 90% token savings
GENESIS_MEMORY_ENABLE_AUTO_MEMORIES=true   # Enable automatic extraction (default: true)
GENESIS_MEMORY_CORE_MEMORY_ENABLED=true    # Enable core memory blocks (default: true)
GENESIS_MEMORY_ENABLE_MEMORY_TOOLS=true    # Enable agent self-editing (default: true)

# mem0 Platform (for cloud-hosted mem0)
GENESIS_MEMORY_MEM0_API_KEY=m0-...         # Optional: mem0 Platform API key

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434     # Custom Ollama URL (default shown)
```

## Quick Start Examples

### Example 1: Groq + No Compression (Fastest Setup)
```bash
export GROQ_API_KEY=gsk_...

genesis birth quick-mind \
  --reasoning-model groq/llama-3.3-70b-versatile \
  --email you@example.com
```

### Example 2: Groq + Ollama Compression (Best Performance)
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Create Mind
export GROQ_API_KEY=gsk_...
export GENESIS_MEMORY_ENABLE_COMPRESSION=true

genesis birth optimized-mind \
  --reasoning-model groq/llama-3.3-70b-versatile \
  --email you@example.com
```

### Example 3: Anthropic + OpenAI Embeddings
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...  # For embeddings only
export GENESIS_MEMORY_ENABLE_COMPRESSION=true

genesis birth claude-mind \
  --reasoning-model anthropic/claude-3-5-sonnet-20241022 \
  --email you@example.com
```

### Example 4: 100% Local with Ollama
```bash
# Start Ollama
ollama serve

# Pull models
ollama pull llama3.2
ollama pull nomic-embed-text

export GENESIS_MEMORY_ENABLE_COMPRESSION=true

genesis birth local-mind \
  --reasoning-model ollama/llama3.2 \
  --email you@example.com
```

## Performance Comparison

### Without mem0 Compression
- Token Usage: **100%** baseline
- Retrieval Speed: baseline
- Accuracy: baseline
- Setup: Zero configuration

### With mem0 Compression
- Token Usage: **10%** (90% reduction!)
- Retrieval Speed: **11x faster**
- Accuracy: **+26%** improvement
- Setup: Requires Ollama OR OpenAI

## Troubleshooting

### "Failed to initialize mem0: The api_key client option must be set"

**Cause:** mem0 compression is enabled but no embeddings provider is configured.

**Solution:** Choose one:
1. **Disable compression** (still get auto-extraction, core memory, self-editing):
   ```bash
   export GENESIS_MEMORY_ENABLE_COMPRESSION=false
   ```

2. **Install Ollama** (free, local):
   ```bash
   # Install from https://ollama.ai/download
   ollama serve
   ollama pull nomic-embed-text
   export GENESIS_MEMORY_ENABLE_COMPRESSION=true
   ```

3. **Use OpenAI for embeddings**:
   ```bash
   export OPENAI_API_KEY=sk-...
   export GENESIS_MEMORY_ENABLE_COMPRESSION=true
   ```

### "MemoryExtractor: 'ModelOrchestrator' object has no attribute 'get_client'"

**Status:** [Done] Fixed in latest version

**Solution:** Update to latest Genesis version or manually fix:
```bash
cd genesis
git pull origin main
```

### mem0 compression not working with Groq

**Status:** [Done] Fixed - Groq now fully supported!

mem0 compression now works with Groq for the LLM. You just need:
- Groq API key for reasoning/generation
- Ollama OR OpenAI for embeddings only

## Best Practices

### For Development/Testing
- Use Groq (fastest, free tier)
- Disable compression for quick iteration
- Enable auto-extraction (minimal overhead)

### For Production
- Enable mem0 compression (90% cost savings)
- Use Ollama for embeddings (free, private)
- Configure monitoring for memory growth

### For Privacy-Focused Applications
- Use 100% local setup with Ollama
- Enable compression with local embeddings
- All memory stays on your machine

## Feature Matrix

| Feature | Default Enabled | Requires |
|---------|----------------|----------|
| **Automatic Extraction** | [Done] Yes | Any LLM |
| **Core Memory Blocks** | [Done] Yes | Nothing |
| **Agent Self-Editing** | [Done] Yes | Nothing |
| **mem0 Compression** | ⚠️ No | Ollama OR OpenAI |

## Summary

**You asked:** "do we need openAI key for this, cant we use any llm api?"

**Answer:** 
- [Done] **You can use ANY LLM provider** for the main Mind reasoning (Groq, Anthropic, Ollama, Gemini, etc.)
- [Done] **3 out of 4 memory features** work with zero extra setup
- ⚠️ **mem0 compression** (90% token savings) requires embeddings:
  - Option 1: Ollama (free, local, recommended)
  - Option 2: OpenAI (only for embeddings, not for main LLM)

**The system is truly LLM agnostic!** The only OpenAI dependency is optional and only for embeddings in mem0 compression.

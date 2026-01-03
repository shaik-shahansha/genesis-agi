# Genesis Quick Reference - Plugin System & Web Playground

## 🔌 Plugin System Quick Reference

### List Available Plugins
```bash
genesis plugin list-available
```

### Add Plugin to Mind
```bash
genesis plugin add MyMind browser_use
genesis plugin add MyMind perplexity_search --api-key pplx-...
```

### List Mind's Plugins
```bash
genesis plugin list MyMind
```

### Remove Plugin
```bash
genesis plugin remove MyMind browser_use
```

### Python API
```python
from genesis import Mind
from genesis.core.mind_config import MindConfig
from genesis.plugins.browser_use_plugin import BrowserUsePlugin

# Add plugin at birth
config = MindConfig()
config.add_plugin(BrowserUsePlugin())
mind = Mind.birth("WebExplorer", config=config)

# Or use registry
from genesis.plugins.registry import PluginRegistry
plugin = PluginRegistry.get("browser_use")
```

## 🌐 Browser Automation Quick Start

### Installation
```bash
pip install browser-use playwright langchain-openai
playwright install chromium
```

### Add to Mind
```bash
genesis plugin add MyMind browser_use
```

### Use in Chat
```bash
genesis chat MyMind
> Can you scrape the product prices from example.com?
> Fill out the contact form on website.com with my info
> Take a screenshot of news.ycombinator.com
```

### Automatic Invocation
The browser plugin is automatically invoked when you ask for:
- Web scraping
- Form filling
- Page navigation
- Element interaction
- Data extraction

## 🎮 Web Playground Quick Reference

### Access Tabs
Navigate to `http://localhost:3000/mind/{mind_id}` and click tabs:

**Thinking Tab:**
- Enter prompt and press Ctrl+Enter
- View reasoning steps
- See final response

**Autonomy Tab:**
- Adjust initiative level (0-10)
- Enable/disable autonomous actions
- Set action limits
- View recent actions

**LLM Calls Tab:**
- View token usage and costs
- See provider breakdown
- Check call history

**Plugins Tab:**
- Browse available plugins
- Filter by category
- One-click install
- Configure API keys

### Start Web Playground
```bash
cd web-playground
npm install
npm run dev
```

Access at: `http://localhost:3000`

## 📊 Monitoring & Analytics

### LLM Call Tracking
```bash
# Via API
curl http://localhost:8000/api/v1/minds/{mind_id}/llm-calls?limit=50
```

### Autonomous Actions
```bash
# Via API
curl http://localhost:8000/api/v1/minds/{mind_id}/autonomous-actions?limit=20
```

### Available Plugins
```bash
# Via API
curl http://localhost:8000/api/v1/minds/plugins/available
```

## 🛠️ Custom Plugin Creation

### Minimal Plugin
```python
from genesis.plugins.base import Plugin
from typing import List

class MyPlugin(Plugin):
    def get_name(self) -> str:
        return "my_plugin"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_description(self) -> str:
        return "My custom plugin"
    
    def get_capabilities(self) -> List[str]:
        return ["my_capability"]
    
    def on_init(self, mind):
        # Initialize plugin
        mind.my_feature = MyFeature()

# Register
from genesis.plugins.registry import PluginRegistry
PluginRegistry.register(MyPlugin, category="enhancement")
```

## 🔧 Troubleshooting

### Plugin Not Found
```bash
# Check available plugins
genesis plugin list-available

# Verify plugin name spelling
```

### Browser Plugin Not Working
```bash
# Reinstall dependencies
pip install --upgrade browser-use playwright langchain-openai
playwright install chromium

# Check if plugin is added
genesis plugin list MyMind
```

### Web Playground Tabs Empty
- Ensure backend API is running on port 8000
- Check browser console for errors
- Verify Mind exists: `genesis list`

### LLM Calls Tab Shows No Data
- Feature requires backend logging
- Chat with Mind first to generate data
- Check logs: `genesis logs MyMind`

## 📚 Documentation Links

- **Full Plugin Guide**: [PLUGIN_AND_WEB_ENHANCEMENT_SUMMARY.md](PLUGIN_AND_WEB_ENHANCEMENT_SUMMARY.md)
- **Main README**: [README.md](README.md)
- **CLI Commands**: [docs/CLI_COMMANDS.md](docs/CLI_COMMANDS.md)
- **API Reference**: [docs/API.md](docs/API.md)
- **Advanced Features**: [docs/ADVANCED.md](docs/ADVANCED.md)

## ⚡ Common Use Cases

### Web Scraping
```bash
genesis chat MyMind
> Scrape all article titles from news.ycombinator.com
```

### Form Filling
```bash
genesis chat MyMind
> Fill out the contact form on example.com with:
> Name: John Doe
> Email: john@example.com
> Message: Hello!
```

### Data Extraction
```bash
genesis chat MyMind
> Extract all product prices from store.example.com
```

### Autonomous Action Control
1. Go to Web Playground → Mind → Autonomy
2. Set Initiative Level: 7
3. Enable "Autonomous Actions"
4. Set Max Actions Per Hour: 50
5. Click "Save Settings"

### Monitor LLM Usage
1. Go to Web Playground → Mind → LLM Calls
2. View statistics dashboard
3. Check provider breakdown
4. Review recent calls

## 🎯 Best Practices

### Plugins
- Start with Core plugins (lifecycle, GEN, tasks, workspace)
- Add Integration plugins as needed (browser_use, perplexity_search)
- Test plugins before production use
- Monitor plugin performance

### Browser Automation
- Use specific selectors for reliable element location
- Handle errors gracefully
- Respect robots.txt and rate limits
- Consider using stealth mode for CAPTCHAs

### Web Playground
- Enable auto-refresh on Logs tab for monitoring
- Use Thinking tab to debug reasoning
- Monitor LLM costs regularly
- Adjust autonomy levels based on needs

### Monitoring
- Check LLM Calls tab weekly for cost optimization
- Review Autonomous Actions for unexpected behavior
- Use Logs tab for debugging issues
- Export logs for long-term analysis

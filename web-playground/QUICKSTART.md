# Genesis Web Playground - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
```bash
# Check Node.js version (need 18+)
node --version

# Verify npm
npm --version
```

### Step 1: Install Dependencies
```bash
cd web-playground
npm install
```

### Step 2: Configure API URL
Create `.env.local` file:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 3: Start Development Server
```bash
npm run dev
```

Visit: **http://localhost:3000**

### Step 4: Ensure API is Running
In another terminal:
```bash
cd ..  # Back to genesis root
genesis server  # Start API on port 8000
```

## 🎯 First Steps

### 1. Create Your First Mind

Click **"✨ Birth New Mind"** and follow the wizard:

**Step 1 - Identity:**
- Enter a name (e.g., "Atlas")
- Choose a personality template
- Click "Next"

**Step 2 - Models:**
- Select "Groq Llama 3.1 70B" (Free & Fast!)
- Click "Next"

**Step 3 - Advanced:**
- Enable "Consciousness Engine v2" ✓
- Enable "LLM Response Cache" ✓
- Click "✨ Birth Mind"

### 2. Start Chatting

- You'll be redirected to the chat interface
- Type a message and press Enter
- Watch the consciousness orb change with emotions!
- Use Shift+Enter for multi-line messages

### 3. Explore Mind Profile

Click **"📊 Dashboard"** to see:
- Overview with stats
- Memories browser
- Settings

## 🎨 Interface Overview

### Homepage
```
┌────────────────────────────────────┐
│  Stats Cards (Minds, Memories...)  │
│  Active Minds Grid                 │
│  Activity Feed                     │
│  Quick Actions                     │
└────────────────────────────────────┘
```

### Chat Interface
```
┌────────────────────────────────────┐
│  [Orb] Mind Name - Emotion         │
│  Messages with Markdown Support    │
│  Typing Indicators                 │
│  Message Input                     │
└────────────────────────────────────┘
```

### Mind Profile
```
┌────────────────────────────────────┐
│  Large Consciousness Orb + Stats   │
│  [Overview | Memories | Settings]  │
│  Detailed Analytics                │
│  Actions & Settings                │
└────────────────────────────────────┘
```

## 💡 Pro Tips

### Chat Interface
- **Shift+Enter**: New line without sending
- **Markdown**: Use `**bold**`, `*italic*`, `` `code` ``
- **Code Blocks**: Wrap in `` ``` ``
- **Export**: Save chat history to file

### Creating Minds
- **Free Option**: Use Groq for zero cost
- **Local Option**: Use Ollama for privacy
- **Premium**: Use GPT-4 for best quality
- **Enable Cache**: Save 90% on costs

### Performance
- Keep API server running in background
- Enable caching for faster responses
- Use Consciousness Engine v2 for efficiency
- Monitor system status on homepage

## 🔧 Troubleshooting

### "Cannot connect to API"
[Done] **Solution**: Make sure API server is running
```bash
genesis server
```

### "WebSocket connection failed"
[Done] **Solution**: Check API URL in `.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### "Mind creation failed"
[Done] **Solution**: Verify you have API keys configured
```bash
# Check .env in genesis root
cat ../.env
```

### Page won't load
[Done] **Solution**: Clear browser cache and restart dev server
```bash
# Stop server (Ctrl+C)
rm -rf .next
npm run dev
```

### Styling looks broken
[Done] **Solution**: Make sure all dependencies are installed
```bash
npm install
```

## 📚 Learn More

### Key Features to Explore

1. **Dashboard Stats** - Real-time metrics
2. **Consciousness Orbs** - Emotional visualization
3. **Memory Browser** - Search 5 memory types
4. **3-Step Wizard** - Easy mind creation
5. **Markdown Chat** - Rich formatting
6. **Profile Analytics** - Detailed insights

### Advanced Features

- **Autonomy Levels**: Control mind proactivity
- **Model Selection**: Choose AI backends
- **Consciousness Modes**: Configure thinking patterns
- **Cache System**: Optimize costs
- **Export/Import**: Save chat logs

## 🎯 Common Tasks

### Change Mind's Model
1. Go to Mind Profile
2. Click "Settings" tab
3. Update model selection
4. Save changes

### Export Chat History
1. Open chat interface
2. Click "💾 Export" in sidebar
3. Save `.txt` file

### Clear Mind's Memories
1. Go to Mind Profile
2. Click "Settings" tab
3. Scroll to "Danger Zone"
4. Click "🗑️ Clear All Memories"
5. Confirm action

## 🚀 Next Steps

### Explore More
- Browse the marketplace (coming soon)
- Join environments (coming soon)
- Create multiple minds
- Experiment with templates
- Try different models
- Enable autonomous mode

### Customize
- Adjust theme colors in `globals.css`
- Modify templates in `/components`
- Add custom personality types
- Extend the API client

### Deploy
```bash
# Production build
npm run build

# Start production server
npm start

# Or deploy to Vercel
vercel
```

## 📖 Documentation

- **Full Guide**: See [README.md](README.md)
- **Design System**: See [WEB_PLAYGROUND_VISUAL_GUIDE.md](../WEB_PLAYGROUND_VISUAL_GUIDE.md)
- **Transformation**: See [WEB_PLAYGROUND_TRANSFORMATION.md](../WEB_PLAYGROUND_TRANSFORMATION.md)
- **API Docs**: http://localhost:8000/docs

## 💬 Support

### Issues?
1. Check API server is running
2. Verify environment variables
3. Check browser console for errors
4. Review error messages

### Need Help?
- GitHub Issues: [Genesis-AGI Issues](https://github.com/shaik-shahansha/genesis-agi/issues)
- Documentation: [Main README](../README.md)
- Examples: [examples/](../examples/)

---

**Enjoy creating your digital beings!** 🧠✨

*The playground is production-ready and rivals OpenAI & Azure AI Studio*

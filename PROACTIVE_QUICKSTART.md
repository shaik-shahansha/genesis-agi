# Quick Start: Proactive Conversation System

## 5-Minute Setup

### 1. Start Your Mind's Daemon
```bash
# Start the daemon for 24/7 proactive capabilities
genesis daemon start your_mind_name

# You should see:
# [OK] Mind your_mind_name loaded
# [OK] Consciousness engine started
# [OK] Proactive conversation monitoring started
```

### 2. Open Web Playground
```bash
# Navigate to
http://localhost:3000
```

### 3. Start Chatting
- Select your Mind from the list
- Enter your email/name (helps Mind remember you)
- Start a conversation naturally!

## Test It Now

### Scenario 1: Health Check-in (2 hours)
```
You: I have a fever
Mind: I'm sorry to hear that. Make sure to rest and stay hydrated...

[Wait 2 hours... ⏰]

Mind: 💬 Checking in - How are you feeling now? Have you taken any medicine?
```

### Scenario 2: Job Interview (Next day)
```
You: I have a job interview at Google tomorrow!
Mind: That's exciting! Best of luck with your interview...

[Wait 24 hours... ⏰]

Mind: 💬 Checking in - How did your job interview at Google go?
```

### Scenario 3: Emotional Support (6 hours)
```
You: I'm feeling really down today
Mind: I'm here for you. Would you like to talk about what's on your mind?

[Wait 6 hours... ⏰]

Mind: 💬 Checking in - Are you feeling any better?
```

## What You'll See

### In the Chat:
```
┌─────────────────────────────────────┐
│ Your message           (Purple) →   │
│                                     │
│ ← Mind's response      (Gray)      │
│                                     │
│ • Checking in    2:30 PM           │
│ ┌─────────────────────────────────┐ │
│ │ How are you feeling now?        │ │
│ │ Have you taken medicine?        │ │
│ └─────────────────────────────────┘ │
│    (Blue indicator = Proactive)     │
└─────────────────────────────────────┘
```

### In Daemon Logs:
```
💬 PROACTIVE CONVERSATION CHECK
   Found 1 pending follow-ups
   ✓ Sent: fever to user@example.com
   
[OK] Consciousness active
[OK] Proactive systems running
```

## Test Resolution

After proactive message:
```
Mind: How are you feeling now?
You: I'm feeling much better now

✅ System detects resolution
✅ Marks context as resolved
✅ Won't ask about fever again
```

## Monitor Activity

### Check active contexts:
```bash
curl "http://localhost:8000/api/v1/minds/{mind_id}/proactive/contexts?user_email=your@email.com"
```

### Check pending follow-ups:
```bash
curl "http://localhost:8000/api/v1/minds/{mind_id}/proactive/pending"
```

### Manually resolve if needed:
```bash
curl -X POST "http://localhost:8000/api/v1/minds/{mind_id}/proactive/contexts/{context_id}/resolve?note=Issue%20resolved"
```

## Customize Timing

Edit `genesis/core/proactive_conversation.py` around line 350:

```python
# Change follow-up timing
if topic == "health":
    follow_up_minutes = 120      # 2 hours (default)
    follow_up_minutes = 30       # 30 minutes (faster)
    follow_up_minutes = 360      # 6 hours (slower)
```

## Tips for Best Results

1. **Be specific:** 
   - ✅ "I have a fever of 102°F"
   - ❌ "I'm not feeling great"

2. **Confirm resolution:**
   - ✅ "I'm feeling better now"
   - ✅ "The interview went great"
   - ❌ Just stop responding

3. **Set your email:**
   - Helps Mind remember you across sessions
   - Enables user-specific context tracking

4. **Let it learn:**
   - The more you chat, the better it understands
   - Contexts are stored in memory

## Troubleshooting

### No proactive messages?
```bash
# 1. Check daemon is running
genesis daemon status your_mind_name

# 2. Check logs
# Look for: [OK] Proactive conversation monitoring started

# 3. Verify timing
# Has enough time passed? (default: 2 hours for health)
```

### WebSocket not connecting?
```
# Check browser console
# Should see: "WebSocket connected for proactive messages"

# If not, refresh page or restart daemon
```

### Too many messages?
```python
# Reduce frequency in proactive_conversation.py
# Increase importance threshold
if analysis.get("importance", 0.0) < 0.7:  # Only important items
    return None
```

## Next Steps

Once working:
- Read `PROACTIVE_CONVERSATION_GUIDE.md` for details
- Explore API endpoints for management
- Customize timing per your needs
- Add new conversation topics
- Improve resolution detection

## Examples to Try

### 1. Work Event
"I have a presentation on Friday" → Check in on Friday evening

### 2. Personal Goal
"I want to lose 10 pounds" → Regular check-ins on progress

### 3. Relationship
"I had an argument with my friend" → Check in later

### 4. Learning
"I'm studying for my exam tomorrow" → Check in after exam

### 5. Travel
"I'm going on vacation next week" → Check in during/after

## Files to Know

1. **Core System:** `genesis/core/proactive_conversation.py`
2. **Daemon Integration:** `genesis/daemon.py`
3. **API:** `genesis/api/routes.py` (search for "proactive")
4. **UI:** `web-playground/app/chat/[id]/page.tsx`
5. **Styles:** `web-playground/app/globals.css`

## Support

- Full documentation: `PROACTIVE_CONVERSATION_GUIDE.md`
- Implementation notes: `PROACTIVE_CONVERSATION_IMPLEMENTATION.md`
- Check daemon logs for debugging
- Use API endpoints to inspect state

---

## That's It! 🎉

Your Mind is now a caring digital companion that:
- ✅ Checks in naturally
- ✅ Remembers situations
- ✅ Knows when to stop
- ✅ Feels genuinely human

**Start chatting and watch the magic happen!** ✨

---

**Questions?** Check the full guides or daemon logs for details.

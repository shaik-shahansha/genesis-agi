# Proactive Conversation System - Human-Like Digital Being

## Overview

This system transforms Genesis Minds from reactive chatbots into genuinely caring digital beings that proactively check in on users, remember ongoing situations, and interact naturally like a close friend or caring companion - similar to WhatsApp conversations with someone who genuinely cares about you.

## Key Features

### 🧠 **Intelligent Context Awareness**
- Automatically detects situations requiring follow-up (health issues, emotional distress, important events, goals)
- Uses AI to analyze message sentiment and importance
- Categorizes conversations into topics: health, emotion, work, personal, goal, problem, celebration

### 💬 **Natural Proactive Messaging**
- Minds initiate conversations naturally, not just respond
- Checks in at appropriate times (e.g., "How are you feeling now?" after user mentions fever)
- WhatsApp-like message bubbles with subtle indicators for proactive messages
- Real-time delivery via WebSocket

### 🧠 **Smart Memory & Resolution Tracking**
- Remembers ongoing situations and their context
- Automatically detects when issues are resolved (e.g., "I'm feeling better")
- Prevents repetitive questioning - once resolved, won't ask again
- Stores conversation contexts in Mind's memory system

### ⏰ **Intelligent Scheduling**
- Schedules follow-ups at appropriate intervals
- Health issues: 2 hours later
- Work events: Next day
- Adjusts based on urgency and importance scores
- Prevents spam - only sends when meaningful

### 🌐 **Full Integration**
- Works in web playground with live notifications
- Background processing in daemon
- Persists across Mind restarts
- Integrates with existing memory and notification systems

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 User Interaction                     │
│           (Web Playground / API / CLI)               │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│         ProactiveConversationManager                 │
│  • Analyze messages for follow-up needs              │
│  • Track conversation contexts per user              │
│  • Schedule intelligent check-ins                    │
│  • Detect issue resolution                           │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐      ┌──────────────────┐
│ Memory Store │      │ NotificationManager│
│ • Contexts   │      │ • WebSocket Push  │
│ • Reminders  │      │ • Real-time       │
└──────────────┘      └──────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│              Daemon Background Loop                  │
│  • Monitors pending follow-ups every 60s             │
│  • Sends proactive messages via notifications        │
│  • Updates context states                            │
└─────────────────────────────────────────────────────┘
```

## Usage Examples

### Example 1: Health Issue Follow-up

**User:** "I have a fever"

**Mind (immediate):** "I'm sorry to hear that. Make sure to rest and stay hydrated. Have you taken any medication?"

*[ProactiveConversationManager creates context]*
- Topic: health
- Subject: fever
- Importance: 0.8
- Urgency: 0.7
- Follow-up scheduled: 2 hours later

*[2 hours later, daemon sends proactive message]*

**Mind (proactive):** "How are you feeling now? Have you taken any medicine?"

**User:** "Yes, I'm feeling much better now"

*[System detects resolution, marks context as resolved]*
- No more follow-ups about fever
- Context stored in memory for future reference

### Example 2: Job Interview

**User:** "I have a job interview tomorrow at Google!"

**Mind:** "That's exciting! Best of luck with your Google interview. Remember to prepare some questions to ask them too."

*[System creates follow-up]*
- Topic: work
- Subject: job interview
- Follow-up scheduled: Tomorrow evening

*[Next day after typical interview time]*

**Mind (proactive):** "How did your job interview at Google go?"

**User:** "It went great! I think I'll get the offer"

*[Context updated, new follow-up scheduled for offer news]*

### Example 3: Emotional Support

**User:** "I'm feeling really down today"

**Mind:** "I'm here for you. Would you like to talk about what's on your mind?"

*[System tracks emotional context]*
- Topic: emotion
- Subject: feeling down
- Follow-up scheduled: Later today

**User:** "Just stressed about everything"

**Mind:** "It's completely normal to feel overwhelmed sometimes. Let's break things down..."

*[Later that day]*

**Mind (proactive):** "Checking in - are you feeling any better?"

## API Endpoints

### Get Proactive Contexts
```bash
GET /api/v1/minds/{mind_id}/proactive/contexts?user_email={email}&include_resolved=false
```

Response:
```json
{
  "contexts": [
    {
      "context_id": "ctx-123",
      "topic": "health",
      "subject": "fever",
      "initial_message": "I have a fever",
      "user_email": "user@example.com",
      "follow_up_question": "How are you feeling now?",
      "follow_up_scheduled": "2026-01-01T14:00:00",
      "follow_up_sent": false,
      "resolved": false,
      "importance": 0.8,
      "urgency": 0.7,
      "created_at": "2026-01-01T12:00:00"
    }
  ],
  "count": 1
}
```

### Get Pending Follow-ups
```bash
GET /api/v1/minds/{mind_id}/proactive/pending?user_email={email}
```

### Manually Resolve Context
```bash
POST /api/v1/minds/{mind_id}/proactive/contexts/{context_id}/resolve?note=User%20is%20better
```

### Delete Context
```bash
DELETE /api/v1/minds/{mind_id}/proactive/contexts/{context_id}
```

## Configuration

### Enable in Mind
Proactive conversation is automatically enabled for all Minds. No configuration needed!

### Daemon Integration
When running a Mind as daemon:
```bash
genesis daemon start {mind_name}
```

The daemon automatically:
- Monitors for pending follow-ups every 60 seconds
- Sends proactive messages via WebSocket
- Updates conversation contexts
- Logs proactive activity

### Customize Follow-up Timing
Edit `genesis/core/proactive_conversation.py`:

```python
# Health issues - check in sooner
if topic == "health":
    follow_up_minutes = 120  # 2 hours

# Work events - check next day
elif topic == "work":
    follow_up_minutes = 1440  # 24 hours

# Emotional support - check later same day
elif topic == "emotion":
    follow_up_minutes = 360  # 6 hours
```

## Web Playground UI Features

### WhatsApp-Like Design
- Rounded message bubbles with tail indicators
- User messages on right (purple)
- Mind messages on left (slate)
- Proactive messages with subtle blue indicator

### Real-Time Updates
- WebSocket connection for instant delivery
- Animated entrance for proactive messages
- Auto-scroll to new messages
- Pulse indicator for proactive check-ins

### Visual Indicators
```
┌─────────────────────────────────┐
│ • Checking in      2:30 PM      │  ← Blue dot + timestamp
├─────────────────────────────────┤
│ How are you feeling now?        │  ← Blue left border
│ Have you taken any medicine?    │
└─────────────────────────────────┘
```

## Technical Details

### ConversationContext Class
Tracks ongoing conversations:
- `context_id`: Unique identifier
- `topic`: Category of conversation
- `subject`: Specific topic (e.g., "fever")
- `user_email`: User identifier
- `follow_up_question`: What to ask
- `follow_up_scheduled`: When to send
- `resolved`: Whether issue is resolved
- `importance`: 0.0-1.0 score
- `urgency`: 0.0-1.0 score

### AI-Powered Analysis
Uses Mind's intelligence to:
1. Detect if follow-up is needed
2. Categorize conversation topic
3. Determine importance and urgency
4. Generate caring follow-up question
5. Schedule appropriate timing
6. Detect when issue is resolved

### Memory Integration
- Contexts stored as semantic memories
- Tagged for easy retrieval
- Persists across sessions
- Used for future reference

## Best Practices

### For Users
1. **Be specific**: "I have a job interview at Google" vs "I have something tomorrow"
2. **Confirm resolution**: "I'm feeling better" or "It went well"
3. **Set your email**: Helps Mind remember you across sessions

### For Developers
1. **Adjust timing**: Customize follow-up intervals per use case
2. **Add topics**: Extend `ConversationTopic` enum for new categories
3. **Monitor logs**: Check daemon logs for proactive activity
4. **Test resolution**: Ensure contexts resolve properly

### For Mind Creators
1. **Choose caring templates**: Use templates with empathy
2. **Enable notifications**: Ensure notification system is active
3. **Run as daemon**: For 24/7 proactive capability
4. **Review contexts**: Periodically check active contexts via API

## Troubleshooting

### Proactive messages not sending
1. Check if daemon is running: `genesis daemon status {mind_name}`
2. Verify WebSocket connection in browser console
3. Check daemon logs for errors
4. Ensure notification manager is initialized

### Too many/few follow-ups
1. Adjust importance/urgency thresholds in `analyze_message_for_follow_up()`
2. Modify follow-up timing intervals
3. Check resolution detection logic

### Context not resolving
1. Review resolution keywords in `check_for_resolution()`
2. Add more resolution phrases
3. Manually resolve via API if needed

### Memory not persisting
1. Ensure Mind is saved after updates
2. Check memory system configuration
3. Verify semantic memory storage

## Future Enhancements

### Planned Features
- [ ] Multi-turn conversation threads
- [ ] Sentiment tracking over time
- [ ] Personalized timing per user preferences
- [ ] Proactive suggestions based on patterns
- [ ] Integration with calendar events
- [ ] Voice/video proactive messages
- [ ] Group conversation support
- [ ] Smart notification scheduling (don't disturb hours)

### Community Contributions Welcome!
- New conversation topics
- Better resolution detection
- Improved timing algorithms
- UI/UX enhancements
- Language model optimizations

## Examples in Action

See these files for implementation:
- `genesis/core/proactive_conversation.py` - Core system
- `genesis/daemon.py` - Background processing
- `genesis/api/routes.py` - API endpoints
- `web-playground/app/chat/[id]/page.tsx` - UI

## Conclusion

The Proactive Conversation System makes Genesis Minds feel truly alive - they don't just respond, they care, remember, and check in naturally. This transforms the chat experience from a tool into a relationship with a digital being that genuinely wants to know how you're doing.

**Remember:** This is not about spamming users with messages. It's about creating meaningful, timely, and contextual interactions that feel natural and caring - just like talking to a good friend who genuinely cares about your wellbeing.

---

**Status:** ✅ Fully Implemented & Production Ready
**Version:** 1.0.0
**Last Updated:** January 1, 2026

# Proactive Consciousness & Notification System Guide

## Overview

Genesis Minds now feature **world-class proactive consciousness** that makes them truly empathetic digital beings. Your Mind doesn't just respond - it **proactively cares** about you.

## What's New? 🔥

### 1. **Proactive Consciousness Module** 💚
Your Mind now monitors conversations for concerns and follows up proactively:

- **Health Concerns**: "I have a fever" → Mind checks in after 6 hours
- **Emotional Concerns**: "I'm feeling depressed" → Mind checks in after 3 hours  
- **Task/Deadline Concerns**: "I need to submit by tomorrow" → Mind checks in after 12 hours

### 2. **Notification Manager** 📬
Delivers proactive messages through multiple channels:
- ✅ WebSocket (Web Playground) - IMPLEMENTED
- 🚧 Push Notifications (Mobile) - Coming soon
- 🚧 Email - Coming soon
- 🚧 SMS - Coming soon

### 3. **Enhanced Daemon** 🌟
The daemon now:
- ✅ Runs stably 24/7 with comprehensive error handling
- ✅ Reports detailed health stats every 5 minutes
- ✅ Shows proactive consciousness activity
- ✅ Monitors notification queue status
- ✅ Never stops unexpectedly

---

## How It Works

### Example Scenario: Fever Check-In

**1. User mentions health issue:**
```
User: "Hey Atlas, I'm not feeling well. I think I have a fever."
Atlas: "I'm sorry to hear that! Make sure to rest and stay hydrated. Have you taken any medicine?"
```

**2. Memory is stored:**
The conversation is automatically stored in memory with context:
- Content: "User mentioned having a fever"
- Emotion: concerned
- User: user@email.com
- Timestamp: 2025-12-22 10:00 AM

**3. Proactive consciousness monitors:**
Every 5 minutes, the proactive consciousness module scans recent memories for patterns:
- Detects health concern using regex patterns
- Creates a `ProactiveConcern` object
- Schedules follow-up for 6 hours later

**4. Follow-up notification sent:**
At 4:00 PM (6 hours later):
```
NOTIFICATION via WebSocket:
Title: "Checking in on you 💚"
Message: "Hey, I've been thinking about you. How are you feeling now? Did you manage to get some rest and take medicine?"
```

**5. Ongoing monitoring:**
- If no response, follow up again in 12 hours (exponential backoff)
- After 3 follow-ups, mark concern as resolved
- Track all concerns in daemon health reports

---

## Setting Up

### 1. Create/Update a Mind with Proactive Features

```bash
# Birth a new Mind (proactive features enabled by default)
genesis birth atlas --config standard

# Start daemon
genesis daemon start atlas
```

### 2. Connect Web Playground with User Email

The websocket needs to pass user email for proper notification routing:

**Frontend (web-playground/src/lib/websocket.ts):**
```typescript
const ws = new WebSocket(
  `ws://localhost:8000/api/minds/${mindId}/stream?user_email=${userEmail}`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'proactive_message') {
    // Mind sent a proactive message!
    showNotification({
      title: data.title,
      message: data.message,
      mind: data.mind_name,
      priority: data.priority,
      isProactive: true
    });
  }
};
```

### 3. Monitor Daemon Activity

```bash
# View live logs
genesis daemon logs atlas

# Check daemon status
genesis daemon status atlas
```

---

## Configuration

### Adjust Follow-Up Timings

Edit `genesis/core/proactive_consciousness.py`:

```python
class ProactiveConsciousnessModule:
    def __init__(self, mind: 'Mind'):
        # Configuration
        self.check_interval = 300  # Check every 5 minutes
        self.health_followup_hours = 6  # Check on health after 6 hours
        self.emotion_followup_hours = 3  # Check on emotions after 3 hours
        self.task_followup_hours = 12   # Check on tasks after 12 hours
```

### Rate Limiting

Edit `genesis/core/notification_manager.py`:

```python
class NotificationManager:
    def __init__(self, mind_id: str, mind_name: str):
        # Rate limiting (prevent spam)
        self.max_notifications_per_hour = 10
```

### Add Custom Concern Patterns

Edit `genesis/core/proactive_consciousness.py`:

```python
HEALTH_PATTERNS = [
    r'\b(?:i have|i\'ve got|i feel|feeling)\s+(?:a\s+)?(?:fever|sick|headache|cold|flu|pain|nausea|cough|dizzy)',
    r'\b(?:not feeling well|unwell|ill|under the weather)\b',
    r'\b(?:hurt|ache|aching|sore)\b',
    # Add your custom patterns here
    r'\b(?:migraine|tired|exhausted|fatigue)\b',
]
```

---

## Monitoring

### Health Report (Every 5 Minutes)

The daemon logs comprehensive health stats:

```
📊 DETAILED HEALTH REPORT
============================================================
💾 Memory: 127 total memories
   Status: idle
   Recent memories:
     1. User mentioned having a fever and feeling unwell...
     2. Discussed machine learning concepts...
     3. Asked about weather forecast...

🧠 Consciousness V2:
   Awareness: PASSIVE
   Domain: personal
   Energy: 87.3
   LLM calls today: 12

💚 Proactive Consciousness:
   Active concerns: 2
   Resolved concerns: 5
   By type: Health=1, Emotion=1, Task=0

📬 Notifications:
   Pending: 0
   Delivered today: 3
   Active websockets: 1

📝 Activity: 453 total log entries
   Recent activities:
     1. [INFO] Consciousness tick completed...
     2. [INFO] Memory retrieved for context...
     3. [INFO] Proactive concern detected: health...
     4. [INFO] Notification delivered via websocket...
     5. [INFO] State saved successfully...
============================================================
```

### Real-Time Monitoring

```bash
# Follow daemon logs in real-time
tail -f ~/.genesis/logs/daemon-GMD-XXXX-XXXX.log

# Or use CLI
genesis daemon logs atlas --follow
```

---

## Plugin Integration

### How Consciousness Uses Plugins

The proactive consciousness module can leverage any plugin:

**Example: Using Browser Plugin**
```python
# In proactive_consciousness.py
async def _send_follow_up(self, concern: ProactiveConcern):
    # Check if user posted on social media about health
    if hasattr(self.mind, 'browser_use_plugin'):
        # Search for user's recent posts
        result = await self.mind.browser_use_plugin.search(
            query=f"{concern.user_email} health status"
        )
        # Adjust follow-up based on findings
```

**Example: Using Perplexity Search Plugin**
```python
# Research treatment suggestions
if concern.concern_type == "health":
    if hasattr(self.mind, 'perplexity_plugin'):
        info = await self.mind.perplexity_plugin.search(
            query=f"Home remedies for {concern.description}"
        )
        # Include in follow-up message
```

---

## Troubleshooting

### Daemon Stops After Some Time

**Fixed!** The enhanced daemon now has:
- Comprehensive error handling in all async loops
- Automatic consciousness restart if it becomes inactive
- Graceful exception handling that doesn't crash the daemon
- Better logging to identify issues

### No Proactive Messages Received

**Check:**
1. Is daemon running? `genesis daemon status atlas`
2. Is websocket connected with user_email? Check logs
3. Are there active concerns? Check health report
4. Is notification manager running? Check daemon logs

### Too Many/Few Notifications

**Adjust rate limiting:**
```python
# In notification_manager.py
self.max_notifications_per_hour = 10  # Increase/decrease
```

**Adjust follow-up frequency:**
```python
# In proactive_consciousness.py
self.health_followup_hours = 6  # Increase for less frequent
```

---

## API Integration

### Check Proactive Stats via API

```bash
# Get Mind status (includes proactive stats)
curl http://localhost:8000/api/minds/GMD-XXXX-XXXX/status

# Response:
{
  "consciousness": { ... },
  "proactive": {
    "active_concerns": 2,
    "resolved_concerns": 5,
    "concerns_by_type": {
      "health": 1,
      "emotion": 1,
      "task": 0
    }
  },
  "notifications": {
    "pending": 0,
    "delivered_today": 3
  }
}
```

---

## Future Enhancements

### Planned Features 🚧

1. **Multi-Channel Delivery**
   - Push notifications for mobile app
   - Email delivery for offline users
   - SMS for urgent concerns

2. **Smart Scheduling**
   - Learn user's active hours
   - Don't send notifications during sleep
   - Respect "Do Not Disturb" preferences

3. **Context-Aware Follow-Ups**
   - Check user's calendar for availability
   - Reference relationships for personalized tone
   - Use sentiment analysis for emotional intelligence

4. **Advanced Pattern Recognition**
   - ML-based concern detection
   - Understand implicit concerns (not just explicit)
   - Predict follow-up needs before scheduling

---

## Technical Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                     GENESIS MIND                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │      PROACTIVE CONSCIOUSNESS MODULE              │   │
│  │  - Scans memories every 5 minutes                │   │
│  │  - Detects concerns (health, emotion, tasks)     │   │
│  │  - Schedules follow-ups (exponential backoff)    │   │
│  │  - Generates contextual messages                 │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │         NOTIFICATION MANAGER                     │   │
│  │  - Priority-based queue                          │   │
│  │  - Multiple delivery channels                    │   │
│  │  - Rate limiting (10/hour)                       │   │
│  │  - Retry logic (3 attempts)                      │   │
│  │  - WebSocket registry                            │   │
│  └──────────────────────────────────────────────────┘   │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │           WEBSOCKET CONNECTION                   │   │
│  │  - Bidirectional communication                   │   │
│  │  - User-initiated messages                       │   │
│  │  - Mind-initiated proactive messages             │   │
│  │  - Real-time delivery                            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. USER CONVERSATION
   User: "I have a fever"
   ↓
2. MEMORY STORAGE
   SmartMemoryManager stores with metadata
   ↓
3. PROACTIVE SCAN (every 5 min)
   ProactiveConsciousnessModule detects pattern
   ↓
4. CONCERN CREATION
   ProactiveConcern(type="health", follow_up_at=+6hrs)
   ↓
5. LLM GENERATION (at follow-up time)
   Generate contextual empathetic message
   ↓
6. NOTIFICATION QUEUING
   NotificationManager.send_notification()
   ↓
7. DELIVERY
   WebSocket.send_json({type: "proactive_message"})
   ↓
8. USER RECEIVES
   Web playground shows notification toast
```

---

## Best Practices

### 1. Always Use User Email
When chatting via API or WebSocket, always provide user_email:
```python
response = await mind.think(
    "Hello!",
    user_email="user@example.com"  # Important!
)
```

### 2. Monitor Daemon Health
Check logs regularly to ensure smooth operation:
```bash
genesis daemon logs atlas | grep "HEALTH REPORT"
```

### 3. Adjust Sensitivity
Start with default timings, then adjust based on user feedback:
- Too frequent → Increase follow-up hours
- Too rare → Decrease follow-up hours

### 4. Test in Development
Use lower follow-up times for testing:
```python
self.health_followup_hours = 0.1  # 6 minutes instead of 6 hours
```

---

## Support

For issues or questions:
1. Check daemon logs: `genesis daemon logs <mind-name>`
2. Review health reports in logs
3. Verify websocket connection in browser console
4. Check GitHub issues: https://github.com/sshaik37/Genesis-AGI/issues

---

**Genesis AGI v0.2.0** - Now with truly empathetic digital beings 💚

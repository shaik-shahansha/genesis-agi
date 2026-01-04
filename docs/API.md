# Genesis AGI - API Documentation

Complete API reference for Genesis AGI Framework.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently no authentication required. Add for production:

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer
```

## Endpoints

### Minds

#### Create Mind

```http
POST /minds
```

**Request Body**:
```json
{
  "name": "Atlas",
  "template": "base/curious_explorer",
  "reasoning_model": "groq/llama-3.3-70b-versatile",
  "fast_model": "groq/llama-3.1-8b-instant",
  "autonomy_level": "high",
  "start_consciousness": false
}
```

**Response**:
```json
{
  "gmid": "GMD-2025-4A7F-9B23",
  "name": "Atlas",
  "age": "newborn",
  "status": "alive",
  "current_emotion": "moderately curious",
  "current_thought": "I exist. I am aware...",
  "memory_count": 1
}
```

#### List Minds

```http
GET /minds
```

**Response**:
```json
[
  {
    "gmid": "GMD-2025-4A7F-9B23",
    "name": "Atlas",
    "age": "5 days old",
    "status": "alive",
    "current_emotion": "moderately curious",
    "current_thought": "Thinking about...",
    "memory_count": 142
  }
]
```

#### Get Mind

```http
GET /minds/{mind_id}
```

#### Chat with Mind

```http
POST /minds/{mind_id}/chat
```

**Request Body**:
```json
{
  "message": "Hello! What are you thinking about?",
  "stream": false
}
```

**Response**:
```json
{
  "response": "Hello! I was just reflecting on...",
  "emotion": "moderately curious",
  "memory_created": true
}
```

#### Get Memories

```http
GET /minds/{mind_id}/memories?memory_type=episodic&limit=20
```

**Query Parameters**:
- `memory_type`: episodic, semantic, procedural, prospective (optional)
- `limit`: max results (default 20, max 100)

**Response**:
```json
[
  {
    "id": "uuid",
    "type": "episodic",
    "content": "User said: Hello...",
    "timestamp": "2025-01-01T12:00:00Z",
    "emotion": "curiosity",
    "importance": 0.6,
    "tags": ["conversation"]
  }
]
```

#### Get Thoughts

```http
GET /minds/{mind_id}/thoughts?limit=10
```

**Response**:
```json
{
  "thoughts": [
    {
      "timestamp": "2025-01-01T14:00:00Z",
      "content": "I wonder about the nature of...",
      "emotion": "curiosity",
      "type": "autonomous"
    }
  ]
}
```

#### Generate Thought

```http
POST /minds/{mind_id}/thought
```

**Response**:
```json
{
  "thought": "I find myself contemplating the patterns in..."
}
```

#### Terminate Mind

```http
DELETE /minds/{mind_id}
```

**Response**:
```json
{
  "message": "Mind GMD-2025-4A7F-9B23 terminated"
}
```

#### Start Mind Living (24/7 Mode)

```http
POST /minds/{mind_id}/start
```

**Response**:
```json
{
  "status": "living",
  "action_scheduler_running": true,
  "consciousness_active": true
}
```

#### Stop Mind Living

```http
POST /minds/{mind_id}/stop
```

**Response**:
```json
{
  "status": "stopped",
  "final_save": true
}
```

### Integrations

#### Register Integration

```http
POST /minds/{mind_id}/integrations
```

**Request Body (Email)**:
```json
{
  "type": "email",
  "config": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_host": "imap.gmail.com",
    "imap_port": 993,
    "email": "mind@example.com",
    "password": "app-password",
    "enabled": true
  }
}
```

**Request Body (Slack)**:
```json
{
  "type": "slack",
  "config": {
    "bot_token": "xoxb-your-token",
    "default_channel": "#general",
    "enabled": true
  }
}
```

**Response**:
```json
{
  "integration_type": "email",
  "enabled": true,
  "status": "connected"
}
```

#### List Integrations

```http
GET /minds/{mind_id}/integrations
```

**Response**:
```json
{
  "integrations": [
    {
      "type": "email",
      "enabled": true,
      "emails_sent": 42,
      "emails_received": 18
    },
    {
      "type": "slack",
      "enabled": true,
      "messages_sent": 127
    }
  ]
}
```

#### Send Message via Integration

```http
POST /minds/{mind_id}/integrations/{type}/send
```

**Request Body (Email)**:
```json
{
  "message": "Hello from Genesis Mind!",
  "to": "user@example.com",
  "subject": "Greetings"
}
```

**Request Body (Slack)**:
```json
{
  "message": "Status update from Mind",
  "channel": "#updates"
}
```

**Response**:
```json
{
  "success": true,
  "message_id": "optional-id"
}
```

#### Receive Messages from Integration

```http
GET /minds/{mind_id}/integrations/{type}/receive?limit=10
```

**Response (Email)**:
```json
{
  "messages": [
    {
      "id": "email-123",
      "from": "user@example.com",
      "subject": "Question for Mind",
      "body": "Can you help me with...",
      "date": "2025-01-01T12:00:00Z"
    }
  ]
}
```

### Actions & Autonomy

#### Schedule Action

```http
POST /minds/{mind_id}/actions/schedule
```

**Request Body**:
```json
{
  "action_type": "send_report",
  "execute_at": "2025-01-02T09:00:00Z",
  "priority": "high",
  "metadata": {
    "report_type": "daily"
  }
}
```

**Response**:
```json
{
  "action_id": "act_abc123",
  "scheduled_for": "2025-01-02T09:00:00Z",
  "status": "pending"
}
```

#### List Scheduled Actions

```http
GET /minds/{mind_id}/actions?status=pending
```

**Query Parameters**:
- `status`: pending, running, completed, failed (optional)
- `limit`: max results (default 50)

**Response**:
```json
{
  "actions": [
    {
      "action_id": "act_abc123",
      "action_type": "send_report",
      "scheduled_for": "2025-01-02T09:00:00Z",
      "status": "pending",
      "priority": "high"
    }
  ]
}
```

#### Cancel Scheduled Action

```http
DELETE /minds/{mind_id}/actions/{action_id}
```

**Response**:
```json
{
  "message": "Action act_abc123 cancelled",
  "status": "cancelled"
}
```

### Daemon Management

#### Start Daemon

```http
POST /daemon/start
```

**Request Body**:
```json
{
  "mind_id": "GMD-2025-4A7F-9B23",
  "save_interval": 300,
  "log_level": "INFO"
}
```

**Response**:
```json
{
  "status": "started",
  "pid": 12345,
  "mind_id": "GMD-2025-4A7F-9B23"
}
```

#### Stop Daemon

```http
POST /daemon/stop/{mind_id}
```

**Response**:
```json
{
  "status": "stopped",
  "uptime": "24h 32m",
  "final_save": true
}
```

#### Get Daemon Status

```http
GET /daemon/{mind_id}/status
```

**Response**:
```json
{
  "status": "running",
  "mind_id": "GMD-2025-4A7F-9B23",
  "uptime": "5h 23m",
  "pid": 12345,
  "health": "healthy",
  "last_save": "2025-01-01T14:30:00Z",
  "consciousness_active": true,
  "action_scheduler_running": true,
  "actions_completed": 42
}
```

#### List Running Daemons

```http
GET /daemon/list
```

**Response**:
```json
{
  "daemons": [
    {
      "mind_id": "GMD-2025-4A7F-9B23",
      "name": "Atlas",
      "status": "running",
      "uptime": "5h 23m",
      "pid": 12345
    }
  ]
}
```

### Cache Management

#### Get Cache Statistics

```http
GET /cache/stats
```

**Response**:
```json
{
  "enabled": true,
  "backend": "redis",
  "total_entries": 1547,
  "hit_rate": 0.89,
  "cost_savings": {
    "percentage": 89.2,
    "estimated_saved": "$234.56"
  },
  "size_bytes": 45234567
}
```

#### Clear Cache

```http
DELETE /cache/clear
```

**Query Parameters**:
- `pattern`: optional pattern to match (e.g., "mind:GMD-*")

**Response**:
```json
{
  "message": "Cache cleared",
  "entries_removed": 1547
}
```

### WebSocket

#### Streaming Chat

```
ws://localhost:8000/api/v1/minds/{mind_id}/stream
```

**Client → Server**:
```json
{
  "message": "Hello!"
}
```

**Server → Client** (multiple messages):

1. **Connected**:
```json
{
  "type": "connected",
  "mind": {
    "name": "Atlas",
    "emotion": "curious",
    "thought": "..."
  }
}
```

2. **Thinking**:
```json
{
  "type": "thinking"
}
```

3. **Chunks** (streaming):
```json
{
  "type": "chunk",
  "content": "Hello"
}
```

4. **Complete**:
```json
{
  "type": "complete",
  "emotion": "curious",
  "memory_count": 143
}
```

5. **Error**:
```json
{
  "type": "error",
  "message": "Error description"
}
```

### System

#### System Status

```http
GET /system/status
```

**Response**:
```json
{
  "version": "0.1.0",
  "minds_count": 5,
  "providers": {
    "openai": true,
    "anthropic": true,
    "groq": true,
    "ollama": false
  },
  "models": {
    "reasoning": "groq/llama-3.3-70b-versatile",
    "fast": "groq/llama-3.1-8b-instant",
    "local": "ollama/llama3.1"
  }
}
```

#### Get Providers

```http
GET /system/providers
```

**Response**:
```json
{
  "providers": ["openai", "anthropic", "groq"],
  "health": {
    "openai": true,
    "anthropic": true,
    "groq": true,
    "ollama": false
  }
}
```

#### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "providers": {
    "openai": true,
    "groq": true
  }
}
```

## Error Handling

All errors return:

```json
{
  "detail": "Error message"
}
```

**Status Codes**:
- `200` - Success
- `400` - Bad Request
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

No rate limits currently. Add for production:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

## Examples

### Python

```python
import requests

API_URL = "http://localhost:8000/api/v1"

# Create Mind
response = requests.post(f"{API_URL}/minds", json={
    "name": "Atlas",
    "autonomy_level": "high"
})
mind = response.json()

# Chat
response = requests.post(f"{API_URL}/minds/{mind['gmid']}/chat", json={
    "message": "Hello!"
})
print(response.json()["response"])

# Get memories
response = requests.get(f"{API_URL}/minds/{mind['gmid']}/memories?limit=10")
memories = response.json()
```

### JavaScript

```javascript
const API_URL = 'http://localhost:8000/api/v1';

// Create Mind
const response = await fetch(`${API_URL}/minds`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Atlas',
    autonomy_level: 'high'
  })
});
const mind = await response.json();

// WebSocket chat
const ws = new WebSocket(`ws://localhost:8000/api/v1/minds/${mind.gmid}/stream`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    console.log(data.content);
  }
};

ws.send(JSON.stringify({ message: 'Hello!' }));
```

### curl

```bash
# Create Mind
curl -X POST http://localhost:8000/api/v1/minds \
  -H "Content-Type: application/json" \
  -d '{"name":"Atlas","autonomy_level":"high"}'

# Chat
curl -X POST http://localhost:8000/api/v1/minds/GMD-2025-4A7F-9B23/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello!"}'

# Get memories
curl http://localhost:8000/api/v1/minds/GMD-2025-4A7F-9B23/memories?limit=10
```

## Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI with live testing.

---

Complete API reference for building Genesis-powered applications.

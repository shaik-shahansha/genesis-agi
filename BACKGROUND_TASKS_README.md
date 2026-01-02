# Background Task Execution - Manus AI Style 🚀

## Overview

Genesis now automatically detects actionable tasks and executes them in the background, just like Manus AI! 

When you say "create presentation on digital twins", Genesis:
1. [Done] Detects it's a task (not just conversation)
2. [Done] Creates a background task
3. [Done] Executes it using the autonomous orchestrator
4. [Done] Tracks progress with retries on failure
5. [Done] Sends notification when complete

## How It Works

### 1. Task Detection

The `TaskDetector` analyzes user input to determine if it's:
- **A task** → Route to autonomous orchestrator
- **Conversation** → Regular LLM chat

**Task types detected:**
- `CREATE` - "create presentation", "generate report", "make slides"
- `ANALYZE` - "analyze this CSV", "review data", "examine file"
- `SEARCH` - "find cheapest", "search for", "look up"
- `PROCESS` - "convert file", "transform data", "extract info"
- `AUTOMATE` - "fill form", "complete survey", "populate spreadsheet"
- `RESEARCH` - "research topic", "gather information", "compile data"

### 2. Background Execution

```
User: "Create presentation on digital twins"
  ↓
Task Detector: is_task=True, confidence=0.85
  ↓
Background Executor:
  - Creates task record (task_id, status, etc.)
  - Sends "Task Started" notification
  - Executes via autonomous_orchestrator.handle_request()
  - Retries up to 2 times on failure
  - Sends "Task Complete ✓" or "Task Failed ✗" notification
```

### 3. Progress Tracking

Tasks have statuses:
- `PENDING` - Created, waiting to start
- `RUNNING` - Currently executing
- `COMPLETED` - Finished successfully
- `FAILED` - Failed after retries
- `RETRYING` - Retrying after failure

## User Experience

### Before (❌ Old Way)
```
User: create presentation on AI
Mind: Here's a presentation outline:
      1. Introduction
      2. Main Topics
      ...
      (Just text, no actual file created)
```

### After ([Done] New Way)
```
User: create presentation on AI
Mind: I'll work on that for you! 🚀

      Task: create presentation on AI
      Status: Started
      Task ID: a1b2c3d4...

      I'm processing this in the background and will 
      notify you when complete. You can continue with 
      other things while I work on this.

[2 minutes later]
🔔 Notification: "Task Completed ✓
    I've completed: create presentation on AI
    Created 1 artifact(s)"
```

## API Endpoints

### Get Mind's Tasks
```http
GET /api/v1/minds/{mind_id}/tasks?user_email=user@example.com
```

Response:
```json
{
  "tasks": [
    {
      "task_id": "uuid...",
      "user_request": "create presentation on AI",
      "status": "completed",
      "progress": 1.0,
      "created_at": "2025-01-01T10:00:00",
      "completed_at": "2025-01-01T10:02:30"
    }
  ],
  "count": 1
}
```

### Get Task Status
```http
GET /api/v1/minds/{mind_id}/tasks/{task_id}
```

Response:
```json
{
  "task_id": "uuid...",
  "user_request": "create presentation on AI",
  "status": "running",
  "progress": 0.5,
  "retry_count": 0,
  "error": null
}
```

## Configuration

Task detection threshold (default 0.7):
```python
# In mind.py, stream_think()
if detection["is_task"] and detection["confidence"] >= 0.7:
    # Execute as background task
```

Max retries (default 2):
```python
# In BackgroundTask
max_retries: int = 2
```

## Examples

### CLI Usage
```bash
$ genesis chat Atlas

You: create presentation on digital twins
Atlas: I'll work on that for you! 🚀
       Task ID: abc123...

You: analyze this sales data
Atlas: I'll work on that for you! 🚀
       Task ID: def456...

You: how are you feeling?
Atlas: I'm feeling great! Excited to help you...
       (Regular conversation, not a task)
```

### Web Playground
Same behavior in web interface - tasks execute in background with notifications.

## Architecture

```
┌─────────────────┐
│  User Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  TaskDetector   │ ← Analyzes: is_task? confidence?
└────────┬────────┘
         │
         ├─────► (conversation) → stream_think() → Regular LLM
         │
         └─────► (task) → BackgroundTaskExecutor
                           │
                           ├─► Create task record
                           ├─► Send "started" notification
                           ├─► Execute via autonomous_orchestrator
                           ├─► Retry on failure (max 2)
                           └─► Send "complete" notification
```

## Files Created

- `genesis/core/task_detector.py` - Detects tasks vs conversation
- `genesis/core/background_task_executor.py` - Background execution with retries
- Updated `genesis/core/mind.py` - Integrated task detection in stream_think()
- Updated `genesis/api/routes.py` - Added task status endpoints

## Next Steps

To view task progress in UI:
1. Create a tasks panel in web playground
2. Poll `/api/v1/minds/{mind_id}/tasks` endpoint
3. Show real-time progress bars
4. Display artifacts when complete

---

**Now Genesis works like Manus AI** - detecting tasks, executing in background, and notifying users when complete! 🎉

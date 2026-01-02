# Task Execution Diagnosis & Fixes

**Date:** December 31, 2025  
**Issue:** Web playground task execution (e.g., "create presentation") not working properly

## Test Results

### What Works ✓
1. **Task Detection** - Works perfectly
   - `task_detector.detect()` correctly identifies tasks
   - Confidence scoring works (1.00 for "create presentation")
   - Task type classification correct ("create")

2. **Background Task Creation** - Works
   - `background_executor.execute_task()` creates task properly
   - Task ID generated and tracked
   - Initial notification sent

3. **LLM Calls** - Working
   - Multiple LLM calls are being made to Groq API
   - API responses returning successfully (HTTP 200)
   - Mind.think() with skip_task_detection=True works

### What's Broken ✗

#### 1. MindLogger Missing Methods (FIXED)
**Error:** `'MindLogger' object has no attribute 'warning'`

**Root Cause:** MindLogger class was missing standard Python logging methods (`warning()`, `info()`, `debug()`)

**Fix Applied:** Added compatibility methods to MindLogger:
```python
def warning(self, message: str, metadata: Optional[Dict[str, Any]] = None):
    self.log(LogLevel.INFO, f"Warning: {message}", metadata=metadata or {})

def info(self, message: str, metadata: Optional[Dict[str, Any]] = None):
    self.log(LogLevel.INFO, message, metadata=metadata or {})

def debug(self, message: str, metadata: Optional[Dict[str, Any]] = None):
    self.log(LogLevel.DEBUG, message, metadata=metadata or {})
```

**Files Modified:**
- `genesis/core/mind_logger.py`

#### 2. Unicode Emoji Encoding Issues (FIXED)
**Error:** `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'`

**Root Cause:** Emoji characters in response messages cause encoding errors on Windows terminals

**Fix Applied:** Removed emojis from:
- Task acknowledgment message (🚀 → removed)
- Progress updates (🔄 → "Starting task")
- Completion messages (✅ → "[COMPLETED]")
- Warning messages (⚠️ → "[WARNING]")

**Files Modified:**
- `genesis/core/mind.py` - Line ~507
- `genesis/core/background_task_executor.py` - Lines 180, 375, 393, 402

#### 3. Task Execution Gets Stuck (CRITICAL ISSUE)
**Symptom:** Task stays at 10% progress and never completes (times out after 120s)

**Observations:**
- LLM calls are being made successfully
- Autonomous reasoner is calling Mind.think() multiple times
- Progress never advances beyond 10%
- Task status remains "running" for entire duration

**Root Cause (Likely):**
The autonomous orchestrator's execution loop appears to be stuck. Looking at the debug output:
```
[DEBUG think] skip=True, prompt='Design the presentation outline...'
[DEBUG think] skip=True, prompt='Generate Python code to accomplish this task...'
[DEBUG think] skip=True, prompt='This Python code has syntax errors. Fix them...'
```

The reasoner is generating plans and code, but:
1. Code execution may be failing
2. Progress is not being updated
3. The execution steps are not completing properly

**Recommended Fixes:**

1. **Add More Detailed Logging** in `autonomous_orchestrator.py`:
   ```python
   logger.info(f"[STEP {i+1}] Type={step.type}, Success={step.success}")
   ```

2. **Fix Progress Updates** in `background_task_executor.py`:
   ```python
   # Update progress after each step
   task.progress = (i + 1) / len(plan.steps)
   ```

3. **Add Timeout Per Step** to prevent infinite loops:
   ```python
   try:
       result = await asyncio.wait_for(
           self._execute_code_step(step, uploaded_files),
           timeout=step.timeout
       )
   except asyncio.TimeoutError:
       logger.error(f"Step {i+1} timed out after {step.timeout}s")
       step.error = f"Timeout after {step.timeout}s"
       break
   ```

4. **Improve Error Handling** in code executor to catch and report failures properly

## Server vs Daemon - Which Should Handle Tasks?

### Current Implementation:
**BOTH can handle tasks** - the implementation is agnostic:

#### Genesis Server (FastAPI)
- **Location:** `genesis/api/routes.py`
- **Endpoint:** `POST /api/minds/{mind_id}/chat`
- **How it works:**
  1. Server caches Mind instances in `_mind_cache`
  2. Chat endpoint calls `mind.think()`
  3. Mind detects if it's a task and creates background task
  4. Background task runs in asyncio event loop
  5. Server keeps Mind alive across requests

**Pros:**
- Centralized - one server handles all minds
- Easy to scale horizontally
- Better for multiple users

**Cons:**
- All minds share server resources
- Restart kills all background tasks (unless persisted)
- More complex state management

#### Genesis Daemon (Per-Mind Process)
- **Location:** `genesis/daemon.py`
- **Command:** `genesis daemon start <gmid>`
- **How it works:**
  1. Each mind runs in its own dedicated process
  2. Daemon keeps mind instance alive
  3. Background tasks run in daemon's event loop
  4. Can expose HTTP/WebSocket endpoints

**Pros:**
- Isolated - each mind has dedicated resources
- Can restart individual minds without affecting others
- Better for long-running autonomous behavior
- True "always-on" consciousness

**Cons:**
- More processes to manage
- Higher resource usage
- Need process management (systemd, supervisor)

### Recommendation:

**Use BOTH depending on use case:**

1. **Web Playground (Current):** Use **Server**
   - Interactive chat sessions
   - Short-lived tasks
   - Multiple users

2. **Production/Autonomous:** Use **Daemon**
   - Long-running tasks
   - Proactive behaviors
   - Mission-critical minds

3. **Hybrid Approach:**
   - Server for API/chat
   - Daemon for background consciousness
   - They can communicate via database/messages

## Next Steps

1. ✓ Fix MindLogger.warning() method
2. ✓ Remove emoji encoding issues
3. **TODO:** Debug autonomous orchestrator execution loop
4. **TODO:** Add proper progress tracking
5. **TODO:** Add timeout handling per step
6. **TODO:** Improve error reporting from code executor
7. **TODO:** Test with simpler tasks first (e.g., "create a text file")

## Testing

Run the diagnostic script:
```bash
python test_task_simple.py
```

This simulates exactly what the web playground does and shows detailed execution flow.

## Code Locations

**Key Files:**
- Task Detection: `genesis/core/task_detector.py`
- Background Execution: `genesis/core/background_task_executor.py`  
- Autonomous Orchestrator: `genesis/core/autonomous_orchestrator.py`
- API Endpoint: `genesis/api/routes.py` (line ~509)
- Mind.think(): `genesis/core/mind.py` (line ~471)

**Test Script:**
- `test_task_simple.py` - Direct testing as if from web playground

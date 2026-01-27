"""
Background Task Executor - Execute tasks asynchronously with notifications.

Handles:
- Async task execution
- Progress tracking
- Retry on failure
- Notification on completion
- Task status management
"""

import asyncio
import logging
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind
    from genesis.core.autonomous_orchestrator import TaskResult

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of background tasks."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class BackgroundTask:
    """Represents a background task."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_request: str = ""
    user_email: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "user_request": self.user_request,
            "user_email": self.user_email,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "error": self.error,
            "retry_count": self.retry_count
        }


class BackgroundTaskExecutor:
    """
    Executes tasks in background and sends notifications.
    
    ARCHITECTURE CHANGE:
    - Tasks now persisted to SQLite for crash recovery
    - Daemon can resume tasks after restart
    - Better task tracking and querying
    
    Like Manus AI:
    - User makes request → Task created immediately
    - Task executes in background
    - User gets notification when complete
    - Can retry on failure
    - Persists across restarts
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize background task executor.
        
        Args:
            mind: Mind instance
        """
        self.mind = mind
        self.active_tasks: Dict[str, BackgroundTask] = {}  # In-memory cache
        self.completed_tasks: List[BackgroundTask] = []  # In-memory cache
        self.max_completed_history = 100
        
        # Load pending/running tasks from SQLite (for crash recovery)
        self._load_active_tasks()
    
    async def execute_task(
        self,
        user_request: str,
        user_email: Optional[str] = None,
        uploaded_files: Optional[List] = None,
        context: Optional[Dict] = None,
        notify_on_complete: bool = True,
        task_metadata: Optional[Dict] = None
    ) -> BackgroundTask:
        """
        Execute a task in background.
        
        Args:
            user_request: What user wants
            user_email: User's email for notifications
            uploaded_files: Any uploaded files
            context: Additional context
            notify_on_complete: Send notification when done
            task_metadata: Additional metadata like classification details
            
        Returns:
            BackgroundTask object for tracking
        """
        # Merge task_metadata into context if provided
        if task_metadata:
            if context is None:
                context = {}
            context.update(task_metadata)
        
        # Create task record
        task = BackgroundTask(
            user_request=user_request,
            user_email=user_email,
            status=TaskStatus.PENDING
        )
        
        self.active_tasks[task.task_id] = task
        
        # Log task creation
        self.mind.logger.action(
            "background_task",
            f"Created task: {user_request[:100]}"
        )
        
        # Send initial notification
        if notify_on_complete and user_email and hasattr(self.mind, 'notification_manager'):
            await self.mind.notification_manager.send_notification(
                recipient=user_email,
                title="Task Started",
                message=f"I'm working on: {user_request}",
                priority="normal",
                channel="web"
            )
        
        # Execute asynchronously
        asyncio.create_task(
            self._execute_task_async(
                task=task,
                user_request=user_request,
                user_email=user_email,
                uploaded_files=uploaded_files,
                context=context,
                notify_on_complete=notify_on_complete
            )
        )
        
        return task
    
    async def _execute_task_async(
        self,
        task: BackgroundTask,
        user_request: str,
        user_email: Optional[str],
        uploaded_files: Optional[List],
        context: Optional[Dict],
        notify_on_complete: bool
    ):
        """Execute task asynchronously with retry logic and progress updates."""
        while task.retry_count <= task.max_retries:
            try:
                # Update status
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                task.progress = 0.1
                self._save_task(task)  # Persist state change
                
                self.mind.logger.action(
                    "background_task",
                    f"Executing task {task.task_id}: {user_request[:100]}"
                )
                
                # Log to console for debugging
                logger.info(f"[TASK {task.task_id[:8]}] Starting execution: {user_request[:80]}")
                
                # Send progress update via WebSocket if available
                await self._send_progress_update(
                    task, 
                    user_email,
                    f"Starting task: {user_request[:100]}"
                )
                
                print(f"[DEBUG BG_EXEC] About to call handle_request...")
                
                # Execute through autonomous orchestrator
                result = await self.mind.handle_request(
                    user_request=user_request,
                    uploaded_files=uploaded_files,
                    context=context,
                    user_email=user_email,
                    skip_task_detection=True  # Prevent infinite loop
                )
                
                print(f"[DEBUG BG_EXEC] handle_request returned!")
                print(f"[DEBUG BG_EXEC] Result type: {type(result)}")
                print(f"[DEBUG BG_EXEC] Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
                
                print(f"[DEBUG BG_EXEC] handle_request returned!")
                print(f"[DEBUG BG_EXEC] Result type: {type(result)}")
                print(f"[DEBUG BG_EXEC] Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
                
                # Check if task was actually successful
                task_success = result.get('success', False) if isinstance(result, dict) else False
                print(f"[DEBUG BG_EXEC] Task success status: {task_success}")
                
                # Mark task status based on actual execution result
                if task_success:
                    task.status = TaskStatus.COMPLETED
                    print(f"[DEBUG BG_EXEC] Task marked as COMPLETED")
                else:
                    task.status = TaskStatus.FAILED
                    print(f"[DEBUG BG_EXEC] Task marked as FAILED")
                
                task.completed_at = datetime.now()
                task.progress = 1.0
                task.result = result
                
                # Save final state to SQLite
                self._save_task(task)
                
                # Move to completed
                self.active_tasks.pop(task.task_id, None)
                self.completed_tasks.append(task)
                
                print(f"[DEBUG BG_EXEC] Task moved to completed list")
                
                print(f"[DEBUG BG_EXEC] Task moved to completed list")
                
                # Trim history
                if len(self.completed_tasks) > self.max_completed_history:
                    self.completed_tasks = self.completed_tasks[-self.max_completed_history:]
                
                print(f"[DEBUG BG_EXEC] Preparing completion notification...")
                
                # Log based on actual status
                if task_success:
                    logger.info(f"[TASK {task.task_id[:8]}] ✓ COMPLETED successfully")
                    self.mind.logger.action(
                        "background_task",
                        f"Task {task.task_id} completed successfully"
                    )
                else:
                    logger.warning(f"[TASK {task.task_id[:8]}] ✗ FAILED")
                    self.mind.logger.action(
                        "background_task",
                        f"Task {task.task_id} failed"
                    )
                
                print(f"[DEBUG BG_EXEC] Formatting completion message...")
                
                # Format completion message for WebSocket delivery
                result_message = self._format_completion_message(task, result)
                
                print(f"[DEBUG BG_EXEC] Completion message length: {len(result_message)}")
                print(f"[DEBUG BG_EXEC] Message preview: {result_message[:100]}...")
                
                # NOTE: NOT adding to conversation_history to prevent duplicates
                # The WebSocket notification will display in the chat interface
                
                print(f"[DEBUG BG_EXEC] Will send via WebSocket only (no conversation history duplicate)")
                
                # NOTE: Removed _send_progress_update() here to prevent duplicate
                # We're sending task_complete below which contains the full message
                
                print(f"[DEBUG BG_EXEC] Checking notification conditions...")
                print(f"[DEBUG BG_EXEC]   notify_on_complete={notify_on_complete}")
                print(f"[DEBUG BG_EXEC]   user_email={user_email}")
                print(f"[DEBUG BG_EXEC]   has_notification_manager={hasattr(self.mind, 'notification_manager')}")
                
                # Send completion notification via WebSocket (IMMEDIATE delivery)
                if notify_on_complete and user_email and hasattr(self.mind, 'notification_manager'):
                    logger.info(f"[TASK {task.task_id[:8]}] Sending completion notification...")
                    print(f"[DEBUG BG_EXEC] Sending WebSocket notification...")
                    
                    # Send via WebSocket for immediate delivery
                # Convert any Path objects to strings for JSON serialization
                # Only send filename, not full path, for security/UX
                artifacts = result.get("artifacts", []) if isinstance(result, dict) else []
                serializable_artifacts = []
                for artifact in artifacts:
                    if isinstance(artifact, dict):
                        serializable_artifact = artifact.copy()
                        if "path" in serializable_artifact:
                            # Extract just the filename from the path
                            full_path = Path(str(serializable_artifact["path"]))
                            serializable_artifact["filename"] = full_path.name
                            # Remove the full path for security
                            del serializable_artifact["path"]
                        serializable_artifacts.append(serializable_artifact)
                    else:
                        serializable_artifacts.append(artifact)
                
                websocket_sent = await self.mind.notification_manager.send_to_websocket(
                    user_email=user_email,
                    message_type="task_complete",
                    data={
                        "task_id": task.task_id,
                        "user_request": user_request,
                        "status": "completed",
                        "message": result_message,
                        "artifacts": serializable_artifacts,
                        "timestamp": task.completed_at.isoformat()
                    }
                )
                
                print(f"[DEBUG BG_EXEC] WebSocket sent status: {websocket_sent}")
                
                if websocket_sent:
                    logger.info(f"[TASK {task.task_id[:8]}] ✓ Sent completion via WebSocket")
                    print(f"[DEBUG BG_EXEC] ✓ Notification delivered via WebSocket!")
                else:
                    logger.info(f"[TASK {task.task_id[:8]}] WebSocket not available, using fallback notification")
                    print(f"[DEBUG BG_EXEC] WebSocket not connected, using fallback notification")
                    print(f"[DEBUG BG_EXEC] Adding to conversation history as backup...")
                    
                    # FALLBACK STRATEGY:
                    # 1. Add to conversation history so it shows when user next visits
                    # 2. Queue persistent notification for when user reconnects
                    
                    # Add to conversation history as backup
                    self.mind.conversation.add_assistant_message(result_message)
                    print(f"[DEBUG BG_EXEC] ✓ Added to conversation history")
                    
                    # Queue persistent notification for when user reconnects
                    result_summary = self._format_result_summary(result)
                    # Convert any Path objects to strings for JSON serialization
                    # Only send filename, not full path, for security/UX
                    artifacts = result.get("artifacts", []) if isinstance(result, dict) else []
                    serializable_artifacts = []
                    for artifact in artifacts:
                        if isinstance(artifact, dict):
                            serializable_artifact = artifact.copy()
                            if "path" in serializable_artifact:
                                # Extract just the filename from the path
                                full_path = Path(str(serializable_artifact["path"]))
                                serializable_artifact["filename"] = full_path.name
                                # Remove the full path for security
                                del serializable_artifact["path"]
                            serializable_artifacts.append(serializable_artifact)
                        else:
                            serializable_artifacts.append(artifact)
                    
                    await self.mind.notification_manager.send_notification(
                        recipient=user_email,
                        title="Task Completed ✓",
                        message=f"I've completed: {user_request}\n\n{result_summary}",
                        priority="normal",
                        channel="web",
                        metadata={
                            "task_id": task.task_id,
                            "artifacts": serializable_artifacts
                        }
                    )
                
                break  # Success, exit retry loop
                
            except Exception as e:
                task.retry_count += 1
                error_trace = traceback.format_exc()
                task.error = str(e)
                
                # Log detailed error to console
                logger.error(
                    f"[TASK {task.task_id[:8]}] FAILED (attempt {task.retry_count}/{task.max_retries}): {str(e)}\n"
                    f"Traceback:\n{error_trace}"
                )
                
                self.mind.logger.error(
                    "background_task",
                    f"Task {task.task_id} failed (attempt {task.retry_count}): {str(e)}"
                )
                
                # Retry or fail
                if task.retry_count <= task.max_retries:
                    task.status = TaskStatus.RETRYING
                    task.progress = 0.0
                    self._save_task(task)  # Persist retry state
                    
                    # Wait before retry (exponential backoff)
                    wait_time = 2 ** task.retry_count
                    await asyncio.sleep(wait_time)
                    
                else:
                    # Max retries exceeded
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    self._save_task(task)  # Persist failure
                    
                    # Move to completed (as failed)
                    self.active_tasks.pop(task.task_id, None)
                    self.completed_tasks.append(task)
                    
                    # Send failure notification
                    if notify_on_complete and user_email and hasattr(self.mind, 'notification_manager'):
                        await self.mind.notification_manager.send_notification(
                            recipient=user_email,
                            title="Task Failed ✗",
                            message=f"I couldn't complete: {user_request}\n\nError: {task.error}",
                            priority="high",
                            channel="web"
                        )
    
    def _format_result_summary(self, result: Any) -> str:
        """Format task result for notification."""
        if isinstance(result, dict):
            if result.get("success"):
                artifacts = result.get("artifacts", [])
                if artifacts:
                    return f"Created {len(artifacts)} artifact(s)"
                else:
                    return "Task completed successfully"
            else:
                return f"Task completed with issues: {result.get('error', 'Unknown error')}"
        else:
            return "Task completed"
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task by ID."""
        # Check active first
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]
        
        # Check completed
        for task in self.completed_tasks:
            if task.task_id == task_id:
                return task
        
        return None
    
    def get_active_tasks(self) -> List[BackgroundTask]:
        """Get all active tasks."""
        return list(self.active_tasks.values())
    
    def get_completed_tasks(self, limit: int = 10) -> List[BackgroundTask]:
        """Get recent completed tasks."""
        return self.completed_tasks[-limit:]
    
    def get_tasks_for_user(self, user_email: str) -> List[BackgroundTask]:
        """Get all tasks for a specific user."""
        active = [t for t in self.active_tasks.values() if t.user_email == user_email]
        completed = [t for t in self.completed_tasks if t.user_email == user_email]
        return active + completed[-10:]  # Last 10 completed
    
    async def _send_progress_update(
        self,
        task: BackgroundTask,
        user_email: Optional[str],
        message: str
    ):
        """Send progress update via WebSocket if connected."""
        if not user_email or not hasattr(self.mind, 'notification_manager'):
            logger.debug(f"[TASK {task.task_id[:8]}] No notification manager or user_email for progress")
            return
        
        try:
            logger.info(f"[TASK {task.task_id[:8]}] Progress {task.progress*100:.0f}% - {message[:80]}")
            
            # Send via notification manager's WebSocket
            sent = await self.mind.notification_manager.send_to_websocket(
                user_email=user_email,
                message_type="task_progress",
                data={
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "progress": task.progress,
                    "message": message,
                    "user_request": task.user_request,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            if sent:
                logger.debug(f"[TASK {task.task_id[:8]}] Progress sent via WebSocket")
            else:
                logger.debug(f"[TASK {task.task_id[:8]}] WebSocket not connected")
                
        except Exception as e:
            # Non-critical, just log
            logger.debug(f"[TASK {task.task_id[:8]}] Could not send progress: {e}")
    
    def _format_completion_message(self, task: BackgroundTask, result: Any) -> str:
        """Format a nice completion message for chat."""
        
        # Extract key info from result
        if isinstance(result, dict):
            success = result.get("success", False)
            artifacts = result.get("artifacts", [])
            error = result.get("error")
            results = result.get("results", [])
            
            if success:
                msg = f"[COMPLETED] **Task Completed Successfully! ✅**\n\n"
                msg += f"**Request:** {task.user_request}\n\n"
                
                if artifacts:
                    msg += f"**📁 Generated Files:**\n\n"
                    for i, artifact in enumerate(artifacts[:10], 1):  # Max 10
                        artifact_type = artifact.get("type", "file")
                        artifact_name = artifact.get("name", "result")
                        
                        # Determine icon based on extension
                        ext = artifact_name.split('.')[-1].lower() if '.' in artifact_name else ""
                        icon = "📄"
                        if ext in ['pptx', 'ppt']:
                            icon = "📊"
                        elif ext in ['docx', 'doc']:
                            icon = "📝"
                        elif ext in ['xlsx', 'xls', 'csv']:
                            icon = "📈"
                        elif ext in ['pdf']:
                            icon = "📕"
                        elif ext in ['jpg', 'jpeg', 'png', 'gif']:
                            icon = "🖼️"
                        
                        msg += f"{i}. {icon} **{artifact_name}**\n\n"
                    
                    if len(artifacts) > 10:
                        msg += f"_...and {len(artifacts) - 10} more files_\n\n"
                    
                    msg += "\n💡 **Click the download buttons below to save the files**\n"
                else:
                    msg += "**Result:** Task completed successfully!\n\n"
                
                msg += f"\n_Task ID: {task.task_id[:8]}_"
                return msg
            else:
                msg = f"[WARNING] **Task Completed with Issues ⚠️**\n\n"
                msg += f"**Request:** {task.user_request}\n\n"
                if error:
                    msg += f"**Error:** {error}\n\n"
                else:
                    msg += "**Issue:** Task did not complete successfully.\n\n"
                
                msg += f"\n_Task ID: {task.task_id[:8]}_"
                return msg
        else:
            # Simple result
            return (
                f"[COMPLETED] **Task Completed**\n\n"
                f"**Request:** {task.user_request}\n\n"
                f"_Task ID: {task.task_id}_"
            )
    
    def _save_task(self, task: BackgroundTask):
        """
        Save task to SQLite for persistence.
        
        ARCHITECTURE CHANGE:
        - Tasks saved to SQLite immediately on create/update
        - Enables crash recovery and daemon restarts
        """
        from genesis.database.base import get_session
        from genesis.database.models import BackgroundTaskRecord
        
        try:
            with get_session() as session:
                # Check if task exists
                existing = session.query(BackgroundTaskRecord).filter(
                    BackgroundTaskRecord.task_id == task.task_id
                ).first()
                
                if existing:
                    # Update existing task
                    existing.status = task.status.value
                    existing.progress = task.progress
                    existing.started_at = task.started_at
                    existing.completed_at = task.completed_at
                    existing.result = task.result
                    existing.error = task.error
                    existing.retry_count = task.retry_count
                else:
                    # Create new task record
                    record = BackgroundTaskRecord(
                        task_id=task.task_id,
                        mind_gmid=self.mind.identity.gmid,
                        user_email=task.user_email,
                        user_request=task.user_request,
                        status=task.status.value,
                        progress=task.progress,
                        created_at=task.created_at,
                        started_at=task.started_at,
                        completed_at=task.completed_at,
                        result=task.result,
                        error=task.error,
                        retry_count=task.retry_count,
                        max_retries=task.max_retries
                    )
                    session.add(record)
                
                session.commit()
                logger.debug(f"[BACKGROUND] Saved task {task.task_id} to SQLite")
        except Exception as e:
            logger.error(f"[BACKGROUND] Error saving task to SQLite: {e}")
    
    def _load_active_tasks(self):
        """
        Load pending/running tasks from SQLite for crash recovery.
        
        ARCHITECTURE CHANGE:
        - On daemon start, resume any incomplete tasks
        - Prevents task loss from crashes/restarts
        """
        from genesis.database.base import get_session
        from genesis.database.models import BackgroundTaskRecord
        
        try:
            with get_session() as session:
                # Load pending and running tasks
                active_records = session.query(BackgroundTaskRecord).filter(
                    BackgroundTaskRecord.mind_gmid == self.mind.identity.gmid,
                    BackgroundTaskRecord.status.in_(['pending', 'running', 'retrying'])
                ).all()
                
                for record in active_records:
                    task = BackgroundTask(
                        task_id=record.task_id,
                        user_request=record.user_request,
                        user_email=record.user_email,
                        status=TaskStatus(record.status),
                        created_at=record.created_at,
                        started_at=record.started_at,
                        completed_at=record.completed_at,
                        progress=record.progress,
                        result=record.result,
                        error=record.error,
                        retry_count=record.retry_count,
                        max_retries=record.max_retries
                    )
                    self.active_tasks[task.task_id] = task
                
                if active_records:
                    logger.info(f"[BACKGROUND] Loaded {len(active_records)} pending tasks for recovery")
        except Exception as e:
            logger.error(f"[BACKGROUND] Error loading tasks from SQLite: {e}")
            # Not fatal - start with empty task list


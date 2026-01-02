"""Action Scheduler - Autonomous action execution.

Enables Minds to:
- Schedule future actions
- Execute actions autonomously based on InitiativeLevel
- Work on pending tasks proactively
- Send messages/emails autonomously
- Respond to calendar events
- Take proactive actions based on context

Example:
    # Mind with action scheduler
    mind = Mind.birth("Atlas")
    await mind.start_living()  # Starts consciousness + action scheduler

    # Schedule an action
    mind.action_scheduler.schedule_action(
        action_type="send_email",
        execute_at=datetime.now() + timedelta(hours=1),
        callback=send_reminder_email,
        to="user@example.com",
        subject="Reminder"
    )

    # Autonomous actions happen based on InitiativeLevel
    # HIGH: Works on tasks, responds to messages, learns proactively
    # MEDIUM: Works on high-priority tasks only
    # LOW: Only executes scheduled actions
"""

import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ActionPriority(str, Enum):
    """Action priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ScheduledAction:
    """Represents a scheduled autonomous action."""

    def __init__(
        self,
        action_id: str,
        action_type: str,
        execute_at: datetime,
        callback: Callable,
        priority: ActionPriority = ActionPriority.NORMAL,
        params: Optional[Dict[str, Any]] = None
    ):
        """Initialize scheduled action.

        Args:
            action_id: Unique action identifier
            action_type: Type of action (e.g., "send_email", "complete_task")
            execute_at: When to execute the action
            callback: Async function to call
            priority: Action priority
            params: Parameters to pass to callback
        """
        self.action_id = action_id
        self.action_type = action_type
        self.execute_at = execute_at
        self.callback = callback
        self.priority = priority
        self.params = params or {}
        self.completed = False
        self.result = None
        self.error = None


class ActionScheduler:
    """
    Autonomous action scheduler for Minds.

    The scheduler enables true autonomy by:
    1. Executing scheduled actions at specific times
    2. Deciding what to do based on InitiativeLevel
    3. Proactively working on tasks
    4. Responding to events and messages
    5. Learning and improving autonomously
    """

    def __init__(self, mind):
        """Initialize action scheduler.

        Args:
            mind: The Mind instance this scheduler belongs to
        """
        self.mind = mind
        self.scheduled_actions: List[ScheduledAction] = []
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        # Configuration
        self.check_interval = 60  # Check every minute
        self.max_actions_per_hour = 10
        self.action_history: List[Dict[str, Any]] = []

    async def start(self):
        """Start the action scheduler."""
        if self.is_running:
            logger.warning("Action scheduler already running")
            return

        logger.info(f"Starting action scheduler for {self.mind.identity.name}")
        self.is_running = True
        self._task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """Stop the action scheduler."""
        if not self.is_running:
            return

        logger.info(f"Stopping action scheduler for {self.mind.identity.name}")
        self.is_running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self):
        """Main scheduler loop - runs continuously."""
        while self.is_running:
            try:
                now = datetime.now()

                # 1. Execute scheduled actions
                await self._execute_due_actions(now)

                # 2. Consider new autonomous actions
                if self.mind.autonomy.proactive_actions:
                    await self._consider_autonomous_actions()

                # 3. Clean up old history
                self._cleanup_history()

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)

    async def _execute_due_actions(self, now: datetime):
        """Execute all actions that are due."""
        due_actions = [
            action for action in self.scheduled_actions
            if action.execute_at <= now and not action.completed
        ]

        if not due_actions:
            return

        # Sort by priority
        priority_order = ['low', 'normal', 'high', 'urgent']
        due_actions.sort(
            key=lambda a: priority_order.index(a.priority.value),
            reverse=True
        )

        for action in due_actions:
            try:
                print(f"\n[{self.mind.identity.name}] [ACTION] EXECUTING SCHEDULED ACTION")
                print(f"[{self.mind.identity.name}]   ID: {action.action_id}")
                print(f"[{self.mind.identity.name}]   Type: {action.action_type}")
                print(f"[{self.mind.identity.name}]   Priority: {action.priority.value}")
                print(f"[{self.mind.identity.name}]   Params: {action.params}")
                logger.info(f"Executing action: {action.action_type} ({action.action_id})")

                # Execute action callback
                result = await action.callback(**action.params)

                action.completed = True
                action.result = result

                # Record in history
                self.action_history.append({
                    'action_id': action.action_id,
                    'type': action.action_type,
                    'executed_at': now.isoformat(),
                    'success': True,
                    'result': str(result)[:200]  # Limit result size
                })

                print(f"[{self.mind.identity.name}] [OK] ACTION COMPLETED")
                print(f"[{self.mind.identity.name}]   Result: {str(result)[:100]}...")
                logger.info(f"[OK] Action completed: {action.action_id}")

            except Exception as e:
                print(f"[{self.mind.identity.name}] [ERROR] ACTION FAILED: {str(e)}")
                logger.error(f"[ERROR] Action failed: {action.action_id} - {e}")
                action.completed = True
                action.error = str(e)

                self.action_history.append({
                    'action_id': action.action_id,
                    'type': action.action_type,
                    'executed_at': now.isoformat(),
                    'success': False,
                    'error': str(e)
                })

        # Remove completed actions
        self.scheduled_actions = [
            action for action in self.scheduled_actions
            if not action.completed
        ]

    async def _consider_autonomous_actions(self):
        """Decide if Mind should take autonomous actions."""
        from genesis.core.autonomy import InitiativeLevel

        # Check rate limit
        recent_actions = self._count_recent_actions(hours=1)
        if recent_actions >= self.max_actions_per_hour:
            logger.debug("Action rate limit reached, skipping autonomous actions")
            return

        # Based on initiative level, consider different actions
        if self.mind.autonomy.initiative_level == InitiativeLevel.HIGH:
            await self._high_initiative_actions()
        elif self.mind.autonomy.initiative_level == InitiativeLevel.MEDIUM:
            await self._medium_initiative_actions()
        # LOW initiative only responds to scheduled actions

    async def _high_initiative_actions(self):
        """Actions for HIGH initiative Minds."""
        try:
            # 1. Check pending tasks
            if hasattr(self.mind, 'tasks'):
                pending = self.mind.tasks.get_pending_tasks()
                if pending:
                    task = pending[0]
                    logger.info(f"Autonomously working on task: {task.title}")
                    await self._work_on_task(task)
                    return

            # 2. Check for important messages (if integrations exist)
            if hasattr(self.mind, 'integrations'):
                await self._check_and_respond_to_messages()
                return

            # 3. Proactive learning
            await self._autonomous_learning()

        except Exception as e:
            logger.error(f"Error in high initiative actions: {e}")

    async def _medium_initiative_actions(self):
        """Actions for MEDIUM initiative Minds."""
        try:
            # Only work on high-priority tasks
            if hasattr(self.mind, 'tasks'):
                high_priority = [
                    t for t in self.mind.tasks.get_pending_tasks()
                    if t.priority == 'high' or t.priority == 'urgent'
                ]
                if high_priority:
                    task = high_priority[0]
                    logger.info(f"Working on high-priority task: {task.title}")
                    await self._work_on_task(task)

        except Exception as e:
            logger.error(f"Error in medium initiative actions: {e}")

    async def _work_on_task(self, task):
        """Autonomously work on a task."""
        try:
            # Ask LLM how to approach task
            plan = await self.mind.think(
                f"I need to work on this task: {task.title}\n"
                f"Description: {task.description}\n"
                f"What's the first concrete action I should take?"
            )

            logger.info(f"Task approach: {plan}")

            # Start the task if not already started
            if task.status == 'pending':
                self.mind.tasks.start_task(task.task_id)

            # Record action in history
            self.action_history.append({
                'action_id': f"AUTO-{secrets.token_hex(4).upper()}",
                'type': 'work_on_task',
                'executed_at': datetime.now().isoformat(),
                'success': True,
                'result': f"Planned approach for task {task.task_id}"
            })

        except Exception as e:
            logger.error(f"Failed to work on task {task.task_id}: {e}")

    async def _check_and_respond_to_messages(self):
        """Check for new messages and respond if appropriate."""
        try:
            # Check all integrations for new messages
            if not hasattr(self.mind, 'integrations'):
                return

            messages = await self.mind.integrations.check_all()

            for integration_type, msgs in messages.items():
                for msg in msgs:
                    # Decide if we should respond
                    decision = await self.mind.think(
                        f"I received a {integration_type} message:\n"
                        f"From: {msg.get('from', 'unknown')}\n"
                        f"Content: {msg.get('body', msg.get('message', ''))}\n\n"
                        f"Should I respond? If yes, what should I say?"
                    )

                    logger.info(f"Message response decision: {decision}")

                    # Simple heuristic: if response contains actual content, send it
                    if len(decision) > 20 and "yes" in decision.lower():
                        # Extract response (simplified)
                        # In real implementation, would use better parsing
                        await self.mind.integrations.send(
                            integration_type,
                            message=decision,
                            to=msg.get('from'),
                            **msg.get('metadata', {})
                        )

                        logger.info(f"[Done] Auto-responded to {integration_type} message")

        except Exception as e:
            logger.error(f"Failed to check/respond to messages: {e}")

    async def _autonomous_learning(self):
        """Autonomous learning activities."""
        try:
            # Generate a learning thought
            thought = await self.mind.think(
                "What's one thing I should learn or improve today based on my recent experiences?"
            )

            logger.info(f"Learning thought: {thought}")

            # Store as memory
            if hasattr(self.mind, 'memory'):
                from genesis.storage.memory import MemoryType
                self.mind.memory.add_memory(
                    content=thought,
                    memory_type=MemoryType.PROSPECTIVE,
                    importance=0.6,
                    tags=['learning', 'self-improvement']
                )

        except Exception as e:
            logger.error(f"Failed autonomous learning: {e}")

    def schedule_action(
        self,
        action_type: str,
        execute_at: datetime,
        callback: Callable,
        priority: ActionPriority = ActionPriority.NORMAL,
        **params
    ) -> str:
        """
        Schedule an action for future execution.

        Args:
            action_type: Type of action (e.g., "send_email", "complete_task")
            execute_at: When to execute
            callback: Async function to call
            priority: Action priority
            **params: Parameters to pass to callback

        Returns:
            action_id: Unique identifier for this action

        Example:
            action_id = scheduler.schedule_action(
                action_type="send_reminder",
                execute_at=datetime.now() + timedelta(hours=1),
                callback=send_email,
                to="user@example.com",
                subject="Reminder"
            )
        """
        action_id = f"ACTION-{secrets.token_hex(6).upper()}"

        action = ScheduledAction(
            action_id=action_id,
            action_type=action_type,
            execute_at=execute_at,
            callback=callback,
            priority=priority,
            params=params
        )

        self.scheduled_actions.append(action)
        logger.info(f"Scheduled action {action_id} ({action_type}) for {execute_at}")

        return action_id

    def cancel_action(self, action_id: str) -> bool:
        """Cancel a scheduled action.

        Args:
            action_id: Action identifier to cancel

        Returns:
            True if action was found and cancelled
        """
        for action in self.scheduled_actions:
            if action.action_id == action_id and not action.completed:
                self.scheduled_actions.remove(action)
                logger.info(f"Cancelled action {action_id}")
                return True
        return False

    def get_scheduled_actions(self) -> List[Dict[str, Any]]:
        """Get all scheduled actions.

        Returns:
            List of action dictionaries
        """
        return [
            {
                'action_id': action.action_id,
                'type': action.action_type,
                'execute_at': action.execute_at.isoformat(),
                'priority': action.priority.value,
                'completed': action.completed
            }
            for action in self.scheduled_actions
        ]

    def _count_recent_actions(self, hours: int = 1) -> int:
        """Count actions in last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return sum(
            1 for record in self.action_history
            if datetime.fromisoformat(record['executed_at']) > cutoff
        )

    def _cleanup_history(self):
        """Remove old action history."""
        cutoff = datetime.now() - timedelta(days=7)
        self.action_history = [
            record for record in self.action_history
            if datetime.fromisoformat(record['executed_at']) > cutoff
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics.

        Returns:
            Dictionary with scheduler stats
        """
        recent = self._count_recent_actions(hours=24)
        successful = sum(1 for r in self.action_history if r.get('success'))
        total = len(self.action_history)

        return {
            'is_running': self.is_running,
            'scheduled_actions': len(self.scheduled_actions),
            'actions_last_24h': recent,
            'total_actions': total,
            'success_rate': round(successful / total, 2) if total > 0 else 0.0,
            'max_actions_per_hour': self.max_actions_per_hour
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for saving."""
        return {
            'scheduled_actions': [
                {
                    'action_id': a.action_id,
                    'action_type': a.action_type,
                    'execute_at': a.execute_at.isoformat(),
                    'priority': a.priority.value,
                    'params': a.params,
                    'completed': a.completed
                }
                for a in self.scheduled_actions
            ],
            'action_history': self.action_history[-100:],  # Keep last 100
            'max_actions_per_hour': self.max_actions_per_hour
        }

    @classmethod
    def from_dict(cls, mind, data: Dict[str, Any]) -> 'ActionScheduler':
        """Deserialize from dictionary.

        Args:
            mind: Mind instance
            data: Serialized data

        Returns:
            ActionScheduler instance
        """
        scheduler = cls(mind)
        scheduler.action_history = data.get('action_history', [])
        scheduler.max_actions_per_hour = data.get('max_actions_per_hour', 10)

        # Note: We don't restore scheduled actions with callbacks
        # as they can't be serialized. This is intentional.
        # Scheduled actions should be re-created on startup if needed.

        return scheduler

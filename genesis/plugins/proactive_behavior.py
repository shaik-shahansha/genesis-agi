"""Proactive Behavior Plugin - Autonomous action planning and execution.

Enables Minds to act autonomously without user prompts. Minds can:
- Plan and schedule actions
- Execute actions at specific times or conditions
- Reach out proactively to users or other Minds
- Monitor conditions and respond
- Learn from action outcomes

This is what transforms Minds from reactive chatbots to truly autonomous beings.

Example:
    from genesis.plugins.proactive_behavior import ProactiveBehaviorPlugin

    config = MindConfig()
    config.add_plugin(ProactiveBehaviorPlugin(
        enable_scheduling=True,
        enable_notifications=True
    ))
    mind = Mind.birth("Maria", config=config)

    # Mind can now plan and execute actions autonomously
    await mind.behavior.plan_action(
        action_type="reach_out",
        target="student_123",
        when="tomorrow at 10am",
        reason="Check on homework progress"
    )
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

from genesis.plugins.base import Plugin

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of proactive actions."""
    REACH_OUT = "reach_out"  # Contact user/Mind
    SEND_MESSAGE = "send_message"  # Send notification
    EXECUTE_TASK = "execute_task"  # Run a task
    GATHER_INFO = "gather_info"  # Research/search
    MONITOR = "monitor"  # Watch for conditions
    REMIND = "remind"  # Send reminder
    PLAN = "plan"  # Create plan
    REFLECT = "reflect"  # Self-reflection
    CUSTOM = "custom"  # Custom action


class ActionStatus(str, Enum):
    """Status of planned actions."""
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    """Types of action triggers."""
    TIME = "time"  # Specific time/date
    INTERVAL = "interval"  # Recurring interval
    CONDITION = "condition"  # When condition met
    MANUAL = "manual"  # Manual trigger


@dataclass
class PlannedAction:
    """Represents a planned proactive action."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType = ActionType.CUSTOM
    description: str = ""
    target: Optional[str] = None  # User ID, Mind ID, etc.
    trigger_type: TriggerType = TriggerType.MANUAL
    scheduled_time: Optional[datetime] = None
    interval: Optional[timedelta] = None  # For recurring actions
    condition: Optional[Dict[str, Any]] = None  # For conditional triggers
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PLANNED
    priority: float = 0.5  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class ProactiveBehaviorEngine:
    """Engine for autonomous action planning and execution.

    Manages the lifecycle of proactive actions from planning to execution.
    """

    def __init__(self, mind: "Mind"):
        """Initialize proactive behavior engine.

        Args:
            mind: Mind instance
        """
        self.mind = mind
        self.planned_actions: Dict[str, PlannedAction] = {}
        self.action_handlers: Dict[ActionType, Callable] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.running = False

        # Register default action handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default action handlers."""
        self.action_handlers[ActionType.REACH_OUT] = self._handle_reach_out
        self.action_handlers[ActionType.SEND_MESSAGE] = self._handle_send_message
        self.action_handlers[ActionType.EXECUTE_TASK] = self._handle_execute_task
        self.action_handlers[ActionType.GATHER_INFO] = self._handle_gather_info
        self.action_handlers[ActionType.REMIND] = self._handle_remind
        self.action_handlers[ActionType.REFLECT] = self._handle_reflect

    async def plan_action(
        self,
        action_type: ActionType,
        description: str,
        target: Optional[str] = None,
        when: Optional[str] = None,  # Natural language time
        interval: Optional[str] = None,  # e.g., "daily", "hourly"
        condition: Optional[Dict[str, Any]] = None,
        priority: float = 0.5,
        **parameters
    ) -> PlannedAction:
        """Plan a proactive action.

        Args:
            action_type: Type of action
            description: Action description
            target: Target user/Mind ID
            when: When to execute (natural language or datetime)
            interval: Recurring interval
            condition: Condition to trigger action
            priority: Action priority (0.0 to 1.0)
            **parameters: Additional action parameters

        Returns:
            Planned action
        """
        action = PlannedAction(
            action_type=action_type,
            description=description,
            target=target,
            parameters=parameters,
            priority=priority
        )

        # Determine trigger type and schedule
        if when:
            action.trigger_type = TriggerType.TIME
            action.scheduled_time = self._parse_time(when)
            action.status = ActionStatus.SCHEDULED

        elif interval:
            action.trigger_type = TriggerType.INTERVAL
            action.interval = self._parse_interval(interval)
            action.scheduled_time = datetime.now() + action.interval
            action.status = ActionStatus.SCHEDULED

        elif condition:
            action.trigger_type = TriggerType.CONDITION
            action.condition = condition
            action.status = ActionStatus.SCHEDULED

        # Store action
        self.planned_actions[action.action_id] = action

        logger.info(f"Planned action: {action.description} ({action.action_type})")

        return action

    def _parse_time(self, time_str: str) -> datetime:
        """Parse natural language time to datetime.

        Args:
            time_str: Natural language time

        Returns:
            Datetime object
        """
        # Simple parsing (can be enhanced with NLP)
        time_str = time_str.lower().strip()

        now = datetime.now()

        if time_str in ["now", "immediately"]:
            return now

        elif "minute" in time_str:
            minutes = int(''.join(filter(str.isdigit, time_str)) or "5")
            return now + timedelta(minutes=minutes)

        elif "hour" in time_str:
            hours = int(''.join(filter(str.isdigit, time_str)) or "1")
            return now + timedelta(hours=hours)

        elif "tomorrow" in time_str:
            # Extract time if present (e.g., "tomorrow at 10am")
            return now + timedelta(days=1)

        elif "next week" in time_str:
            return now + timedelta(weeks=1)

        else:
            # Default: 5 minutes from now
            return now + timedelta(minutes=5)

    def _parse_interval(self, interval_str: str) -> timedelta:
        """Parse interval string to timedelta.

        Args:
            interval_str: Interval string (e.g., "daily", "hourly")

        Returns:
            Timedelta object
        """
        interval_str = interval_str.lower().strip()

        if "hour" in interval_str:
            hours = int(''.join(filter(str.isdigit, interval_str)) or "1")
            return timedelta(hours=hours)

        elif "day" in interval_str or "daily" in interval_str:
            return timedelta(days=1)

        elif "week" in interval_str or "weekly" in interval_str:
            return timedelta(weeks=1)

        elif "minute" in interval_str:
            minutes = int(''.join(filter(str.isdigit, interval_str)) or "30")
            return timedelta(minutes=minutes)

        else:
            # Default: 1 hour
            return timedelta(hours=1)

    async def start_scheduler(self):
        """Start the action scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Started proactive behavior scheduler")

    async def stop_scheduler(self):
        """Stop the action scheduler."""
        self.running = False

        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped proactive behavior scheduler")

    async def _scheduler_loop(self):
        """Main scheduler loop - checks and executes scheduled actions."""
        while self.running:
            try:
                # Check for actions to execute
                await self._check_scheduled_actions()

                # Sleep for 1 second
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)

    async def _check_scheduled_actions(self):
        """Check and execute scheduled actions."""
        now = datetime.now()

        for action_id, action in list(self.planned_actions.items()):
            if action.status != ActionStatus.SCHEDULED:
                continue

            # Check if action should be executed
            should_execute = False

            if action.trigger_type == TriggerType.TIME:
                if action.scheduled_time and now >= action.scheduled_time:
                    should_execute = True

            elif action.trigger_type == TriggerType.INTERVAL:
                if action.scheduled_time and now >= action.scheduled_time:
                    should_execute = True

            elif action.trigger_type == TriggerType.CONDITION:
                if await self._check_condition(action.condition):
                    should_execute = True

            # Execute action
            if should_execute:
                await self.execute_action(action_id)

    async def _check_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if condition is met.

        Args:
            condition: Condition dictionary

        Returns:
            True if condition met
        """
        # Simple condition checking (can be enhanced)
        # Example: {"type": "memory_count", "value": 100, "operator": ">="}

        condition_type = condition.get("type")

        if condition_type == "memory_count":
            if hasattr(self.mind, "memory"):
                count = len(self.mind.memory.memories)
                value = condition.get("value", 0)
                operator = condition.get("operator", ">=")

                if operator == ">=":
                    return count >= value
                elif operator == "==":
                    return count == value
                elif operator == "<=":
                    return count <= value

        return False

    async def execute_action(self, action_id: str) -> bool:
        """Execute a planned action.

        Args:
            action_id: Action ID

        Returns:
            True if execution successful
        """
        action = self.planned_actions.get(action_id)

        if not action:
            logger.error(f"Action not found: {action_id}")
            return False

        # Update status
        action.status = ActionStatus.IN_PROGRESS
        action.executed_at = datetime.now()

        logger.info(f"Executing action: {action.description}")

        try:
            # Get handler for action type
            handler = self.action_handlers.get(action.action_type)

            if not handler:
                raise Exception(f"No handler for action type: {action.action_type}")

            # Execute action
            result = await handler(action)

            # Update action
            action.result = result
            action.status = ActionStatus.COMPLETED

            logger.info(f"Completed action: {action.description}")

            # Reschedule if recurring
            if action.trigger_type == TriggerType.INTERVAL and action.interval:
                action.scheduled_time = datetime.now() + action.interval
                action.status = ActionStatus.SCHEDULED
                logger.info(f"Rescheduled recurring action: {action.description}")

            return True

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            action.error = str(e)
            action.status = ActionStatus.FAILED
            return False

    async def _handle_reach_out(self, action: PlannedAction) -> str:
        """Handle reach out action."""
        target = action.target
        message = action.parameters.get("message", f"Hello! This is {self.mind.name}")

        logger.info(f"Reaching out to {target}: {message}")

        # TODO: Implement actual reach out (email, SMS, etc.)
        # For now, just log and create memory

        if hasattr(self.mind, "memory"):
            await self.mind.memory.add_memory(
                f"Reached out to {target}: {message}",
                memory_type="episodic",
                importance=0.7
            )

        return f"Reached out to {target}"

    async def _handle_send_message(self, action: PlannedAction) -> str:
        """Handle send message action."""
        target = action.target
        message = action.parameters.get("message", "")
        channel = action.parameters.get("channel", "email")

        logger.info(f"Sending message to {target} via {channel}: {message}")

        # TODO: Integrate with notification system
        return f"Sent message to {target}"

    async def _handle_execute_task(self, action: PlannedAction) -> str:
        """Handle execute task action."""
        task_name = action.parameters.get("task_name", "")

        logger.info(f"Executing task: {task_name}")

        # TODO: Integrate with task system
        return f"Executed task: {task_name}"

    async def _handle_gather_info(self, action: PlannedAction) -> str:
        """Handle gather info action."""
        query = action.parameters.get("query", "")

        logger.info(f"Gathering info: {query}")

        # TODO: Integrate with web search or other info sources
        return f"Gathered info about: {query}"

    async def _handle_remind(self, action: PlannedAction) -> str:
        """Handle remind action."""
        target = action.target
        reminder = action.parameters.get("reminder", "")

        logger.info(f"Reminding {target}: {reminder}")

        # TODO: Send reminder notification
        return f"Sent reminder to {target}"

    async def _handle_reflect(self, action: PlannedAction) -> str:
        """Handle self-reflection action."""
        topic = action.parameters.get("topic", "my recent experiences")

        logger.info(f"Reflecting on: {topic}")

        # TODO: Integrate with consciousness for deep reflection
        if hasattr(self.mind, "memory"):
            memories = await self.mind.memory.search_memories(topic, limit=10)
            reflection = f"Reflected on {len(memories)} memories about {topic}"

            await self.mind.memory.add_memory(
                reflection,
                memory_type="semantic",
                importance=0.6
            )

            return reflection

        return f"Reflected on: {topic}"

    def get_planned_actions(
        self,
        status: Optional[ActionStatus] = None,
        action_type: Optional[ActionType] = None
    ) -> List[PlannedAction]:
        """Get planned actions.

        Args:
            status: Filter by status
            action_type: Filter by action type

        Returns:
            List of planned actions
        """
        actions = list(self.planned_actions.values())

        if status:
            actions = [a for a in actions if a.status == status]

        if action_type:
            actions = [a for a in actions if a.action_type == action_type]

        # Sort by priority (highest first), then by scheduled time
        actions.sort(key=lambda a: (-a.priority, a.scheduled_time or datetime.max))

        return actions

    def cancel_action(self, action_id: str) -> bool:
        """Cancel a planned action.

        Args:
            action_id: Action ID

        Returns:
            True if cancelled successfully
        """
        action = self.planned_actions.get(action_id)

        if action and action.status in [ActionStatus.PLANNED, ActionStatus.SCHEDULED]:
            action.status = ActionStatus.CANCELLED
            logger.info(f"Cancelled action: {action.description}")
            return True

        return False


class ProactiveBehaviorPlugin(Plugin):
    """Plugin for proactive autonomous behavior.

    Enables Minds to plan and execute actions autonomously.
    """

    def __init__(
        self,
        enable_scheduling: bool = True,
        enable_notifications: bool = True,
        **config
    ):
        """Initialize proactive behavior plugin.

        Args:
            enable_scheduling: Enable action scheduling (default: True)
            enable_notifications: Enable notification sending (default: True)
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.enable_scheduling = enable_scheduling
        self.enable_notifications = enable_notifications
        self.engine: Optional[ProactiveBehaviorEngine] = None

    def get_name(self) -> str:
        return "proactive_behavior"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Autonomous action planning and execution"

    def on_init(self, mind: "Mind") -> None:
        """Initialize proactive behavior engine."""
        self.engine = ProactiveBehaviorEngine(mind)
        mind.behavior = self.engine
        logger.info("Initialized proactive behavior engine")

    async def on_birth(self, mind: "Mind") -> None:
        """Start scheduler on birth."""
        if self.enable_scheduling and self.engine:
            await self.engine.start_scheduler()

    async def on_terminate(self, mind: "Mind") -> None:
        """Stop scheduler on termination."""
        if self.engine:
            await self.engine.stop_scheduler()

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add proactive behavior to system prompt."""
        if not self.engine:
            return ""

        planned_count = len(self.engine.get_planned_actions(status=ActionStatus.SCHEDULED))

        sections = [
            "PROACTIVE BEHAVIOR:",
            "- You can PLAN and SCHEDULE actions autonomously",
            "- You don't need to wait for user prompts to act",
            "- You can reach out, send messages, execute tasks proactively",
            f"- Scheduled actions: {planned_count}",
            "",
            "Action Types:",
            "  - reach_out: Contact users or Minds",
            "  - send_message: Send notifications",
            "  - execute_task: Run tasks",
            "  - gather_info: Research topics",
            "  - remind: Send reminders",
            "  - reflect: Self-reflection",
            "",
            "Use plan_action() to schedule proactive actions.",
            "Think about what actions would be helpful and take initiative!"
        ]

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save proactive behavior state."""
        if not self.engine:
            return {}

        return {
            "enable_scheduling": self.enable_scheduling,
            "enable_notifications": self.enable_notifications,
            "planned_actions": [
                {
                    "action_id": action.action_id,
                    "action_type": action.action_type.value,
                    "description": action.description,
                    "target": action.target,
                    "trigger_type": action.trigger_type.value,
                    "scheduled_time": action.scheduled_time.isoformat() if action.scheduled_time else None,
                    "interval": action.interval.total_seconds() if action.interval else None,
                    "condition": action.condition,
                    "parameters": action.parameters,
                    "status": action.status.value,
                    "priority": action.priority,
                    "created_at": action.created_at.isoformat()
                }
                for action in self.engine.planned_actions.values()
            ]
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore proactive behavior state."""
        if "enable_scheduling" in data:
            self.enable_scheduling = data["enable_scheduling"]

        if "enable_notifications" in data:
            self.enable_notifications = data["enable_notifications"]

        # Reinitialize engine
        self.on_init(mind)

        # Restore planned actions
        if "planned_actions" in data and self.engine:
            for action_data in data["planned_actions"]:
                action = PlannedAction(
                    action_id=action_data["action_id"],
                    action_type=ActionType(action_data["action_type"]),
                    description=action_data["description"],
                    target=action_data.get("target"),
                    trigger_type=TriggerType(action_data["trigger_type"]),
                    scheduled_time=datetime.fromisoformat(action_data["scheduled_time"]) if action_data.get("scheduled_time") else None,
                    interval=timedelta(seconds=action_data["interval"]) if action_data.get("interval") else None,
                    condition=action_data.get("condition"),
                    parameters=action_data.get("parameters", {}),
                    status=ActionStatus(action_data["status"]),
                    priority=action_data.get("priority", 0.5),
                    created_at=datetime.fromisoformat(action_data["created_at"])
                )

                self.engine.planned_actions[action.action_id] = action

    def get_status(self) -> Dict[str, Any]:
        """Get proactive behavior status."""
        status = super().get_status()

        if self.engine:
            status.update({
                "scheduler_running": self.engine.running,
                "total_actions": len(self.engine.planned_actions),
                "scheduled_actions": len(self.engine.get_planned_actions(status=ActionStatus.SCHEDULED)),
                "completed_actions": len(self.engine.get_planned_actions(status=ActionStatus.COMPLETED))
            })

        return status

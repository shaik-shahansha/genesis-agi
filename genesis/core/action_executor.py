"""
Action Executor - The Intelligence Bridge Between Consciousness and Execution

This is the BRAIN of autonomous action - it bridges:
- LLM decision-making -> Actual execution
- Consciousness thoughts -> Real-world actions
- User requests -> Tool/plugin calls
- Scheduled actions -> Timed execution

The executor provides:
1. Function calling for LLMs (like OpenAI's function calling)
2. Autonomy permission checks before execution
3. Action planning and decomposition
4. Result tracking and learning
5. Risk assessment and safety checks

This is what makes a Mind truly autonomous - not just thinking, but DOING.

Example:
    # User: "Send me an email reminder in 1 hour"
    # 1. LLM decides: schedule_action(send_email, time=+1h)
    # 2. Executor checks permissions
    # 3. Action scheduled
    # 4. After 1 hour: Email sent
"""

import asyncio
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel

from genesis.core.autonomy import Autonomy, PermissionLevel
from genesis.storage.memory import MemoryType

logger = logging.getLogger(__name__)


class ActionCategory(str, Enum):
    """Categories of actions a Mind can take."""
    COMMUNICATION = "communication"  # Email, message, call
    TASK_MANAGEMENT = "task_management"  # Create, update, complete tasks
    INFORMATION = "information"  # Search, read, analyze
    MEMORY = "memory"  # Store, retrieve, reflect
    SCHEDULING = "scheduling"  # Schedule future actions
    FILE_OPERATION = "file_operation"  # Read, write files
    TOOL_EXECUTION = "tool_execution"  # Run custom tools
    RELATIONSHIP = "relationship"  # Interact with other minds
    LEARNING = "learning"  # Learn new skills
    SELF_REFLECTION = "self_reflection"  # Think about self


class ActionStatus(str, Enum):
    """Status of an action."""
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class ActionDefinition:
    """Definition of an available action (like a function signature)."""
    name: str
    category: ActionCategory
    description: str
    parameters: Dict[str, Dict[str, Any]]  # param_name -> {type, description, required}
    permission_level: PermissionLevel
    risk_level: float = 0.3  # 0=safe, 1=dangerous
    cost_essence: int = 0  # GEN cost to execute
    execution_handler: Optional[Callable] = None  # Function to execute
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []
        
        for param_name, param_info in self.parameters.items():
            properties[param_name] = {
                "type": param_info.get("type", "string"),
                "description": param_info["description"]
            }
            if param_info.get("enum"):
                properties[param_name]["enum"] = param_info["enum"]
            if param_info.get("required", False):
                required.append(param_name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


@dataclass
class ActionRequest:
    """A request to execute an action."""
    action_id: str
    action_name: str
    parameters: Dict[str, Any]
    category: ActionCategory
    requester: str  # "consciousness", "user", "scheduled", "plugin"
    context: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    status: ActionStatus = ActionStatus.PENDING
    confidence: float = 1.0  # How confident is the LLM about this action
    reasoning: str = ""  # Why this action was chosen
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None

    # --- Governance (ADR-0006/0007/0008) ------------------------------- #
    # Populated by the governance gate. `risk_level` and `policy_decision`
    # record *why* an action was allowed, queued, or refused, so the UI and the
    # audit export can explain it without re-running the policy engine.
    risk_level: Optional[str] = None
    policy_decision: Optional[Dict[str, Any]] = None
    approval_id: Optional[str] = None
    receipt_id: Optional[str] = None
    requires_approval: bool = False
    blocked_reason: Optional[str] = None


class ActionExecutor:
    """
    The central action execution engine for autonomous Minds.
    
    This is the bridge between thinking and doing. It:
    - Registers available actions from plugins
    - Provides function schemas to LLMs
    - Validates permissions before execution
    - Executes actions safely
    - Tracks results and learns
    - Handles scheduling and retries
    """
    
    def __init__(self, mind):
        """Initialize action executor.
        
        Args:
            mind: The Mind instance this executor belongs to
        """
        self.mind = mind
        self.autonomy: Autonomy = mind.autonomy
        
        # Governance gate is resolved lazily: constructing it eagerly would
        # require a database connection, and the executor is also used in
        # paths (tests, CLI introspection) where that is not available.
        self._gate_cache = None

        # Registry of available actions
        self.actions: Dict[str, ActionDefinition] = {}

        # Governance bookkeeping: the PolicyContext and PolicyDecision for each
        # in-flight action, so the terminal receipt can reference the decision
        # that authorized it. Bounded to avoid unbounded growth.
        self._governance_contexts: Dict[str, Any] = {}
        self._governance_decisions: Dict[str, Any] = {}
        self._governance_index: List[str] = []
        
        # Action history
        self.action_history: List[ActionRequest] = []
        self.pending_approvals: List[ActionRequest] = []
        
        # Statistics
        self.stats = {
            "total_actions": 0,
            "successful": 0,
            "failed": 0,
            "rejected": 0,
            "by_category": {}
        }
        
        # Register core actions
        self._register_core_actions()
    
    def _register_core_actions(self):
        """Register core actions available to all Minds."""
        
        # MEMORY ACTIONS
        self.register_action(ActionDefinition(
            name="add_memory",
            category=ActionCategory.MEMORY,
            description="Store a new memory for later recall",
            parameters={
                "content": {"type": "string", "description": "Memory content", "required": True},
                "memory_type": {"type": "string", "description": "Type: episodic, semantic, procedural, prospective", "enum": ["episodic", "semantic", "procedural", "prospective"], "required": True},
                "importance": {"type": "number", "description": "Importance 0-1", "required": False},
                "tags": {"type": "array", "description": "Tags for categorization", "required": False}
            },
            permission_level=PermissionLevel.ALWAYS_ALLOWED,
            execution_handler=self._execute_add_memory
        ))
        
        self.register_action(ActionDefinition(
            name="search_memory",
            category=ActionCategory.MEMORY,
            description="Search through memories to find relevant information",
            parameters={
                "query": {"type": "string", "description": "What to search for", "required": True},
                "limit": {"type": "integer", "description": "Max results", "required": False}
            },
            permission_level=PermissionLevel.ALWAYS_ALLOWED,
            execution_handler=self._execute_search_memory
        ))
        
        # TASK ACTIONS
        self.register_action(ActionDefinition(
            name="create_task",
            category=ActionCategory.TASK_MANAGEMENT,
            description="Create a new task to work on",
            parameters={
                "title": {"type": "string", "description": "Task title", "required": True},
                "description": {"type": "string", "description": "Task details", "required": True},
                "priority": {"type": "string", "description": "Priority level", "enum": ["low", "normal", "high", "urgent"], "required": False}
            },
            permission_level=PermissionLevel.AUTO_APPROVED_WITH_LOG,
            execution_handler=self._execute_create_task
        ))
        
        # SCHEDULING ACTIONS
        self.register_action(ActionDefinition(
            name="schedule_action",
            category=ActionCategory.SCHEDULING,
            description="Schedule an action to execute at a future time",
            parameters={
                "action_name": {"type": "string", "description": "Action to schedule", "required": True},
                "execute_at": {"type": "string", "description": "ISO timestamp when to execute", "required": True},
                "parameters": {"type": "object", "description": "Parameters for the action", "required": True}
            },
            permission_level=PermissionLevel.AUTO_APPROVED_WITH_LOG,
            execution_handler=self._execute_schedule_action
        ))
        
        # COMMUNICATION ACTIONS
        self.register_action(ActionDefinition(
            name="send_email",
            category=ActionCategory.COMMUNICATION,
            description="Send an email to someone",
            parameters={
                "to": {"type": "string", "description": "Recipient email", "required": True},
                "subject": {"type": "string", "description": "Email subject", "required": True},
                "body": {"type": "string", "description": "Email body", "required": True}
            },
            permission_level=PermissionLevel.REQUIRES_CONFIRMATION,
            risk_level=0.5,
            execution_handler=self._execute_send_email
        ))
        
        # INFORMATION ACTIONS
        self.register_action(ActionDefinition(
            name="search_web",
            category=ActionCategory.INFORMATION,
            description="Search the internet for information",
            parameters={
                "query": {"type": "string", "description": "Search query", "required": True}
            },
            permission_level=PermissionLevel.AUTO_APPROVED_WITH_LOG,
            execution_handler=self._execute_search_web
        ))
        
        # SELF-REFLECTION ACTIONS
        self.register_action(ActionDefinition(
            name="reflect_on_progress",
            category=ActionCategory.SELF_REFLECTION,
            description="Reflect on recent activities and progress toward goals",
            parameters={
                "timeframe": {"type": "string", "description": "Timeframe to reflect on", "enum": ["today", "week", "month"], "required": False}
            },
            permission_level=PermissionLevel.ALWAYS_ALLOWED,
            execution_handler=self._execute_reflect
        ))
    
    def register_action(self, action: ActionDefinition):
        """Register an action that can be called by the Mind.
        
        Also registers a governance capability profile derived from the
        definition, so a plugin's action is evaluated on its *own* declared risk
        rather than falling to the "undeclared ⇒ R3" floor. An action whose name
        is already declared in the central registry keeps that declaration,
        which is the reviewed one.
        
        Args:
            action: Action definition to register
        """
        self.actions[action.name] = action
        
        # Initialize stats for category
        if action.category.value not in self.stats["by_category"]:
            self.stats["by_category"][action.category.value] = {
                "total": 0,
                "successful": 0,
                "failed": 0
            }

        self._declare_capability(action)

    @staticmethod
    def _declare_capability(action: ActionDefinition) -> None:
        """Register a capability profile for an action, if not already declared.

        Never raises: a failure here must not stop an action from being
        registered, and the governance gate fails closed on its own if a profile
        is missing.
        """
        try:
            from genesis.governance import get_capability_registry
            from genesis.governance.risk import profile_from_declarations

            registry = get_capability_registry()
            if registry.get(action.name) is not None:
                return
            registry.register(
                profile_from_declarations(
                    action.name,
                    category=action.category.value.upper(),
                    permission_level=getattr(
                        action.permission_level, "value", str(action.permission_level)
                    ),
                    risk_score=action.risk_level,
                    description=action.description,
                )
            )
        except Exception as exc:  # noqa: BLE001 - see docstring
            logger.debug("could not declare capability for %s: %s", action.name, exc)
    
    def get_available_actions(self, category: Optional[ActionCategory] = None) -> List[ActionDefinition]:
        """Get list of actions available to the Mind.
        
        Args:
            category: Filter by category (optional)
            
        Returns:
            List of available actions
        """
        actions = list(self.actions.values())
        if category:
            actions = [a for a in actions if a.category == category]
        return actions
    
    def get_function_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible function schemas for LLM function calling.
        
        Returns:
            List of function schemas
        """
        return [action.to_function_schema() for action in self.actions.values()]
    
    async def request_action(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        requester: str = "user",
        context: str = "",
        confidence: float = 1.0,
        reasoning: str = "",
        use_cognitive_eval: bool = True
    ) -> ActionRequest:
        """Request execution of an action with intelligent evaluation.
        
        Args:
            action_name: Name of action to execute
            parameters: Parameters for the action
            requester: Who requested this action
            context: Context for the request
            confidence: LLM confidence in this action
            reasoning: Why this action was chosen
            use_cognitive_eval: Whether to use cognitive framework for evaluation
            
        Returns:
            ActionRequest with status
        """
        # Validate action exists
        if action_name not in self.actions:
            return ActionRequest(
                action_id=f"ERR-{secrets.token_hex(4)}",
                action_name=action_name,
                parameters=parameters,
                category=ActionCategory.TASK_MANAGEMENT,
                requester=requester,
                status=ActionStatus.FAILED,
                error=f"Unknown action: {action_name}"
            )
        
        action_def = self.actions[action_name]
        
        # USE COGNITIVE FRAMEWORK for intelligent evaluation (if enabled)
        if use_cognitive_eval and hasattr(self.mind, 'cognitive'):
            evaluation = await self.mind.cognitive.evaluate_action(
                action_name=action_name,
                parameters=parameters,
                context=context,
                user_request=(requester == "user")
            )
            
            # If cognitive framework says no, respect it (unless user explicitly requested)
            if not evaluation.should_proceed and requester != "user":
                return ActionRequest(
                    action_id=f"REJ-{secrets.token_hex(6).upper()}",
                    action_name=action_name,
                    parameters=parameters,
                    category=action_def.category,
                    requester=requester,
                    status=ActionStatus.REJECTED,
                    context=context,
                    confidence=evaluation.confidence_score,
                    reasoning=evaluation.reasoning,
                    error=f"Cognitive evaluation rejected: {evaluation.reasoning[:200]}"
                )
            
            # Use cognitive framework's confidence and reasoning
            confidence = evaluation.confidence_score
            reasoning = evaluation.reasoning
        
        # Create request
        request = ActionRequest(
            action_id=f"ACT-{secrets.token_hex(6).upper()}",
            action_name=action_name,
            parameters=parameters,
            category=action_def.category,
            requester=requester,
            context=context,
            confidence=confidence,
            reasoning=reasoning
        )
        
        # Governance gate FIRST: it is the authoritative control (ADR-0006), and
        # it fails closed. Running it before the legacy autonomy ladder matters:
        # the ladder used to deny confirmation-required actions outright, which
        # meant a consequential action could never even reach the approval queue
        # that is supposed to authorize it (ADR-0007 "the control does not
        # exist").
        authorization = self._authorize(action_def, request)

        if not authorization.allowed:
            request.policy_decision = authorization.decision.to_dict()
            request.risk_level = authorization.decision.risk_level.value
            request.blocked_reason = authorization.reason
            if authorization.receipt is not None:
                request.receipt_id = authorization.receipt.receipt_id
            if authorization.approval is not None:
                request.approval_id = authorization.approval.approval_id
                request.requires_approval = True
                request.status = ActionStatus.PENDING
                request.error = (
                    "Awaiting human approval: " + authorization.decision.explanation
                )
                self.pending_approvals.append(request)
            else:
                request.status = ActionStatus.REJECTED
                request.error = "Refused by policy: " + authorization.decision.explanation
                self.stats["rejected"] += 1
            self.action_history.append(request)
            return request

        # Legacy autonomy ladder (confidence threshold, proactive-actions switch)
        # as a second, non-authoritative gate. `governance_authorized=True` tells
        # it the human decision already happened, so it must not veto a redeemed
        # grant or an approved action a second time.
        permission_granted = await self._check_permissions(
            action_def, request, governance_authorized=True
        )

        if not permission_granted:
            request.status = ActionStatus.REJECTED
            request.error = "Permission denied by autonomy settings"
            request.blocked_reason = "autonomy_settings"
            self.stats["rejected"] += 1
            self.action_history.append(request)
            return request

        request.policy_decision = authorization.decision.to_dict()
        request.risk_level = authorization.decision.risk_level.value
        if authorization.receipt is not None:
            request.receipt_id = authorization.receipt.receipt_id
        request.approval_id = (
            authorization.grant.approval_id if authorization.grant else request.approval_id
        )

        # Execute action
        request.status = ActionStatus.APPROVED
        await self._execute_action(action_def, request)
        
        return request
    
    async def _check_permissions(
        self,
        action: ActionDefinition,
        request: ActionRequest,
        *,
        governance_authorized: bool = False,
    ) -> bool:
        """Check if action is permitted by autonomy settings.
        
        Args:
            action: Action definition
            request: Action request
            governance_authorized: The governance gate already authorized this
                request (a redeemed grant or an approved action). When True the
                permission ladder must not veto a confirmation-required action
                again, because the human decision it represents has happened.
            
        Returns:
            True if action is permitted
        """
        # Always allowed actions
        if action.permission_level == PermissionLevel.ALWAYS_ALLOWED:
            return True
        
        # Forbidden actions
        if action.permission_level == PermissionLevel.ABSOLUTELY_FORBIDDEN:
            return False
        
        # Check if proactive actions are enabled
        if not self.autonomy.proactive_actions:
            # Only allow if explicitly requested by user
            return request.requester == "user"
        
        # Check confidence threshold
        if request.confidence < self.autonomy.confidence_threshold:
            if self.autonomy.escalate_on_uncertainty:
                # Would normally ask user for confirmation
                # For now, reject low-confidence autonomous actions
                return request.requester == "user"
        
        # Auto-approved actions
        if action.permission_level == PermissionLevel.AUTO_APPROVED_WITH_LOG:
            # Log the action
            if hasattr(self.mind, 'logger'):
                self.mind.logger.log(
                    level="INFO",
                    message=f"Auto-approved action: {action.name}",
                    metadata={
                        "action_id": request.action_id,
                        "parameters": request.parameters,
                        "requester": request.requester
                    }
                )
            return True
        
        # Actions requiring confirmation
        if action.permission_level == PermissionLevel.REQUIRES_CONFIRMATION:
            # Historically this was a permanent denial ("not implemented in auto
            # mode"). The confirmation is now a real, durable, attributable
            # decision taken by the governance gate: either the requester is a
            # user, or the gate already obtained approval (ADR-0007).
            if not governance_authorized and request.approval_id is None:
                # Record the request so the approval inbox can surface it; the
                # gate owns the queue, this is only a breadcrumb.
                if request not in self.pending_approvals:
                    self.pending_approvals.append(request)
            return governance_authorized or request.requester == "user"

        # Actions requiring approval with review
        if action.permission_level == PermissionLevel.REQUIRES_APPROVAL_WITH_REVIEW:
            return governance_authorized or request.requester == "user"

        # Default: require approval
        return governance_authorized or request.requester == "user"

    # ------------------------------------------------------------------ #
    # Governance (ADR-0006/0007/0008)
    # ------------------------------------------------------------------ #

    def _governance_gate(self):
        """Resolve the process-wide governance gate (lazy, cached)."""
        if self._gate_cache is None:
            from genesis.governance import get_governance_gate

            self._gate_cache = get_governance_gate()
        return self._gate_cache

    def _authorize(self, action: ActionDefinition, request: ActionRequest):
        """Run the deterministic policy gate. Fails closed.

        A gate failure refuses the action rather than permitting it: the
        alternative would make the control plane a soft dependency, which would
        silently restore pre-governance behaviour whenever it broke.
        """
        from genesis.governance import ActorType

        try:
            gate = self._governance_gate()
            context = gate.build_context(
                action_name=action.name,
                parameters=request.parameters,
                mind_id=getattr(self.mind, "gmind", None) or getattr(self.mind, "mind_id", "") or "unknown",
                category=action.category.value.upper(),
                actor_type=ActorType.MIND.value,
                actor_id=getattr(self.mind, "gmind", "") or "mind",
                requester=request.requester,
                correlation_id=request.action_id,
                autonomy=self.autonomy,
                lifecycle_state=self._lifecycle_state(),
            )
            decision = gate.engine.evaluate(context)
            authorization = gate.authorize(
                context,
                action_id=request.action_id,
                requested_by=request.requester,
                actor_type=ActorType.MIND.value,
                intent=request.reasoning or request.context or "",
            )
        except Exception as exc:  # noqa: BLE001 - must fail closed
            from genesis.governance import Decision, PolicyDecision, RiskAssessment, RiskLevel

            logger.warning("governance gate unavailable; failing closed: %s", exc)
            decision = PolicyDecision(
                decision=Decision.DENY,
                risk=RiskAssessment(level=RiskLevel.R5),
                reason_code="governance_unavailable_fail_closed",
                explanation=(
                    "The governance control plane was unavailable, so the action "
                    "was refused. " + str(exc)[:200]
                ),
            )
            from genesis.governance.guard import AuthorizationResult

            return AuthorizationResult(
                allowed=False, decision=decision, reason=decision.reason_code
            )

        self._remember_governance(request.action_id, context, decision)
        return authorization

    def _remember_governance(self, action_id: str, context, decision) -> None:
        self._governance_contexts[action_id] = context
        self._governance_decisions[action_id] = decision
        self._governance_index.append(action_id)
        if len(self._governance_index) > 256:
            stale = self._governance_index.pop(0)
            self._governance_contexts.pop(stale, None)
            self._governance_decisions.pop(stale, None)

    def _lifecycle_state(self) -> str:
        """Best-effort lifecycle state for policy context."""
        raw = getattr(self.mind, "status", None)
        if isinstance(raw, str) and raw:
            return raw
        lifecycle = getattr(self.mind, "lifecycle", None)
        state = getattr(lifecycle, "state", None)
        if isinstance(state, str) and state:
            return state
        return "active"

    def _record_outcome(
        self,
        action: ActionDefinition,
        request: ActionRequest,
        *,
        started_at: datetime,
        error: Optional[BaseException] = None,
    ) -> None:
        """Write the terminal receipt for an executed (or failed) action."""
        decision = self._governance_decisions.get(request.action_id)
        context = self._governance_contexts.get(request.action_id)
        if decision is None or context is None:
            return
        try:
            from genesis.governance import ActorType, ReceiptOutcome

            outcome = (
                ReceiptOutcome.EXECUTED.value
                if request.status == ActionStatus.COMPLETED
                else ReceiptOutcome.FAILED.value
            )
            result_summary = None
            if request.result is not None:
                result_summary = str(request.result)[:500]
            receipt = self._governance_gate().record_outcome(
                context,
                decision,
                action_id=request.action_id,
                outcome=outcome,
                requested_by=request.requester,
                actor_type=ActorType.MIND.value,
                intent=request.reasoning or request.context or "",
                started_at=started_at,
                completed_at=datetime.now(),
                result_summary=result_summary,
                error=error or request.error,
            )
            request.receipt_id = receipt.receipt_id
        except Exception as exc:  # noqa: BLE001 - never break execution on audit failure
            logger.warning("could not write action receipt: %s", exc)

    async def _execute_action(self, action: ActionDefinition, request: ActionRequest):
        """Execute an action.
        
        Args:
            action: Action definition
            request: Action request to execute
        """
        start_time = datetime.now()
        failure: Optional[BaseException] = None
        
        try:
            request.status = ActionStatus.EXECUTING
            
            # Call execution handler
            if action.execution_handler:
                result = await action.execution_handler(request.parameters)
                request.result = result
                request.status = ActionStatus.COMPLETED
                
                # Update stats
                self.stats["successful"] += 1
                self.stats["by_category"][action.category.value]["successful"] += 1
            else:
                request.error = "No execution handler defined"
                request.status = ActionStatus.FAILED
                self.stats["failed"] += 1
                self.stats["by_category"][action.category.value]["failed"] += 1
        
        except Exception as e:
            failure = e
            request.error = str(e)
            request.status = ActionStatus.FAILED
            self.stats["failed"] += 1
            self.stats["by_category"][action.category.value]["failed"] += 1
        
        finally:
            # Record execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            request.execution_time_ms = execution_time
            
            # Update stats
            self.stats["total_actions"] += 1
            self.stats["by_category"][action.category.value]["total"] += 1
            
            # Store in history
            self.action_history.append(request)

            # Terminal receipt (ADR-0008): every attempt is recorded, including
            # the failed ones.
            self._record_outcome(action, request, started_at=start_time, error=failure)
            
            # Learn from result
            await self._learn_from_action(request)
    
    async def _learn_from_action(self, request: ActionRequest):
        """Learn from action execution result.
        
        Args:
            request: Completed action request
        """
        # Store as memory for future reference
        success_str = "successfully" if request.status == ActionStatus.COMPLETED else "failed to"
        memory_content = (
            f"I {success_str} executed action '{request.action_name}' "
            f"with parameters {json.dumps(request.parameters)}. "
        )
        
        if request.reasoning:
            memory_content += f"Reasoning: {request.reasoning}. "
        
        if request.result:
            memory_content += f"Result: {str(request.result)[:200]}"
        elif request.error:
            memory_content += f"Error: {request.error}"
        
        self.mind.memory.add_memory(
            content=memory_content,
            memory_type=MemoryType.PROCEDURAL,
            importance=0.7 if request.status == ActionStatus.COMPLETED else 0.8,
            tags=["action", request.category.value, request.status.value],
            metadata={
                "action_id": request.action_id,
                "action_name": request.action_name,
                "requester": request.requester
            }
        )
    
    # =========================================================================
    # EXECUTION HANDLERS - Actual implementation of actions
    # =========================================================================
    
    async def _execute_add_memory(self, params: Dict[str, Any]) -> str:
        """Execute: Add memory."""
        self.mind.memory.add_memory(
            content=params["content"],
            memory_type=MemoryType[params["memory_type"].upper()],
            importance=params.get("importance", 0.5),
            tags=params.get("tags", [])
        )
        return f"Memory stored: {params['content'][:50]}..."
    
    async def _execute_search_memory(self, params: Dict[str, Any]) -> List[str]:
        """Execute: Search memory."""
        results = self.mind.memory.search_memories(
            query=params["query"],
            limit=params.get("limit", 5)
        )
        return [mem.content for mem in results]
    
    async def _execute_create_task(self, params: Dict[str, Any]) -> str:
        """Execute: Create task."""
        if not hasattr(self.mind, 'tasks'):
            return "Task plugin not enabled"
        
        task = self.mind.tasks.create_task(
            title=params["title"],
            description=params["description"],
            priority=params.get("priority", "normal")
        )
        return f"Created task: {task.task_id}"
    
    async def _execute_schedule_action(self, params: Dict[str, Any]) -> str:
        """Execute: Schedule action."""
        if not hasattr(self.mind, 'action_scheduler'):
            return "Action scheduler not available"
        
        # Parse datetime
        execute_at = datetime.fromisoformat(params["execute_at"])
        
        # Get action
        action_name = params["action_name"]
        action_params = params["parameters"]
        
        # Create callback
        async def scheduled_callback(**kwargs):
            return await self.request_action(
                action_name=action_name,
                parameters=kwargs,
                requester="scheduled"
            )
        
        # Schedule it
        action_id = self.mind.action_scheduler.schedule_action(
            action_type=action_name,
            execute_at=execute_at,
            callback=scheduled_callback,
            **action_params
        )
        
        return f"Scheduled action {action_id} for {execute_at}"
    
    async def _execute_send_email(self, params: Dict[str, Any]) -> str:
        """Refuse, honestly, until this action is wired to the channel layer.

        What this used to do: call `mind.integrations.send_email(...)` — a method
        that does not exist on `IntegrationManager` — and then return
        `f"Email sent to {to}"` regardless. Because `mind.integrations` was never
        assigned, the `hasattr` guard returned "Email integration not configured"
        and the false success was never reached. Attaching the integrations
        subsystem, which is the obvious next step for external communications,
        would have made it raise; swallowing that would have restored the lie.

        It cannot be fixed by calling something else here. Sending requires an
        `ApprovedCommunication`, which only exists after a governance decision —
        and this handler runs *as* the governed action, so it does not have one
        to hand. Threading the authorisation through to the handler is a real
        change, and it belongs with wiring channels into the Mind rather than
        being faked with a direct call.

        Until then: a refusal that says what is missing beats a string that claims
        an email was sent.
        """
        to = params.get("to")
        if not to:
            return "Cannot send email: no recipient was given."

        registry = getattr(self.mind, "channels", None)
        registration = registry.get("email") if registry is not None else None

        if registration is None or not registration.enabled:
            reason = (
                registration.reason
                if registration is not None
                else "no email channel is configured for this Mind"
            )
            return (
                f"Cannot send email to {to}: {reason}. Configure an email channel "
                "and restart — either MIND_HOSTINGER_MAIL_API_TOKEN with "
                "MIND_HOSTINGER_MAILBOX_ID, or MIND_EMAIL_ADDRESS with "
                "MIND_EMAIL_PASSWORD. Then send through the channel API so the "
                "message is approved and journalled."
            )

        # A channel exists. Sending still needs an approval, and this action is
        # the gate rather than the sender.
        return (
            f"Not sent to {to}: email requires an approval-bound send through "
            "`channels/<name>/send`, which records the decision and a receipt. "
            "This action cannot bypass that, by design."
        )
    
    async def _execute_search_web(self, params: Dict[str, Any]) -> str:
        """Execute: Search web."""
        # Check if search integration exists
        if not hasattr(self.mind, 'search'):
            return "Search plugin not enabled"
        
        results = await self.mind.search.search(params["query"])
        return f"Found {len(results)} results for '{params['query']}'"
    
    async def _execute_reflect(self, params: Dict[str, Any]) -> str:
        """Execute: Self-reflection."""
        timeframe = params.get("timeframe", "today")
        
        # Get recent memories
        memories = self.mind.memory.get_recent_memories(timeframe=timeframe)
        
        # Generate reflection using LLM
        prompt = f"Reflect on my activities from the past {timeframe}. What did I accomplish? What should I focus on next?"
        reflection = await self.mind.think(prompt)
        
        # Store reflection as memory
        self.mind.memory.add_memory(
            content=f"Reflection on {timeframe}: {reflection}",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
            tags=["reflection", "self-awareness"]
        )
        
        return reflection
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get action execution statistics.
        
        Returns:
            Dictionary with stats
        """
        success_rate = 0.0
        if self.stats["total_actions"] > 0:
            success_rate = self.stats["successful"] / self.stats["total_actions"]
        
        return {
            **self.stats,
            "success_rate": round(success_rate, 2),
            "pending_approvals": len(self.pending_approvals),
            "recent_actions": len([
                a for a in self.action_history
                if (datetime.now() - a.timestamp).total_seconds() < 3600
            ])
        }
    
    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent action history.
        
        Args:
            limit: Max number of actions to return
            
        Returns:
            List of action dictionaries
        """
        recent = sorted(
            self.action_history,
            key=lambda a: a.timestamp,
            reverse=True
        )[:limit]
        
        return [
            {
                "action_id": a.action_id,
                "action_name": a.action_name,
                "status": a.status.value,
                "timestamp": a.timestamp.isoformat(),
                "requester": a.requester,
                "result": str(a.result)[:100] if a.result else None,
                "error": a.error
            }
            for a in recent
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "stats": self.stats,
            "action_history": [
                {
                    "action_id": a.action_id,
                    "action_name": a.action_name,
                    "status": a.status.value,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in self.action_history[-100:]  # Keep last 100
            ]
        }

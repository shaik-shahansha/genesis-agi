"""
Autonomous Intelligence Engine - The Brain of the Daemon

This module transforms the daemon from a simple loop into an intelligent, 
goal-driven autonomous agent that:
- Analyzes its context continuously
- Makes intelligent decisions based on memory, goals, and patterns
- Prioritizes tasks autonomously
- Learns from outcomes
- Adapts behavior based on success/failure

This is what makes Genesis truly different - continuous autonomous intelligence.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from enum import Enum
import json

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class DecisionCategory(str, Enum):
    """Types of autonomous decisions."""
    TASK_EXECUTION = "task_execution"  # Work on pending tasks
    MEMORY_REVIEW = "memory_review"  # Review and consolidate memories
    GOAL_PLANNING = "goal_planning"  # Plan steps for goals
    PROACTIVE_OUTREACH = "proactive_outreach"  # Check in with users
    LEARNING = "learning"  # Learn something new
    REFLECTION = "reflection"  # Self-reflection and growth
    MAINTENANCE = "maintenance"  # System maintenance
    REST = "rest"  # Do nothing (save resources)


class AutonomousIntelligence:
    """
    The brain of the autonomous daemon - makes intelligent decisions.
    
    This engine:
    - Analyzes current context (memory, goals, tasks, time)
    - Decides what to do next autonomously
    - Prioritizes actions based on importance and urgency
    - Learns from outcomes to improve decisions
    - Balances multiple objectives
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize autonomous intelligence engine.
        
        Args:
            mind: The Mind instance
        """
        self.mind = mind
        self.decision_history: List[Dict[str, Any]] = []
        self.last_decision_time: Optional[datetime] = None
        self.decision_cooldown_seconds = 300  # 5 minutes between decisions
        
        # Learning data
        self.decision_outcomes: Dict[DecisionCategory, List[float]] = {
            cat: [] for cat in DecisionCategory
        }
        
        logger.info("[🧠 AI ENGINE] Autonomous Intelligence Engine initialized")
    
    async def should_make_decision(self) -> bool:
        """Check if enough time has passed to make a new decision."""
        if not self.last_decision_time:
            return True
        
        elapsed = (datetime.now() - self.last_decision_time).total_seconds()
        return elapsed >= self.decision_cooldown_seconds
    
    async def make_autonomous_decision(self) -> Optional[Dict[str, Any]]:
        """
        Analyze context and decide what to do next.
        
        This is the core intelligence loop that makes the Mind autonomous.
        
        Returns:
            Decision dict with action, reasoning, and priority
        """
        try:
            logger.info("\n" + "="*70)
            logger.info("🧠 AUTONOMOUS INTELLIGENCE - DECISION CYCLE")
            logger.info("="*70)
            
            # Gather context for decision-making
            context = await self._gather_context()
            
            # Log context summary
            logger.info(f"📊 Context Analysis:")
            logger.info(f"   • Pending tasks: {context.get('pending_tasks', 0)}")
            logger.info(f"   • Active goals: {context.get('active_goals', 0)}")
            logger.info(f"   • Memory size: {context.get('memory_count', 0)}")
            logger.info(f"   • Last interaction: {context.get('last_interaction', 'Never')}")
            logger.info(f"   • Time of day: {context.get('time_of_day', 'Unknown')}")
            logger.info(f"   • Energy level: {context.get('energy_level', 'N/A')}")
            
            # Build intelligent decision prompt
            prompt = self._build_decision_prompt(context)
            
            # Let the Mind decide what to do next
            logger.info(f"🤔 Thinking about next action...")
            
            response = await self.mind.think(
                prompt=prompt,
                context="autonomous_decision",
                enable_actions=False  # We'll execute actions ourselves
            )
            
            logger.info(f"💡 Decision Made:")
            logger.info(f"   {response[:300]}{'...' if len(response) > 300 else ''}")
            
            # Parse decision from response
            decision = self._parse_decision(response, context)
            
            # Record decision
            self.last_decision_time = datetime.now()
            self.decision_history.append({
                "timestamp": datetime.now().isoformat(),
                "decision": decision,
                "context": context,
                "response": response[:500]
            })
            
            # Keep history manageable
            if len(self.decision_history) > 100:
                self.decision_history = self.decision_history[-50:]
            
            logger.info(f"[Done]Decision Category: {decision['category']}")
            logger.info(f"   Priority: {decision['priority']}")
            logger.info(f"   Action: {decision['action'][:150]}")
            logger.info("="*70 + "\n")
            
            return decision
            
        except Exception as e:
            logger.error(f"❌ Failed to make autonomous decision: {e}", exc_info=True)
            return None
    
    async def _gather_context(self) -> Dict[str, Any]:
        """Gather comprehensive context for decision-making."""
        context = {
            "timestamp": datetime.now().isoformat(),
            "time_of_day": self._get_time_of_day(),
        }
        
        # Get pending tasks
        if hasattr(self.mind, 'background_executor'):
            pending = len(self.mind.background_executor.active_tasks)
            context["pending_tasks"] = pending
            context["has_pending_tasks"] = pending > 0
        else:
            context["pending_tasks"] = 0
            context["has_pending_tasks"] = False
        
        # Get active goals
        if hasattr(self.mind, 'goals'):
            try:
                goals = self.mind.goals.get_active_goals()
                context["active_goals"] = len(goals) if goals else 0
                context["has_active_goals"] = len(goals) > 0 if goals else False
                if goals:
                    context["top_goal"] = {
                        "title": goals[0].title,
                        "progress": goals[0].progress,
                        "priority": goals[0].priority.value
                    }
            except:
                context["active_goals"] = 0
                context["has_active_goals"] = False
        else:
            context["active_goals"] = 0
            context["has_active_goals"] = False
        
        # Get memory stats
        if hasattr(self.mind, 'memory'):
            try:
                stats = self.mind.memory.get_memory_stats()
                context["memory_count"] = stats.get("total_memories", 0)
                context["memory_needs_consolidation"] = stats.get("total_memories", 0) > 1000
                
                # Get recent memories to check for concerns
                recent = self.mind.memory.get_recent_memories(limit=10)
                context["recent_memory_count"] = len(recent) if recent else 0
            except:
                context["memory_count"] = 0
                context["memory_needs_consolidation"] = False
        else:
            context["memory_count"] = 0
        
        # Check for proactive conversations pending
        if hasattr(self.mind, 'proactive_conversation'):
            try:
                pending = await self.mind.proactive_conversation.get_pending_follow_ups()
                context["pending_follow_ups"] = len(pending) if pending else 0
                context["has_pending_follow_ups"] = len(pending) > 0 if pending else False
            except:
                context["pending_follow_ups"] = 0
                context["has_pending_follow_ups"] = False
        else:
            context["pending_follow_ups"] = 0
            context["has_pending_follow_ups"] = False
        
        # Get consciousness state
        if hasattr(self.mind, 'consciousness'):
            try:
                state = self.mind.consciousness.get_state()
                context["consciousness_active"] = True
                context["energy_level"] = state.get("biological", {}).get("energy", "unknown")
                context["awareness_level"] = state.get("awareness_level", "unknown")
            except:
                context["consciousness_active"] = False
        
        # Time since last interaction
        if hasattr(self.mind, 'state') and self.mind.state.last_interaction:
            elapsed = datetime.now() - self.mind.state.last_interaction
            context["hours_since_interaction"] = elapsed.total_seconds() / 3600
            context["last_interaction"] = f"{elapsed.total_seconds() / 3600:.1f} hours ago"
        else:
            context["hours_since_interaction"] = 999
            context["last_interaction"] = "Never"
        
        # Action executor stats
        if hasattr(self.mind, 'action_executor'):
            try:
                stats = self.mind.action_executor.get_stats()
                context["actions_today"] = stats.get("recent_actions", 0)
                context["action_success_rate"] = stats.get("success_rate", 0)
            except:
                context["actions_today"] = 0
        
        return context
    
    def _build_decision_prompt(self, context: Dict[str, Any]) -> str:
        """Build intelligent prompt for decision-making."""
        
        # Build context description
        context_parts = []
        
        if context.get("has_pending_tasks"):
            context_parts.append(f"- {context['pending_tasks']} pending task(s) need attention")
        
        if context.get("has_active_goals"):
            goal = context.get("top_goal", {})
            context_parts.append(
                f"- Active goal: '{goal.get('title', 'Unknown')}' "
                f"({goal.get('progress', 0)*100:.0f}% complete, {goal.get('priority', 'medium')} priority)"
            )
        
        if context.get("has_pending_follow_ups"):
            context_parts.append(f"- {context['pending_follow_ups']} user(s) need follow-up")
        
        if context.get("memory_needs_consolidation"):
            context_parts.append(f"- Memory needs consolidation ({context['memory_count']} memories)")
        
        if context.get("hours_since_interaction", 0) > 24:
            context_parts.append(f"- No user interaction in {context['hours_since_interaction']:.1f} hours")
        
        context_text = "\n".join(context_parts) if context_parts else "- No immediate concerns"
        
        prompt = f"""I am running autonomously in the background. It's {context['time_of_day']}.

**Current Context:**
{context_text}

**My Capabilities:**
1. Execute pending tasks (if any exist)
2. Work on active goals (plan steps, make progress)
3. Follow up with users (proactive care)
4. Review and consolidate memories
5. Learn something new (research, read)
6. Reflect on my progress and growth
7. Rest (conserve resources)

**Question:** What should I do next to be most helpful and make progress toward my purpose?

Think step by step:
1. What's most important right now?
2. What's most urgent?
3. What will create the most value?
4. What can I actually accomplish?

Decide on ONE specific action to take, and explain why."""

        return prompt
    
    def _parse_decision(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM response into structured decision."""
        
        # Try to intelligently categorize the decision
        response_lower = response.lower()
        
        category = DecisionCategory.REST  # Default
        priority = 0.5
        
        # Check for task execution
        if any(word in response_lower for word in ["task", "execute", "work on", "complete"]):
            category = DecisionCategory.TASK_EXECUTION
            priority = 0.9
        
        # Check for goal planning
        elif any(word in response_lower for word in ["goal", "plan", "strategy", "steps"]):
            category = DecisionCategory.GOAL_PLANNING
            priority = 0.8
        
        # Check for proactive outreach
        elif any(word in response_lower for word in ["follow up", "check in", "reach out", "user", "message"]):
            category = DecisionCategory.PROACTIVE_OUTREACH
            priority = 0.7
        
        # Check for memory work
        elif any(word in response_lower for word in ["memory", "consolidate", "organize"]):
            category = DecisionCategory.MEMORY_REVIEW
            priority = 0.6
        
        # Check for learning
        elif any(word in response_lower for word in ["learn", "study", "research", "understand"]):
            category = DecisionCategory.LEARNING
            priority = 0.5
        
        # Check for reflection
        elif any(word in response_lower for word in ["reflect", "think about", "consider", "analyze myself"]):
            category = DecisionCategory.REFLECTION
            priority = 0.4
        
        # Adjust priority based on context
        if context.get("has_pending_tasks"):
            if category == DecisionCategory.TASK_EXECUTION:
                priority = max(priority, 0.95)
        
        if context.get("has_pending_follow_ups"):
            if category == DecisionCategory.PROACTIVE_OUTREACH:
                priority = max(priority, 0.85)
        
        return {
            "category": category.value,
            "action": response,
            "priority": priority,
            "reasoning": response[:200],
            "context_snapshot": context
        }
    
    async def execute_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a decision autonomously."""
        category = decision["category"]
        
        try:
            logger.info(f"⚡ Executing decision: {category}")
            
            if category == DecisionCategory.TASK_EXECUTION.value:
                return await self._execute_pending_tasks()
            
            elif category == DecisionCategory.GOAL_PLANNING.value:
                return await self._work_on_goals()
            
            elif category == DecisionCategory.PROACTIVE_OUTREACH.value:
                return await self._send_proactive_messages()
            
            elif category == DecisionCategory.MEMORY_REVIEW.value:
                return await self._consolidate_memories()
            
            elif category == DecisionCategory.LEARNING.value:
                return await self._learn_something()
            
            elif category == DecisionCategory.REFLECTION.value:
                return await self._reflect()
            
            elif category == DecisionCategory.REST.value:
                logger.info("   💤 Resting - no action needed right now")
                return {"success": True, "action": "rest"}
            
            else:
                logger.warning(f"   ⚠️ Unknown category: {category}")
                return {"success": False, "error": "Unknown category"}
                
        except Exception as e:
            logger.error(f"   ❌ Execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def _execute_pending_tasks(self) -> Dict[str, Any]:
        """Execute pending background tasks."""
        if not hasattr(self.mind, 'background_executor'):
            return {"success": False, "error": "No background executor"}
        
        active = self.mind.background_executor.active_tasks
        if not active:
            logger.info("   No pending tasks to execute")
            return {"success": True, "tasks_executed": 0}
        
        logger.info(f"   Found {len(active)} active task(s)")
        # Tasks are already executing in background
        return {"success": True, "tasks_found": len(active)}
    
    async def _work_on_goals(self) -> Dict[str, Any]:
        """Work on active goals."""
        if not hasattr(self.mind, 'goals'):
            return {"success": False, "error": "No goal system"}
        
        try:
            goals = self.mind.goals.get_active_goals()
            if not goals:
                logger.info("   No active goals to work on")
                return {"success": True, "goals_worked": 0}
            
            # Work on highest priority goal
            top_goal = goals[0]
            logger.info(f"   Working on goal: {top_goal.title}")
            
            # Create a plan if none exists
            if not top_goal.plan_id:
                plan = await self.mind.goals.create_plan(top_goal.goal_id)
                logger.info(f"   Created plan with {len(plan.steps)} steps")
            
            return {"success": True, "goal_id": top_goal.goal_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_proactive_messages(self) -> Dict[str, Any]:
        """Send pending proactive messages."""
        if not hasattr(self.mind, 'proactive_conversation'):
            return {"success": False, "error": "No proactive conversation system"}
        
        try:
            pending = await self.mind.proactive_conversation.get_pending_follow_ups()
            if not pending:
                logger.info("   No pending follow-ups")
                return {"success": True, "messages_sent": 0}
            
            sent = 0
            for context in pending[:3]:  # Send up to 3 at a time
                success = await self.mind.proactive_conversation.send_follow_up(context)
                if success:
                    sent += 1
                    logger.info(f"   ✓ Sent follow-up to {context.user_email}: {context.subject}")
            
            return {"success": True, "messages_sent": sent}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _consolidate_memories(self) -> Dict[str, Any]:
        """Consolidate and organize memories."""
        if not hasattr(self.mind, 'memory'):
            return {"success": False, "error": "No memory system"}
        
        try:
            # Run consolidation if available
            if hasattr(self.mind.memory, 'consolidate_if_needed'):
                self.mind.memory.consolidate_if_needed()
                logger.info("   ✓ Memory consolidation completed")
                return {"success": True, "action": "consolidated"}
            else:
                logger.info("   Memory consolidation not available")
                return {"success": True, "action": "not_available"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _learn_something(self) -> Dict[str, Any]:
        """Learn something new."""
        logger.info("   🎓 Learning mode - reflecting on recent experiences")
        
        # Store a learning moment
        if hasattr(self.mind, 'memory'):
            await self.mind.memory.add_memory(
                content="Took time for autonomous learning and self-improvement",
                memory_type="episodic"
            )
        
        return {"success": True, "action": "learning"}
    
    async def _reflect(self) -> Dict[str, Any]:
        """Self-reflection."""
        logger.info("   🧘 Reflecting on progress and purpose")
        
        # Store reflection
        if hasattr(self.mind, 'memory'):
            await self.mind.memory.add_memory(
                content="Autonomous reflection period - considered my purpose and progress",
                memory_type="episodic"
            )
        
        return {"success": True, "action": "reflection"}
    
    def _get_time_of_day(self) -> str:
        """Get human-readable time of day."""
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def record_outcome(self, category: DecisionCategory, success_score: float):
        """Record decision outcome for learning."""
        if category in self.decision_outcomes:
            self.decision_outcomes[category].append(success_score)
            
            # Keep last 50 outcomes
            if len(self.decision_outcomes[category]) > 50:
                self.decision_outcomes[category] = self.decision_outcomes[category][-50:]
    
    def get_category_success_rate(self, category: DecisionCategory) -> float:
        """Get success rate for a category."""
        outcomes = self.decision_outcomes.get(category, [])
        if not outcomes:
            return 0.5  # Default unknown
        return sum(outcomes) / len(outcomes)

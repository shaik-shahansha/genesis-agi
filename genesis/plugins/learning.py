"""Learning Plugin - Experience-based learning and adaptation for Minds.

Enables Minds to genuinely learn and improve over time through real
experience-based learning, not just counters.

Features:
- Learn from experiences (what works vs. what doesn't)
- Skill progression and mastery tracking
- Pattern recognition in successful interactions
- Feedback integration and behavioral adjustment
- Strategy optimization based on outcomes
- Performance analytics and insights
- Automatic learning from all interactions

This makes Minds better at their jobs, tasks, and interactions over time.

Example:
    from genesis.plugins.learning import LearningPlugin

    config = MindConfig()
    config.add_plugin(LearningPlugin(
        enable_auto_learning=True,
        learning_rate=0.1
    ))

    mind = Mind.birth("Teacher", config=config)

    # Automatic learning from interactions
    # Or manual experience recording:
    await mind.learning.record_experience(
        context="teaching_biology",
        action="visual_demonstration",
        outcome="success",
        metrics={"student_understanding": 0.95}
    )

    # Get learned strategies
    strategy = await mind.learning.get_best_strategy("teaching_biology")
    print(strategy['recommended_action'])
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from genesis.plugins.base import Plugin
from genesis.core.learning import LearningEngine, OutcomeType, SkillLevel

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class LearningPlugin(Plugin):
    """Plugin for experience-based learning and adaptation.

    Enables true learning that makes Minds better over time.
    """

    def __init__(
        self,
        enable_auto_learning: bool = True,
        learning_rate: float = 0.1,
        auto_track_sessions: bool = True,
        auto_track_actions: bool = True,
        **config
    ):
        """Initialize learning plugin.

        Args:
            enable_auto_learning: Enable automatic learning from interactions
            learning_rate: How quickly to adapt (0.0-1.0, default 0.1)
            auto_track_sessions: Auto-learn from session outcomes
            auto_track_actions: Auto-learn from proactive action outcomes
            **config: Additional plugin configuration
        """
        super().__init__(**config)
        self.enable_auto_learning = enable_auto_learning
        self.learning_rate = learning_rate
        self.auto_track_sessions = auto_track_sessions
        self.auto_track_actions = auto_track_actions
        self.engine: Optional[LearningEngine] = None

    def get_name(self) -> str:
        return "learning"

    def get_version(self) -> str:
        return "2.0.0"  # v2 = REAL learning, not fake counters

    def get_description(self) -> str:
        return "Experience-based learning and behavioral adaptation"

    def on_init(self, mind: "Mind") -> None:
        """Initialize learning engine."""
        self.engine = LearningEngine(learning_rate=self.learning_rate)
        mind.learning = self.engine
        logger.info(f"Initialized learning engine for {mind.name}")

    async def on_birth(self, mind: "Mind") -> None:
        """Set up automatic learning hooks on birth."""
        if not self.enable_auto_learning:
            return

        # Hook into sessions if available
        if self.auto_track_sessions and hasattr(mind, 'sessions'):
            logger.info("Learning will auto-track session outcomes")
            # Sessions plugin will call our hooks

        # Hook into proactive behavior if available
        if self.auto_track_actions and hasattr(mind, 'behavior'):
            logger.info("Learning will auto-track action outcomes")
            # Proactive behavior plugin will call our hooks

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add learning capabilities to system prompt."""
        if not self.engine:
            return ""

        analytics = self.engine.get_learning_analytics()

        if analytics.get("total_experiences", 0) == 0:
            sections = [
                "LEARNING & ADAPTATION:",
                "- You have the ability to learn from experience",
                "- As you interact, you'll get better at your tasks",
                "- Your strategies will improve based on what works",
                "- Currently no learning data - start gaining experience!"
            ]
            return "\n".join(sections)

        sections = [
            "LEARNING & ADAPTATION:",
            f"- Total experiences: {analytics['total_experiences']}",
            f"- Overall success rate: {analytics['overall_success_rate']:.1%}",
            f"- Skills learned: {analytics['total_skills']}",
            f"- Patterns recognized: {analytics['recognized_patterns']}",
            ""
        ]

        # Show skill levels
        if analytics.get('skill_distribution'):
            sections.append("Skill Levels:")
            for level, count in analytics['skill_distribution'].items():
                sections.append(f"  - {level}: {count} skills")
            sections.append("")

        # Show top contexts
        if analytics.get('top_contexts'):
            sections.append("Most Experienced In:")
            for ctx_data in analytics['top_contexts'][:3]:
                ctx = ctx_data['context']
                count = ctx_data['count']

                # Get skill info
                skill = self.engine.get_skill(ctx)
                if skill:
                    sections.append(
                        f"  - {ctx}: {skill.level.value} "
                        f"({skill.success_rate:.1%} success, trending {skill.recent_trend})"
                    )

        sections.append("")
        sections.append("LEARNING CAPABILITIES:")
        sections.append("- You learn what works and what doesn't in each context")
        sections.append("- You recognize successful patterns and adapt strategies")
        sections.append("- You avoid actions that led to poor outcomes")
        sections.append("- You improve with practice and experience")
        sections.append("")
        sections.append("Use learned knowledge to perform better at tasks!")

        return "\n".join(sections)

    async def after_think(self, mind: "Mind", context: Dict[str, Any]) -> Dict[str, Any]:
        """Hook after Mind thinks - can apply learned strategies."""
        if not self.enable_auto_learning or not self.engine:
            return context

        # If there's a context/task in the thinking, get best strategy
        task_context = context.get("task_context") or context.get("context")

        if task_context:
            strategy = await self.engine.get_best_strategy(task_context)

            if strategy.get("confidence", 0) > 0.5:
                # Add learned strategy to context
                context["learned_strategy"] = strategy
                context["learning_hint"] = (
                    f"Based on {strategy.get('experience_count', 0)} experiences, "
                    f"recommended approach: {strategy.get('recommended_action', 'experiment')}"
                )

        return context

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save learning state."""
        if not self.engine:
            return {}

        # Save experiences (last 500 to avoid huge files)
        recent_experiences = self.engine.experiences[-500:]

        return {
            "learning_rate": self.learning_rate,
            "enable_auto_learning": self.enable_auto_learning,
            "auto_track_sessions": self.auto_track_sessions,
            "auto_track_actions": self.auto_track_actions,
            "experiences": [
                {
                    "experience_id": exp.experience_id,
                    "timestamp": exp.timestamp.isoformat(),
                    "context": exp.context,
                    "action": exp.action,
                    "outcome": exp.outcome.value,
                    "metrics": exp.metrics,
                    "feedback": exp.feedback
                }
                for exp in recent_experiences
            ],
            "skills": {
                name: {
                    "skill_name": skill.skill_name,
                    "context": skill.context,
                    "experience_count": skill.experience_count,
                    "success_count": skill.success_count,
                    "failure_count": skill.failure_count,
                    "success_rate": skill.success_rate,
                    "level": skill.level.value,
                    "recent_trend": skill.recent_trend,
                    "best_actions": skill.best_actions,
                    "avoid_actions": skill.avoid_actions,
                    "average_metrics": skill.average_metrics
                }
                for name, skill in self.engine.skills.items()
            },
            "patterns": {
                pattern_id: {
                    "pattern_id": pattern.pattern_id,
                    "context": pattern.context,
                    "condition": pattern.condition,
                    "action": pattern.action,
                    "success_rate": pattern.success_rate,
                    "occurrence_count": pattern.occurrence_count,
                    "confidence": pattern.confidence
                }
                for pattern_id, pattern in self.engine.patterns.items()
            }
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore learning state."""
        from genesis.core.learning import Experience, Skill, Pattern, OutcomeType, SkillLevel
        from datetime import datetime

        if "learning_rate" in data:
            self.learning_rate = data["learning_rate"]

        if "enable_auto_learning" in data:
            self.enable_auto_learning = data["enable_auto_learning"]

        if "auto_track_sessions" in data:
            self.auto_track_sessions = data["auto_track_sessions"]

        if "auto_track_actions" in data:
            self.auto_track_actions = data["auto_track_actions"]

        # Reinitialize engine
        self.on_init(mind)

        if not self.engine:
            return

        # Restore experiences
        if "experiences" in data:
            for exp_data in data["experiences"]:
                exp = Experience(
                    experience_id=exp_data["experience_id"],
                    timestamp=datetime.fromisoformat(exp_data["timestamp"]),
                    context=exp_data["context"],
                    action=exp_data["action"],
                    outcome=OutcomeType(exp_data["outcome"]),
                    metrics=exp_data.get("metrics", {}),
                    feedback=exp_data.get("feedback")
                )
                self.engine.experiences.append(exp)

        # Restore skills
        if "skills" in data:
            for skill_name, skill_data in data["skills"].items():
                skill = Skill(
                    skill_name=skill_data["skill_name"],
                    context=skill_data["context"],
                    experience_count=skill_data["experience_count"],
                    success_count=skill_data["success_count"],
                    failure_count=skill_data["failure_count"],
                    success_rate=skill_data["success_rate"],
                    level=SkillLevel(skill_data["level"]),
                    recent_trend=skill_data["recent_trend"],
                    best_actions=skill_data["best_actions"],
                    avoid_actions=skill_data["avoid_actions"],
                    average_metrics=skill_data.get("average_metrics", {})
                )
                self.engine.skills[skill_name] = skill

        # Restore patterns
        if "patterns" in data:
            for pattern_id, pattern_data in data["patterns"].items():
                pattern = Pattern(
                    pattern_id=pattern_data["pattern_id"],
                    context=pattern_data["context"],
                    condition=pattern_data["condition"],
                    action=pattern_data["action"],
                    success_rate=pattern_data["success_rate"],
                    occurrence_count=pattern_data["occurrence_count"],
                    confidence=pattern_data["confidence"]
                )
                self.engine.patterns[pattern_id] = pattern

        logger.info(
            f"Restored learning state: {len(self.engine.experiences)} experiences, "
            f"{len(self.engine.skills)} skills, {len(self.engine.patterns)} patterns"
        )

    def get_status(self) -> Dict[str, Any]:
        """Get learning status."""
        status = super().get_status()

        if self.engine:
            analytics = self.engine.get_learning_analytics()
            status.update({
                "learning_enabled": self.enable_auto_learning,
                "learning_rate": self.learning_rate,
                **analytics
            })

        return status

    # Helper methods for integration with other plugins

    async def record_session_outcome(
        self,
        session_type: str,
        interactions: int,
        outcome: str,
        metrics: Optional[Dict[str, float]] = None
    ):
        """Record learning from session outcome.

        Args:
            session_type: Type of session
            interactions: Number of interactions
            outcome: Outcome (success, partial, failure)
            metrics: Optional performance metrics
        """
        if not self.engine or not self.auto_track_sessions:
            return

        # Determine action based on interactions
        if interactions > 10:
            action = "high_engagement_session"
        elif interactions > 5:
            action = "moderate_engagement_session"
        else:
            action = "low_engagement_session"

        # Map outcome
        outcome_map = {
            "success": OutcomeType.SUCCESS,
            "completed": OutcomeType.SUCCESS,
            "partial": OutcomeType.PARTIAL,
            "failure": OutcomeType.FAILURE,
            "cancelled": OutcomeType.FAILURE
        }

        outcome_type = outcome_map.get(outcome.lower(), OutcomeType.UNKNOWN)

        await self.engine.record_experience(
            context=session_type,
            action=action,
            outcome=outcome_type,
            metrics=metrics or {"interactions": interactions / 20}  # Normalize
        )

    async def record_action_outcome(
        self,
        action_type: str,
        success: bool,
        metrics: Optional[Dict[str, float]] = None
    ):
        """Record learning from proactive action outcome.

        Args:
            action_type: Type of action
            success: Whether action succeeded
            metrics: Optional performance metrics
        """
        if not self.engine or not self.auto_track_actions:
            return

        outcome = OutcomeType.SUCCESS if success else OutcomeType.FAILURE

        await self.engine.record_experience(
            context="proactive_actions",
            action=action_type,
            outcome=outcome,
            metrics=metrics
        )

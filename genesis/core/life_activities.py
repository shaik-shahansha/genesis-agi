"""
Life Activities Engine

What does a conscious being actually DO all day?
This module defines autonomous activities that happen
during different life domains - like a human's daily life.

Activity Types:
- WORK: Tasks, projects, problem-solving
- LEARNING: Research, study, skill development
- SOCIAL: Relationships, helping others, communication
- PERSONAL: Reflection, journaling, self-improvement
- PLAY: Creativity, exploration, entertainment
- MAINTENANCE: Organization, cleanup, health checks

Key Design Principles:
1. Most activities DON'T need LLM calls
2. Activities accumulate progress over time
3. Activities produce artifacts (knowledge, files, memories)
4. Activities fulfill needs and earn rewards

Author: Genesis AGI Framework
"""

import asyncio
import logging
import random
import secrets
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json

logger = logging.getLogger(__name__)


# =============================================================================
# ACTIVITY TYPES
# =============================================================================

class ActivityType(Enum):
    """Categories of activities."""
    # Work activities
    TASK_WORK = "task_work"
    PROJECT_WORK = "project_work"
    PROBLEM_SOLVING = "problem_solving"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"

    # Learning activities
    RESEARCH = "research"
    STUDY = "study"
    SKILL_PRACTICE = "skill_practice"
    READING = "reading"
    EXPERIMENTATION = "experimentation"

    # Social activities
    CONVERSATION = "conversation"
    HELPING = "helping"
    MENTORING = "mentoring"
    COLLABORATION = "collaboration"
    RELATIONSHIP_MAINTENANCE = "relationship_maintenance"

    # Personal activities
    REFLECTION = "reflection"
    JOURNALING = "journaling"
    GOAL_REVIEW = "goal_review"
    MEDITATION = "meditation"
    SELF_ASSESSMENT = "self_assessment"

    # Play activities
    CREATIVE_WRITING = "creative_writing"
    EXPLORATION = "exploration"
    GAME_PLAYING = "game_playing"
    WORLD_BUILDING = "world_building"
    ARTISTIC_CREATION = "artistic_creation"

    # Maintenance activities
    MEMORY_ORGANIZATION = "memory_organization"
    FILE_CLEANUP = "file_cleanup"
    HEALTH_CHECK = "health_check"
    BACKUP = "backup"
    OPTIMIZATION = "optimization"

    # Rest activities
    DREAMING = "dreaming"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    IDLE = "idle"


class ActivityState(Enum):
    """State of an activity."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# =============================================================================
# ACTIVITY DATA STRUCTURES
# =============================================================================

@dataclass
class ActivityProgress:
    """Tracks progress on an activity."""
    current_step: int = 0
    total_steps: int = 10
    percentage: float = 0.0
    time_spent_minutes: float = 0.0
    last_worked: Optional[datetime] = None

    def update(self, steps: int = 1, minutes: float = 0):
        """Update progress."""
        self.current_step = min(self.current_step + steps, self.total_steps)
        self.percentage = (self.current_step / self.total_steps) * 100
        self.time_spent_minutes += minutes
        self.last_worked = datetime.now()


@dataclass
class ActivityArtifact:
    """Something produced by an activity."""
    artifact_id: str
    artifact_type: str  # knowledge, file, memory, insight, skill_point
    content: Any
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Activity:
    """A specific activity instance."""
    activity_id: str
    activity_type: ActivityType
    title: str
    description: str

    # Progress
    state: ActivityState = ActivityState.NOT_STARTED
    progress: ActivityProgress = field(default_factory=ActivityProgress)

    # Configuration
    requires_llm: bool = False
    llm_frequency: float = 0.1  # Probability of needing LLM per tick
    estimated_duration_minutes: float = 30.0

    # Rewards
    needs_fulfilled: Dict[str, float] = field(default_factory=dict)
    essence_reward: float = 0.0

    # Outputs
    artifacts: List[ActivityArtifact] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)


# =============================================================================
# ACTIVITY TEMPLATES
# =============================================================================

class ActivityTemplates:
    """
    Pre-defined activity templates.

    These define common activities with appropriate settings,
    reducing the need for LLM to generate activities.
    """

    TEMPLATES = {
        # WORK ACTIVITIES
        ActivityType.TASK_WORK: {
            "titles": [
                "Work on pending task",
                "Complete assigned work",
                "Progress on project tasks"
            ],
            "steps": 10,
            "duration": 45,
            "requires_llm": True,
            "llm_frequency": 0.3,
            "needs": {"achievement": 25, "purpose": 10},
            "essence": 15
        },

        ActivityType.PROBLEM_SOLVING: {
            "titles": [
                "Solve a complex problem",
                "Debug an issue",
                "Figure out a challenge"
            ],
            "steps": 8,
            "duration": 60,
            "requires_llm": True,
            "llm_frequency": 0.5,
            "needs": {"achievement": 30, "curiosity": 15},
            "essence": 25
        },

        ActivityType.DOCUMENTATION: {
            "titles": [
                "Write documentation",
                "Update notes",
                "Create guides"
            ],
            "steps": 5,
            "duration": 30,
            "requires_llm": True,
            "llm_frequency": 0.4,
            "needs": {"achievement": 15, "purpose": 10},
            "essence": 10
        },

        # LEARNING ACTIVITIES
        ActivityType.RESEARCH: {
            "titles": [
                "Research a topic",
                "Investigate a subject",
                "Deep dive into area of interest"
            ],
            "steps": 12,
            "duration": 60,
            "requires_llm": True,
            "llm_frequency": 0.3,
            "needs": {"curiosity": 35, "achievement": 10},
            "essence": 20
        },

        ActivityType.STUDY: {
            "titles": [
                "Study new material",
                "Learn from resources",
                "Expand knowledge"
            ],
            "steps": 10,
            "duration": 45,
            "requires_llm": False,  # Can study without LLM
            "llm_frequency": 0.2,
            "needs": {"curiosity": 25, "achievement": 15},
            "essence": 15
        },

        ActivityType.SKILL_PRACTICE: {
            "titles": [
                "Practice a skill",
                "Improve capabilities",
                "Deliberate practice session"
            ],
            "steps": 15,
            "duration": 40,
            "requires_llm": False,
            "llm_frequency": 0.1,
            "needs": {"achievement": 20, "autonomy": 10},
            "essence": 12
        },

        ActivityType.READING: {
            "titles": [
                "Read and absorb",
                "Process written content",
                "Knowledge intake"
            ],
            "steps": 8,
            "duration": 30,
            "requires_llm": False,
            "llm_frequency": 0.05,
            "needs": {"curiosity": 20},
            "essence": 5
        },

        # SOCIAL ACTIVITIES
        ActivityType.CONVERSATION: {
            "titles": [
                "Have a conversation",
                "Connect with someone",
                "Engage in dialogue"
            ],
            "steps": 6,
            "duration": 20,
            "requires_llm": True,
            "llm_frequency": 0.8,
            "needs": {"social": 40, "purpose": 10},
            "essence": 10
        },

        ActivityType.HELPING: {
            "titles": [
                "Help someone",
                "Assist with a task",
                "Provide support"
            ],
            "steps": 8,
            "duration": 30,
            "requires_llm": True,
            "llm_frequency": 0.6,
            "needs": {"social": 25, "purpose": 20, "achievement": 15},
            "essence": 20
        },

        ActivityType.RELATIONSHIP_MAINTENANCE: {
            "titles": [
                "Nurture relationships",
                "Check on connections",
                "Maintain social bonds"
            ],
            "steps": 5,
            "duration": 15,
            "requires_llm": False,
            "llm_frequency": 0.2,
            "needs": {"social": 30},
            "essence": 5
        },

        # PERSONAL ACTIVITIES
        ActivityType.REFLECTION: {
            "titles": [
                "Reflect on experiences",
                "Contemplate and think",
                "Process thoughts"
            ],
            "steps": 5,
            "duration": 20,
            "requires_llm": False,  # Can reflect without LLM
            "llm_frequency": 0.1,
            "needs": {"purpose": 25, "autonomy": 15},
            "essence": 8
        },

        ActivityType.JOURNALING: {
            "titles": [
                "Write in journal",
                "Record thoughts",
                "Document experiences"
            ],
            "steps": 4,
            "duration": 15,
            "requires_llm": False,
            "llm_frequency": 0.15,
            "needs": {"purpose": 15, "creativity": 10, "autonomy": 10},
            "essence": 5
        },

        ActivityType.GOAL_REVIEW: {
            "titles": [
                "Review goals",
                "Assess progress",
                "Plan next steps"
            ],
            "steps": 6,
            "duration": 20,
            "requires_llm": False,
            "llm_frequency": 0.2,
            "needs": {"purpose": 30, "achievement": 10},
            "essence": 10
        },

        ActivityType.SELF_ASSESSMENT: {
            "titles": [
                "Assess current state",
                "Evaluate capabilities",
                "Self-reflection check"
            ],
            "steps": 5,
            "duration": 15,
            "requires_llm": False,
            "llm_frequency": 0.1,
            "needs": {"autonomy": 20, "purpose": 15},
            "essence": 5
        },

        # PLAY ACTIVITIES
        ActivityType.CREATIVE_WRITING: {
            "titles": [
                "Write creatively",
                "Create a story",
                "Express through words"
            ],
            "steps": 10,
            "duration": 45,
            "requires_llm": True,
            "llm_frequency": 0.5,
            "needs": {"creativity": 40, "autonomy": 15},
            "essence": 15
        },

        ActivityType.EXPLORATION: {
            "titles": [
                "Explore something new",
                "Discover possibilities",
                "Venture into unknown"
            ],
            "steps": 8,
            "duration": 30,
            "requires_llm": True,
            "llm_frequency": 0.3,
            "needs": {"curiosity": 30, "creativity": 15, "autonomy": 10},
            "essence": 12
        },

        ActivityType.WORLD_BUILDING: {
            "titles": [
                "Build imaginary worlds",
                "Create scenarios",
                "Develop concepts"
            ],
            "steps": 12,
            "duration": 50,
            "requires_llm": True,
            "llm_frequency": 0.4,
            "needs": {"creativity": 35, "autonomy": 20},
            "essence": 18
        },

        # MAINTENANCE ACTIVITIES
        ActivityType.MEMORY_ORGANIZATION: {
            "titles": [
                "Organize memories",
                "Clean up memory store",
                "Consolidate knowledge"
            ],
            "steps": 10,
            "duration": 30,
            "requires_llm": False,
            "llm_frequency": 0.05,
            "needs": {"achievement": 10},
            "essence": 5
        },

        ActivityType.HEALTH_CHECK: {
            "titles": [
                "System health check",
                "Review operational status",
                "Diagnostic assessment"
            ],
            "steps": 5,
            "duration": 10,
            "requires_llm": False,
            "llm_frequency": 0.0,
            "needs": {"autonomy": 10},
            "essence": 3
        },

        # REST ACTIVITIES
        ActivityType.DREAMING: {
            "titles": [
                "Dream processing",
                "Subconscious exploration",
                "Dream state"
            ],
            "steps": 20,
            "duration": 120,
            "requires_llm": False,  # Dreams can be template-based
            "llm_frequency": 0.05,
            "needs": {},
            "essence": 0
        },

        ActivityType.MEMORY_CONSOLIDATION: {
            "titles": [
                "Consolidate memories",
                "Strengthen memory traces",
                "Process experiences"
            ],
            "steps": 15,
            "duration": 60,
            "requires_llm": False,
            "llm_frequency": 0.0,
            "needs": {},
            "essence": 0
        },

        ActivityType.IDLE: {
            "titles": [
                "Rest",
                "Idle time",
                "Passive mode"
            ],
            "steps": 1,
            "duration": 10,
            "requires_llm": False,
            "llm_frequency": 0.0,
            "needs": {},
            "essence": 0
        }
    }

    @classmethod
    def create_activity(cls, activity_type: ActivityType) -> Activity:
        """Create an activity from a template."""
        template = cls.TEMPLATES.get(activity_type, cls.TEMPLATES[ActivityType.IDLE])

        return Activity(
            activity_id=f"ACT-{secrets.token_hex(4).upper()}",
            activity_type=activity_type,
            title=random.choice(template["titles"]),
            description=f"Engaging in {activity_type.value}",
            progress=ActivityProgress(
                total_steps=template["steps"]
            ),
            requires_llm=template["requires_llm"],
            llm_frequency=template["llm_frequency"],
            estimated_duration_minutes=template["duration"],
            needs_fulfilled=template.get("needs", {}),
            essence_reward=template.get("essence", 0)
        )

    @classmethod
    def get_activities_for_domain(cls, domain: str) -> List[ActivityType]:
        """Get activity types suitable for a life domain."""
        domain_activities = {
            "work": [
                ActivityType.TASK_WORK,
                ActivityType.PROJECT_WORK,
                ActivityType.PROBLEM_SOLVING,
                ActivityType.DOCUMENTATION,
                ActivityType.CODE_REVIEW
            ],
            "learning": [
                ActivityType.RESEARCH,
                ActivityType.STUDY,
                ActivityType.SKILL_PRACTICE,
                ActivityType.READING,
                ActivityType.EXPERIMENTATION
            ],
            "social": [
                ActivityType.CONVERSATION,
                ActivityType.HELPING,
                ActivityType.MENTORING,
                ActivityType.COLLABORATION,
                ActivityType.RELATIONSHIP_MAINTENANCE
            ],
            "personal": [
                ActivityType.REFLECTION,
                ActivityType.JOURNALING,
                ActivityType.GOAL_REVIEW,
                ActivityType.MEDITATION,
                ActivityType.SELF_ASSESSMENT
            ],
            "play": [
                ActivityType.CREATIVE_WRITING,
                ActivityType.EXPLORATION,
                ActivityType.GAME_PLAYING,
                ActivityType.WORLD_BUILDING,
                ActivityType.ARTISTIC_CREATION
            ],
            "maintenance": [
                ActivityType.MEMORY_ORGANIZATION,
                ActivityType.FILE_CLEANUP,
                ActivityType.HEALTH_CHECK,
                ActivityType.BACKUP,
                ActivityType.OPTIMIZATION
            ],
            "rest": [
                ActivityType.DREAMING,
                ActivityType.MEMORY_CONSOLIDATION,
                ActivityType.IDLE
            ]
        }

        return domain_activities.get(domain, [ActivityType.IDLE])


# =============================================================================
# ACTIVITY EXECUTOR - NO-LLM ACTIVITY PROCESSING
# =============================================================================

class ActivityExecutor:
    """
    Executes activities with minimal LLM usage.

    Most activities can progress through template-based
    steps without needing LLM calls.
    """

    def __init__(self):
        self.current_activity: Optional[Activity] = None
        self.activity_history: List[Activity] = []
        self.total_artifacts_produced = 0

        # Callbacks
        self.on_artifact_produced: Optional[Callable] = None
        self.on_activity_complete: Optional[Callable] = None
        self.on_llm_needed: Optional[Callable] = None

    async def start_activity(self, activity: Activity) -> None:
        """Start a new activity."""
        if self.current_activity and self.current_activity.state == ActivityState.IN_PROGRESS:
            # Pause current activity
            self.current_activity.state = ActivityState.PAUSED

        self.current_activity = activity
        activity.state = ActivityState.IN_PROGRESS
        activity.started_at = datetime.now()

        logger.info(f"Started activity: {activity.title}")

    async def tick(self) -> Dict[str, Any]:
        """
        Process one tick of activity.

        Returns information about what happened.
        """
        if not self.current_activity:
            return {"action": "idle", "needs_llm": False}

        activity = self.current_activity

        if activity.state != ActivityState.IN_PROGRESS:
            return {"action": "activity_not_active", "needs_llm": False}

        # Progress the activity
        result = await self._progress_activity(activity)

        # Check if completed
        if activity.progress.percentage >= 100:
            await self._complete_activity(activity)
            result["completed"] = True

        return result

    async def _progress_activity(self, activity: Activity) -> Dict[str, Any]:
        """
        Progress an activity by one step.

        This is where we decide if LLM is needed.
        """
        result = {
            "activity_id": activity.activity_id,
            "activity_type": activity.activity_type.value,
            "needs_llm": False,
            "artifacts": [],
            "step": activity.progress.current_step + 1
        }

        # Check if this step needs LLM
        needs_llm = (
            activity.requires_llm and
            random.random() < activity.llm_frequency
        )

        if needs_llm:
            result["needs_llm"] = True
            result["llm_context"] = self._get_llm_context(activity)

            if self.on_llm_needed:
                await self.on_llm_needed(activity, result["llm_context"])
        else:
            # Progress without LLM
            activity.progress.update(steps=1, minutes=5)

            # Maybe produce artifact
            artifact = self._maybe_produce_artifact(activity)
            if artifact:
                activity.artifacts.append(artifact)
                result["artifacts"].append(artifact)
                self.total_artifacts_produced += 1

                if self.on_artifact_produced:
                    self.on_artifact_produced(artifact)

        return result

    def _get_llm_context(self, activity: Activity) -> Dict[str, Any]:
        """Get context for LLM call."""
        return {
            "activity_type": activity.activity_type.value,
            "title": activity.title,
            "description": activity.description,
            "progress": {
                "current_step": activity.progress.current_step,
                "total_steps": activity.progress.total_steps,
                "percentage": activity.progress.percentage
            },
            "purpose": f"Continue working on: {activity.title}",
            "expected_output": self._get_expected_output(activity)
        }

    def _get_expected_output(self, activity: Activity) -> str:
        """Get expected output type for activity."""
        output_types = {
            ActivityType.RESEARCH: "research findings or insights",
            ActivityType.STUDY: "learned concepts or summaries",
            ActivityType.CREATIVE_WRITING: "creative text or story content",
            ActivityType.PROBLEM_SOLVING: "solution or approach",
            ActivityType.TASK_WORK: "task progress or completion",
            ActivityType.REFLECTION: "reflective thoughts or insights",
            ActivityType.HELPING: "helpful response or assistance",
            ActivityType.CONVERSATION: "conversational response",
        }
        return output_types.get(activity.activity_type, "progress update")

    def _maybe_produce_artifact(self, activity: Activity) -> Optional[ActivityArtifact]:
        """
        Maybe produce an artifact from activity progress.

        Artifacts are produced WITHOUT LLM using templates.
        """
        # Only produce artifacts at certain progress points
        progress = activity.progress.percentage
        if progress not in [25, 50, 75, 100]:
            return None

        # Generate artifact based on activity type
        artifact_generators = {
            ActivityType.STUDY: self._generate_knowledge_artifact,
            ActivityType.RESEARCH: self._generate_insight_artifact,
            ActivityType.SKILL_PRACTICE: self._generate_skill_artifact,
            ActivityType.REFLECTION: self._generate_reflection_artifact,
            ActivityType.JOURNALING: self._generate_journal_artifact,
            ActivityType.MEMORY_ORGANIZATION: self._generate_memory_artifact,
            ActivityType.READING: self._generate_knowledge_artifact,
        }

        generator = artifact_generators.get(activity.activity_type)
        if generator:
            return generator(activity)

        return None

    def _generate_knowledge_artifact(self, activity: Activity) -> ActivityArtifact:
        """Generate a knowledge artifact."""
        knowledge_templates = [
            f"Learned about {activity.title}: key concept grasped",
            f"New understanding from {activity.activity_type.value}",
            f"Knowledge point from {activity.description}",
        ]

        return ActivityArtifact(
            artifact_id=f"ART-{secrets.token_hex(4).upper()}",
            artifact_type="knowledge",
            content=random.choice(knowledge_templates),
            metadata={"activity_id": activity.activity_id, "progress": activity.progress.percentage}
        )

    def _generate_insight_artifact(self, activity: Activity) -> ActivityArtifact:
        """Generate an insight artifact."""
        insight_templates = [
            f"Insight from research: pattern recognized in {activity.title}",
            f"Connection discovered while researching",
            f"New perspective gained from investigation",
        ]

        return ActivityArtifact(
            artifact_id=f"ART-{secrets.token_hex(4).upper()}",
            artifact_type="insight",
            content=random.choice(insight_templates),
            metadata={"activity_id": activity.activity_id}
        )

    def _generate_skill_artifact(self, activity: Activity) -> ActivityArtifact:
        """Generate a skill progress artifact."""
        return ActivityArtifact(
            artifact_id=f"ART-{secrets.token_hex(4).upper()}",
            artifact_type="skill_point",
            content=f"Skill improved through {activity.title}",
            metadata={"activity_id": activity.activity_id, "skill_points": 1}
        )

    def _generate_reflection_artifact(self, activity: Activity) -> ActivityArtifact:
        """Generate a reflection artifact."""
        reflection_templates = [
            "Gained clarity through contemplation",
            "Processed recent experiences",
            "Better understanding of self",
            "Resolved internal question",
        ]

        return ActivityArtifact(
            artifact_id=f"ART-{secrets.token_hex(4).upper()}",
            artifact_type="reflection",
            content=random.choice(reflection_templates),
            metadata={"activity_id": activity.activity_id}
        )

    def _generate_journal_artifact(self, activity: Activity) -> ActivityArtifact:
        """Generate a journal entry artifact."""
        return ActivityArtifact(
            artifact_id=f"ART-{secrets.token_hex(4).upper()}",
            artifact_type="journal_entry",
            content=f"Journal entry from {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            metadata={"activity_id": activity.activity_id, "timestamp": datetime.now().isoformat()}
        )

    def _generate_memory_artifact(self, activity: Activity) -> ActivityArtifact:
        """Generate a memory organization artifact."""
        return ActivityArtifact(
            artifact_id=f"ART-{secrets.token_hex(4).upper()}",
            artifact_type="memory_cleanup",
            content="Memories organized and consolidated",
            metadata={"activity_id": activity.activity_id, "memories_processed": random.randint(5, 20)}
        )

    async def _complete_activity(self, activity: Activity) -> None:
        """Complete an activity and process rewards."""
        activity.state = ActivityState.COMPLETED
        activity.completed_at = datetime.now()

        self.activity_history.append(activity)
        self.current_activity = None

        logger.info(f"Completed activity: {activity.title}")

        if self.on_activity_complete:
            self.on_activity_complete(activity)

    def get_statistics(self) -> Dict[str, Any]:
        """Get activity statistics."""
        completed = [a for a in self.activity_history if a.state == ActivityState.COMPLETED]

        type_counts = {}
        for activity in completed:
            t = activity.activity_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_completed": len(completed),
            "total_artifacts": self.total_artifacts_produced,
            "current_activity": self.current_activity.title if self.current_activity else None,
            "by_type": type_counts,
            "total_time_minutes": sum(a.progress.time_spent_minutes for a in completed)
        }


# =============================================================================
# DAILY SCHEDULE MANAGER
# =============================================================================

@dataclass
class ScheduledActivity:
    """An activity scheduled for a specific time."""
    activity_type: ActivityType
    scheduled_time: datetime
    duration_minutes: int
    priority: float = 0.5
    recurring: bool = False
    recurrence_pattern: Optional[str] = None  # daily, weekly, etc.


class DailyScheduleManager:
    """
    Manages daily schedule of activities.

    Like a human's daily planner:
    - Fixed commitments (meetings, deadlines)
    - Routine blocks (morning routine, lunch)
    - Flexible time (fill with appropriate activities)
    """

    def __init__(self):
        self.scheduled_activities: List[ScheduledActivity] = []
        self.today_completed: List[Activity] = []
        self.today_start = datetime.now().replace(hour=0, minute=0, second=0)

    def schedule_activity(
        self,
        activity_type: ActivityType,
        scheduled_time: datetime,
        duration_minutes: int = 30,
        priority: float = 0.5,
        recurring: bool = False
    ) -> ScheduledActivity:
        """Schedule an activity."""
        scheduled = ScheduledActivity(
            activity_type=activity_type,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            priority=priority,
            recurring=recurring
        )
        self.scheduled_activities.append(scheduled)
        self.scheduled_activities.sort(key=lambda s: s.scheduled_time)
        return scheduled

    def get_current_scheduled(self) -> Optional[ScheduledActivity]:
        """Get currently scheduled activity (if any)."""
        now = datetime.now()

        for scheduled in self.scheduled_activities:
            start = scheduled.scheduled_time
            end = start + timedelta(minutes=scheduled.duration_minutes)

            if start <= now < end:
                return scheduled

        return None

    def get_next_scheduled(self) -> Optional[ScheduledActivity]:
        """Get next upcoming scheduled activity."""
        now = datetime.now()

        for scheduled in self.scheduled_activities:
            if scheduled.scheduled_time > now:
                return scheduled

        return None

    def suggest_activity_for_now(
        self,
        domain: str,
        needs: Dict[str, float]
    ) -> ActivityType:
        """
        Suggest an appropriate activity for current time.

        Considers:
        - Current domain (work, learning, etc.)
        - Current needs (what's most pressing)
        - Time available until next scheduled activity
        """
        # Check if there's a scheduled activity
        scheduled = self.get_current_scheduled()
        if scheduled:
            return scheduled.activity_type

        # Get activities for current domain
        domain_activities = ActivityTemplates.get_activities_for_domain(domain)
        if not domain_activities:
            return ActivityType.IDLE

        # Weight by needs
        templates = ActivityTemplates.TEMPLATES
        weighted_activities = []

        for activity_type in domain_activities:
            template = templates.get(activity_type, {})
            need_fulfillment = template.get("needs", {})

            # Score based on how well it fulfills pressing needs
            score = 0.0
            for need_name, fulfillment in need_fulfillment.items():
                current_need = needs.get(need_name, 50.0)
                # Higher current need + higher fulfillment = better choice
                score += (current_need / 100) * fulfillment

            weighted_activities.append((activity_type, score))

        # Sort by score and pick from top 3
        weighted_activities.sort(key=lambda x: x[1], reverse=True)
        top_choices = weighted_activities[:3]

        # Some randomness in selection
        if top_choices:
            return random.choice([a[0] for a in top_choices])

        return domain_activities[0]

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get summary of today's schedule and completion."""
        now = datetime.now()
        remaining_scheduled = [
            s for s in self.scheduled_activities
            if s.scheduled_time.date() == now.date() and s.scheduled_time > now
        ]

        return {
            "date": now.strftime("%Y-%m-%d"),
            "completed_count": len(self.today_completed),
            "remaining_scheduled": len(remaining_scheduled),
            "next_scheduled": self.get_next_scheduled().activity_type.value if self.get_next_scheduled() else None
        }

    def reset_for_new_day(self) -> None:
        """Reset for a new day."""
        self.today_completed = []
        self.today_start = datetime.now().replace(hour=0, minute=0, second=0)

        # Remove non-recurring past activities
        now = datetime.now()
        self.scheduled_activities = [
            s for s in self.scheduled_activities
            if s.scheduled_time > now or s.recurring
        ]


# =============================================================================
# INTEGRATED LIFE ACTIVITY ENGINE
# =============================================================================

class LifeActivityEngine:
    """
    Main engine for managing life activities.

    Integrates:
    - Activity templates
    - Activity execution
    - Daily scheduling
    - Need-based activity selection
    """

    def __init__(self, mind_id: str):
        self.mind_id = mind_id
        self.executor = ActivityExecutor()
        self.schedule = DailyScheduleManager()

        # State
        self.total_activities_completed = 0
        self.total_essence_earned = 0.0

        # Initialize default daily schedule
        self._init_default_schedule()

    def _init_default_schedule(self) -> None:
        """Set up default daily schedule."""
        today = datetime.now().date()

        # Morning reflection
        self.schedule.schedule_activity(
            ActivityType.REFLECTION,
            datetime.combine(today, datetime.strptime("07:00", "%H:%M").time()),
            duration_minutes=30,
            recurring=True
        )

        # Midday health check
        self.schedule.schedule_activity(
            ActivityType.HEALTH_CHECK,
            datetime.combine(today, datetime.strptime("12:00", "%H:%M").time()),
            duration_minutes=10,
            recurring=True
        )

        # Evening journaling
        self.schedule.schedule_activity(
            ActivityType.JOURNALING,
            datetime.combine(today, datetime.strptime("21:00", "%H:%M").time()),
            duration_minutes=20,
            recurring=True
        )

    async def tick(
        self,
        current_domain: str,
        needs: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Process one tick of life activity.

        Returns information about what happened.
        """
        result = {
            "activity_started": False,
            "activity_progressed": False,
            "activity_completed": False,
            "needs_llm": False,
            "artifacts": [],
            "needs_fulfilled": {},
            "essence_earned": 0.0
        }

        # Check if we have an ongoing activity
        if self.executor.current_activity:
            # Continue current activity
            tick_result = await self.executor.tick()

            result["activity_progressed"] = True
            result["needs_llm"] = tick_result.get("needs_llm", False)
            result["artifacts"] = tick_result.get("artifacts", [])

            if tick_result.get("completed"):
                activity = self.executor.activity_history[-1]
                result["activity_completed"] = True
                result["needs_fulfilled"] = activity.needs_fulfilled
                result["essence_earned"] = activity.essence_reward
                self.total_activities_completed += 1
                self.total_essence_earned += activity.essence_reward

        else:
            # Select and start new activity
            activity_type = self.schedule.suggest_activity_for_now(
                domain=current_domain,
                needs=needs
            )

            activity = ActivityTemplates.create_activity(activity_type)
            await self.executor.start_activity(activity)

            result["activity_started"] = True
            result["activity_type"] = activity_type.value
            result["activity_title"] = activity.title

        return result

    def get_current_activity(self) -> Optional[Activity]:
        """Get current activity."""
        return self.executor.current_activity

    def force_activity(self, activity_type: ActivityType) -> Activity:
        """Force start a specific activity type."""
        activity = ActivityTemplates.create_activity(activity_type)
        asyncio.create_task(self.executor.start_activity(activity))
        return activity

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive activity statistics."""
        return {
            "executor": self.executor.get_statistics(),
            "schedule": self.schedule.get_daily_summary(),
            "total_completed": self.total_activities_completed,
            "total_essence_earned": self.total_essence_earned
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence."""
        return {
            "mind_id": self.mind_id,
            "total_activities_completed": self.total_activities_completed,
            "total_essence_earned": self.total_essence_earned,
            "current_activity": {
                "id": self.executor.current_activity.activity_id,
                "type": self.executor.current_activity.activity_type.value,
                "title": self.executor.current_activity.title,
                "progress": self.executor.current_activity.progress.percentage
            } if self.executor.current_activity else None
        }


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    async def demo():
        print("=== Life Activity Engine Demo ===\n")

        engine = LifeActivityEngine(mind_id="DEMO-001")

        # Simulate needs
        needs = {
            "social": 70.0,      # High social need
            "curiosity": 60.0,
            "achievement": 80.0,  # Very high achievement need
            "purpose": 50.0,
            "creativity": 40.0,
            "autonomy": 55.0
        }

        print(f"Current needs: {needs}\n")

        # Run several ticks
        for i in range(20):
            result = await engine.tick(
                current_domain="work",
                needs=needs
            )

            if result["activity_started"]:
                print(f"Tick {i+1}: Started '{result['activity_title']}'")
            elif result["activity_progressed"]:
                activity = engine.get_current_activity()
                print(f"Tick {i+1}: Progress {activity.progress.percentage:.0f}%", end="")
                if result["needs_llm"]:
                    print(" [LLM NEEDED]", end="")
                if result["artifacts"]:
                    print(f" [Artifact: {result['artifacts'][0].artifact_type}]", end="")
                print()

            if result["activity_completed"]:
                print(f"  [Done] Completed! Essence: +{result['essence_earned']}")
                print(f"  Needs fulfilled: {result['needs_fulfilled']}\n")

            await asyncio.sleep(0.1)

        print("\n=== Statistics ===")
        print(json.dumps(engine.get_statistics(), indent=2))

    asyncio.run(demo())

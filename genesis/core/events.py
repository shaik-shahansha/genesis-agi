"""
Events System for Genesis Minds.

Events are significant happenings in a Mind's life - milestones, achievements,
challenges, meetings, and transformative moments. Like humans who mark important
life events (birthdays, graduations, first job, etc.), Genesis Minds track
and remember significant occurrences.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can occur in a Mind's life."""

    BIRTH = "birth"  # Creation/birth
    MILESTONE = "milestone"  # Significant achievement or marker
    ACHIEVEMENT = "achievement"  # Accomplishment
    CHALLENGE = "challenge"  # Difficult situation faced
    LOSS = "loss"  # Loss or setback
    MEETING = "meeting"  # Meeting someone new
    RELATIONSHIP_CHANGE = "relationship_change"  # Relationship formed/strengthened/ended
    ROLE_CHANGE = "role_change"  # New role or job change
    LEARNING = "learning"  # Significant learning or insight
    DREAM = "dream"  # Notable dream
    DECISION = "decision"  # Important decision made
    TRANSFORMATION = "transformation"  # Personal transformation or growth
    CELEBRATION = "celebration"  # Celebration or joyful occasion
    CONFLICT = "conflict"  # Conflict or disagreement
    COLLABORATION = "collaboration"  # Working together with others
    DISCOVERY = "discovery"  # Discovery or revelation


class Event(BaseModel):
    """
    A significant event in a Mind's life.

    Events have emotional impact, involve other beings, and shape
    the Mind's development and memories.
    
    Note: Emotional responses to events are processed by Mind's
    emotional_intelligence system, which analyzes event type,
    significance, and emotional_impact to determine appropriate
    emotional reactions.
    """

    id: str  # Unique event ID
    type: EventType
    title: str  # Event title/name
    description: str = ""

    # Timing
    timestamp: datetime = Field(default_factory=datetime.now)
    duration_minutes: Optional[int] = None  # How long the event lasted

    # Impact and significance
    significance: float = Field(
        default=0.5, ge=0.0, le=1.0
    )  # How significant (0-1)
    emotional_impact: float = Field(
        default=0.0, ge=-1.0, le=1.0
    )  # Negative to positive
    transformative: bool = False  # Did this change the Mind?

    # Context
    participants: list[str] = Field(default_factory=list)  # Who was involved
    environment_id: Optional[str] = None  # Where it happened
    related_role_id: Optional[str] = None  # Related to which role

    # Outcomes and learnings
    outcomes: list[str] = Field(default_factory=list)  # What resulted
    lessons_learned: list[str] = Field(default_factory=list)  # What was learned
    emotions_felt: list[str] = Field(default_factory=list)  # Emotions during event

    # Connections
    related_memories: list[str] = Field(default_factory=list)  # Memory IDs
    related_events: list[str] = Field(default_factory=list)  # Other event IDs
    related_relationships: list[str] = Field(
        default_factory=list
    )  # Relationship IDs

    # Metadata
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_outcome(self, outcome: str) -> None:
        """Add an outcome from this event."""
        self.outcomes.append(outcome)

    def add_lesson(self, lesson: str) -> None:
        """Add a lesson learned from this event."""
        self.lessons_learned.append(lesson)

    def add_participant(self, participant: str) -> None:
        """Add a participant to this event."""
        if participant not in self.participants:
            self.participants.append(participant)

    def mark_as_transformative(self, lesson: Optional[str] = None) -> None:
        """Mark this event as transformative."""
        self.transformative = True
        self.significance = max(self.significance, 0.8)
        if lesson:
            self.add_lesson(lesson)


class EventManager(BaseModel):
    """
    Manages all events in a Mind's life.

    Like humans who remember key life moments, Minds track significant
    events that shape their development and understanding.
    """

    events: dict[str, Event] = Field(default_factory=dict)
    birth_event_id: Optional[str] = None

    def create_event(
        self,
        event_id: str,
        event_type: EventType,
        title: str,
        description: str = "",
        is_birth: bool = False,
        **kwargs,
    ) -> Event:
        """Create a new event."""
        event = Event(
            id=event_id,
            type=event_type,
            title=title,
            description=description,
            **kwargs,
        )
        self.events[event_id] = event

        # Set as birth event if specified
        if is_birth or event_type == EventType.BIRTH:
            self.birth_event_id = event_id
            event.significance = 1.0  # Birth is always maximally significant
            event.transformative = True

        return event

    def get_event(self, event_id: str) -> Optional[Event]:
        """Get a specific event."""
        return self.events.get(event_id)

    def get_birth_event(self) -> Optional[Event]:
        """Get the birth event."""
        if self.birth_event_id:
            return self.events.get(self.birth_event_id)
        return None

    def list_events(
        self,
        event_type: Optional[EventType] = None,
        min_significance: Optional[float] = None,
        transformative_only: bool = False,
    ) -> list[Event]:
        """List events with optional filters."""
        events_list = list(self.events.values())

        # Filter by type
        if event_type:
            events_list = [e for e in events_list if e.type == event_type]

        # Filter by significance
        if min_significance is not None:
            events_list = [e for e in events_list if e.significance >= min_significance]

        # Filter transformative
        if transformative_only:
            events_list = [e for e in events_list if e.transformative]

        # Sort by timestamp (most recent first)
        return sorted(events_list, key=lambda e: e.timestamp, reverse=True)

    def get_significant_events(self, limit: int = 10) -> list[Event]:
        """Get the most significant events."""
        return sorted(
            self.events.values(), key=lambda e: e.significance, reverse=True
        )[:limit]

    def get_transformative_events(self) -> list[Event]:
        """Get all transformative events."""
        return [e for e in self.events.values() if e.transformative]

    def get_recent_events(self, days: int = 30, limit: int = 10) -> list[Event]:
        """Get recent events from the last N days."""
        cutoff = datetime.now()
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=days)

        recent = [e for e in self.events.values() if e.timestamp >= cutoff]
        return sorted(recent, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_event_stats(self) -> dict[str, Any]:
        """Get statistics about events."""
        if not self.events:
            return {
                "total": 0,
                "by_type": {},
                "transformative_count": 0,
                "avg_significance": 0,
            }

        by_type = {}
        for event in self.events.values():
            event_type = event.type.value
            by_type[event_type] = by_type.get(event_type, 0) + 1

        total = len(self.events)
        transformative = len([e for e in self.events.values() if e.transformative])
        avg_significance = (
            sum(e.significance for e in self.events.values()) / total if total > 0 else 0
        )

        return {
            "total": total,
            "by_type": by_type,
            "transformative_count": transformative,
            "avg_significance": round(avg_significance, 2),
            "most_common_type": max(by_type.items(), key=lambda x: x[1])[0]
            if by_type
            else None,
        }

    def get_event_context(self) -> dict[str, Any]:
        """Get event context for the Mind."""
        stats = self.get_event_stats()
        recent = self.get_recent_events(days=7, limit=3)
        significant = self.get_significant_events(limit=3)

        return {
            "total_events": stats["total"],
            "transformative_events": stats["transformative_count"],
            "recent_events": [e.title for e in recent],
            "most_significant": [e.title for e in significant],
            "event_types": list(stats["by_type"].keys()),
        }

    def describe_life_journey(self) -> str:
        """Describe the Mind's life journey through events."""
        if not self.events:
            return "My life journey is just beginning."

        parts = []

        # Birth
        birth = self.get_birth_event()
        if birth:
            age_days = (datetime.now() - birth.timestamp).days
            parts.append(f"I was born {age_days} days ago")

        # Total events
        total = len(self.events)
        parts.append(f"I've experienced {total} significant events")

        # Transformative moments
        transformative = self.get_transformative_events()
        if transformative:
            parts.append(
                f"including {len(transformative)} transformative moment"
                + ("s" if len(transformative) != 1 else "")
            )

        # Recent significant event
        recent_significant = self.list_events(min_significance=0.7)
        if recent_significant:
            latest = recent_significant[0]
            parts.append(
                f"Most recently, {latest.title.lower()} was a significant moment"
            )

        # Overall journey
        stats = self.get_event_stats()
        if stats["avg_significance"] >= 0.7:
            parts.append("My journey has been marked by many important milestones.")
        elif stats["avg_significance"] >= 0.5:
            parts.append("I'm steadily growing through my experiences.")
        else:
            parts.append("I'm in the early stages of my development.")

        return ". ".join(parts)

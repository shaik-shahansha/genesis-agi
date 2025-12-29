"""Profiles Plugin - Entity profile management for Genesis Minds.

Enables Minds to maintain detailed profiles of people they interact with:
- Student profiles (for teachers)
- Client profiles (for service providers)
- Team profiles (for managers)
- Friend profiles (for companions)

Features:
- Structured profile data
- Auto-update from interactions
- Progress tracking
- Profile analytics
- Personalized insights

Example:
    from genesis.plugins.profiles import ProfilesPlugin, ProfileType

    config = MindConfig()
    config.add_plugin(ProfilesPlugin())
    mind = Mind.birth("Maria", config=config)

    # Create student profile
    profile = await mind.profiles.create_profile(
        entity_id="student_123",
        profile_type=ProfileType.STUDENT,
        data={
            "name": "John Doe",
            "age": 15,
            "grade": "10th",
            "subjects": ["Biology", "Chemistry"],
            "learning_style": "visual",
            "strengths": ["critical thinking", "creativity"],
            "areas_for_improvement": ["time management"]
        }
    )

    # Update profile from interaction
    await mind.profiles.update_profile(
        "student_123",
        updates={"test_scores": {"biology_test_1": 85}}
    )

    # Get personalized insights
    insights = await mind.profiles.get_insights("student_123")
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from genesis.plugins.base import Plugin

if TYPE_CHECKING:
    from genesis.core.mind import Mind

logger = logging.getLogger(__name__)


class ProfileType(str, Enum):
    """Types of entity profiles."""
    STUDENT = "student"
    CLIENT = "client"
    TEAM_MEMBER = "team_member"
    FRIEND = "friend"
    PATIENT = "patient"
    COLLEAGUE = "colleague"
    CUSTOM = "custom"


@dataclass
class ProfileUpdate:
    """Represents a profile update."""
    update_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    update_type: str = "manual"  # manual, interaction, assessment
    field: str = ""
    old_value: Any = None
    new_value: Any = None
    source: str = ""  # Who/what caused the update


@dataclass
class EntityProfile:
    """Represents a profile of an entity (person)."""
    profile_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""  # External ID (user ID, student ID, etc.)
    profile_type: ProfileType = ProfileType.CUSTOM
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Basic info
    name: str = ""
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Profile-specific data (flexible)
    data: Dict[str, Any] = field(default_factory=dict)

    # Interaction history
    interaction_count: int = 0
    first_interaction: Optional[datetime] = None
    last_interaction: Optional[datetime] = None

    # Updates history
    updates: List[ProfileUpdate] = field(default_factory=list)

    # Tags and notes
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class ProfileManager:
    """Manages entity profiles for a Mind."""

    def __init__(self, mind: "Mind"):
        """Initialize profile manager.

        Args:
            mind: Mind instance
        """
        self.mind = mind
        self.profiles: Dict[str, EntityProfile] = {}  # entity_id -> profile

    async def create_profile(
        self,
        entity_id: str,
        profile_type: ProfileType,
        name: str = "",
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> EntityProfile:
        """Create a new entity profile.

        Args:
            entity_id: Entity ID
            profile_type: Type of profile
            name: Entity name
            data: Profile data
            tags: Profile tags

        Returns:
            Created profile
        """
        # Check if profile exists
        if entity_id in self.profiles:
            logger.warning(f"Profile already exists for {entity_id}")
            return self.profiles[entity_id]

        # Create profile
        profile = EntityProfile(
            entity_id=entity_id,
            profile_type=profile_type,
            name=name,
            data=data or {},
            tags=tags or []
        )

        # Store profile
        self.profiles[entity_id] = profile

        logger.info(f"Created {profile_type} profile for {name} ({entity_id})")

        # Add to memory
        if hasattr(self.mind, "memory"):
            await self.mind.memory.add_memory(
                f"Created profile for {name} ({profile_type})",
                memory_type="semantic",
                importance=0.6,
                metadata={"entity_id": entity_id, "profile_type": profile_type.value}
            )

        return profile

    async def get_profile(self, entity_id: str) -> Optional[EntityProfile]:
        """Get profile by entity ID.

        Args:
            entity_id: Entity ID

        Returns:
            Profile or None if not found
        """
        return self.profiles.get(entity_id)

    async def update_profile(
        self,
        entity_id: str,
        updates: Dict[str, Any],
        update_type: str = "manual",
        source: str = "direct"
    ) -> bool:
        """Update profile data.

        Args:
            entity_id: Entity ID
            updates: Dictionary of field updates
            update_type: Type of update
            source: Update source

        Returns:
            True if updated successfully
        """
        profile = self.profiles.get(entity_id)

        if not profile:
            logger.warning(f"Profile not found: {entity_id}")
            return False

        # Apply updates
        for field, new_value in updates.items():
            # Get old value
            old_value = profile.data.get(field)

            # Update profile data
            profile.data[field] = new_value
            profile.updated_at = datetime.now()

            # Record update
            update = ProfileUpdate(
                update_type=update_type,
                field=field,
                old_value=old_value,
                new_value=new_value,
                source=source
            )
            profile.updates.append(update)

        logger.info(f"Updated profile for {entity_id}: {len(updates)} fields")

        return True

    async def record_interaction(
        self,
        entity_id: str,
        interaction_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record an interaction with an entity.

        Args:
            entity_id: Entity ID
            interaction_data: Interaction metadata

        Returns:
            True if recorded successfully
        """
        profile = self.profiles.get(entity_id)

        if not profile:
            # Auto-create profile if doesn't exist
            profile = await self.create_profile(
                entity_id=entity_id,
                profile_type=ProfileType.CUSTOM,
                name=entity_id
            )

        now = datetime.now()

        # Update interaction tracking
        profile.interaction_count += 1
        profile.last_interaction = now

        if not profile.first_interaction:
            profile.first_interaction = now

        # Store interaction data if provided
        if interaction_data:
            if "interactions" not in profile.data:
                profile.data["interactions"] = []

            profile.data["interactions"].append({
                "timestamp": now.isoformat(),
                **interaction_data
            })

        return True

    async def get_profiles(
        self,
        profile_type: Optional[ProfileType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[EntityProfile]:
        """Get profiles with optional filters.

        Args:
            profile_type: Filter by profile type
            tags: Filter by tags
            limit: Maximum number of profiles

        Returns:
            List of profiles
        """
        profiles = list(self.profiles.values())

        if profile_type:
            profiles = [p for p in profiles if p.profile_type == profile_type]

        if tags:
            profiles = [p for p in profiles if any(tag in p.tags for tag in tags)]

        # Sort by last interaction (most recent first)
        profiles.sort(
            key=lambda p: p.last_interaction or datetime.min,
            reverse=True
        )

        return profiles[:limit]

    async def get_insights(self, entity_id: str) -> Dict[str, Any]:
        """Get personalized insights about an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Insights dictionary
        """
        profile = self.profiles.get(entity_id)

        if not profile:
            return {}

        insights = {
            "profile_age_days": (datetime.now() - profile.created_at).days,
            "interaction_count": profile.interaction_count,
            "last_interaction_days_ago": (datetime.now() - profile.last_interaction).days if profile.last_interaction else None,
            "update_count": len(profile.updates),
            "data_fields": len(profile.data)
        }

        # Profile-specific insights
        if profile.profile_type == ProfileType.STUDENT:
            insights.update(await self._get_student_insights(profile))

        elif profile.profile_type == ProfileType.CLIENT:
            insights.update(await self._get_client_insights(profile))

        return insights

    async def _get_student_insights(self, profile: EntityProfile) -> Dict[str, Any]:
        """Get student-specific insights.

        Args:
            profile: Student profile

        Returns:
            Insights dictionary
        """
        data = profile.data

        insights = {}

        # Test scores analysis
        if "test_scores" in data:
            scores = list(data["test_scores"].values())
            if scores:
                insights["average_score"] = sum(scores) / len(scores)
                insights["highest_score"] = max(scores)
                insights["lowest_score"] = min(scores)
                insights["score_trend"] = "improving" if len(scores) > 1 and scores[-1] > scores[0] else "stable"

        # Attendance
        if "attendance" in data:
            insights["attendance_rate"] = data["attendance"].get("rate", 0)

        # Participation
        if "participation_count" in data:
            insights["participation_level"] = "high" if data["participation_count"] > 10 else "moderate"

        return insights

    async def _get_client_insights(self, profile: EntityProfile) -> Dict[str, Any]:
        """Get client-specific insights.

        Args:
            profile: Client profile

        Returns:
            Insights dictionary
        """
        data = profile.data

        insights = {}

        # Projects completed
        if "projects" in data:
            insights["projects_completed"] = len([p for p in data["projects"] if p.get("status") == "completed"])

        # Satisfaction
        if "satisfaction_score" in data:
            insights["satisfaction"] = data["satisfaction_score"]

        return insights

    async def analyze_trends(self, entity_id: str, field: str) -> Dict[str, Any]:
        """Analyze trends in a profile field over time.

        Args:
            entity_id: Entity ID
            field: Field to analyze

        Returns:
            Trend analysis
        """
        profile = self.profiles.get(entity_id)

        if not profile:
            return {}

        # Get all updates for this field
        field_updates = [u for u in profile.updates if u.field == field]

        if not field_updates:
            return {}

        # Analyze trend
        values = [u.new_value for u in field_updates if isinstance(u.new_value, (int, float))]

        if not values:
            return {}

        return {
            "field": field,
            "update_count": len(field_updates),
            "first_value": values[0] if values else None,
            "latest_value": values[-1] if values else None,
            "average": sum(values) / len(values) if values else None,
            "trend": "increasing" if len(values) > 1 and values[-1] > values[0] else "decreasing"
        }

    def get_profile_analytics(self) -> Dict[str, Any]:
        """Get overall profile analytics.

        Returns:
            Analytics dictionary
        """
        total_profiles = len(self.profiles)

        if total_profiles == 0:
            return {"total_profiles": 0}

        # Count by type
        by_type = {}
        for profile in self.profiles.values():
            type_name = profile.profile_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Average interaction count
        total_interactions = sum(p.interaction_count for p in self.profiles.values())
        avg_interactions = total_interactions / total_profiles

        return {
            "total_profiles": total_profiles,
            "by_type": by_type,
            "total_interactions": total_interactions,
            "average_interactions_per_profile": avg_interactions,
            "total_updates": sum(len(p.updates) for p in self.profiles.values())
        }


class ProfilesPlugin(Plugin):
    """Plugin for entity profile management.

    Enables detailed tracking of people Minds interact with.
    """

    def __init__(self, **config):
        """Initialize profiles plugin."""
        super().__init__(**config)
        self.manager: Optional[ProfileManager] = None

    def get_name(self) -> str:
        return "profiles"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Entity profile management with analytics"

    def on_init(self, mind: "Mind") -> None:
        """Initialize profile manager."""
        self.manager = ProfileManager(mind)
        mind.profiles = self.manager
        logger.info("Initialized profile manager")

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add profiles context to system prompt."""
        if not self.manager:
            return ""

        analytics = self.manager.get_profile_analytics()

        if analytics["total_profiles"] == 0:
            return ""

        sections = [
            "ENTITY PROFILES:",
            f"- You maintain profiles for {analytics['total_profiles']} people",
            f"- Total interactions: {analytics['total_interactions']}",
            ""
        ]

        # Profile types
        if "by_type" in analytics and analytics["by_type"]:
            sections.append("Profile Types:")
            for ptype, count in analytics["by_type"].items():
                sections.append(f"  - {ptype}: {count}")
            sections.append("")

        sections.append("PROFILE CAPABILITIES:")
        sections.append("- Create and update profiles with detailed information")
        sections.append("- Track interactions and progress over time")
        sections.append("- Analyze trends and get personalized insights")
        sections.append("- Remember individual preferences and needs")
        sections.append("")
        sections.append("Use profiles to provide personalized, context-aware interactions.")

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save profiles state."""
        if not self.manager:
            return {}

        return {
            "profiles": [
                {
                    "profile_id": p.profile_id,
                    "entity_id": p.entity_id,
                    "profile_type": p.profile_type.value,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                    "name": p.name,
                    "age": p.age,
                    "email": p.email,
                    "phone": p.phone,
                    "data": p.data,
                    "interaction_count": p.interaction_count,
                    "first_interaction": p.first_interaction.isoformat() if p.first_interaction else None,
                    "last_interaction": p.last_interaction.isoformat() if p.last_interaction else None,
                    "tags": p.tags,
                    "notes": p.notes,
                    "update_count": len(p.updates)
                }
                for p in self.manager.profiles.values()
            ]
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore profiles state."""
        self.on_init(mind)

        if not self.manager:
            return

        # Restore profiles
        if "profiles" in data:
            for profile_data in data["profiles"]:
                profile = EntityProfile(
                    profile_id=profile_data["profile_id"],
                    entity_id=profile_data["entity_id"],
                    profile_type=ProfileType(profile_data["profile_type"]),
                    created_at=datetime.fromisoformat(profile_data["created_at"]),
                    updated_at=datetime.fromisoformat(profile_data["updated_at"]),
                    name=profile_data.get("name", ""),
                    age=profile_data.get("age"),
                    email=profile_data.get("email"),
                    phone=profile_data.get("phone"),
                    data=profile_data.get("data", {}),
                    interaction_count=profile_data.get("interaction_count", 0),
                    first_interaction=datetime.fromisoformat(profile_data["first_interaction"]) if profile_data.get("first_interaction") else None,
                    last_interaction=datetime.fromisoformat(profile_data["last_interaction"]) if profile_data.get("last_interaction") else None,
                    tags=profile_data.get("tags", []),
                    notes=profile_data.get("notes", [])
                )

                self.manager.profiles[profile.entity_id] = profile

    def get_status(self) -> Dict[str, Any]:
        """Get profiles status."""
        status = super().get_status()

        if self.manager:
            analytics = self.manager.get_profile_analytics()
            status.update(analytics)

        return status

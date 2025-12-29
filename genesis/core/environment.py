"""
Environment System for Genesis Minds.

Environments define where a Mind exists, operates, and interacts.
Like humans who have homes, workplaces, and social spaces,
Genesis Minds can inhabit multiple environments.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EnvironmentType(str, Enum):
    """Types of environments a Mind can inhabit."""

    PHYSICAL = "physical"  # Physical locations (office, home, city)
    DIGITAL = "digital"  # Digital spaces (Slack, GitHub, email)
    SOCIAL = "social"  # Social contexts (family, team, community)
    VIRTUAL = "virtual"  # Virtual worlds (metaverse, games, simulations)
    PROFESSIONAL = "professional"  # Work contexts (company, project, department)


class Environment(BaseModel):
    """
    An environment where a Mind exists and operates.

    Environments are like metaverse spaces - Minds can own them, visit them,
    and interact with other Minds within them.
    """

    id: str  # Unique environment ID
    name: str  # Environment name (e.g., "Home", "Acme Corp Workspace")
    type: EnvironmentType
    description: str = ""

    # Ownership - metaverse-like
    owner_id: Optional[str] = None  # GMID of the Mind that owns this environment
    owner_name: Optional[str] = None  # Name of the owner
    is_shared: bool = False  # Can multiple Minds inhabit this?
    is_public: bool = False  # Can any Mind visit?

    # Environment details
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    access_frequency: int = 0  # How often accessed

    # Inhabitants and visitors - who's here now
    current_inhabitants: list[dict[str, str]] = Field(
        default_factory=list
    )  # [{"gmid": "...", "name": "..."}]
    visitors_history: list[dict[str, Any]] = Field(
        default_factory=list
    )  # History of visits
    invited_minds: list[str] = Field(
        default_factory=list
    )  # GMIDs of invited Minds    
    # Access control - who can access this environment
    allowed_users: list[str] = Field(
        default_factory=list
    )  # Email addresses of users who can access
    allowed_minds: list[str] = Field(
        default_factory=list
    )  # GMIDs of Minds that can access (in addition to invited_minds)
    # Context
    participants: list[str] = Field(default_factory=list)  # Who else is here (humans)
    objects: list[str] = Field(default_factory=list)  # What's in this environment
    atmosphere: str = "neutral"  # professional, casual, intimate, creative, etc.

    # Resources (files, info, documents available in this environment)
    resources: list[dict[str, Any]] = Field(default_factory=list)  # {"type": "file", "name": "...", "content": "...", "added_by": "..."}

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    # Memory associations
    significant_memories: list[str] = Field(
        default_factory=list
    )  # Memory IDs associated with this environment

    def access(self) -> None:
        """Record an access to this environment."""
        self.last_accessed = datetime.now()
        self.access_frequency += 1

    def add_participant(self, participant: str) -> None:
        """Add a participant to this environment."""
        if participant not in self.participants:
            self.participants.append(participant)

    def add_memory_association(self, memory_id: str) -> None:
        """Associate a memory with this environment."""
        if memory_id not in self.significant_memories:
            self.significant_memories.append(memory_id)

    # Metaverse-like interaction methods

    def invite_mind(self, mind_gmid: str) -> None:
        """Invite another Mind to this environment."""
        if mind_gmid not in self.invited_minds:
            self.invited_minds.append(mind_gmid)

    def can_visit(self, mind_gmid: str, user_email: Optional[str] = None) -> bool:
        """Check if a Mind can visit this environment."""
        # Owner can always visit
        if mind_gmid == self.owner_id:
            return True
        # Public environments allow anyone
        if self.is_public:
            return True
        # Check if invited
        if mind_gmid in self.invited_minds:
            return True
        # Check if explicitly allowed
        if mind_gmid in self.allowed_minds:
            return True
        # Check if user has access (for human-initiated interactions)
        if user_email and user_email in self.allowed_users:
            return True
        return False
    
    def add_user_access(self, user_email: str) -> None:
        """Grant a user access to this environment."""
        if user_email not in self.allowed_users:
            self.allowed_users.append(user_email)
    
    def remove_user_access(self, user_email: str) -> None:
        """Revoke a user's access to this environment."""
        if user_email in self.allowed_users:
            self.allowed_users.remove(user_email)
    
    def add_mind_access(self, mind_gmid: str) -> None:
        """Grant a Mind explicit access to this environment."""
        if mind_gmid not in self.allowed_minds:
            self.allowed_minds.append(mind_gmid)
    
    def remove_mind_access(self, mind_gmid: str) -> None:
        """Revoke a Mind's access to this environment."""
        if mind_gmid in self.allowed_minds:
            self.allowed_minds.remove(mind_gmid)
    
    def has_user_access(self, user_email: str) -> bool:
        """Check if a user has access to this environment."""
        if self.is_public:
            return True
        return user_email in self.allowed_users

    def mind_enters(self, mind_gmid: str, mind_name: str) -> dict[str, Any]:
        """Record a Mind entering this environment."""
        # Check if can visit
        if not self.can_visit(mind_gmid):
            return {"success": False, "reason": "Not authorized to visit"}

        # Add to current inhabitants
        inhabitant = {"gmid": mind_gmid, "name": mind_name}
        if inhabitant not in self.current_inhabitants:
            self.current_inhabitants.append(inhabitant)

        # Record visit in history
        visit_record = {
            "gmid": mind_gmid,
            "name": mind_name,
            "entered_at": datetime.now(),
            "is_owner": mind_gmid == self.owner_id,
        }
        self.visitors_history.append(visit_record)

        # Update access time
        self.access()

        return {
            "success": True,
            "environment": self.name,
            "current_inhabitants": self.current_inhabitants,
        }

    def mind_leaves(self, mind_gmid: str) -> None:
        """Record a Mind leaving this environment."""
        self.current_inhabitants = [
            i for i in self.current_inhabitants if i["gmid"] != mind_gmid
        ]

    def get_current_minds(self) -> list[str]:
        """Get list of Minds currently in this environment."""
        return [i["name"] for i in self.current_inhabitants]

    def add_resource(
        self,
        resource_type: str,
        name: str,
        content: Any,
        added_by: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Add a resource (file, info, document) to this environment."""
        resource = {
            "id": f"resource_{len(self.resources) + 1}",
            "type": resource_type,
            "name": name,
            "content": content,
            "added_by": added_by,
            "added_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.resources.append(resource)
        return resource

    def get_resources(self, resource_type: Optional[str] = None) -> list[dict[str, Any]]:
        """Get all resources, optionally filtered by type."""
        if resource_type:
            return [r for r in self.resources if r["type"] == resource_type]
        return self.resources

    def remove_resource(self, resource_id: str) -> bool:
        """Remove a resource from the environment."""
        original_count = len(self.resources)
        self.resources = [r for r in self.resources if r["id"] != resource_id]
        return len(self.resources) < original_count


class EnvironmentManager(BaseModel):
    """
    Manages all environments for a Mind.

    Like humans who navigate between home, work, and social spaces,
    Minds move between and exist in multiple environments.
    """

    environments: dict[str, Environment] = Field(default_factory=dict)
    current_environment_id: Optional[str] = None
    primary_environment_id: Optional[str] = None  # Home base

    def create_environment(
        self,
        env_id: str,
        name: str,
        env_type: EnvironmentType,
        description: str = "",
        **kwargs,
    ) -> Environment:
        """Create a new environment."""
        env = Environment(
            id=env_id,
            name=name,
            type=env_type,
            description=description,
            **kwargs,
        )
        self.environments[env_id] = env

        # Set as primary if first environment
        if self.primary_environment_id is None:
            self.primary_environment_id = env_id

        return env

    def enter_environment(self, env_id: str) -> Environment:
        """Enter an environment (change context)."""
        if env_id not in self.environments:
            raise ValueError(f"Environment {env_id} does not exist")

        env = self.environments[env_id]
        env.access()
        self.current_environment_id = env_id
        return env

    def get_current_environment(self) -> Optional[Environment]:
        """Get the current environment."""
        if self.current_environment_id:
            return self.environments.get(self.current_environment_id)
        return None

    def get_environment(self, env_id: str) -> Optional[Environment]:
        """Get a specific environment."""
        return self.environments.get(env_id)

    def get_primary_environment(self) -> Optional[Environment]:
        """Get the primary (home) environment."""
        if self.primary_environment_id:
            return self.environments.get(self.primary_environment_id)
        return None

    def list_environments(self, env_type: Optional[EnvironmentType] = None) -> list[Environment]:
        """List all environments, optionally filtered by type."""
        envs = list(self.environments.values())
        if env_type:
            envs = [e for e in envs if e.type == env_type]
        return sorted(envs, key=lambda e: e.access_frequency, reverse=True)

    def get_environment_context(self) -> dict[str, Any]:
        """Get current environmental context for the Mind."""
        current = self.get_current_environment()
        primary = self.get_primary_environment()

        return {
            "current_environment": {
                "name": current.name if current else None,
                "type": current.type.value if current else None,
                "atmosphere": current.atmosphere if current else None,
                "participants": current.participants if current else [],
            }
            if current
            else None,
            "primary_environment": primary.name if primary else None,
            "total_environments": len(self.environments),
            "environment_types": list(
                set(e.type.value for e in self.environments.values())
            ),
        }

    def describe_current_context(self) -> str:
        """Describe the current environmental context in natural language."""
        current = self.get_current_environment()

        if not current:
            return "I'm not currently in any specific environment."

        parts = [f"I'm currently in {current.name}"]

        if current.type:
            parts.append(f"({current.type.value} environment)")

        if current.participants:
            if len(current.participants) == 1:
                parts.append(f"with {current.participants[0]}")
            elif len(current.participants) <= 3:
                parts.append(f"with {', '.join(current.participants)}")
            else:
                parts.append(f"with {len(current.participants)} others")

        if current.atmosphere and current.atmosphere != "neutral":
            parts.append(f"The atmosphere is {current.atmosphere}.")

        # Mention other Minds present
        other_minds = current.get_current_minds()
        if other_minds:
            parts.append(f"Also here: {', '.join(other_minds)}")

        return " ".join(parts)

    # Metaverse-like Mind interaction methods

    def visit_environment(
        self, env_id: str, mind_gmid: str, mind_name: str
    ) -> dict[str, Any]:
        """Visit another Mind's environment or a shared environment."""
        if env_id not in self.environments:
            return {"success": False, "reason": f"Environment {env_id} not found"}

        env = self.environments[env_id]

        # Record Mind entering
        result = env.mind_enters(mind_gmid, mind_name)

        if result["success"]:
            # Update current environment
            self.current_environment_id = env_id

        return result

    def leave_environment(self, env_id: str, mind_gmid: str) -> None:
        """Leave an environment."""
        if env_id in self.environments:
            self.environments[env_id].mind_leaves(mind_gmid)

    def create_shared_environment(
        self,
        env_id: str,
        name: str,
        env_type: EnvironmentType,
        description: str = "",
        is_public: bool = False,
        owner_gmid: Optional[str] = None,
        owner_name: Optional[str] = None,
        **kwargs,
    ) -> Environment:
        """Create a shared environment where multiple Minds can interact."""
        env = self.create_environment(
            env_id=env_id,
            name=name,
            env_type=env_type,
            description=description,
            is_shared=True,
            is_public=is_public,
            owner_id=owner_gmid,
            owner_name=owner_name,
            **kwargs,
        )
        return env

    def get_public_environments(self) -> list[Environment]:
        """Get all public environments that any Mind can visit."""
        return [e for e in self.environments.values() if e.is_public]

    def get_environments_with_visitors(self) -> list[Environment]:
        """Get environments that currently have Minds in them."""
        return [e for e in self.environments.values() if e.current_inhabitants]

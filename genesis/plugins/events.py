"""Events Plugin - Adds life events tracking."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.events import EventManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class EventsPlugin(Plugin):
    """Adds life events tracking."""

    def __init__(self, **config):
        super().__init__(**config)
        self.events: Optional[EventManager] = None

    def get_name(self) -> str:
        return "events"

    def get_version(self) -> str:
        return "1.0.0"

    def on_init(self, mind: "Mind") -> None:
        self.events = EventManager()
        mind.events = self.events

    def extend_system_prompt(self, mind: "Mind") -> str:
        if not self.events:
            return ""
        journey = self.events.describe_life_journey()
        if journey and len(journey) > 20:  # Only if substantial
            return f"LIFE JOURNEY:\n{journey[:500]}"  # Truncate if too long
        return ""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        if not self.events:
            return {}
        return {"events": self.events.model_dump(mode='json')}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        if "events" in data:
            self.events = EventManager(**data["events"])
            mind.events = self.events

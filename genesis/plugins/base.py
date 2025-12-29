"""Base Plugin class for Genesis Mind extensions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class Plugin(ABC):
    """
    Base class for all Genesis Mind plugins.

    Plugins extend Mind functionality in a modular way:
    - Lifecycle hooks (init, birth, save, load, terminate)
    - System prompt extension
    - Thought processing hooks
    - Configurable and composable

    Example:
        class MyPlugin(Plugin):
            def get_name(self) -> str:
                return "my_plugin"

            def get_version(self) -> str:
                return "1.0.0"

            def on_init(self, mind: Mind) -> None:
                mind.my_feature = MyFeature()

            def extend_system_prompt(self, mind: Mind) -> str:
                return "You have feature X enabled."
    """

    def __init__(self, **config):
        """
        Initialize plugin with configuration.

        Args:
            **config: Plugin-specific configuration options
        """
        self.config = config
        self.enabled = True

    @abstractmethod
    def get_name(self) -> str:
        """
        Return plugin name (unique identifier).

        Returns:
            Plugin name (lowercase, underscores)
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """
        Return plugin version (semantic versioning).

        Returns:
            Version string (e.g., "1.0.0")
        """
        pass

    def get_description(self) -> str:
        """
        Return plugin description.

        Returns:
            Human-readable description
        """
        return f"{self.get_name()} plugin"

    def on_init(self, mind: "Mind") -> None:
        """
        Called when Mind is initialized.

        Use this to:
        - Attach plugin systems to Mind
        - Initialize plugin state
        - Register callbacks
        - Set up dependencies

        Args:
            mind: The Mind instance being initialized
        """
        pass

    def on_birth(self, mind: "Mind") -> None:
        """
        Called when Mind is born (after __init__).

        Use this to:
        - Create initial plugin data
        - Log birth events
        - Set up defaults specific to birth
        - Add birth memories

        Args:
            mind: The newly born Mind instance
        """
        pass

    def on_think_start(self, mind: "Mind", prompt: str) -> Optional[str]:
        """
        Called before Mind processes a thought.

        Use this to:
        - Modify or augment the prompt
        - Add context
        - Inject instructions

        Args:
            mind: The Mind instance
            prompt: The original user prompt

        Returns:
            - None: No modification (use original prompt)
            - str: Modified prompt to use instead
        """
        return None

    def on_think_end(self, mind: "Mind", response: str) -> Optional[str]:
        """
        Called after Mind generates a response.

        Use this to:
        - Modify the response
        - Add post-processing
        - Log interactions

        Args:
            mind: The Mind instance
            response: The generated response

        Returns:
            - None: No modification (use original response)
            - str: Modified response to return instead
        """
        return None

    def extend_system_prompt(self, mind: "Mind") -> str:
        """
        Add content to system prompt if this plugin is enabled.

        Use this to:
        - Add plugin-specific context
        - Inform Mind about capabilities
        - Set behavioral guidelines

        Args:
            mind: The Mind instance

        Returns:
            - Empty string: No addition to system prompt
            - String: Content to append to system prompt
        """
        return ""

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """
        Serialize plugin state for persistence.

        Use this to:
        - Save plugin data
        - Serialize internal state
        - Prepare for restoration

        Args:
            mind: The Mind instance being saved

        Returns:
            Dict with plugin data to save (JSON-serializable)
        """
        return {}

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """
        Deserialize plugin state from saved data.

        Use this to:
        - Restore plugin state
        - Reconstruct internal data
        - Reattach to Mind

        Args:
            mind: The Mind instance being loaded
            data: Plugin data from save (from on_save)
        """
        pass

    def on_terminate(self, mind: "Mind") -> None:
        """
        Called when Mind is terminated.

        Use this to:
        - Clean up resources
        - Log final state
        - Perform cleanup

        Args:
            mind: The Mind instance being terminated
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Get plugin status and health information.

        Returns:
            Dict with status information
        """
        return {
            "name": self.get_name(),
            "version": self.get_version(),
            "description": self.get_description(),
            "enabled": self.enabled,
            "config": self.config,
        }

    def enable(self) -> None:
        """Enable this plugin."""
        self.enabled = True

    def disable(self) -> None:
        """Disable this plugin (stops hooks from running)."""
        self.enabled = False

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.get_name()}', version='{self.get_version()}')>"

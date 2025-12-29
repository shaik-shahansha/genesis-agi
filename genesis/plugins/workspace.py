"""Workspace Plugin - Adds personal file system for Minds."""

from typing import Dict, Any, TYPE_CHECKING
from genesis.plugins.base import Plugin
from genesis.core.workspace import WorkspaceManager

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class WorkspacePlugin(Plugin):
    """
    Adds personal file workspace for Mind creations.

    Features:
    - Mind-specific directory (by GMID)
    - Create, read, update, delete files
    - File metadata (type, tags, description)
    - File sharing with other Minds
    - Workspace statistics

    Workspace gives Minds a PERSISTENT HOME for their creations.

    Example:
        config = MindConfig()
        config.add_plugin(WorkspacePlugin())
        mind = Mind.birth("Creator", config=config)

        # Create file
        file = mind.workspace.create_file(
            filename="notes.txt",
            content="My thoughts...",
            file_type="text"
        )

        # Read file
        content = mind.workspace.read_file(file.file_id)
    """

    def __init__(self, **config):
        """Initialize workspace plugin."""
        super().__init__(**config)
        self.workspace: Optional[WorkspaceManager] = None

    def get_name(self) -> str:
        return "workspace"

    def get_version(self) -> str:
        return "1.0.0"

    def get_description(self) -> str:
        return "Personal file workspace"

    def on_init(self, mind: "Mind") -> None:
        """Attach workspace manager to Mind."""
        self.workspace = WorkspaceManager(mind_gmid=mind.identity.gmid)
        mind.workspace = self.workspace

    def extend_system_prompt(self, mind: "Mind") -> str:
        """Add workspace context to system prompt."""
        if not self.workspace:
            return ""

        stats = self.workspace.get_workspace_stats()

        sections = [
            "PERSONAL WORKSPACE:",
            f"- Files: {stats['total_files']}",
            f"- Size: {stats['total_size_mb']:.2f} MB",
            f"- Workspace path: {self.workspace.workspace_path}",
            "",
            "You can create, store, and organize files in your workspace.",
            "Your creations persist across sessions.",
        ]

        return "\n".join(sections)

    def on_save(self, mind: "Mind") -> Dict[str, Any]:
        """Save workspace state."""
        if not self.workspace:
            return {}

        return {
            "workspace": self.workspace.to_dict(),
        }

    def on_load(self, mind: "Mind", data: Dict[str, Any]) -> None:
        """Restore workspace state."""
        if "workspace" in data:
            self.workspace = WorkspaceManager.from_dict(data["workspace"])
            mind.workspace = self.workspace

    def get_status(self) -> Dict[str, Any]:
        """Get workspace status."""
        status = super().get_status()

        if self.workspace:
            stats = self.workspace.get_workspace_stats()
            status.update(stats)

        return status

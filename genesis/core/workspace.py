"""Workspace file management for Genesis Minds."""

import secrets
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MindFile(BaseModel):
    """A file owned by a Mind in their workspace."""

    file_id: str = Field(default_factory=lambda: f"FILE-{secrets.token_hex(6).upper()}")
    owner_gmid: str

    # File details
    filename: str
    filepath: str  # Relative to Mind's workspace
    file_type: str  # text, code, data, image, etc.
    size_bytes: int = 0

    # Access control
    is_private: bool = True
    shared_with: List[str] = Field(default_factory=list)  # GMIDs

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0

    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    def can_access(self, gmid: str) -> bool:
        """Check if a Mind can access this file."""
        if gmid == self.owner_gmid:
            return True
        if not self.is_private:
            return True
        return gmid in self.shared_with

    def share_with(self, gmid: str) -> None:
        """Share file with another Mind."""
        if gmid not in self.shared_with:
            self.shared_with.append(gmid)

    def unshare_with(self, gmid: str) -> None:
        """Unshare file with another Mind."""
        if gmid in self.shared_with:
            self.shared_with.remove(gmid)


class WorkspaceManager:
    """
    Manager for a Mind's personal workspace and files.

    Each Mind has a workspace directory where they can store files,
    data, and creations. This provides persistence between sessions.
    """

    def __init__(self, mind_gmid: str, workspace_root: Optional[Path] = None):
        """
        Initialize workspace manager.

        Args:
            mind_gmid: The Mind's GMID
            workspace_root: Root directory for workspaces (defaults to ~/.genesis/workspaces)
        """
        self.mind_gmid = mind_gmid

        if workspace_root is None:
            from genesis.config import get_settings
            settings = get_settings()
            workspace_root = settings.genesis_home / "workspaces"

        self.workspace_root = workspace_root
        self.workspace_path = self.workspace_root / mind_gmid

        # File registry
        self.files: dict[str, MindFile] = {}

        # Create workspace directory
        self.workspace_path.mkdir(parents=True, exist_ok=True)

    def create_file(
        self,
        filename: str,
        content: str = "",
        file_type: str = "text",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_private: bool = True
    ) -> MindFile:
        """
        Create a new file in the workspace.

        Args:
            filename: Name of the file
            content: File content
            file_type: Type of file
            description: Description of the file
            tags: Tags for categorization
            is_private: Whether file is private

        Returns:
            The created MindFile record
        """
        filepath = self.workspace_path / filename

        # Write content to file
        filepath.write_text(content)
        size_bytes = len(content.encode('utf-8'))

        # Create file record
        mind_file = MindFile(
            owner_gmid=self.mind_gmid,
            filename=filename,
            filepath=str(filepath.relative_to(self.workspace_path)),
            file_type=file_type,
            size_bytes=size_bytes,
            is_private=is_private,
            description=description,
            tags=tags or []
        )

        self.files[mind_file.file_id] = mind_file
        return mind_file

    def read_file(self, file_id: str, requesting_gmid: Optional[str] = None) -> str:
        """
        Read a file's content.

        Args:
            file_id: File ID
            requesting_gmid: GMID of the Mind requesting access

        Returns:
            File content

        Raises:
            ValueError: If file not found or access denied
        """
        mind_file = self.files.get(file_id)
        if not mind_file:
            raise ValueError(f"File {file_id} not found")

        # Check access
        if requesting_gmid and not mind_file.can_access(requesting_gmid):
            raise ValueError(f"Access denied to file {file_id}")

        # Read content
        filepath = self.workspace_path / mind_file.filepath
        content = filepath.read_text()

        # Update access count
        mind_file.access_count += 1

        return content

    def update_file(self, file_id: str, content: str) -> MindFile:
        """Update a file's content."""
        mind_file = self.files.get(file_id)
        if not mind_file:
            raise ValueError(f"File {file_id} not found")

        filepath = self.workspace_path / mind_file.filepath
        filepath.write_text(content)

        mind_file.size_bytes = len(content.encode('utf-8'))
        mind_file.modified_at = datetime.now()

        return mind_file

    def delete_file(self, file_id: str) -> None:
        """Delete a file."""
        mind_file = self.files.get(file_id)
        if not mind_file:
            raise ValueError(f"File {file_id} not found")

        filepath = self.workspace_path / mind_file.filepath
        if filepath.exists():
            filepath.unlink()

        del self.files[file_id]

    def list_files(
        self,
        file_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[MindFile]:
        """List files with optional filtering."""
        files = list(self.files.values())

        if file_type:
            files = [f for f in files if f.file_type == file_type]

        if tags:
            files = [f for f in files if any(tag in f.tags for tag in tags)]

        return files

    def get_workspace_stats(self) -> dict:
        """Get workspace statistics."""
        total_size = sum(f.size_bytes for f in self.files.values())
        file_types = {}
        for f in self.files.values():
            file_types[f.file_type] = file_types.get(f.file_type, 0) + 1

        return {
            "total_files": len(self.files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "private_files": len([f for f in self.files.values() if f.is_private]),
            "shared_files": len([f for f in self.files.values() if not f.is_private]),
            "workspace_path": str(self.workspace_path),
        }

    def share_file(self, file_id: str, with_gmid: str) -> MindFile:
        """Share a file with another Mind."""
        mind_file = self.files.get(file_id)
        if not mind_file:
            raise ValueError(f"File {file_id} not found")

        mind_file.share_with(with_gmid)
        return mind_file

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "mind_gmid": self.mind_gmid,
            "workspace_path": str(self.workspace_path),
            "files": {
                file_id: file.model_dump(mode='json')
                for file_id, file in self.files.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict, workspace_root: Optional[Path] = None) -> "WorkspaceManager":
        """Deserialize from dictionary."""
        manager = cls(
            mind_gmid=data["mind_gmid"],
            workspace_root=workspace_root
        )

        manager.files = {
            file_id: MindFile(**file_data)
            for file_id, file_data in data.get("files", {}).items()
        }

        return manager

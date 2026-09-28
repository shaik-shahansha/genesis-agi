"""SEC-02 — path traversal, arbitrary file write, and arbitrary file read.

Three defects are covered:

(a) ``WorkspaceManager`` joined an unvalidated ``filename`` onto the workspace
    root, so ``create_file``/``read_file``/``update_file``/``delete_file`` could
    reach outside the workspace. ``pathlib`` treats an absolute path as a
    replacement for the base, and ``relative_to`` does not normalise, so
    ``"../../x"`` was stored verbatim and re-resolved on every later access.

(b) The workspace upload endpoint joined ``workspace_path / filepath`` directly
    and read the whole upload into memory with no size limit.

(c) ``GET /minds/{id}/artifacts/download`` had **no authentication** and used a
    string-prefix containment check (``str(path).startswith(str(dir))``), which
    ``/data-evil`` vs ``/data`` defeats. ``Path.cwd()`` was also allow-listed,
    which made arbitrary file read reachable.

See docs/v3/SECURITY_BASELINE.md SEC-02/SEC-14 and docs/v3/THREAT_MODEL.md T-01.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from genesis.core.paths import (
    UnsafePathError,
    ensure_within,
    safe_child,
    safe_filename,
)
from genesis.core.workspace import WorkspaceManager

# ---------------------------------------------------------------------------
# safe_filename
# ---------------------------------------------------------------------------

ESCAPE_ATTEMPTS = [
    "../etc/passwd",
    "../../etc/passwd",
    "..",
    ".",
    "sub/dir/file.txt",
    r"sub\dir\file.txt",
    r"..\..\windows\system32\config",
    "/etc/passwd",
    "/tmp/pwned",
    r"C:\Windows\Temp\pwned",
    "C:/Windows/Temp/pwned",
    r"\\server\share\file",
    "",
    "   ",
    "nul\x00byte",
    "line\nbreak",
    "tab\tname",
]


@pytest.mark.parametrize("name", ESCAPE_ATTEMPTS)
def test_safe_filename_rejects_escapes(name):
    with pytest.raises(UnsafePathError):
        safe_filename(name)


@pytest.mark.parametrize(
    "name",
    [
        "notes.txt",
        "report-2026.pdf",
        "data (1).csv",
        "résumé.md",
        "a" * 200,
        ".hidden",
        "file.tar.gz",
    ],
)
def test_safe_filename_accepts_legitimate_names(name):
    assert safe_filename(name) == name


def test_safe_filename_rejects_windows_device_names():
    for name in ("CON", "con.txt", "PRN", "AUX", "NUL", "COM1", "lpt9.log"):
        with pytest.raises(UnsafePathError):
            safe_filename(name)


def test_safe_filename_rejects_overlong_names():
    with pytest.raises(UnsafePathError):
        safe_filename("a" * 256)


def test_safe_filename_rejects_non_strings():
    with pytest.raises(UnsafePathError):
        safe_filename(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ensure_within
# ---------------------------------------------------------------------------


def test_ensure_within_allows_descendants(tmp_path):
    target = ensure_within(tmp_path / "a" / "b.txt", tmp_path)
    assert target.is_relative_to(tmp_path.resolve())


def test_ensure_within_rejects_parent_escape(tmp_path):
    with pytest.raises(UnsafePathError):
        ensure_within(tmp_path / ".." / "outside.txt", tmp_path)


def test_ensure_within_allows_the_base_itself(tmp_path):
    assert ensure_within(tmp_path, tmp_path) == tmp_path.resolve()


def test_ensure_within_does_not_use_prefix_matching(tmp_path):
    """The classic bug: '/data-evil'.startswith('/data') is True."""
    base = tmp_path / "data"
    sibling = tmp_path / "data-evil"
    base.mkdir()
    sibling.mkdir()

    with pytest.raises(UnsafePathError):
        ensure_within(sibling / "secret.txt", base)


def test_ensure_within_rejects_symlink_pointing_outside(tmp_path):
    base = tmp_path / "workspace"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    link = base / "link.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted in this environment")

    with pytest.raises(UnsafePathError):
        ensure_within(link, base)


def test_safe_child_combines_both_checks(tmp_path):
    assert safe_child(tmp_path, "ok.txt") == (tmp_path / "ok.txt").resolve()
    with pytest.raises(UnsafePathError):
        safe_child(tmp_path, "../escape.txt")


# ---------------------------------------------------------------------------
# WorkspaceManager — (a)
# ---------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path):
    return WorkspaceManager("GMD-TEST-0000-0001", workspace_root=tmp_path / "workspaces")


def test_create_file_writes_inside_workspace(workspace):
    record = workspace.create_file("notes.txt", content="hello")

    written = workspace.workspace_path / record.filepath
    assert written.read_text(encoding="utf-8") == "hello"
    assert written.resolve().is_relative_to(workspace.workspace_path.resolve())


def test_create_file_rejects_traversal(workspace, tmp_path):
    """Regression: this previously wrote outside the workspace."""
    with pytest.raises(UnsafePathError):
        workspace.create_file("../../../pwned.txt", content="pwned")

    assert not (tmp_path / "pwned.txt").exists()
    assert not (tmp_path.parent / "pwned.txt").exists()


def test_create_file_rejects_absolute_path(workspace, tmp_path):
    target = tmp_path / "absolute-pwned.txt"
    with pytest.raises(UnsafePathError):
        workspace.create_file(str(target), content="pwned")
    assert not target.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="drive-absolute is Windows-specific")
def test_create_file_rejects_windows_drive_path(workspace):
    with pytest.raises(UnsafePathError):
        workspace.create_file(r"C:\Windows\Temp\pwned.txt", content="pwned")


def test_delete_file_cannot_remove_outside_the_workspace(workspace, tmp_path):
    """delete_file previously unlinked whatever the stored path resolved to."""
    victim = tmp_path / "victim.txt"
    victim.write_text("important", encoding="utf-8")

    workspace.files["FILE-FAKE"] = workspace.files.get("FILE-FAKE")  # no-op
    from genesis.core.workspace import MindFile

    workspace.files["FILE-EVIL"] = MindFile(
        file_id="FILE-EVIL",
        owner_gmid=workspace.mind_gmid,
        filename="victim.txt",
        filepath="../victim.txt",  # as if persisted by the old buggy code
        file_type="text",
    )

    with pytest.raises(UnsafePathError):
        workspace.delete_file("FILE-EVIL")

    assert victim.exists(), "file outside the workspace must not be deleted"


def test_read_file_cannot_read_outside_the_workspace(workspace, tmp_path):
    victim = tmp_path / "secret.txt"
    victim.write_text("classified", encoding="utf-8")

    from genesis.core.workspace import MindFile

    workspace.files["FILE-EVIL"] = MindFile(
        file_id="FILE-EVIL",
        owner_gmid=workspace.mind_gmid,
        filename="secret.txt",
        filepath="../secret.txt",
        file_type="text",
    )

    with pytest.raises(UnsafePathError):
        workspace.read_file("FILE-EVIL")


def test_binary_upload_is_written_inside_the_workspace(workspace):
    payload = b"\x89PNG\r\n"
    record = workspace.create_file("image.png", file_type="image", raw_bytes=payload)

    written = workspace.workspace_path / record.filepath
    assert written.read_bytes() == payload
    assert record.size_bytes == len(payload)
    assert written.resolve().is_relative_to(workspace.workspace_path.resolve())


def test_binary_upload_rejects_traversal(workspace, tmp_path):
    with pytest.raises(UnsafePathError):
        workspace.create_file("../escape.png", file_type="image", raw_bytes=b"x")
    assert not (tmp_path / "escape.png").exists()


def test_get_path_validates_and_returns_the_file(workspace):
    record = workspace.create_file("a.txt", content="x")
    assert workspace.get_path(record.file_id).name == "a.txt"


def test_get_path_rejects_unknown_file_id(workspace):
    with pytest.raises(ValueError):
        workspace.get_path("FILE-DOES-NOT-EXIST")


def test_from_dict_rejects_hostile_stored_paths(tmp_path):
    """A registry loaded from disk is untrusted input too."""
    manager = WorkspaceManager.from_dict(
        {
            "mind_gmid": "GMD-TEST-0000-0002",
            "files": {
                "FILE-EVIL": {
                    "file_id": "FILE-EVIL",
                    "owner_gmid": "GMD-TEST-0000-0002",
                    "filename": "passwd",
                    "filepath": "../../../../etc/passwd",
                    "file_type": "text",
                }
            },
        },
        workspace_root=tmp_path / "workspaces",
    )

    with pytest.raises(UnsafePathError):
        manager.read_file("FILE-EVIL")

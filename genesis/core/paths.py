"""Path safety helpers.

Centralises filesystem-name validation so that no module has to re-implement
containment checks.

Why this exists: user- and model-supplied names were previously joined directly
onto a base directory (``base / name``). ``pathlib`` semantics make that unsafe:

* ``base / "/etc/cron.d/x"``  → ``/etc/cron.d/x`` (absolute paths replace the base)
* ``base / "C:\\\\Windows\\\\x"``  → ``C:\\Windows\\x`` (drive-absolute replaces the base)
* ``base / "../../x"``        → escapes upward
* and ``relative_to()`` does **not** normalise, so ``"../../x"`` was stored verbatim

See docs/v3/SECURITY_BASELINE.md SEC-02 and docs/v3/THREAT_MODEL.md T-01.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Names that Windows resolves to devices; harmless on Linux but rejected for
# consistency across the dev (Windows) and deploy (Linux) environments.
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Control characters (including NUL) are never valid in a filename here.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")

# Any path separator or traversal token.
_SEPARATORS = ("/", "\\")

DEFAULT_MAX_FILENAME_LENGTH = 255


class UnsafePathError(ValueError):
    """Raised when a name or path would escape its intended directory."""


def safe_filename(name: str, *, max_length: int = DEFAULT_MAX_FILENAME_LENGTH) -> str:
    """Validate a single filename and return it unchanged.

    The workspace uses flat filenames: a name is a *name*, not a path. Anything
    containing a separator, a traversal token, an absolute path, a Windows drive
    letter, a control character, or a device name is rejected.

    Raises:
        UnsafePathError: if the name is not a safe bare filename.
    """
    if not isinstance(name, str):
        raise UnsafePathError("Filename must be a string")

    # Strip only surrounding whitespace; never silently "clean" a hostile name,
    # because a name that needed cleaning was not a legitimate filename.
    candidate = name.strip()

    if not candidate:
        raise UnsafePathError("Filename must not be empty")

    if candidate in (".", ".."):
        raise UnsafePathError(f"Filename '{candidate}' is not allowed")

    if any(sep in candidate for sep in _SEPARATORS):
        raise UnsafePathError(
            f"Filename '{name}' must not contain a path separator; "
            "workspace files are stored by bare name"
        )

    if _CONTROL_CHARS.search(candidate):
        raise UnsafePathError(f"Filename '{name}' contains control characters")

    # Absolute POSIX path.
    if candidate.startswith("/"):
        raise UnsafePathError(f"Filename '{name}' must not be an absolute path")

    # Windows drive-absolute (C:\..., C:/..., or a bare drive prefix).
    if re.match(r"^[A-Za-z]:", candidate):
        raise UnsafePathError(f"Filename '{name}' must not contain a drive letter")

    # UNC path (\\server\share).
    if candidate.startswith("\\\\"):
        raise UnsafePathError(f"Filename '{name}' must not be a UNC path")

    stem = candidate.split(".", 1)[0].upper()
    if stem in _WINDOWS_RESERVED:
        raise UnsafePathError(f"Filename '{name}' is a reserved device name")

    if len(candidate) > max_length:
        raise UnsafePathError(
            f"Filename is too long ({len(candidate)} > {max_length} characters)"
        )

    # Normalise Unicode so that visually-confusable lookalikes from different
    # input sources map to one canonical form rather than two distinct files.
    normalised = unicodedata.normalize("NFC", candidate)
    if normalised != candidate:
        # Re-validate: normalisation must not have introduced a separator.
        if any(sep in normalised for sep in _SEPARATORS):
            raise UnsafePathError(f"Filename '{name}' is not allowed")
        return normalised

    return candidate


def ensure_within(path: Path, base: Path) -> Path:
    """Return ``path`` only if it resolves inside ``base`` (inclusive).

    ``base`` is treated as a directory: the result must be ``base`` itself or a
    descendant. Symlinks are followed by ``resolve()``, so a symlink pointing
    outside the base is rejected too. Works for paths that do not exist yet.

    Use ``str.startswith`` for nothing: ``"/data-evil".startswith("/data")`` is
    True, which is the classic containment-bypass bug.

    Raises:
        UnsafePathError: if ``path`` escapes ``base``.
    """
    base_resolved = Path(base).resolve()
    target = path if path.is_absolute() else base_resolved / path
    target_resolved = target.resolve()

    if target_resolved == base_resolved:
        return target_resolved

    if not target_resolved.is_relative_to(base_resolved):
        raise UnsafePathError(
            f"Path '{path}' resolves outside the permitted directory '{base}'"
        )

    return target_resolved


def safe_child(base: Path, name: str) -> Path:
    """Combine a validated filename with a base directory, asserting containment.

    Defence in depth: ``safe_filename`` rejects traversals, and
    ``ensure_within`` verifies the resolved result, so a future change to either
    function cannot silently reintroduce an escape.
    """
    return ensure_within(Path(base) / safe_filename(name), base)

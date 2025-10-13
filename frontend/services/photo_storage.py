from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


DEFAULT_SESSIONS_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"
_SANITIZE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_component(value: str) -> str:
    """Return a filesystem-friendly version of *value*."""
    cleaned = _SANITIZE_PATTERN.sub("_", value)
    cleaned = cleaned.strip("._")
    return cleaned or "session"


def ensure_sessions_root(base_path: str | Path | None = None) -> Path:
    """
    Create (if needed) and return the root directory that stores photo sessions.

    When *base_path* is omitted we fall back to ``frontend/data/sessions``.
    """
    root = Path(base_path) if base_path else DEFAULT_SESSIONS_DIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def build_session_directory_name(session_id: int, session_start: str | None = None) -> str:
    """
    Format the directory name used to store photos for a session.

    The name looks like ``session_00001`` with an optional suffix built from
    *session_start* (colons and spaces replaced with safe characters).
    """
    base = f"session_{session_id:05d}"
    if session_start:
        suffix = _sanitize_component(session_start.replace(":", "-").replace(" ", "_"))
        if suffix:
            return f"{base}_{suffix}"
    return base


def ensure_session_directory(
    root: str | Path | None,
    session_id: int,
    session_start: str | None = None,
) -> Path:
    """
    Materialize and return the directory for *session_id* under *root*.

    The directory name is produced by :func:`build_session_directory_name`.
    """
    root_path = ensure_sessions_root(root)
    directory = root_path / build_session_directory_name(session_id, session_start)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def pose_filename(pose_index: int, extension: str = "png") -> str:
    """Return the standardized filename for a pose capture."""
    return f"pose_{pose_index:02d}.{extension.lstrip('.')}"


def pose_capture_path(
    session_dir: str | Path,
    pose_index: int,
    extension: str = "png",
) -> Path:
    """
    Return the full path for the photo belonging to *pose_index*.

    The path is not created here; callers should handle writing the file.
    """
    return Path(session_dir) / pose_filename(pose_index, extension)


def list_pose_files(session_dir: str | Path) -> Iterable[Path]:
    """Yield pose capture files stored inside *session_dir*."""
    directory = Path(session_dir)
    if not directory.exists():
        return []

    return sorted(directory.glob("pose_*.png"))

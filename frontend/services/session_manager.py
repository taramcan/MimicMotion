from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import db
from .photo_storage import (
    ensure_session_directory,
    ensure_sessions_root,
    pose_capture_path,
)
from kivy.graphics.texture import Texture


MAX_POSES = 9


@dataclass
class SessionState:
    session_id: int
    session_start: str
    current_pose: int
    user_id: int
    notes: str | None = None
    session_dir: Path | None = None
    completed: bool = False


class SessionManager:
    """Orchestrates photo capture sessions for a single user."""

    def __init__(
        self,
        db_path: str | Path,
        user_id: int,
        root_dir: str | Path | None = None,
        on_pose_complete: Optional[Callable[[SessionState, int, Path], None]] = None,
        on_session_complete: Optional[Callable[[SessionState], None]] = None,
    ) -> None:
        self._db_path = db_path
        self._user_id = user_id
        self._root_dir = ensure_sessions_root(root_dir)
        self._on_pose_complete = on_pose_complete
        self._on_session_complete = on_session_complete
        self._state: SessionState | None = None

    @property
    def state(self) -> SessionState | None:
        return self._state

    def start_session(self, notes: str | None = None) -> SessionState:
        """Create a new session and prepare its storage directory."""
        session_id, session_start = db.create_session(self._db_path, self._user_id, notes)
        session_dir = ensure_session_directory(
            self._root_dir, session_id, session_start
        )

        self._state = SessionState(
            session_id=session_id,
            session_start=session_start,
            current_pose=1,
            user_id=self._user_id,
            notes=notes,
            session_dir=session_dir,
        )
        return self._state

    def resume_session(self, session_id: int) -> SessionState:
        """Load session progress based on stored pose photos."""
        # Determine last completed pose to resume properly.
        rows = db.fetch_pose_photos_for_session(self._db_path, session_id)
        last_pose = max((pose for pose, *_ in rows), default=0)

        conn_state = db._connect(self._db_path)
        with conn_state:
            session_row = conn_state.execute(
                "SELECT session_start, user_id, notes, is_complete FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

        if not session_row:
            raise ValueError(f"Session {session_id} does not exist")

        session_start, user_id, notes, is_complete = session_row
        if user_id != self._user_id:
            raise ValueError("Session user mismatch")

        session_dir = ensure_session_directory(self._root_dir, session_id, session_start)

        current_pose = last_pose + 1 if last_pose < MAX_POSES else MAX_POSES

        self._state = SessionState(
            session_id=session_id,
            session_start=session_start,
            current_pose=current_pose,
            user_id=user_id,
            notes=notes,
            session_dir=session_dir,
            completed=bool(is_complete),
        )
        return self._state

    def _assert_session_active(self) -> SessionState:
        if not self._state:
            raise RuntimeError("No active session. Call start_session() first.")
        return self._state

    def capture_pose(self, image_bytes: bytes, pose_index: int | None = None) -> Path:
        """
        Persist the captured image and update database state.

        Returns the filesystem path for the stored image.
        """
        state = self._assert_session_active()

        pose = pose_index or state.current_pose
        if pose < 1 or pose > MAX_POSES:
            raise ValueError("pose_index must be between 1 and 9")

        session_dir = state.session_dir or ensure_session_directory(
            self._root_dir, state.session_id, state.session_start
        )

        file_path = pose_capture_path(session_dir, pose)
        file_path.write_bytes(image_bytes)

        return self._record_pose(state, pose, file_path, pose_index is None)

    def capture_pose_texture(
        self,
        texture: Texture,
        pose_index: int | None = None,
        extension: str = "png",
    ) -> Path:
        state = self._assert_session_active()

        pose = pose_index or state.current_pose
        if pose < 1 or pose > MAX_POSES:
            raise ValueError("pose_index must be between 1 and 9")

        session_dir = state.session_dir or ensure_session_directory(
            self._root_dir, state.session_id, state.session_start
        )

        file_path = pose_capture_path(session_dir, pose, extension=extension)
        capture_texture = texture.get_region(0, 0, texture.width, texture.height)
        capture_texture.save(str(file_path), flipped=False)

        return self._record_pose(state, pose, file_path, pose_index is None)

    def finish_session(self) -> None:
        state = self._assert_session_active()
        if state.completed:
            return

        db.mark_session_complete(self._db_path, state.session_id)
        state.completed = True
        if self._on_session_complete:
            self._on_session_complete(state)

    def _record_pose(
        self,
        state: SessionState,
        pose: int,
        file_path: Path,
        auto_advance: bool,
        symmetry_score: float | None = None,
    ) -> Path:
        db.upsert_pose_photo(
            self._db_path,
            session_id=state.session_id,
            pose_index=pose,
            photo_path=str(file_path),
            symmetry_score=symmetry_score,
        )

        if self._on_pose_complete:
            self._on_pose_complete(state, pose, file_path)

        if auto_advance and state.current_pose < MAX_POSES:
            state.current_pose += 1

        if pose >= MAX_POSES:
            self.finish_session()

        return file_path

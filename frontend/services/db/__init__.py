from __future__ import annotations

import sqlite3
from pathlib import Path

from .migrations import apply_migrations


def _normalize_path(db_path: str | Path) -> str:
    """Return the database path as a string, resolving Path inputs."""
    return str(Path(db_path))

def _connect(db_path: str | Path) -> sqlite3.Connection:
    """Helper for obtaining a SQLite connection with row factory when needed."""
    return sqlite3.connect(_normalize_path(db_path))


def init_db(db_path: str | Path) -> None:
    """
    Initialize the database and apply pending migrations.

    The schema version is tracked in the metadata table so additional
    migrations can be appended over time without modifying this function.
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

        row = conn.execute(
            "SELECT value FROM metadata WHERE key = 'schema_version'"
        ).fetchone()
        current_version = int(row[0]) if row else 0

        final_version = apply_migrations(conn, current_version)

        if final_version != current_version or row is None:
            conn.execute(
                """
                INSERT OR REPLACE INTO metadata (key, value)
                VALUES ('schema_version', ?)
                """,
                (str(final_version),),
            )


def fetch_users(db_path: str | Path) -> list[tuple[int, str, str | None]]:
    """Return all users ordered by insertion."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                email
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()

    return rows


def fetch_single_user(db_path: str | Path) -> tuple[int, str, str | None] | None:
    """Return the first (and only) user row or None if the table is empty."""
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                id,
                username,
                email
            FROM users
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

    return row


def upsert_single_user(db_path: str | Path, username: str, email: str) -> None:
    """
    Create or update the single user row.

    We pin the primary key to 1 so repeated saves simply update the same row.
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO users (id, username, email)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                email = excluded.email
            """,
            (username, email),
        )
        conn.commit()


def fetch_latest_symmetry_scores(
    db_path: str | Path, user_id: int
) -> tuple[str | None, list[tuple[int, float | None]]]:
    """
    Return the most recent session date and its symmetry scores for the user.

    Scores are ordered by photo index. If the user has no sessions, an empty
    list is returned alongside None for the session date.
    """
    try:
        with _connect(db_path) as conn:
            session_row = conn.execute(
                """
                SELECT id, session_date
                FROM photo_sessions
                WHERE user_id = ?
                ORDER BY COALESCE(datetime(session_date), session_date) DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            if not session_row:
                return None, []

            session_id, session_date = session_row

            score_rows = conn.execute(
                """
                SELECT photo_index, symmetry_score
                FROM photo_symmetry_scores
                WHERE session_id = ?
                ORDER BY photo_index ASC
                """,
                (session_id,),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        # When legacy databases are missing the new tables, behave as if no data exists.
        if "no such table" in str(exc):
            return None, []
        raise

    return session_date, score_rows


def create_session(
    db_path: str | Path,
    user_id: int,
    notes: str | None = None,
) -> tuple[int, str]:
    """Insert a new session row and return its id plus start timestamp."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions (user_id, session_start, notes)
            VALUES (
                ?,
                datetime('now'),
                ?
            )
            """,
            (user_id, notes),
        )
        session_id = cursor.lastrowid
        session_row = conn.execute(
            """
            SELECT session_start
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

    return session_id, session_row[0] if session_row else ""


def upsert_pose_photo(
    db_path: str | Path,
    session_id: int,
    pose_index: int,
    photo_path: str,
    symmetry_score: float | None = None,
) -> None:
    """
    Insert or replace a pose photo entry.

    Used during capture to attach the saved image path to the session.
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO pose_photos (session_id, pose_index, photo_path, symmetry_score)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id, pose_index) DO UPDATE SET
                photo_path = excluded.photo_path,
                symmetry_score = excluded.symmetry_score,
                captured_at = datetime('now')
            """,
            (session_id, pose_index, photo_path, symmetry_score),
        )
        conn.commit()


def fetch_pose_photos_for_session(
    db_path: str | Path, session_id: int
) -> list[tuple[int, str, float | None]]:
    """Return pose index, photo path, and symmetry score for a session."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT pose_index, photo_path, symmetry_score
            FROM pose_photos
            WHERE session_id = ?
            ORDER BY pose_index ASC
            """,
            (session_id,),
        ).fetchall()

    return rows


def mark_session_complete(db_path: str | Path, session_id: int) -> None:
    """Flip the completion flag for *session_id*."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            UPDATE sessions
            SET is_complete = 1
            WHERE id = ?
            """,
            (session_id,),
        )
        conn.commit()

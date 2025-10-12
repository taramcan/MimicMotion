from __future__ import annotations

import sqlite3
from pathlib import Path

from .migrations import apply_migrations


def _normalize_path(db_path: str | Path) -> str:
    """Return the database path as a string, resolving Path inputs."""
    return str(Path(db_path))


def init_db(db_path: str | Path) -> None:
    """
    Initialize the database and apply pending migrations.

    The schema version is tracked in the metadata table so additional
    migrations can be appended over time without modifying this function.
    """
    normalized_path = _normalize_path(db_path)

    with sqlite3.connect(normalized_path) as conn:
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


def sign_in(db_path: str | Path, username: str, _password: str) -> bool:
    """
    Placeholder sign-in check. For now we verify that the user exists.
    Extend this once password support is implemented.
    """
    normalized_path = _normalize_path(db_path)

    with sqlite3.connect(normalized_path) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return False

    # TODO: When password hashing is implemented, compare _password against the stored hash.
    return True


def fetch_users(db_path: str | Path) -> list[tuple[int, str]]:
    """Return all users ordered by insertion."""
    normalized_path = _normalize_path(db_path)

    with sqlite3.connect(normalized_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                last_sign_in,
                minutes_spent_signed_on,
                voluntary_movement_score,
                resting_symmetry_score,
                synk_score,
                composite_score
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()

    return rows

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


def sign_in(db_path: str | Path, username: str, _password: str) -> bool:
    """
    Placeholder sign-in check. For now we verify that the user exists.
    Extend this once password support is implemented.
    """
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return False

    # TODO: When password hashing is implemented, compare _password against the stored hash.
    return True


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

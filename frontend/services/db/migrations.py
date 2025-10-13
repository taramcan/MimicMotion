from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import List, Tuple

Migration = Callable[[sqlite3.Connection], None]
_MIGRATIONS: List[Tuple[int, Migration]] = []


def migration(version: int) -> Callable[[Migration], Migration]:
    """Decorator used to register a migration function."""

    def decorator(func: Migration) -> Migration:
        _MIGRATIONS.append((version, func))
        return func

    return decorator


def apply_migrations(conn: sqlite3.Connection, current_version: int) -> int:
    """Apply all migrations newer than current_version and return the latest."""
    target_version = current_version

    for version, migrate in sorted(_MIGRATIONS, key=lambda item: item[0]):
        if version > target_version:
            migrate(conn)
            target_version = version

    return target_version


# Migration 1: Users table
@migration(1)
def _create_users_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT
        );
        """
    )


# Migration 2: Sessions table
@migration(2)
def _create_sessions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_start TEXT NOT NULL DEFAULT (datetime('now')),
            is_complete BOOLEAN DEFAULT 0,
            notes TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )


# Migration 3: Pose photos table with symmetry scores
@migration(3)
def _create_pose_photos_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pose_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            pose_index INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            symmetry_score REAL NOT NULL,
            captured_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(session_id) REFERENCES sessions(id),
            UNIQUE(session_id, pose_index),
            CHECK(pose_index BETWEEN 1 AND 9)
        );
        """
    )

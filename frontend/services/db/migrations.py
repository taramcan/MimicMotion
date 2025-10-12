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


@migration(1)
def _create_users_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT,
            last_sign_in TEXT,
            minutes_spent_signed_on INTEGER DEFAULT 0,
            voluntary_movement_score REAL,
            resting_symmetry_score REAL,
            synk_score REAL,
            composite_score REAL,
            symmetry_score_neutral REAL,
            symmetry_score_eyes_closed REAL,
            symmetry_score_eyes_shut REAL,
            symmetry_score_surprise REAL,
            symmetry_score_kiss REAL,
            symmetry_score_balloon REAL,
            symmetry_score_smile REAL,
            symmetry_score_wide_smile REAL,
            symmetry_score_grin REAL
        )
        """
    )

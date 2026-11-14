"""SQLite persistence for SkillPath application state.

One row is stored per ``user_id`` and the full ``AppState`` is serialized with
``model_dump_json``. Connections are short-lived and every call is idempotent,
which keeps the module safe for Streamlit reruns.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from contracts.schemas import AppState, UserProfile

DB_PATH = Path(__file__).resolve().parent / "skillpath.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_state (
    user_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _db_path() -> Path:
    """Resolve the database path, allowing tests and deployments to override it."""

    override = os.getenv("SKILLPATH_DB_PATH")
    if override:
        return Path(override).expanduser()
    return DB_PATH


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute(_SCHEMA)
    connection.commit()
    return connection


def _user_key(user_id: str) -> str:
    if not isinstance(user_id, str):
        raise TypeError("user_id must be a string")
    key = user_id.strip()
    if not key:
        raise ValueError("user_id must be a non-empty string")
    return key


def load_state(user_id: str) -> AppState:
    """Load the stored state for a user, returning a fresh state for new users."""

    key = _user_key(user_id)
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT state_json FROM app_state WHERE user_id = ?",
            (key,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return AppState(profile=UserProfile(name=key))

    try:
        return AppState.model_validate_json(row["state_json"])
    except Exception as exc:  # pragma: no cover - defensive guard for corrupt rows
        raise ValueError(f"Stored state for user {key!r} is invalid: {exc}") from exc


def save_state(user_id: str, state: AppState) -> None:
    """Persist the app state for a user, replacing any existing snapshot."""

    key = _user_key(user_id)
    if not isinstance(state, AppState):
        raise TypeError("state must be an AppState instance")

    payload = state.model_dump_json()
    updated_at = datetime.now(timezone.utc).isoformat()

    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO app_state (user_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state_json = excluded.state_json,
                updated_at = excluded.updated_at
            """,
            (key, payload, updated_at),
        )
        connection.commit()
    finally:
        connection.close()

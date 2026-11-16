"""SQLite persistence and authentication for SkillForce application state.

One row is stored per ``user_id`` and the full ``AppState`` is serialized with
``model_dump_json``. User credentials are stored separately for authentication.
Connections are short-lived and every call is idempotent, which keeps the module
safe for Streamlit reruns.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from contracts.schemas import AppState, UserProfile

DB_PATH = Path(__file__).resolve().parent / "skillforce.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_state (
    user_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _db_path() -> Path:
    """Resolve the database path, allowing tests and deployments to override it."""

    override = os.getenv("SKILLFORCE_DB_PATH")
    if override:
        return Path(override).expanduser()
    return DB_PATH


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.executescript(_SCHEMA)
    connection.commit()
    return connection


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return base64.b64encode(digest).decode("ascii")


def user_exists(username: str) -> bool:
    key = _user_key(username)
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (key,),
        ).fetchone()
        return row is not None
    finally:
        connection.close()


def create_user(username: str, password: str) -> None:
    key = _user_key(username)
    if not isinstance(password, str) or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long.")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    created_at = datetime.now(timezone.utc).isoformat()

    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, salt, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, password_hash, salt, created_at),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise ValueError("An account with this username already exists.") from exc
    finally:
        connection.close()


def authenticate_user(username: str, password: str) -> bool:
    key = _user_key(username)
    if not isinstance(password, str) or not password:
        return False

    connection = _connect()
    try:
        row = connection.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?",
            (key,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return False

    expected = row["password_hash"]
    candidate = _hash_password(password, row["salt"])
    return hmac.compare_digest(expected, candidate)


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

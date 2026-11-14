from __future__ import annotations

from contracts.schemas import AppState


def load_state(user_id: str) -> AppState:
    """Load the stored state for a user."""
    raise NotImplementedError("State persistence is scaffolded but not implemented yet.")


def save_state(user_id: str, state: AppState) -> None:
    """Persist the app state for a user."""
    raise NotImplementedError("State persistence is scaffolded but not implemented yet.")

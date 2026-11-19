"""Event dispatch: run UI events through the mentor orchestrator and persist.

Moved from ``ui/events.py`` (which was Streamlit-only) when the frontend
migrated to React. The behaviour is unchanged.
"""

from __future__ import annotations

from agents.mentor import explain_changes, handle_event
from contracts.schemas import AppState
from storage.db import save_state


def dispatch_event(
    state: AppState,
    event: dict,
    user_id: str,
    *,
    previous_state: AppState | None = None,
) -> tuple[AppState, str]:
    """Run an event through the mentor orchestrator and persist its copied state."""
    comparison_state = (
        previous_state if previous_state is not None else state
    ).model_copy(deep=True)
    updated_state = handle_event(state, event)
    if not isinstance(updated_state, AppState):
        raise TypeError("Mentor handle_event must return an AppState")

    explanation = explain_changes(comparison_state, updated_state)
    save_state(user_id, updated_state)
    return updated_state, explanation

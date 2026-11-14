from contracts.schemas import AppState, ScoreResult


def handle_event(state: AppState, event: dict) -> AppState:
    """Handle app events and update state in response to a given event payload.

    Event shapes:
      {"type": "PROFILE_SAVED"}
      {"type": "TARGET_CHANGED", "role": str, "company": str | None}
      {"type": "QUIZ_SUBMITTED", "result": ScoreResult}
      {"type": "CHAT", "message": str}
    """
    raise NotImplementedError


def explain_changes(old: AppState, new: AppState) -> str:
    """Explain how the app state changed between two snapshots."""
    raise NotImplementedError

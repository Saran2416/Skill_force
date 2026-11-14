from __future__ import annotations

from contracts.schemas import AppState
from ui.dashboard import render_dashboard


def render_dashboard_tab(state: AppState) -> None:
    """Render the learner dashboard tab."""
    render_dashboard(state)

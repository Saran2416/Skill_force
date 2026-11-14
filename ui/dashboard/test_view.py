"""Smoke tests that render the dashboard through Streamlit's AppTest."""

from __future__ import annotations


def _render_sample() -> None:
    from contracts.sample import SAMPLE_STATE
    from ui.dashboard.view import render_dashboard

    render_dashboard(SAMPLE_STATE)


def _render_empty() -> None:
    from contracts.schemas import AppState, UserProfile
    from ui.dashboard.view import render_dashboard

    render_dashboard(AppState(profile=UserProfile(name="Empty")))


def test_render_dashboard_sample_has_no_exception() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_function(_render_sample)
    app.run()
    assert not app.exception


def test_render_dashboard_empty_state_has_no_exception() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_function(_render_empty)
    app.run()
    assert not app.exception

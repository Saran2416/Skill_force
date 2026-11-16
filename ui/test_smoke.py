from __future__ import annotations

import os
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture(autouse=True)
def setup_env():
    """Ensure UI_FIXTURE/auth/test env is set for smoke tests."""
    previous_fixture = os.environ.get("UI_FIXTURE")
    previous_mock = os.environ.get("USE_MOCK_LLM")
    previous_auth_user = os.environ.get("SKILLFORCE_AUTH_USER")
    os.environ["UI_FIXTURE"] = "1"
    os.environ["USE_MOCK_LLM"] = "1"
    os.environ["SKILLFORCE_AUTH_USER"] = "demo"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    yield
    if previous_fixture is None:
        os.environ.pop("UI_FIXTURE", None)
    else:
        os.environ["UI_FIXTURE"] = previous_fixture
    if previous_mock is None:
        os.environ.pop("USE_MOCK_LLM", None)
    else:
        os.environ["USE_MOCK_LLM"] = previous_mock
    if previous_auth_user is None:
        os.environ.pop("SKILLFORCE_AUTH_USER", None)
    else:
        os.environ["SKILLFORCE_AUTH_USER"] = previous_auth_user


def test_smoke_app_runs_no_exceptions():
    """Smoke test: app runs with no exceptions under UI_FIXTURE=1."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception, f"App raised an exception: {at.exception}"


def test_all_seven_tabs_render():
    """Verify that all 7 required tabs render with Dashboard FIRST."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    expected_tabs = [
        "Dashboard",
        "Profile",
        "Requirements",
        "Gap",
        "Roadmap",
        "Assessment",
        "Mentor",
    ]
    actual_tabs = [tab.label for tab in at.tabs]
    assert actual_tabs == expected_tabs, f"Expected tabs {expected_tabs}, got {actual_tabs}"


def test_persistent_sidebar_activity_log():
    """Verify that the persistent sidebar displays the live Agent Activity Log."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    # Check sidebar presence and activity log header
    sidebar_subheaders = [s.value for s in at.sidebar.subheader]
    assert any("Agent Activity Log" in s for s in sidebar_subheaders)


def test_dashboard_renders_metrics():
    """Verify Dashboard tab renders core metrics from SAMPLE_STATE."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    metrics = [m.label for m in at.metric]
    assert "Target Role" in metrics
    assert "Target Company" in metrics
    assert "Match %" in metrics


def test_profile_tab_widgets():
    """Verify Profile tab widgets render properly."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    text_inputs = [ti.label for ti in at.text_input]
    assert "Full Name" in text_inputs

    selectboxes = [sb.label for sb in at.selectbox]
    assert "Target Role" in selectboxes
    assert "Target Company" in selectboxes

    text_areas = [ta.label for ta in at.text_area]
    assert "Skills" in text_areas
    assert "Certifications" in text_areas
    assert "Key Projects" in text_areas


def test_requirements_and_gap_render():
    """Verify Requirements and Gap tabs render expected components."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    # Subheaders across tabs
    subheaders = [sh.value for sh in at.subheader]
    assert any("Requirements" in sh for sh in subheaders)
    assert any("Skill Gap" in sh for sh in subheaders)
    assert any("Learning Roadmap" in sh for sh in subheaders)


def test_assessment_tab_simulation_run():
    """Verify Assessment tab has simulate slider and button."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    sliders = [s.label for s in at.slider]
    assert "Simulated Score %" in sliders

    button_labels = [b.label for b in at.button]
    assert "Generate Quiz" in button_labels
    assert "Submit Simulated Score" in button_labels


def test_mentor_tab_chat_input():
    """Verify Mentor tab renders chat input and mentor explanations."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    subheaders = [sh.value for sh in at.subheader]
    assert any("Mentor" in sh for sh in subheaders)
    assert len(at.chat_input) > 0


def test_interactive_profile_save():
    """Verify saving profile updates session state and persists without errors."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    # Find Save Profile button
    save_btn = next((b for b in at.button if b.label == "Save Profile"), None)
    assert save_btn is not None
    save_btn.click().run()
    assert not at.exception


def test_interactive_score_simulation():
    """Verify simulated score submission updates session state without errors."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    sim_btn = next((b for b in at.button if b.label == "Submit Simulated Score"), None)
    assert sim_btn is not None
    sim_btn.click().run()
    assert not at.exception
    assert len(at.session_state.state.scores) >= 1


def test_interactive_mentor_chat():
    """Verify sending a chat message to mentor produces a response."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception

    assert len(at.chat_input) > 0
    at.chat_input[0].set_value("How do I improve my Python skills?").run()
    assert not at.exception
    # Check that user prompt and mentor reply exist in chat history
    chat_history = at.session_state.get("mentor_chat_history", [])
    assert any(m["role"] == "user" for m in chat_history)
    assert any(m["role"] == "assistant" for m in chat_history)
    assert chat_history[-1]["role"] == "assistant"
    assert "Next action:" in chat_history[-1]["content"]


def test_adaptive_demo_full_stack_to_data_analyst():
    """Exercise Agent 7 orchestration through the learner-facing demo flow."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception
    assert [tab.label for tab in at.tabs][0] == "Dashboard"

    sample_state = at.session_state.state
    sample_levels = {skill.name: skill.level for skill in sample_state.profile.skills}
    assert sample_levels["Python"] == 3
    assert sample_levels["SQL"] == 3
    assert sample_levels["HTML"] == 2

    save_button = next(button for button in at.button if button.label == "Save Profile")
    save_button.click().run()
    assert not at.exception
    state = at.session_state.state
    assert state.requirements is not None
    assert state.requirements.role == "Full Stack Developer"
    assert state.requirements.company == "Zoho"
    assert state.requirements.confidence == "curated"
    assert any(item.skill == "React" for item in state.requirements.requirements)
    assert state.gap is not None
    assert state.roadmap is not None
    assert state.recommendations

    skill_select = next(widget for widget in at.selectbox if widget.label == "Select Skill to Assess")
    skill_select.set_value("React").run()
    score_slider = next(widget for widget in at.slider if widget.label == "Simulated Score %")
    score_slider.set_value(30).run()
    submit_score = next(
        button for button in at.button if button.label == "Submit Simulated Score"
    )
    submit_score.click().run()
    assert not at.exception
    assessed_state = at.session_state.state
    assert assessed_state.scores[-1].skill == "React"
    assert assessed_state.scores[-1].weak
    assert assessed_state.roadmap is not None
    assert any(
        step.skill == "React" and step.status == "revision"
        for step in assessed_state.roadmap.steps
    )

    old_roadmap = assessed_state.roadmap.model_dump()
    role_select = next(widget for widget in at.selectbox if widget.label == "Target Role")
    role_select.set_value("Data Analyst").run()
    save_button = next(button for button in at.button if button.label == "Save Profile")
    save_button.click().run()
    assert not at.exception
    data_state = at.session_state.state
    assert data_state.profile.target_role == "Data Analyst"
    assert data_state.requirements is not None
    assert data_state.requirements.role == "Data Analyst"
    assert data_state.roadmap is not None
    assert data_state.roadmap.model_dump() != old_roadmap
    retained_levels = {skill.name: skill.level for skill in data_state.profile.skills}
    assert retained_levels["Python"] == 3
    assert retained_levels["SQL"] == 3
    assert retained_levels["React"] == 0
    assert any(step.skill == "Pandas" for step in data_state.roadmap.steps)
    chat_history = at.session_state.get("mentor_chat_history", [])
    assert chat_history
    assert "Data Analyst" in chat_history[0]["content"]
    assert "Full Stack Developer" not in chat_history[0]["content"]


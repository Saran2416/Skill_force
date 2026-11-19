"""API smoke tests for the FastAPI backend (replaces ui/test_smoke.py).

Runs fully offline: fixture mode + mock LLM + a temp SQLite database.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Must be set before server.app is imported (FIXTURE_MODE is read at import time).
os.environ.setdefault("UI_FIXTURE", "1")
os.environ.setdefault("USE_MOCK_LLM", "1")
os.environ.pop("SKILLFORCE_AUTH_USER", None)

from server.app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("SKILLFORCE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("UI_FIXTURE", "1")
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    monkeypatch.delenv("SKILLFORCE_AUTH_USER", raising=False)
    with TestClient(create_app()) as test_client:
        yield test_client


def _demo(client: TestClient) -> None:
    assert client.post("/api/auth/demo").status_code == 200


def _profile_payload(**overrides: object) -> dict:
    payload: dict = {
        "name": "Aarav",
        "selected_skills": [
            {"name": "Python", "level": 3},
            {"name": "SQL", "level": 3},
            {"name": "HTML", "level": 2},
            {"name": "JavaScript", "level": 2},
        ],
        "custom_skills_text": "",
        "selected_certs": [],
        "custom_certs_text": "",
        "projects_text": "Portfolio website",
        "target_role": "Full Stack Developer",
        "target_company": "Zoho",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_session_requires_no_auth(client: TestClient) -> None:
    body = client.get("/api/auth/session").json()
    assert body["username"] is None
    assert body["fixture_mode"] is True


def test_demo_login_and_state(client: TestClient) -> None:
    _demo(client)
    body = client.get("/api/state").json()
    assert body["username"] == "demo"
    assert body["state"]["profile"]["target_role"] == "Full Stack Developer"
    assert body["profile_ready"] is True


def test_login_with_bad_credentials(client: TestClient) -> None:
    _demo(client)
    client.post("/api/auth/logout")
    res = client.post("/api/auth/login", json={"username": "demo", "password": "wrong"})
    assert res.status_code == 401


def test_signup_validation_and_success(client: TestClient) -> None:
    res = client.post("/api/auth/signup", json={"username": "newbie", "password": "short"})
    assert res.status_code == 400
    res = client.post("/api/auth/signup", json={"username": "newbie", "password": "secret12"})
    assert res.status_code == 200
    assert client.get("/api/state").json()["username"] == "newbie"


def test_logout_clears_session(client: TestClient) -> None:
    _demo(client)
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert client.get("/api/state").status_code == 401


def test_state_requires_auth(client: TestClient) -> None:
    assert client.get("/api/state").status_code == 401


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def test_profile_save_generates_plan(client: TestClient) -> None:
    _demo(client)
    res = client.post("/api/profile/save", json=_profile_payload())
    assert res.status_code == 200
    body = res.json()
    assert body["error"] is None
    state = body["state"]
    assert state["requirements"]["role"] == "Full Stack Developer"
    assert state["requirements"]["company"] == "Zoho"
    assert state["requirements"]["confidence"] == "curated"
    assert any(r["skill"] == "React" for r in state["requirements"]["requirements"])
    assert state["gap"] is not None
    assert state["roadmap"] is not None
    assert state["recommendations"]


def test_profile_save_validation_errors(client: TestClient) -> None:
    _demo(client)
    res = client.post("/api/profile/save", json=_profile_payload(name="  "))
    assert res.status_code == 400
    res = client.post("/api/profile/save", json=_profile_payload(target_role=""))
    assert res.status_code == 400
    res = client.post("/api/profile/save", json=_profile_payload(selected_skills=[]))
    assert res.status_code == 400


def test_target_change_replans_but_keeps_levels(client: TestClient) -> None:
    _demo(client)
    client.post("/api/profile/save", json=_profile_payload())
    res = client.post(
        "/api/profile/save",
        json=_profile_payload(target_role="Data Analyst", target_company=None),
    )
    assert res.status_code == 200
    state = res.json()["state"]
    assert state["requirements"]["role"] == "Data Analyst"
    step_skills = [s["skill"].lower() for s in state["roadmap"]["steps"]]
    assert any("pandas" in skill for skill in step_skills)
    levels = {s["name"]: s["level"] for s in state["profile"]["skills"]}
    assert levels["Python"] == 3


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------


def test_simulate_score_marks_revision(client: TestClient) -> None:
    _demo(client)
    client.post("/api/profile/save", json=_profile_payload())
    res = client.post("/api/assessment/simulate", json={"skill": "React", "percent": 30})
    assert res.status_code == 200
    body = res.json()
    assert body["result"]["weak"] is True
    revision_steps = [
        s for s in body["state"]["roadmap"]["steps"] if s["status"] == "revision"
    ]
    assert any(s["skill"] == "React" for s in revision_steps)


def test_quiz_generate_and_submit(client: TestClient) -> None:
    _demo(client)
    res = client.post("/api/assessment/quiz/generate", json={"skill": "Python"})
    assert res.status_code == 200
    quiz = res.json()["quiz"]
    assert len(quiz["questions"]) == 5

    answers = [q["answer_index"] for q in quiz["questions"]]
    res = client.post("/api/assessment/quiz/submit", json={"quiz": quiz, "answers": answers})
    assert res.status_code == 200
    body = res.json()
    assert body["result"]["score_percent"] == 100.0
    assert body["state"]["scores"]


def test_quiz_submit_rejects_wrong_answer_count(client: TestClient) -> None:
    _demo(client)
    quiz = client.post("/api/assessment/quiz/generate", json={"skill": "Python"}).json()["quiz"]
    res = client.post("/api/assessment/quiz/submit", json={"quiz": quiz, "answers": [0]})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Mentor
# ---------------------------------------------------------------------------


def test_mentor_chat_returns_reply(client: TestClient) -> None:
    _demo(client)
    client.post("/api/profile/save", json=_profile_payload())
    res = client.post("/api/mentor/chat", json={"message": "How should I prepare for interviews?"})
    assert res.status_code == 200
    body = res.json()
    assert body["reply"]
    assert body["error"] is None
    assert body["state"]["log"]


def test_mentor_chat_rejects_blank_message(client: TestClient) -> None:
    _demo(client)
    res = client.post("/api/mentor/chat", json={"message": "   "})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# Read models
# ---------------------------------------------------------------------------


def test_dashboard_read_model(client: TestClient) -> None:
    _demo(client)
    client.post("/api/profile/save", json=_profile_payload())
    body = client.get("/api/dashboard").json()
    assert body["progress"]["total"] >= 1
    assert body["required_skills"]
    assert all("status" in row for row in body["required_skills"])


def test_gap_radar(client: TestClient) -> None:
    _demo(client)
    body = client.get("/api/gap/radar").json()
    assert body["labels"]
    assert len(body["labels"]) == len(body["current"]) == len(body["required"])


def test_meta_options(client: TestClient) -> None:
    _demo(client)
    body = client.get("/api/meta").json()
    assert "Full Stack Developer" in body["roles"]
    assert "Zoho" in body["companies"]
    assert "Python" in body["known_skills"]


# ---------------------------------------------------------------------------
# Automation bypass (SKILLFORCE_AUTH_USER)
# ---------------------------------------------------------------------------


def test_auto_auth_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKILLFORCE_DB_PATH", str(tmp_path / "auto.db"))
    monkeypatch.setenv("UI_FIXTURE", "1")
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    monkeypatch.setenv("SKILLFORCE_AUTH_USER", "demo")
    with TestClient(create_app()) as test_client:
        body = test_client.get("/api/state").json()
        assert body["username"] == "demo"
        assert body["state"]["profile"]["skills"]

"""SkillForce REST API (FastAPI).

Replaces the Streamlit frontend (``app.py`` + ``ui/tab_*.py``) with a JSON API
consumed by the React app in ``frontend/``. All business logic is reused from
the existing modules:

- ``storage.db``        — auth + AppState persistence (SQLite)
- ``server.events``     — event dispatch through the mentor orchestrator
- ``server.profile``    — profile form parsing helpers
- ``agents.*``          — quizzing, scoring, mentoring, radar data
- ``ui.dashboard.logic`` — pure dashboard read models

Session model: an opaque token stored in an HttpOnly cookie (``skillforce_``
prefix) and mirrored in an in-memory table. ``SKILLFORCE_AUTH_USER`` keeps
working as a stateless auto-auth bypass for automation.
"""

from __future__ import annotations

import copy
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents.assessor import generate_quiz, score_quiz, simulate_score
from agents.career_matcher import radar_data
from contracts.sample import SAMPLE_STATE
from contracts.schemas import AppState, Quiz, ScoreResult, Skill
from data.loader import _company_records, _role_records
from storage.db import authenticate_user, create_user, load_state, save_state, user_exists
from ui.dashboard.logic import (
    advantages,
    disadvantages,
    known_languages,
    progress,
    required_skills_table,
)

from .events import dispatch_event
from .profile import KNOWN_CERTS, KNOWN_SKILLS, is_fresh_profile, parse_list_input, parse_skills_input, profile_complete

COOKIE_NAME = "skillforce_session"
FIXTURE_MODE = os.environ.get("UI_FIXTURE", "1") == "1"

# Opaque session token -> username (single-process server, like st.session_state).
_sessions: dict[str, str] = {}
# Username -> latest explain_changes() output (was st.session_state["latest_explanation"]).
_explanations: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _ensure_demo_user() -> None:
    if not user_exists("demo"):
        try:
            create_user("demo", "demo123")
        except Exception:
            pass


def _current_user(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.removeprefix("Bearer ").strip()
    if token and token in _sessions:
        return _sessions[token]

    # Optional auto-auth for testing/automation (auth UI remains available otherwise).
    auto_user = os.environ.get("SKILLFORCE_AUTH_USER", "").strip()
    if auto_user:
        if FIXTURE_MODE and auto_user == "demo":
            _ensure_demo_user()
        return auto_user
    return None


def _require_user(request: Request) -> str:
    user = _current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return user


def _start_session(response: Response, username: str) -> str:
    token = secrets.token_urlsafe(32)
    _sessions[token] = username
    _explanations.pop(username, None)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return token


def _load_state(user_id: str) -> AppState:
    """Load persisted state; the fixture demo user starts from the sample state."""
    if FIXTURE_MODE and user_id == "demo":
        try:
            state = load_state(user_id)
        except ValueError:
            state = None
        if state is None or not state.profile.skills:
            state = copy.deepcopy(SAMPLE_STATE)
            if not (state.profile.name or "").strip():
                state.profile.name = "Demo User"
            save_state(user_id, state)
        return state
    state = load_state(user_id)
    if not (state.profile.name or "").strip():
        state.profile.name = user_id
    return state


def _agent_error(state: AppState) -> str | None:
    """Surface the orchestrator's failure log entry, if the last action failed."""
    if state.log and state.log[-1].action == "agent_failed":
        return state.log[-1].reason
    return None


def _current_level(state: AppState, skill: str) -> int:
    target = skill.strip().casefold()
    for item in state.profile.skills:
        if item.name.strip().casefold() == target:
            return item.level
    return 0


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class Credentials(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    username: str
    fixture_mode: bool


class StateResponse(BaseModel):
    username: str
    fixture_mode: bool
    state: AppState
    latest_explanation: str
    profile_ready: bool


class SkillInput(BaseModel):
    name: str
    level: int = Field(default=3, ge=0, le=5)


class ProfileSaveRequest(BaseModel):
    name: str = ""
    selected_skills: list[SkillInput] = Field(default_factory=list)
    custom_skills_text: str = ""
    selected_certs: list[str] = Field(default_factory=list)
    custom_certs_text: str = ""
    projects_text: str = ""
    target_role: str = ""
    target_company: str | None = None


class MutationResponse(BaseModel):
    state: AppState
    latest_explanation: str
    error: str | None = None


class QuizGenerateRequest(BaseModel):
    skill: str


class QuizSubmitRequest(BaseModel):
    quiz: Quiz
    answers: list[int]


class QuizResponse(BaseModel):
    quiz: Quiz


class ScoreResponse(MutationResponse):
    result: ScoreResult


class SimulateRequest(BaseModel):
    skill: str
    percent: int = Field(ge=0, le=100)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(MutationResponse):
    reply: str


class MetaResponse(BaseModel):
    roles: list[str]
    companies: list[str]
    known_skills: list[str]
    known_certs: list[str]
    fixture_mode: bool


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(title="SkillForce API", version="1.0.0")

    # -- auth ---------------------------------------------------------------

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/auth/session")
    def session(request: Request) -> JSONResponse:
        user = _current_user(request)
        if not user:
            return JSONResponse({"username": None, "fixture_mode": FIXTURE_MODE})
        return JSONResponse({"username": user, "fixture_mode": FIXTURE_MODE})

    @app.post("/api/auth/login", response_model=SessionResponse)
    def login(body: Credentials, response: Response) -> SessionResponse:
        username = body.username.strip()
        if not username or not body.password:
            raise HTTPException(status_code=400, detail="Please enter both username and password.")
        if not authenticate_user(username, body.password):
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        _start_session(response, username)
        return SessionResponse(username=username, fixture_mode=FIXTURE_MODE)

    @app.post("/api/auth/signup", response_model=SessionResponse)
    def signup(body: Credentials, response: Response) -> SessionResponse:
        username = body.username.strip()
        if not username:
            raise HTTPException(status_code=400, detail="Please choose a username.")
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
        try:
            create_user(username, body.password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        _start_session(response, username)
        return SessionResponse(username=username, fixture_mode=FIXTURE_MODE)

    @app.post("/api/auth/demo", response_model=SessionResponse)
    def demo_login(response: Response) -> SessionResponse:
        if not FIXTURE_MODE:
            raise HTTPException(status_code=404, detail="Demo access is disabled.")
        _ensure_demo_user()
        # A fresh demo session always starts from the sample fixture state.
        state = copy.deepcopy(SAMPLE_STATE)
        if not (state.profile.name or "").strip():
            state.profile.name = "Demo User"
        save_state("demo", state)
        _start_session(response, "demo")
        return SessionResponse(username="demo", fixture_mode=FIXTURE_MODE)

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response) -> None:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            _sessions.pop(token, None)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            _sessions.pop(auth.removeprefix("Bearer ").strip(), None)
        user = _current_user(request)
        if user:
            _explanations.pop(user, None)
        response.delete_cookie(COOKIE_NAME)

    # -- state & meta -------------------------------------------------------

    @app.get("/api/state", response_model=StateResponse)
    def get_state(user: str = Depends(_require_user)) -> StateResponse:
        state = _load_state(user)
        return StateResponse(
            username=user,
            fixture_mode=FIXTURE_MODE,
            state=state,
            latest_explanation=_explanations.get(user, ""),
            profile_ready=profile_complete(state),
        )

    @app.get("/api/meta", response_model=MetaResponse)
    def meta(user: str = Depends(_require_user)) -> MetaResponse:
        return MetaResponse(
            roles=[record["role"] for record in _role_records()],
            companies=[record["company"] for record in _company_records()],
            known_skills=KNOWN_SKILLS,
            known_certs=KNOWN_CERTS,
            fixture_mode=FIXTURE_MODE,
        )

    # -- profile ------------------------------------------------------------

    @app.post("/api/profile/save", response_model=MutationResponse)
    def save_profile(
        body: ProfileSaveRequest,
        user: str = Depends(_require_user),
    ) -> MutationResponse:
        state = _load_state(user)

        cleaned_name = body.name.strip()
        cleaned_target_role = (body.target_role or "").strip()
        final_company = (body.target_company or "").strip() or None

        selected_skill_objects = [
            Skill(name=skill.name, level=int(skill.level), source="user")
            for skill in body.selected_skills
        ]
        parsed_custom = parse_skills_input(
            body.custom_skills_text, existing_skills=state.profile.skills
        )
        merged_skills: list[Skill] = []
        seen_skills: set[str] = set()
        for skill in [*selected_skill_objects, *parsed_custom]:
            key = skill.name.strip().casefold()
            if not key or key in seen_skills:
                continue
            seen_skills.add(key)
            merged_skills.append(skill)

        merged_certs: list[str] = []
        seen_certs: set[str] = set()
        for cert in [*body.selected_certs, *parse_list_input(body.custom_certs_text)]:
            clean = str(cert).strip()
            key = clean.casefold()
            if not clean or key in seen_certs:
                continue
            seen_certs.add(key)
            merged_certs.append(clean)

        if not cleaned_name:
            raise HTTPException(status_code=400, detail="Please enter your full name.")
        if not cleaned_target_role:
            raise HTTPException(
                status_code=400,
                detail="Please select a target role to generate your personalized roadmap.",
            )
        if not merged_skills:
            raise HTTPException(
                status_code=400,
                detail="Please select or add at least one skill so we can personalize your roadmap.",
            )

        old_role = state.profile.target_role
        old_company = state.profile.target_company
        target_changed = cleaned_target_role != old_role or final_company != old_company

        updated = state.model_copy(deep=True)
        updated.profile.name = cleaned_name
        updated.profile.skills = merged_skills
        updated.profile.certs = merged_certs
        updated.profile.projects = parse_list_input(body.projects_text)
        updated.profile.target_role = cleaned_target_role
        updated.profile.target_company = final_company

        event = (
            {"type": "TARGET_CHANGED", "role": cleaned_target_role, "company": final_company}
            if target_changed
            else {"type": "PROFILE_SAVED"}
        )

        try:
            updated_state, explanation = dispatch_event(
                updated, event, user, previous_state=state
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=500, detail=f"Failed to save profile: {exc}") from exc

        _explanations[user] = explanation
        return MutationResponse(
            state=updated_state,
            latest_explanation=explanation,
            error=_agent_error(updated_state),
        )

    # -- assessment ---------------------------------------------------------

    @app.post("/api/assessment/quiz/generate", response_model=QuizResponse)
    def quiz_generate(
        body: QuizGenerateRequest,
        user: str = Depends(_require_user),
    ) -> QuizResponse:
        state = _load_state(user)
        level = max(1, _current_level(state, body.skill))
        try:
            quiz = generate_quiz(body.skill, level)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {exc}") from exc
        return QuizResponse(quiz=quiz)

    @app.post("/api/assessment/simulate", response_model=ScoreResponse)
    def simulate(
        body: SimulateRequest,
        user: str = Depends(_require_user),
    ) -> ScoreResponse:
        state = _load_state(user)
        level = _current_level(state, body.skill)
        try:
            result = simulate_score(body.skill, body.percent, level)
            updated_state, explanation = dispatch_event(
                state, {"type": "QUIZ_SUBMITTED", "result": result}, user
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to simulate score: {exc}") from exc
        _explanations[user] = explanation
        return ScoreResponse(
            state=updated_state,
            latest_explanation=explanation,
            error=_agent_error(updated_state),
            result=result,
        )

    @app.post("/api/assessment/quiz/submit", response_model=ScoreResponse)
    def quiz_submit(
        body: QuizSubmitRequest,
        user: str = Depends(_require_user),
    ) -> ScoreResponse:
        state = _load_state(user)
        level = _current_level(state, body.quiz.skill)
        if len(body.answers) != len(body.quiz.questions):
            raise HTTPException(status_code=400, detail="Answer count does not match the quiz.")
        try:
            result = score_quiz(body.quiz, body.answers, level)
            updated_state, explanation = dispatch_event(
                state, {"type": "QUIZ_SUBMITTED", "result": result}, user
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to submit quiz: {exc}") from exc
        _explanations[user] = explanation
        return ScoreResponse(
            state=updated_state,
            latest_explanation=explanation,
            error=_agent_error(updated_state),
            result=result,
        )

    # -- mentor -------------------------------------------------------------

    @app.post("/api/mentor/chat", response_model=ChatResponse)
    def chat(
        body: ChatRequest,
        user: str = Depends(_require_user),
    ) -> ChatResponse:
        state = _load_state(user)
        message = body.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Please enter a message.")

        try:
            updated_state, explanation = dispatch_event(
                state, {"type": "CHAT", "message": message}, user
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to communicate with mentor: {exc}") from exc

        if explanation != "No target, skill, readiness, or roadmap changes.":
            _explanations[user] = explanation

        latest = updated_state.log[-1] if updated_state.log else None
        if latest is not None and latest.action in {"chat_response", "chat_unavailable"}:
            reply = latest.reason
        else:
            reply = "The mentor could not provide a response. Check the activity log for details."

        error = None
        if latest is not None and latest.action == "chat_unavailable":
            error = latest.reason

        return ChatResponse(
            state=updated_state,
            latest_explanation=_explanations.get(user, ""),
            error=error,
            reply=reply,
        )

    # -- read models --------------------------------------------------------

    @app.get("/api/dashboard")
    def get_dashboard(user: str = Depends(_require_user)) -> dict:
        state = _load_state(user)
        return {
            "known_languages": [
                {"name": s.name, "level": s.level} for s in known_languages(state.profile)
            ],
            "required_skills": required_skills_table(state),
            "advantages": advantages(state),
            "disadvantages": disadvantages(state),
            "progress": progress(state),
        }

    @app.get("/api/gap/radar")
    def get_gap_radar(user: str = Depends(_require_user)) -> dict:
        state = _load_state(user)
        if state.gap is None:
            return {"labels": [], "current": [], "required": []}
        return radar_data(state.gap, state.requirements, state.profile.skills)

    # -- static frontend ----------------------------------------------------

    dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if dist.is_dir():
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        index_file = dist / "index.html"

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found.")
            candidate = dist / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_file)

    return app


app = create_app()


def main() -> None:  # pragma: no cover - CLI entrypoint
    import uvicorn

    uvicorn.run("server.app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":  # pragma: no cover
    main()

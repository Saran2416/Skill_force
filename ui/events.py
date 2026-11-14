from __future__ import annotations

import copy
import os
from contracts.sample import SAMPLE_STATE
from contracts.schemas import AppState, ScoreResult, Skill
from storage.db import save_state

try:
    from agents.mentor import explain_changes, handle_event
except ImportError:
    handle_event = None  # type: ignore[assignment]
    explain_changes = None  # type: ignore[assignment]


def fixture_handle_event(state: AppState, event: dict) -> AppState:
    """Fallback fixture event handler used when UI_FIXTURE=1 or mentor agent is unavailable."""
    event_type = event.get("type", "")

    if event_type == "PROFILE_SAVED":
        state.add_log(
            "profile",
            "save_profile",
            f"Saved profile for {state.profile.name} with {len(state.profile.skills)} skills.",
        )
    elif event_type == "TARGET_CHANGED":
        role = event.get("role", state.profile.target_role)
        company = event.get("company", state.profile.target_company)
        state.profile.target_role = role
        state.profile.target_company = company
        state.add_log(
            "mentor",
            "target_changed",
            f"Target changed to {role} at {company or 'Any'}.",
        )
    elif event_type == "QUIZ_SUBMITTED":
        result = event.get("result")
        if isinstance(result, ScoreResult):
            state.scores.append(result)
            skill_found = False
            for s in state.profile.skills:
                if s.name.strip().casefold() == result.skill.strip().casefold():
                    s.level = result.new_level
                    s.source = "assessment"
                    skill_found = True
                    break
            if not skill_found:
                state.profile.skills.append(
                    Skill(name=result.skill, level=result.new_level, source="assessment")
                )
            status_text = "weak score flagged" if result.weak else "level updated"
            state.add_log(
                "assessor",
                "quiz_submitted",
                f"Assessed {result.skill}: {result.score_percent:.1f}% ({status_text}, level {result.new_level}).",
            )
    elif event_type == "CHAT":
        msg = str(event.get("message", ""))
        snippet = msg[:40] + ("..." if len(msg) > 40 else "")
        state.add_log(
            "mentor",
            "chat_query",
            f"Mentor addressed inquiry: {snippet}",
        )
    else:
        state.add_log("system", "event_received", f"Processed event: {event_type}")

    return state


def explain_app_changes(old_state: AppState, new_state: AppState) -> str:
    """Generate or retrieve explanation of state changes."""
    if os.environ.get("UI_FIXTURE") != "1" and explain_changes is not None:
        try:
            return explain_changes(old_state, new_state)
        except (NotImplementedError, Exception):
            pass

    # Fallback explanation
    if len(new_state.scores) > len(old_state.scores):
        latest = new_state.scores[-1]
        status = "needs revision" if latest.weak else "solid performance"
        return (
            f"Assessment completed for {latest.skill} with a score of {latest.score_percent:.1f}% "
            f"({status}). Target skill level adjusted to {latest.new_level}/5. "
            "Your learning roadmap and gap metrics have been updated."
        )

    if (
        old_state.profile.target_role != new_state.profile.target_role
        or old_state.profile.target_company != new_state.profile.target_company
    ):
        return (
            f"Target changed to '{new_state.profile.target_role}' at "
            f"'{new_state.profile.target_company or 'Any'}'. "
            "Skill requirements and learning milestones were updated accordingly."
        )

    if old_state.profile.skills != new_state.profile.skills:
        return (
            "Profile skills updated. Current readiness and gaps were re-evaluated "
            "against role requirements."
        )

    return (
        "Profile and learning progress are current. Work on your top-priority roadmap "
        "steps to close remaining skill gaps."
    )


def dispatch_event(state: AppState, event: dict, user_id: str) -> tuple[AppState, str]:
    """Execute an event, persist the updated state, and return (state, explanation)."""
    old_state = copy.deepcopy(state)

    if os.environ.get("UI_FIXTURE") == "1" or handle_event is None:
        new_state = fixture_handle_event(state, event)
    else:
        try:
            new_state = handle_event(state, event)
        except (NotImplementedError, Exception):
            new_state = fixture_handle_event(state, event)

    explanation = explain_app_changes(old_state, new_state)
    save_state(user_id, new_state)
    return new_state, explanation

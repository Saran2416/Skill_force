from __future__ import annotations

import logging
from collections import Counter

from pydantic import BaseModel, Field, ValidationError

from agents.career_matcher import compute_gap
from agents.company_intel import get_recommendations, get_requirements
from agents.planner import build_roadmap
from contracts.llm import call_llm
from contracts.schemas import (
    AppState,
    GapItem,
    GapReport,
    Recommendation,
    Roadmap,
    RoadmapStep,
    RoleRequirements,
    ScoreResult,
    Skill,
)

from .prompts import SYSTEM_PROMPT, build_chat_prompt

logger = logging.getLogger(__name__)


class _MentorReply(BaseModel):
    """Structured response that gives the learner exactly one next action."""

    response: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


def _normalized(name: str) -> str:
    return name.strip().casefold()


def _copy_with_log(state: AppState, action: str, reason: str) -> AppState:
    result = state.model_copy(deep=True)
    result.add_log("mentor", action, reason)
    return result


def _agent_failure(state: AppState, action: str, exc: Exception) -> AppState:
    logger.warning("Mentor could not complete %s: %s", action, exc)
    return _copy_with_log(
        state,
        "agent_failed",
        f"Could not complete {action}: {type(exc).__name__}: {exc}. The previous learner state was kept.",
    )


def _chat_failure(state: AppState, exc: Exception) -> AppState:
    logger.warning("Mentor could not generate a chat response: %s", exc)
    return _copy_with_log(
        state,
        "chat_unavailable",
        f"Could not generate a mentor response: {type(exc).__name__}: {exc}. "
        "The previous learner state was kept.\n\n"
        "Next action: Retry your message when the mentor service is available.",
    )


def _refresh_for_target(
    state: AppState,
    role: str,
    company: str | None,
    event_action: str,
) -> AppState:
    updated = state.model_copy(deep=True)
    company_label = f" at {company}" if company else ""
    updated.add_log(
        "mentor",
        event_action,
        f"Refreshing the learning plan for {role}{company_label}.",
    )

    requirements = RoleRequirements.model_validate(get_requirements(role, company))
    updated.add_log(
        "mentor",
        "requirements_loaded",
        f"Loaded {len(requirements.requirements)} requirements for {role}{company_label}.",
    )

    gap = GapReport.model_validate(compute_gap(updated.profile.skills, requirements))
    updated.add_log(
        "mentor",
        "gap_computed",
        f"Readiness is {gap.match_percent:.1f}% with {len(gap.gaps)} skill gaps for {role}.",
    )

    recommendations = [
        Recommendation.model_validate(item)
        for item in get_recommendations(requirements, updated.profile)
    ]
    updated.add_log(
        "mentor",
        "recommendations_updated",
        f"Refreshed {len(recommendations)} recommendations for {role}.",
    )

    roadmap = Roadmap.model_validate(
        build_roadmap(gap, requirements, weak_skills=[], completed=[])
    )
    updated.requirements = requirements.model_copy(deep=True)
    updated.gap = gap.model_copy(deep=True)
    updated.recommendations = [item.model_copy(deep=True) for item in recommendations]
    updated.roadmap = roadmap.model_copy(deep=True)
    updated.add_log(
        "mentor",
        "roadmap_replanned",
        f"Built a {len(roadmap.steps)}-step roadmap for {role}.",
    )
    return updated


def _gap_for_weak_skill(
    gap: GapReport,
    requirements: RoleRequirements,
    skill_name: str,
    current_level: int,
) -> GapReport:
    """Ensure a weak required skill is available to the planner for a review step."""
    normalized_skill = _normalized(skill_name)
    if any(_normalized(item.skill) == normalized_skill for item in gap.gaps):
        return gap

    requirement = next(
        (
            item
            for item in requirements.requirements
            if _normalized(item.skill) == normalized_skill
        ),
        None,
    )
    if requirement is None:
        return gap

    review_item = GapItem(
        skill=requirement.skill,
        current=current_level,
        required=requirement.level_required,
        gap=0,
        priority=requirement.priority,
    )
    strengths = [
        strength
        for strength in gap.strengths
        if _normalized(strength) != normalized_skill
    ]
    return GapReport(
        match_percent=gap.match_percent,
        gaps=[*gap.gaps, review_item],
        strengths=strengths,
    )


def _rebuild_after_score(updated: AppState, score: ScoreResult) -> AppState:
    requirements = updated.requirements
    if requirements is None:
        updated.add_log(
            "mentor",
            "quiz_recorded",
            f"Recorded the {score.skill} score, but no target requirements are available for gap analysis or replanning.",
        )
        return updated

    gap = GapReport.model_validate(compute_gap(updated.profile.skills, requirements))
    updated.gap = gap.model_copy(deep=True)
    updated.add_log(
        "mentor",
        "gap_recomputed",
        f"Recomputed role readiness at {gap.match_percent:.1f}% after the {score.skill} assessment.",
    )

    previous_steps = (
        [step.model_copy(deep=True) for step in updated.roadmap.steps]
        if updated.roadmap is not None
        else []
    )
    completed_steps: list[RoadmapStep] = []
    completed_names: list[str] = []
    completed_keys: set[str] = set()
    score_skill = _normalized(score.skill)

    for step in previous_steps:
        step_skill = _normalized(step.skill)
        if score.weak and step_skill == score_skill:
            continue
        if step.status == "done" or (not score.weak and _normalized(step.skill) == score_skill):
            step.status = "done"
            completed_steps.append(step)
            key = step_skill
            if key and key not in completed_keys:
                completed_keys.add(key)
                completed_names.append(step.skill)

    weak_skills = [score.skill] if score.weak else []
    planning_gap = gap
    if score.weak:
        planning_gap = _gap_for_weak_skill(
            gap,
            requirements,
            score.skill,
            score.new_level,
        )
    elif score_skill and score_skill not in completed_keys:
        completed_keys.add(score_skill)
        completed_names.append(score.skill)

    roadmap = Roadmap.model_validate(
        build_roadmap(
            planning_gap,
            requirements,
            weak_skills=weak_skills,
            completed=completed_names,
        )
    )

    merged_steps = [*completed_steps, *roadmap.steps]
    updated.roadmap = Roadmap(
        steps=[
            step.model_copy(update={"order": index})
            for index, step in enumerate(merged_steps, start=1)
        ],
        est_hours=roadmap.est_hours,
    )
    if score.weak:
        updated.add_log(
            "mentor",
            "roadmap_replanned",
            f"The weak {score.skill} score ({score.score_percent:.0f}%) prompted a focused revision step; rebuilt the remaining roadmap.",
        )
    else:
        updated.add_log(
            "mentor",
            "roadmap_replanned",
            f"The strong {score.skill} result marked its existing step done and excluded it from remaining work.",
        )
    return updated


def _chat_mock(state: AppState, message: str) -> _MentorReply:
    target = state.profile.target_role or "a target role"
    if state.roadmap and state.roadmap.steps:
        next_action = f"Start the {state.roadmap.steps[0].skill} roadmap step."
    else:
        next_action = "Choose one skill to practise and add it to your profile."
    return _MentorReply(
        response=f"I can help with “{message}”. Your current plan is focused on {target}.",
        next_action=next_action,
    )


def _format_chat_reply(reply: _MentorReply) -> str:
    response_lines = [
        line
        for line in reply.response.strip().splitlines()
        if not line.strip().casefold().startswith("next action:")
    ]
    response = "\n".join(response_lines).strip()
    next_action = reply.next_action.strip()
    if next_action.casefold().startswith("next action:"):
        next_action = next_action[len("next action:") :].strip()
    if not response:
        response = "I can help you choose a focused practice task."
    return f"{response}\n\nNext action: {next_action}"


def handle_event(state: AppState, event: dict) -> AppState:
    """Handle a learner event without mutating the supplied state.

    Event shapes:
      {"type": "PROFILE_SAVED"}
      {"type": "TARGET_CHANGED", "role": str, "company": str | None}
      {"type": "QUIZ_SUBMITTED", "result": ScoreResult}
      {"type": "CHAT", "message": str}
    """
    if not isinstance(event, dict):
        return _copy_with_log(state, "event_rejected", "Ignored an event because it must be a dictionary.")

    event_type = event.get("type")
    if event_type == "PROFILE_SAVED":
        role = state.profile.target_role.strip()
        company = state.profile.target_company
        if not role:
            return _copy_with_log(
                state,
                "profile_saved",
                "Profile saved; choose a target role before generating role requirements and a roadmap.",
            )
        try:
            return _refresh_for_target(state, role, company, "profile_saved")
        except Exception as exc:
            return _agent_failure(state, "PROFILE_SAVED", exc)

    if event_type == "TARGET_CHANGED":
        role = event.get("role")
        company = event.get("company")
        if not isinstance(role, str) or not role.strip():
            return _copy_with_log(
                state,
                "event_rejected",
                "Ignored TARGET_CHANGED because role must be a non-empty string.",
            )
        if company is not None and not isinstance(company, str):
            return _copy_with_log(
                state,
                "event_rejected",
                "Ignored TARGET_CHANGED because company must be a string or None.",
            )

        updated = state.model_copy(deep=True)
        updated.profile.target_role = role.strip()
        updated.profile.target_company = company.strip() if company and company.strip() else None
        try:
            return _refresh_for_target(
                updated,
                updated.profile.target_role,
                updated.profile.target_company,
                "target_changed",
            )
        except Exception as exc:
            return _agent_failure(state, "TARGET_CHANGED", exc)

    if event_type == "QUIZ_SUBMITTED":
        try:
            score = ScoreResult.model_validate(event.get("result"))
        except (TypeError, ValueError, ValidationError) as exc:
            return _agent_failure(state, "QUIZ_SUBMITTED", exc)

        updated = state.model_copy(deep=True)
        skill_key = _normalized(score.skill)
        found_skill = False
        for index, skill in enumerate(updated.profile.skills):
            if _normalized(skill.name) == skill_key:
                updated.profile.skills[index] = skill.model_copy(
                    update={"level": score.new_level, "source": "assessment"}
                )
                found_skill = True
        if not found_skill:
            updated.profile.skills.append(
                Skill(name=score.skill, level=score.new_level, source="assessment")
            )
        updated.scores.append(score.model_copy(deep=True))
        decision = "weak" if score.weak else "strong"
        updated.add_log(
            "mentor",
            "quiz_submitted",
            f"{score.skill} scored {score.score_percent:.0f}% and was assessed as {decision}; updated the learner's skill level to {score.new_level}.",
        )
        try:
            return _rebuild_after_score(updated, score)
        except Exception as exc:
            return _agent_failure(state, "QUIZ_SUBMITTED", exc)

    if event_type == "CHAT":
        message = event.get("message")
        if not isinstance(message, str) or not message.strip():
            return _copy_with_log(
                state,
                "event_rejected",
                "Ignored CHAT because message must be a non-empty string.",
            )
        try:
            reply = _MentorReply.model_validate(
                call_llm(
                    SYSTEM_PROMPT,
                    build_chat_prompt(state.model_dump_json(), message.strip()),
                    _MentorReply,
                    mock=_chat_mock(state, message.strip()),
                )
            )
        except Exception as exc:
            return _chat_failure(state, exc)

        return _copy_with_log(state, "chat_response", _format_chat_reply(reply))

    return _copy_with_log(
        state,
        "event_ignored",
        f"Ignored unsupported event type {event_type!r}.",
    )


def explain_changes(old: AppState, new: AppState) -> str:
    """Explain target, skill, readiness, and roadmap changes in plain English."""
    changes: list[str] = []

    old_target = old.profile.target_role.strip()
    new_target = new.profile.target_role.strip()
    if old_target != new_target:
        changes.append(
            f"Target role changed from {old_target or 'none'} to {new_target or 'none'}."
        )
    old_company = old.profile.target_company or "none"
    new_company = new.profile.target_company or "none"
    if old_company != new_company:
        changes.append(f"Target company changed from {old_company} to {new_company}.")

    old_skills = {_normalized(skill.name): skill for skill in old.profile.skills}
    new_skills = {_normalized(skill.name): skill for skill in new.profile.skills}
    for key in sorted(old_skills.keys() | new_skills.keys()):
        previous = old_skills.get(key)
        current = new_skills.get(key)
        if previous is None and current is not None:
            changes.append(f"Added {current.name} at level {current.level}.")
        elif current is None and previous is not None:
            changes.append(f"Removed {previous.name} (previously level {previous.level}).")
        elif previous is not None and current is not None and previous.level != current.level:
            changes.append(
                f"{current.name} changed from level {previous.level} to level {current.level}."
            )

    old_match = old.gap.match_percent if old.gap is not None else None
    new_match = new.gap.match_percent if new.gap is not None else None
    if old_match is not None and new_match is not None and old_match != new_match:
        direction = "up" if new_match > old_match else "down"
        changes.append(
            f"Role readiness moved {direction} from {old_match:.1f}% to {new_match:.1f}%."
        )
    elif old_match is None and new_match is not None:
        changes.append(f"Role readiness is now {new_match:.1f}%.")

    old_steps = old.roadmap.steps if old.roadmap is not None else []
    new_steps = new.roadmap.steps if new.roadmap is not None else []
    old_counts = Counter(
        (_normalized(step.skill), step.status) for step in old_steps
    )
    new_counts = Counter(
        (_normalized(step.skill), step.status) for step in new_steps
    )
    step_names = {
        _normalized(step.skill): step.skill for step in [*old_steps, *new_steps]
    }
    for key in sorted(old_counts.keys() | new_counts.keys()):
        difference = new_counts[key] - old_counts[key]
        if difference > 0:
            status = "revision" if key[1] == "revision" else key[1]
            for _ in range(difference):
                changes.append(f"Added a {step_names[key[0]]} {status} step to the roadmap.")
        difference = old_counts[key] - new_counts[key]
        if difference > 0:
            for _ in range(difference):
                changes.append(
                    f"Removed the {step_names[key[0]]} {key[1]} step from the roadmap."
                )

    if old.log and len(new.log) >= len(old.log) and new.log[: len(old.log)] == old.log:
        new_entries = new.log[len(old.log) :]
    else:
        new_entries = new.log
    decision_actions = {
        "profile_saved",
        "target_changed",
        "quiz_submitted",
        "roadmap_replanned",
        "agent_failed",
    }
    for entry in new_entries:
        if entry.agent == "mentor" and entry.action in decision_actions:
            changes.append(f"Reason: {entry.reason}")

    return "\n".join(changes) if changes else "No target, skill, readiness, or roadmap changes."


__all__ = ["handle_event", "explain_changes"]

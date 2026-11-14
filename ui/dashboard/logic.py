"""Pure, Streamlit-free logic for the learner dashboard.

Every function here is read-only with respect to ``AppState`` and tolerates
``None`` for ``requirements``/``gap``/``roadmap`` as well as an empty profile.
They never raise for missing data and never touch the network or disk.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .languages import LANGUAGES

if TYPE_CHECKING:  # pragma: no cover - typing only
    from contracts.schemas import AppState, Skill, UserProfile

# Display ordering for requirement/gap priorities: must-haves first.
_PRIORITY_ORDER: dict[str, int] = {"must": 0, "good": 1, "bonus": 2}


def _fmt_number(value: float) -> str:
    """Render a number without a trailing ``.0`` for whole values."""

    return f"{value:g}"


def _skill_level(profile: "UserProfile | None", name: str) -> int | None:
    """Highest level recorded for ``name`` (case-insensitive), or ``None``."""

    if profile is None:
        return None
    target = name.strip().lower()
    levels = [
        skill.level
        for skill in (getattr(profile, "skills", None) or [])
        if skill.name.strip().lower() == target
    ]
    return max(levels) if levels else None


def known_languages(profile: "UserProfile | None") -> list["Skill"]:
    """Skills that are programming languages, sorted by level descending.

    Matching is case-insensitive and duplicates are collapsed to the highest
    recorded level so each language appears at most once.
    """

    if profile is None:
        return []

    best: dict[str, "Skill"] = {}
    for skill in getattr(profile, "skills", None) or []:
        key = skill.name.strip().lower()
        if key not in LANGUAGES:
            continue
        current = best.get(key)
        if current is None or skill.level > current.level:
            best[key] = skill

    return sorted(best.values(), key=lambda skill: skill.level, reverse=True)


def required_skills_table(state: "AppState | None") -> list[dict]:
    """Return the required-skills rows with must-haves first.

    Each row is ``{"skill", "required", "current", "priority", "status"}`` where
    ``status`` is ``"met"``, ``"gap"`` or ``"missing"``. Missing skills report a
    current level of ``0``.
    """

    requirements = getattr(state, "requirements", None)
    if requirements is None:
        return []

    profile = getattr(state, "profile", None)
    rows: list[dict] = []
    for req in requirements.requirements:
        current = _skill_level(profile, req.skill)
        if current is None:
            status = "missing"
            current_value = 0
        elif current >= req.level_required:
            status = "met"
            current_value = current
        else:
            status = "gap"
            current_value = current
        rows.append(
            {
                "skill": req.skill,
                "required": req.level_required,
                "current": current_value,
                "priority": req.priority,
                "status": status,
            }
        )

    rows.sort(key=lambda row: _PRIORITY_ORDER.get(row["priority"], len(_PRIORITY_ORDER)))
    return rows


def advantages(state: "AppState | None") -> list[str]:
    """Human-readable strengths for the learner (empty when data is missing)."""

    profile = getattr(state, "profile", None)
    gap = getattr(state, "gap", None)
    requirements = getattr(state, "requirements", None)
    result: list[str] = []

    if gap is not None:
        for strength in gap.strengths:
            result.append(f"{strength} is a strength.")

    if requirements is not None:
        for req in requirements.requirements:
            current = _skill_level(profile, req.skill)
            if current is not None and current > req.level_required:
                result.append(
                    f"{req.skill} is above the required level "
                    f"({current} vs {req.level_required})."
                )

        held = {cert.strip().lower() for cert in (getattr(profile, "certs", None) or [])}
        for cert in requirements.certs:
            if cert.strip().lower() in held:
                result.append(f"You already hold the {cert} certification.")

    for score in getattr(state, "scores", None) or []:
        if score.score_percent >= 80:
            result.append(
                f"Your {score.skill} assessment scored "
                f"{_fmt_number(score.score_percent)}%."
            )

    return result


def disadvantages(state: "AppState | None") -> list[str]:
    """Human-readable gaps and risks for the learner (must-haves first)."""

    profile = getattr(state, "profile", None)
    gap = getattr(state, "gap", None)
    requirements = getattr(state, "requirements", None)
    result: list[str] = []

    if gap is not None:
        ordered = sorted(
            gap.gaps,
            key=lambda item: _PRIORITY_ORDER.get(item.priority, len(_PRIORITY_ORDER)),
        )
        for item in ordered:
            plural = "s" if item.gap != 1 else ""
            result.append(f"{item.skill}: needs +{item.gap} level{plural}.")

    if requirements is not None:
        held = {cert.strip().lower() for cert in (getattr(profile, "certs", None) or [])}
        for cert in requirements.certs:
            if cert.strip().lower() not in held:
                result.append(f"Missing certification: {cert}.")

    for score in getattr(state, "scores", None) or []:
        if score.score_percent < 60:
            result.append(
                f"Your {score.skill} assessment scored "
                f"{_fmt_number(score.score_percent)}% (below 60%)."
            )

    if (
        requirements is not None
        and requirements.confidence == "ai_estimated"
        and requirements.disclaimer
    ):
        result.append(requirements.disclaimer)

    return result


def progress(state: "AppState | None") -> dict:
    """Roadmap progress plus the next unfinished step's skill, if any."""

    roadmap = getattr(state, "roadmap", None)
    steps = list(roadmap.steps) if roadmap is not None else []
    total = len(steps)
    done = sum(1 for step in steps if step.status == "done")
    percent = (done / total * 100.0) if total else 0.0

    next_step: str | None = None
    for step in sorted(steps, key=lambda item: item.order):
        if step.status != "done":
            next_step = step.skill
            break

    return {"done": done, "total": total, "percent": percent, "next_step": next_step}


__all__ = [
    "known_languages",
    "required_skills_table",
    "advantages",
    "disadvantages",
    "progress",
]

from __future__ import annotations

from contracts.schemas import GapItem, GapReport, RoleRequirement, RoleRequirements, Skill

_WEIGHTS = {"must": 3, "good": 2, "bonus": 1}
_PRIORITY_ORDER = {"must": 0, "good": 1, "bonus": 2}


def _normalize(name: str) -> str:
    """Normalize a skill name for case-insensitive matching."""
    return name.strip().casefold()


def _level_by_skill(skills: list[Skill]) -> dict[str, int]:
    """Map normalized skill names to the learner's best level for that skill."""
    levels: dict[str, int] = {}
    for skill in skills:
        key = _normalize(skill.name)
        if not key:
            continue
        levels[key] = max(levels.get(key, 0), skill.level)
    return levels


def _gap_for(requirement: RoleRequirement, levels: dict[str, int]) -> GapItem:
    current = levels.get(_normalize(requirement.skill), 0)
    return GapItem(
        skill=requirement.skill,
        current=current,
        required=requirement.level_required,
        gap=max(0, requirement.level_required - current),
        priority=requirement.priority,
    )


def compute_gap(skills: list[Skill], req: RoleRequirements) -> GapReport:
    """Compare a learner's skills against a job requirement set."""
    requirements = req.requirements
    if not requirements:
        return GapReport(match_percent=100.0, gaps=[], strengths=[])

    levels = _level_by_skill(skills or [])
    items = [_gap_for(requirement, levels) for requirement in requirements]

    total_weighted_required = sum(
        _WEIGHTS[item.priority] * item.required for item in items
    )
    weighted_gap = sum(_WEIGHTS[item.priority] * item.gap for item in items)

    if total_weighted_required <= 0:
        match_percent = 100.0
    else:
        match_percent = 100 * (1 - weighted_gap / total_weighted_required)
    match_percent = round(min(100.0, max(0.0, match_percent)), 1)

    gaps = [item for item in items if item.gap > 0]
    gaps.sort(key=lambda item: (-_WEIGHTS[item.priority] * item.gap, _PRIORITY_ORDER[item.priority]))

    strengths: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = _normalize(item.skill)
        if item.gap == 0 and key not in seen:
            seen.add(key)
            strengths.append(item.skill)

    return GapReport(match_percent=match_percent, gaps=gaps, strengths=strengths)


def radar_data(gap: GapReport) -> dict:
    """Return radar chart data for the current gap report."""
    items = sorted(gap.gaps, key=lambda item: _PRIORITY_ORDER[item.priority])
    return {
        "labels": [item.skill for item in items],
        "current": [item.current for item in items],
        "required": [item.required for item in items],
    }

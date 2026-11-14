"""Curriculum planner agent for SkillPath (agent 5).

Generates personalized, topologically sorted roadmaps based on a learner's
skill gap report, target role requirements, weak assessment skills, and completed skills.
"""

from __future__ import annotations

import logging
from typing import Sequence

from contracts.llm import call_llm
from contracts.schemas import GapReport, Resource, Roadmap, RoadmapStep, RoleRequirements
from data.loader import get_resources

from .prereqs import (
    canonical_skill_name,
    get_prerequisites,
    normalize_skill_name,
    topological_sort_skills,
)
from .prompts import SYSTEM_PROMPT, StepPlan, build_user_prompt, get_mock_step_plan

logger = logging.getLogger(__name__)


def _plan_activities(skill: str, target_level: int, is_revision: bool = False) -> tuple[str, list[str]]:
    """Call the LLM (or mock in offline mode) to get a mini-project and 3 practice tasks."""
    mock_plan = get_mock_step_plan(skill, target_level, is_revision=is_revision)
    user_prompt = build_user_prompt(skill, target_level, is_revision=is_revision)

    try:
        response = call_llm(
            SYSTEM_PROMPT,
            user_prompt,
            StepPlan,
            mock=mock_plan,
        )
        if isinstance(response, StepPlan):
            plan = response
        else:
            plan = StepPlan.model_validate(response)
    except Exception as exc:
        logger.warning("LLM call failed for skill %s (revision=%s): %s; using mock fallback", skill, is_revision, exc)
        plan = mock_plan

    mini_project = str(plan.mini_project or "").strip()
    practice_tasks = [str(task).strip() for task in plan.practice_tasks if str(task).strip()]

    # Guarantee at least 3 practice tasks
    if len(practice_tasks) < 3:
        fallback_tasks = mock_plan.practice_tasks
        for task in fallback_tasks:
            if task not in practice_tasks:
                practice_tasks.append(task)
            if len(practice_tasks) == 3:
                break

    return mini_project, practice_tasks[:3]


def build_roadmap(
    gap: GapReport,
    req: RoleRequirements,
    weak_skills: list[str] = [],
    completed: list[str] = [],
) -> Roadmap:
    """Build a topologically sorted training roadmap for the learner.

    Args:
        gap: GapReport containing identified gaps and strengths.
        req: RoleRequirements for the target role.
        weak_skills: List of skills where the learner demonstrated weakness in assessments.
        completed: List of skills the learner has already completed or mastered.

    Returns:
        Roadmap containing ordered RoadmapSteps and total estimated hours.
    """
    completed_norm: set[str] = {
        normalize_skill_name(skill) for skill in (completed or []) if normalize_skill_name(skill)
    }
    weak_norm: set[str] = {
        normalize_skill_name(skill) for skill in (weak_skills or []) if normalize_skill_name(skill)
    }
    strengths_norm: set[str] = {
        normalize_skill_name(skill)
        for skill in (getattr(gap, "strengths", None) or [])
        if normalize_skill_name(skill)
    }

    # Already satisfied skills that do not need to be scheduled
    satisfied_norm = completed_norm | strengths_norm

    # Display name registry
    display_names: dict[str, str] = {}
    if req and getattr(req, "requirements", None):
        for r in req.requirements:
            norm = normalize_skill_name(r.skill)
            if norm and norm not in display_names:
                display_names[norm] = r.skill

    # Collect gap skills, skipping any that are already in completed
    gap_skills_order: list[str] = []
    target_levels: dict[str, int] = {}
    gap_levels: dict[str, int] = {}

    for item in (getattr(gap, "gaps", None) or []):
        norm = normalize_skill_name(item.skill)
        if not norm or norm in completed_norm:
            continue
        if norm not in display_names:
            display_names[norm] = item.skill

        req_level = max(1, min(5, int(getattr(item, "required", 3) or 3)))
        gap_val = max(1, int(getattr(item, "gap", req_level) or req_level))

        if norm not in target_levels:
            gap_skills_order.append(norm)
            target_levels[norm] = req_level
            gap_levels[norm] = gap_val
        else:
            target_levels[norm] = max(target_levels[norm], req_level)
            gap_levels[norm] = max(gap_levels[norm], gap_val)

    # Transitive missing prerequisites resolution (target_level = 2, gap = 2)
    missing_prereqs: list[str] = []
    to_inspect: list[str] = list(gap_skills_order)
    seen_prereqs: set[str] = set(gap_skills_order)

    while to_inspect:
        current_norm = to_inspect.pop(0)
        prereqs = get_prerequisites(current_norm)
        for prereq in prereqs:
            prereq_norm = normalize_skill_name(prereq)
            if not prereq_norm:
                continue
            if prereq_norm in completed_norm or prereq_norm in strengths_norm:
                continue
            if prereq_norm not in display_names:
                display_names[prereq_norm] = canonical_skill_name(prereq)

            if prereq_norm not in target_levels:
                # Missing prerequisite: target_level 2, gap of 2 levels
                target_levels[prereq_norm] = 2
                gap_levels[prereq_norm] = 2
                missing_prereqs.append(prereq_norm)
                to_inspect.append(prereq_norm)
                seen_prereqs.add(prereq_norm)

    # All skills to schedule in topological order
    skills_to_schedule = missing_prereqs + gap_skills_order
    if not skills_to_schedule:
        return Roadmap(steps=[], est_hours=0)

    # Topologically sort with safe cycle detection
    sorted_skills = topological_sort_skills(skills_to_schedule)

    steps: list[RoadmapStep] = []
    total_est_hours: int = 0
    order_index: int = 1

    for skill_name in sorted_skills:
        norm = normalize_skill_name(skill_name)
        disp_name = display_names.get(norm, canonical_skill_name(skill_name))
        target_lvl = target_levels.get(norm, 2)
        gap_lvl = gap_levels.get(norm, 1)

        # Curated resources from data.loader ONLY (never invent URLs)
        step_resources = get_resources(disp_name)

        # For weak skills, insert status="revision" step directly BEFORE the main step
        if norm in weak_norm:
            rev_mini, rev_tasks = _plan_activities(disp_name, target_lvl, is_revision=True)
            rev_step = RoadmapStep(
                order=order_index,
                skill=disp_name,
                target_level=target_lvl,
                resources=step_resources,
                mini_project=rev_mini,
                practice_tasks=rev_tasks,
                status="revision",
            )
            steps.append(rev_step)
            order_index += 1
            total_est_hours += 3  # revision steps 3 hours

        # Main step
        main_mini, main_tasks = _plan_activities(disp_name, target_lvl, is_revision=False)
        main_step = RoadmapStep(
            order=order_index,
            skill=disp_name,
            target_level=target_lvl,
            resources=step_resources,
            mini_project=main_mini,
            practice_tasks=main_tasks,
            status="todo",
        )
        steps.append(main_step)
        order_index += 1
        total_est_hours += 8 * gap_lvl  # ~8 hours per level of gap

    return Roadmap(steps=steps, est_hours=total_est_hours)


__all__ = ["build_roadmap"]

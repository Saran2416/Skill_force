from __future__ import annotations

import agents.mentor.agent as mentor_agent
from contracts.schemas import (
    AppState,
    GapItem,
    GapReport,
    Roadmap,
    RoadmapStep,
    RoleRequirement,
    RoleRequirements,
    ScoreResult,
    Skill,
    UserProfile,
)


def _requirements(role: str, company: str | None) -> RoleRequirements:
    if role == "Full Stack Developer":
        requirements = [
            RoleRequirement(skill="Python", level_required=3, priority="must"),
            RoleRequirement(skill="SQL", level_required=3, priority="must"),
            RoleRequirement(skill="React", level_required=3, priority="must"),
            RoleRequirement(skill="JavaScript", level_required=3, priority="good"),
        ]
    else:
        requirements = [
            RoleRequirement(skill="Python", level_required=3, priority="must"),
            RoleRequirement(skill="SQL", level_required=3, priority="must"),
            RoleRequirement(skill="Pandas", level_required=2, priority="good"),
        ]
    return RoleRequirements(
        role=role,
        company=company,
        requirements=requirements,
        confidence="curated",
    )


def _compute_gap(skills: list[Skill], requirements: RoleRequirements) -> GapReport:
    levels = {skill.name.casefold(): skill.level for skill in skills}
    gaps = []
    strengths = []
    for requirement in requirements.requirements:
        current = levels.get(requirement.skill.casefold(), 0)
        amount = max(0, requirement.level_required - current)
        if amount:
            gaps.append(
                GapItem(
                    skill=requirement.skill,
                    current=current,
                    required=requirement.level_required,
                    gap=amount,
                    priority=requirement.priority,
                )
            )
        else:
            strengths.append(requirement.skill)
    return GapReport(
        match_percent=max(0.0, 100.0 - len(gaps) * 10),
        gaps=gaps,
        strengths=strengths,
    )


def _build_roadmap(
    gap: GapReport,
    requirements: RoleRequirements,
    weak_skills: list[str] | None = None,
    completed: list[str] | None = None,
) -> Roadmap:
    weak = {skill.casefold() for skill in (weak_skills or [])}
    completed_skills = {skill.casefold() for skill in (completed or [])}
    steps = []
    for item in gap.gaps:
        key = item.skill.casefold()
        if key in completed_skills:
            continue
        if key in weak:
            steps.append(
                RoadmapStep(
                    order=len(steps) + 1,
                    skill=item.skill,
                    target_level=item.required,
                    mini_project=f"Review {item.skill} fundamentals",
                    status="revision",
                )
            )
        steps.append(
            RoadmapStep(
                order=len(steps) + 1,
                skill=item.skill,
                target_level=item.required,
                mini_project=f"Practise {item.skill}",
                status="todo",
            )
        )
    return Roadmap(steps=steps, est_hours=len(steps) * 2)


def _install_fake_agents(monkeypatch) -> None:
    monkeypatch.setattr(mentor_agent, "get_requirements", _requirements)
    monkeypatch.setattr(mentor_agent, "compute_gap", _compute_gap)
    monkeypatch.setattr(mentor_agent, "get_recommendations", lambda req, profile: [])
    monkeypatch.setattr(mentor_agent, "build_roadmap", _build_roadmap)


def test_full_mentor_flow_preserves_skills_and_adapts_roadmap(monkeypatch) -> None:
    _install_fake_agents(monkeypatch)
    original = AppState(
        profile=UserProfile(
            name="Sam",
            skills=[
                Skill(name="Python", level=3, source="user"),
                Skill(name="SQL", level=3, source="user"),
            ],
        )
    )
    original_json = original.model_dump_json()

    saved = mentor_agent.handle_event(original, {"type": "PROFILE_SAVED"})
    assert saved is not original
    assert saved.log[-1].action == "profile_saved"

    full_stack = mentor_agent.handle_event(
        saved,
        {
            "type": "TARGET_CHANGED",
            "role": "Full Stack Developer",
            "company": "Zoho",
        },
    )
    assert full_stack.requirements is not None
    assert full_stack.requirements.role == "Full Stack Developer"
    assert full_stack.roadmap is not None
    assert any(step.skill == "React" for step in full_stack.roadmap.steps)

    adapted = mentor_agent.handle_event(
        full_stack,
        {
            "type": "QUIZ_SUBMITTED",
            "result": ScoreResult(
                skill="React",
                score_percent=40,
                new_level=1,
                weak=True,
            ),
        },
    )
    react_skill = next(skill for skill in adapted.profile.skills if skill.name == "React")
    assert react_skill.level == 1
    assert react_skill.source == "assessment"
    assert adapted.roadmap is not None
    assert any(
        step.skill == "React" and step.status == "revision"
        for step in adapted.roadmap.steps
    )
    assert len(adapted.log) >= 6
    explanation = mentor_agent.explain_changes(full_stack, adapted)
    assert "Added React at level 1." in explanation
    assert "weak React score" in explanation

    data_analyst = mentor_agent.handle_event(
        adapted,
        {"type": "TARGET_CHANGED", "role": "Data Analyst", "company": None},
    )
    assert data_analyst.requirements is not None
    assert data_analyst.requirements.role == "Data Analyst"
    assert data_analyst.roadmap is not None
    assert any(step.skill == "Pandas" for step in data_analyst.roadmap.steps)
    assert [(skill.name, skill.level) for skill in data_analyst.profile.skills[:2]] == [
        ("Python", 3),
        ("SQL", 3),
    ]
    assert original.model_dump_json() == original_json


def test_strong_assessment_marks_matching_step_done(monkeypatch) -> None:
    _install_fake_agents(monkeypatch)
    state = AppState(
        profile=UserProfile(
            name="Sam",
            skills=[Skill(name="Python", level=2, source="user")],
            target_role="Full Stack Developer",
        )
    )
    planned = mentor_agent.handle_event(
        state,
        {"type": "PROFILE_SAVED"},
    )
    scored = mentor_agent.handle_event(
        planned,
        {
            "type": "QUIZ_SUBMITTED",
            "result": ScoreResult(
                skill="React",
                score_percent=90,
                new_level=3,
                weak=False,
            ),
        },
    )
    assert scored.roadmap is not None
    assert any(step.skill == "React" and step.status == "done" for step in scored.roadmap.steps)
    assert not any(step.skill == "React" and step.status == "todo" for step in scored.roadmap.steps)


def test_weak_assessment_reopens_a_previously_done_skill(monkeypatch) -> None:
    _install_fake_agents(monkeypatch)
    state = AppState(
        profile=UserProfile(
            name="Sam",
            skills=[Skill(name="Python", level=3, source="user")],
            target_role="Full Stack Developer",
        ),
        requirements=_requirements("Full Stack Developer", None),
        gap=_compute_gap(
            [Skill(name="Python", level=3, source="user")],
            _requirements("Full Stack Developer", None),
        ),
        roadmap=Roadmap(
            steps=[
                RoadmapStep(
                    order=1,
                    skill="React",
                    target_level=3,
                    status="done",
                )
            ]
        ),
    )
    scored = mentor_agent.handle_event(
        state,
        {
            "type": "QUIZ_SUBMITTED",
            "result": ScoreResult(
                skill="React",
                score_percent=35,
                new_level=1,
                weak=True,
            ),
        },
    )
    assert scored.roadmap is not None
    assert any(step.skill == "React" and step.status == "revision" for step in scored.roadmap.steps)


def test_agent_failure_keeps_previous_learner_state(monkeypatch) -> None:
    def fail_requirements(role: str, company: str | None) -> RoleRequirements:
        raise RuntimeError("requirements unavailable")

    monkeypatch.setattr(mentor_agent, "get_requirements", fail_requirements)
    state = AppState(
        profile=UserProfile(
            name="Sam",
            skills=[Skill(name="Python", level=2, source="user")],
            target_role="Old Role",
        )
    )
    before = state.model_dump_json()
    result = mentor_agent.handle_event(
        state,
        {"type": "TARGET_CHANGED", "role": "New Role", "company": None},
    )
    assert result.profile.target_role == "Old Role"
    assert result.log[-1].action == "agent_failed"
    assert "requirements unavailable" in result.log[-1].reason
    assert state.model_dump_json() == before


def test_chat_uses_mock_and_records_one_next_action(monkeypatch) -> None:
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    state = AppState(profile=UserProfile(name="Sam"))
    result = mentor_agent.handle_event(
        state,
        {"type": "CHAT", "message": "What should I practise?"},
    )
    reason = result.log[-1].reason
    assert result.log[-1].action == "chat_response"
    assert reason.count("Next action:") == 1
    assert reason.endswith("Next action: Choose one skill to practise and add it to your profile.")


def test_chat_failure_is_logged_with_a_clear_next_action(monkeypatch) -> None:
    def fail_chat(*args, **kwargs):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(mentor_agent, "call_llm", fail_chat)
    state = AppState(profile=UserProfile(name="Sam"))
    result = mentor_agent.handle_event(
        state,
        {"type": "CHAT", "message": "What should I practise?"},
    )
    reason = result.log[-1].reason
    assert result.log[-1].action == "chat_unavailable"
    assert "LLM unavailable" in reason
    assert reason.count("Next action:") == 1
    assert reason.endswith("Next action: Retry your message when the mentor service is available.")

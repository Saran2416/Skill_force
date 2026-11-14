"""Unit and integration tests for Curriculum Planner (agent 5)."""

from __future__ import annotations

import pytest

from contracts.schemas import (
    GapItem,
    GapReport,
    Resource,
    RoleRequirement,
    RoleRequirements,
)
from agents.planner.agent import build_roadmap
from agents.planner.prereqs import (
    PREREQUISITES,
    canonical_skill_name,
    get_prerequisites,
    has_cycle,
    topological_sort_skills,
)
from agents.planner.prompts import SYSTEM_PROMPT, StepPlan, get_mock_step_plan
import data.loader


def _make_req(role: str = "Full Stack Developer", skills: list[str] | None = None) -> RoleRequirements:
    skill_names = skills or ["HTML", "CSS", "JavaScript", "React", "Node.js"]
    return RoleRequirements(
        role=role,
        company="Acme Corp",
        requirements=[
            RoleRequirement(skill=s, level_required=3, priority="must")
            for s in skill_names
        ],
        confidence="curated",
    )


def _make_sample_gap() -> GapReport:
    """Standard sample gap with JavaScript, React, and Node.js."""
    return GapReport(
        match_percent=55.0,
        gaps=[
            GapItem(skill="JavaScript", current=1, required=3, gap=2, priority="must"),
            GapItem(skill="React", current=0, required=3, gap=3, priority="good"),
            GapItem(skill="Node.js", current=0, required=3, gap=3, priority="must"),
        ],
        strengths=["HTML", "CSS"],
    )


# -------------------------------------------------------------------------
# Core Topological Sort & Ordering Tests
# -------------------------------------------------------------------------

def test_sample_gap_topological_sort(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify sample gap yields JavaScript before React before Node.js."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, completed=["HTML", "CSS"])

    skills = [step.skill for step in roadmap.steps]
    assert skills == ["JavaScript", "React", "Node.js"]

    js_idx = skills.index("JavaScript")
    react_idx = skills.index("React")
    node_idx = skills.index("Node.js")

    assert js_idx < react_idx
    assert react_idx < node_idx
    assert [s.order for s in roadmap.steps] == [1, 2, 3]


def test_topological_sort_skills_dependency_order() -> None:
    """Verify topological sorting orders prerequisites before dependents."""
    # React depends on JavaScript; JavaScript depends on HTML and CSS
    skills = ["React", "CSS", "JavaScript", "HTML"]
    sorted_skills = topological_sort_skills(skills)

    assert sorted_skills.index("HTML") < sorted_skills.index("CSS")
    assert sorted_skills.index("CSS") < sorted_skills.index("JavaScript")
    assert sorted_skills.index("JavaScript") < sorted_skills.index("React")


# -------------------------------------------------------------------------
# Weak Skills & Revision Steps Tests
# -------------------------------------------------------------------------

def test_weak_skills_inserts_revision_step_before_main_step(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify weak_skills=['React'] inserts a status='revision' step directly before React."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, weak_skills=["React"], completed=["HTML", "CSS"])

    steps = roadmap.steps
    assert len(steps) == 4

    # Expected order: JavaScript (main), React (revision), React (main), Node.js (main)
    assert steps[0].skill == "JavaScript"
    assert steps[0].status == "todo"
    assert steps[0].order == 1

    assert steps[1].skill == "React"
    assert steps[1].status == "revision"
    assert steps[1].order == 2
    assert len(steps[1].practice_tasks) == 3
    assert steps[1].mini_project != ""

    assert steps[2].skill == "React"
    assert steps[2].status == "todo"
    assert steps[2].order == 3

    assert steps[3].skill == "Node.js"
    assert steps[3].status == "todo"
    assert steps[3].order == 4

    # Est hours: JS (8 * 2 = 16) + React rev (3) + React main (8 * 3 = 24) + Node (8 * 3 = 24) = 67
    assert roadmap.est_hours == 16 + 3 + 24 + 24


def test_weak_skills_case_insensitivity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify weak_skills matching is case-insensitive."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, weak_skills=["react"], completed=["HTML", "CSS"])
    statuses = [(s.skill, s.status) for s in roadmap.steps]
    assert ("React", "revision") in statuses


# -------------------------------------------------------------------------
# Completed Skills Skipped
# -------------------------------------------------------------------------

def test_completed_skills_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify completed skills are skipped from the roadmap."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, completed=["HTML", "CSS", "JavaScript"])

    skills = [step.skill for step in roadmap.steps]
    assert "JavaScript" not in skills
    assert skills == ["React", "Node.js"]
    assert [s.order for s in roadmap.steps] == [1, 2]


def test_all_skills_completed_returns_empty_roadmap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify roadmap is empty when all skills are completed."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(
        gap,
        req,
        completed=["HTML", "CSS", "JavaScript", "React", "Node.js"],
    )
    assert roadmap.steps == []
    assert roadmap.est_hours == 0


# -------------------------------------------------------------------------
# Missing Prerequisites Addition
# -------------------------------------------------------------------------

def test_missing_prerequisites_added_with_target_level_2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify missing prerequisites are added with target_level 2 before dependent skills."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    # Learner only has gap in React; HTML/CSS are completed, but JavaScript is missing
    gap = GapReport(
        match_percent=40.0,
        gaps=[GapItem(skill="React", current=0, required=3, gap=3, priority="must")],
        strengths=["HTML", "CSS"],
    )
    req = _make_req(skills=["React"])

    roadmap = build_roadmap(gap, req, completed=["HTML", "CSS"])

    skills = [s.skill for s in roadmap.steps]
    assert "JavaScript" in skills
    assert skills.index("JavaScript") < skills.index("React")

    js_step = next(s for s in roadmap.steps if s.skill == "JavaScript")
    assert js_step.target_level == 2


# -------------------------------------------------------------------------
# Safe Cycle Detection
# -------------------------------------------------------------------------

def test_safe_cycle_detection() -> None:
    """Verify circular dependencies are detected and resolved safely without infinite loops."""
    cyclic_prereqs = {
        "alpha": ["beta"],
        "beta": ["alpha"],
    }
    assert has_cycle(["alpha", "beta"], cyclic_prereqs) is True

    sorted_result = topological_sort_skills(["alpha", "beta"], cyclic_prereqs)
    assert len(sorted_result) == 2
    assert set(sorted_result) == {"alpha", "beta"}


def test_build_roadmap_with_cyclic_prereqs_does_not_hang(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify build_roadmap finishes and produces a valid roadmap when cycles exist."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    # Patch get_prerequisites to simulate an unexpected circular dependency
    monkeypatch.setattr(
        "agents.planner.agent.get_prerequisites",
        lambda skill: ["Node.js"] if skill.lower() == "react" else (["React"] if skill.lower() == "node.js" else []),
    )

    gap = GapReport(
        match_percent=50.0,
        gaps=[
            GapItem(skill="React", current=0, required=3, gap=3, priority="must"),
            GapItem(skill="Node.js", current=0, required=3, gap=3, priority="must"),
        ],
        strengths=[],
    )
    req = _make_req(skills=["React", "Node.js"])

    roadmap = build_roadmap(gap, req)
    skills = [s.skill for s in roadmap.steps]
    assert set(skills) == {"React", "Node.js"}
    assert len(roadmap.steps) == 2
    assert [s.order for s in roadmap.steps] == [1, 2]


# -------------------------------------------------------------------------
# Resources: Fakes / Mocks vs Real Loader
# -------------------------------------------------------------------------

def test_resources_only_from_loader_with_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify planner gets resources exclusively from get_resources and invents no URLs."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    fake_resources = {
        "javascript": [Resource(title="Verified JS", url="https://example.edu/js")],
        "react": [Resource(title="Verified React", url="https://example.edu/react")],
        "node.js": [],  # Unknown skill returns empty list
    }

    def fake_get_resources(skill: str) -> list[Resource]:
        return fake_resources.get(skill.lower(), [])

    monkeypatch.setattr("agents.planner.agent.get_resources", fake_get_resources)

    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, completed=["HTML", "CSS"])

    for step in roadmap.steps:
        expected = fake_resources.get(step.skill.lower(), [])
        assert step.resources == expected
        for res in step.resources:
            assert res.url.startswith("https://example.edu/")


def test_real_loader_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration test using the REAL data.loader (merged from Agent 1)."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    # Ensure real data.loader.get_resources is NOT mocked
    real_js_resources = data.loader.get_resources("JavaScript")
    assert len(real_js_resources) >= 2
    assert all(r.url.startswith("http") for r in real_js_resources)

    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, completed=["HTML", "CSS"])

    js_step = next(s for s in roadmap.steps if s.skill == "JavaScript")
    assert js_step.resources == real_js_resources
    assert any("mozilla.org" in r.url or "javascript.info" in r.url for r in js_step.resources)

    react_step = next(s for s in roadmap.steps if s.skill == "React")
    assert react_step.resources == data.loader.get_resources("React")
    assert any("react.dev" in r.url for r in react_step.resources)


# -------------------------------------------------------------------------
# Order, Hours, Schema & LLM Contracts
# -------------------------------------------------------------------------

def test_order_numbering_continuous(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify step order is continuously numbered 1..n."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, weak_skills=["JavaScript", "React"], completed=["HTML", "CSS"])

    orders = [s.order for s in roadmap.steps]
    assert orders == list(range(1, len(roadmap.steps) + 1))


def test_estimated_hours_calculation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify est_hours follows 8 hrs/level of gap for main steps + 3 hrs for revision steps."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = GapReport(
        match_percent=60.0,
        gaps=[
            GapItem(skill="Python", current=1, required=3, gap=2, priority="must"),
            GapItem(skill="SQL", current=2, required=3, gap=1, priority="good"),
        ],
        strengths=[],
    )
    req = _make_req(role="Data Analyst", skills=["Python", "SQL"])

    # Python: 8 * 2 = 16
    # SQL revision: 3
    # SQL main: 8 * 1 = 8
    # Total = 16 + 3 + 8 = 27
    roadmap = build_roadmap(gap, req, weak_skills=["SQL"])
    assert roadmap.est_hours == 27


def test_prerequisites_dict_covers_core_skills_for_all_five_roles() -> None:
    """Verify PREREQUISITES covers core skills across all 5 roles."""
    # Full Stack
    assert "JavaScript" in PREREQUISITES
    assert "React" in PREREQUISITES
    assert "Node.js" in PREREQUISITES
    assert "Express" in PREREQUISITES
    assert "SQL" in PREREQUISITES

    # Data Analyst
    assert "Python" in PREREQUISITES
    assert "Pandas" in PREREQUISITES
    assert "Data Visualization" in PREREQUISITES
    assert "Statistics" in PREREQUISITES

    # ML Engineer
    assert "Linear Algebra" in PREREQUISITES
    assert "Machine Learning" in PREREQUISITES
    assert "Deep Learning" in PREREQUISITES
    assert "MLOps" in PREREQUISITES

    # Cybersecurity
    assert "Networking" in PREREQUISITES
    assert "Linux" in PREREQUISITES
    assert "Security Fundamentals" in PREREQUISITES
    assert "SIEM" in PREREQUISITES
    assert "Incident Response" in PREREQUISITES

    # DevOps
    assert "Docker" in PREREQUISITES
    assert "Kubernetes" in PREREQUISITES
    assert "CI/CD" in PREREQUISITES
    assert "Monitoring" in PREREQUISITES


def test_call_llm_produces_three_practice_tasks_and_mini_project(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify each roadmap step has a non-empty mini_project and exactly 3 practice_tasks."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = _make_sample_gap()
    req = _make_req()

    roadmap = build_roadmap(gap, req, weak_skills=["React"], completed=["HTML", "CSS"])

    for step in roadmap.steps:
        assert step.mini_project != ""
        assert "\n" not in step.mini_project  # one-line mini_project
        assert len(step.practice_tasks) == 3
        assert all(isinstance(task, str) and task.strip() != "" for task in step.practice_tasks)


def test_empty_gap_returns_empty_roadmap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify empty gap report returns Roadmap(steps=[], est_hours=0)."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    gap = GapReport(match_percent=100.0, gaps=[], strengths=["Python"])
    req = _make_req()

    roadmap = build_roadmap(gap, req)
    assert roadmap.steps == []
    assert roadmap.est_hours == 0

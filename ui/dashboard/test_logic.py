"""Unit tests for the pure dashboard logic (no Streamlit involved)."""

from __future__ import annotations

from contracts.sample import SAMPLE_STATE
from contracts.schemas import (
    AppState,
    Roadmap,
    RoadmapStep,
    RoleRequirement,
    RoleRequirements,
    ScoreResult,
    Skill,
    UserProfile,
)

from ui.dashboard.logic import (
    advantages,
    disadvantages,
    known_languages,
    progress,
    required_skills_table,
)


def _empty_state() -> AppState:
    return AppState(profile=UserProfile(name="Empty"))


def _requirements(**kwargs) -> RoleRequirements:
    data = {
        "role": "Developer",
        "company": None,
        "requirements": [],
        "confidence": "curated",
    }
    data.update(kwargs)
    return RoleRequirements(**data)


# --------------------------------------------------------------------------- #
# known_languages
# --------------------------------------------------------------------------- #
def test_known_languages_sample() -> None:
    names = [skill.name for skill in known_languages(SAMPLE_STATE.profile)]
    assert names == ["Python", "SQL", "HTML", "JavaScript"]


def test_known_languages_sorted_by_level_descending() -> None:
    levels = [skill.level for skill in known_languages(SAMPLE_STATE.profile)]
    assert levels == sorted(levels, reverse=True)


def test_known_languages_case_insensitive() -> None:
    profile = UserProfile(name="x", skills=[Skill(name="pYtHoN", level=4, source="user")])
    assert [skill.name for skill in known_languages(profile)] == ["pYtHoN"]


def test_known_languages_excludes_non_languages() -> None:
    profile = UserProfile(
        name="x",
        skills=[Skill(name="Project Delivery", level=5, source="user")],
    )
    assert known_languages(profile) == []


def test_known_languages_empty_profile() -> None:
    assert known_languages(UserProfile(name="x")) == []


def test_known_languages_none_profile() -> None:
    assert known_languages(None) == []


def test_known_languages_collapses_duplicates_keeping_highest() -> None:
    profile = UserProfile(
        name="x",
        skills=[
            Skill(name="Python", level=2, source="user"),
            Skill(name="python", level=5, source="assessment"),
        ],
    )
    result = known_languages(profile)
    assert len(result) == 1
    assert result[0].level == 5


# --------------------------------------------------------------------------- #
# required_skills_table
# --------------------------------------------------------------------------- #
def test_required_skills_table_sample_order_and_status() -> None:
    rows = required_skills_table(SAMPLE_STATE)
    assert [row["skill"] for row in rows] == [
        "Python",
        "SQL",
        "JavaScript",
        "HTML",
        "Project Delivery",
    ]
    by_skill = {row["skill"]: row for row in rows}
    assert by_skill["Python"]["status"] == "met"
    assert by_skill["SQL"]["status"] == "gap"
    assert by_skill["HTML"]["status"] == "gap"
    assert by_skill["Project Delivery"]["status"] == "missing"
    assert by_skill["Project Delivery"]["current"] == 0


def test_required_skills_table_must_haves_first() -> None:
    rows = required_skills_table(SAMPLE_STATE)
    rank = {"must": 0, "good": 1, "bonus": 2}
    ranks = [rank[row["priority"]] for row in rows]
    assert ranks == sorted(ranks)


def test_required_skills_table_requirements_none() -> None:
    assert required_skills_table(_empty_state()) == []


def test_required_skills_table_none_state() -> None:
    assert required_skills_table(None) == []


def test_required_skills_table_case_insensitive_match() -> None:
    state = AppState(
        profile=UserProfile(
            name="x", skills=[Skill(name="python", level=5, source="user")]
        ),
        requirements=_requirements(
            requirements=[
                RoleRequirement(skill="Python", level_required=4, priority="must")
            ]
        ),
    )
    rows = required_skills_table(state)
    assert rows[0]["status"] == "met"
    assert rows[0]["current"] == 5


# --------------------------------------------------------------------------- #
# advantages
# --------------------------------------------------------------------------- #
def test_advantages_sample() -> None:
    items = advantages(SAMPLE_STATE)
    assert "Python is a strength." in items
    assert any("scored 82%" in item for item in items)


def test_advantages_empty_state() -> None:
    assert advantages(_empty_state()) == []


def test_advantages_none_state() -> None:
    assert advantages(None) == []


def test_advantages_above_required_and_held_cert() -> None:
    state = AppState(
        profile=UserProfile(
            name="x",
            skills=[Skill(name="Python", level=5, source="user")],
            certs=["Azure Fundamentals"],
        ),
        requirements=_requirements(
            requirements=[
                RoleRequirement(skill="Python", level_required=3, priority="must")
            ],
            certs=["Azure Fundamentals"],
        ),
    )
    items = advantages(state)
    assert any("above the required" in item for item in items)
    assert any("Azure Fundamentals" in item for item in items)


# --------------------------------------------------------------------------- #
# disadvantages
# --------------------------------------------------------------------------- #
def test_disadvantages_sample_must_first_and_missing_cert() -> None:
    items = disadvantages(SAMPLE_STATE)
    assert items[0].startswith("SQL:")
    assert items[1].startswith("JavaScript:")
    assert items[2].startswith("HTML:")
    assert "Missing certification: Azure Fundamentals." in items


def test_disadvantages_ai_estimated_includes_disclaimer() -> None:
    state = AppState(
        profile=UserProfile(name="x"),
        requirements=_requirements(
            confidence="ai_estimated", disclaimer="Estimated from job postings."
        ),
    )
    assert "Estimated from job postings." in disadvantages(state)


def test_disadvantages_low_score() -> None:
    state = AppState(
        profile=UserProfile(name="x"),
        scores=[ScoreResult(skill="SQL", score_percent=45.0, new_level=2, weak=True)],
    )
    assert any("below 60%" in item for item in disadvantages(state))


def test_disadvantages_empty_state() -> None:
    assert disadvantages(_empty_state()) == []


def test_disadvantages_none_state() -> None:
    assert disadvantages(None) == []


# --------------------------------------------------------------------------- #
# progress
# --------------------------------------------------------------------------- #
def test_progress_sample() -> None:
    assert progress(SAMPLE_STATE) == {
        "done": 0,
        "total": 4,
        "percent": 0.0,
        "next_step": "Python",
    }


def test_progress_all_done() -> None:
    state = AppState(
        profile=UserProfile(name="x"),
        roadmap=Roadmap(
            steps=[RoadmapStep(order=1, skill="Python", target_level=3, status="done")]
        ),
    )
    result = progress(state)
    assert result["done"] == 1
    assert result["total"] == 1
    assert result["percent"] == 100.0
    assert result["next_step"] is None


def test_progress_roadmap_none() -> None:
    assert progress(_empty_state()) == {
        "done": 0,
        "total": 0,
        "percent": 0.0,
        "next_step": None,
    }


def test_progress_next_step_respects_order() -> None:
    state = AppState(
        profile=UserProfile(name="x"),
        roadmap=Roadmap(
            steps=[
                RoadmapStep(order=2, skill="SQL", target_level=4, status="todo"),
                RoadmapStep(order=1, skill="Python", target_level=4, status="doing"),
            ]
        ),
    )
    assert progress(state)["next_step"] == "Python"

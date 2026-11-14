"""Tests for the Skill Analysis agent (run in mock mode)."""

from __future__ import annotations

import pytest

from agents.skill_analyst.agent import analyze_profile
from contracts.schemas import Skill


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_MOCK_LLM", "1")


def _by_name(skills: list[Skill]) -> dict[str, Skill]:
    return {skill.name: skill for skill in skills}


def test_levels_from_profile_text() -> None:
    skills = analyze_profile("Python, SQL, basic HTML", [], [])
    by_name = _by_name(skills)

    assert by_name["Python"].level >= 3
    assert by_name["SQL"].level >= 3
    assert by_name["HTML"].level == 2
    assert all(skill.source == "user" for skill in skills)


def test_comfortable_wording_maps_to_higher_level() -> None:
    skills = analyze_profile("good at python", [], [])
    by_name = _by_name(skills)

    assert by_name["Python"].level >= 4


def test_canonicalization_of_aliases() -> None:
    skills = analyze_profile("JS, ReactJS, node, postgres", [], [])
    names = {skill.name for skill in skills}

    assert {"JavaScript", "React", "Node.js", "PostgreSQL"} <= names
    assert not {"JS", "ReactJS", "node", "postgres"} & names


def test_dedupe_keeps_highest_level() -> None:
    skills = analyze_profile("Python, python, expert Python", [], [])
    python = [skill for skill in skills if skill.name == "Python"]

    assert len(python) == 1
    assert python[0].level == 5


def test_inferred_skills_are_capped_and_tagged() -> None:
    skills = analyze_profile(
        "",
        ["AWS Certified Solutions Architect Expert"],
        ["Built a Kubernetes platform with Docker and used Terraform for 10 years"],
    )
    by_name = _by_name(skills)

    assert {"AWS", "Kubernetes", "Docker", "Terraform"} <= set(by_name)
    assert all(skill.source == "inferred" for skill in skills)
    assert all(skill.level <= 3 for skill in skills)


def test_stated_skill_wins_over_inferred_source() -> None:
    skills = analyze_profile("basic HTML", [], ["Built a portfolio website"])
    html = _by_name(skills)["HTML"]

    assert html.level == 2
    assert html.source == "user"


def test_empty_profile_returns_no_skills() -> None:
    assert analyze_profile("", [], []) == []

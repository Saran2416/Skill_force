from __future__ import annotations

import json
from pathlib import Path

import pytest

from contracts.schemas import Resource
from data.loader import get_company_override, get_resources, get_role

DATA_DIR = Path(__file__).resolve().parent
ROLE_TITLES = [
    "Full Stack Developer",
    "Data Analyst",
    "Cybersecurity Analyst",
    "ML Engineer",
    "DevOps Engineer",
]


def _roles_payload() -> dict:
    return json.loads((DATA_DIR / "roles.json").read_text(encoding="utf-8"))


def _companies_payload() -> dict:
    return json.loads((DATA_DIR / "companies.json").read_text(encoding="utf-8"))


def test_every_role_skill_has_at_least_two_resources() -> None:
    for role in _roles_payload()["roles"]:
        for requirement in role["skills"]:
            skill = requirement["skill"]
            resources = get_resources(skill)
            assert len(resources) >= 2, f"{role['role']} / {skill} has too few resources"
            assert all(isinstance(resource, Resource) for resource in resources)
            assert all(resource.url.startswith("https://") for resource in resources)
            assert len({resource.url for resource in resources}) == len(resources)


def test_company_override_skills_also_have_resources() -> None:
    for company in _companies_payload()["companies"]:
        for role, override in company["overrides"].items():
            skills = [item["skill"] for item in override.get("raised_skills", [])]
            skills += [item["skill"] for item in override.get("extra_skills", [])]
            for skill in skills:
                assert len(get_resources(skill)) >= 2, f"{company['company']} / {role} / {skill}"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Full Stack Developer", "Full Stack Developer"),
        ("full stack dev", "Full Stack Developer"),
        ("Full-Stack Developer", "Full Stack Developer"),
        ("fullstack engineer", "Full Stack Developer"),
        ("senior full stack developer", "Full Stack Developer"),
        ("data analyst", "Data Analyst"),
        ("junior data analyst", "Data Analyst"),
        ("cyber security analyst", "Cybersecurity Analyst"),
        ("SOC Analyst", "Cybersecurity Analyst"),
        ("cyber", "Cybersecurity Analyst"),
        ("machine learning engineer", "ML Engineer"),
        ("ml engineer", "ML Engineer"),
        ("ML", "ML Engineer"),
        ("devops", "DevOps Engineer"),
        ("SRE", "DevOps Engineer"),
        ("cloud engineer", "DevOps Engineer"),
    ],
)
def test_fuzzy_role_lookup(query: str, expected: str) -> None:
    role = get_role(query)
    assert role["role"] == expected
    assert role["company"] is None
    assert role["confidence"] == "curated"
    assert role["skills"] == role["requirements"]
    assert role["skills"]


def test_unknown_role_raises_helpful_key_error() -> None:
    with pytest.raises(KeyError, match="Available roles"):
        get_role("Astronaut")


def test_role_lookup_returns_an_independent_copy() -> None:
    first = get_role("Data Analyst")
    first["skills"][0]["level_required"] = 5
    first["tools"].append("Made-up tool")
    second = get_role("Data Analyst")
    assert second["skills"][0]["level_required"] != 5
    assert "Made-up tool" not in second["tools"]


def test_company_override_is_case_insensitive_and_tolerant() -> None:
    override = get_company_override("zoho", "full stack dev")
    assert override is not None
    assert override["company"] == "Zoho"
    assert override["role"] == "Full Stack Developer"
    assert override["confidence"] == "curated"
    assert override["last_verified"]
    assert any(item["skill"] == "SQL" for item in override["raised_skills"])
    assert any(item["skill"] == "Java" for item in override["extra_skills"])
    assert override["interview_process"]
    assert override["typical_projects"]


def test_company_aliases_resolve() -> None:
    assert get_company_override("TATA CONSULTANCY SERVICES", "data analyst")["company"] == "TCS"
    assert get_company_override("Google LLC", "ml engineer")["company"] == "Google"
    assert get_company_override("AWS", "devops")["company"] == "Amazon"


def test_unknown_company_and_missing_pair_return_none() -> None:
    assert get_company_override("Not A Company", "Full Stack Developer") is None
    assert get_company_override("Zoho", "Astronaut") is None


def test_every_company_has_an_override_for_every_role() -> None:
    for company in _companies_payload()["companies"]:
        for role in ROLE_TITLES:
            override = get_company_override(company["company"], role)
            assert override is not None, f"{company['company']} missing {role}"


def test_resources_are_case_insensitive_and_support_aliases() -> None:
    assert get_resources("js") == get_resources("JavaScript")
    assert get_resources(" K8s ") == get_resources("Kubernetes")
    assert get_resources("powerbi") == get_resources("Power BI")


def test_unknown_skill_returns_empty_list() -> None:
    assert get_resources("Underwater Basket Weaving") == []

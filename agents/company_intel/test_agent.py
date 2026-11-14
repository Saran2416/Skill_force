"""Tests for Company & Role Intelligence agent (Agent 3)."""

from __future__ import annotations

import pytest

import agents.company_intel.agent as company_intel
from contracts.sample import SAMPLE_PROFILE
from contracts.schemas import (
    Recommendation,
    RoleRequirement,
    RoleRequirements,
    Skill,
    UserProfile,
)
from data.loader import get_company_override, get_role


# ---------------------------------------------------------------------------
# Unit tests with monkeypatched fake data
# ---------------------------------------------------------------------------

def test_get_requirements_curated_path_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_role_data = {
        "role": "Fake Engineer",
        "company": None,
        "requirements": [
            {"skill": "Python", "level_required": 2, "priority": "must", "note": "Basic scripting"},
            {"skill": "Git", "level_required": 2, "priority": "must", "note": "Commit & push"},
        ],
        "tools": ["Git", "VS Code"],
        "certs": ["Cloud Basics"],
        "interview_process": [],
        "confidence": "curated",
        "disclaimer": "Base disclaimer",
    }
    fake_override_data = {
        "company": "FakeCorp",
        "role": "Fake Engineer",
        "confidence": "curated",
        "raised_skills": [
            {"skill": "Python", "level_required": 4, "reason": "Heavy algorithmic workloads"},
        ],
        "extra_skills": [
            {"skill": "Docker", "level_required": 3, "priority": "good", "note": "Microservice containers"},
        ],
        "tools": ["Docker", "Python", "Git", "Kubernetes"],
        "certs": ["Certified Kubernetes Administrator"],
        "interview_process": ["Technical Coding", "System Design"],
    }

    monkeypatch.setattr(company_intel, "get_role", lambda role: fake_role_data)
    monkeypatch.setattr(
        company_intel, "get_company_override", lambda company, role: fake_override_data
    )

    req = company_intel.get_requirements("Fake Engineer", "FakeCorp")

    assert req.confidence == "curated"
    assert req.disclaimer == ""
    assert req.company == "FakeCorp"
    assert req.role == "Fake Engineer"

    # Verify override wins: Python level raised from 2 to 4 and note updated
    skill_map = {r.skill: r for r in req.requirements}
    assert skill_map["Python"].level_required == 4
    assert skill_map["Python"].note == "Heavy algorithmic workloads"

    # Verify extra skill added
    assert "Docker" in skill_map
    assert skill_map["Docker"].level_required == 3
    assert skill_map["Docker"].priority == "good"

    # Verify tools, certs, and interview stages overridden
    assert req.tools == ["Docker", "Python", "Git", "Kubernetes"]
    assert req.certs == ["Certified Kubernetes Administrator"]
    assert req.interview_process == ["Technical Coding", "System Design"]


def test_get_requirements_curated_no_company(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_role_data = {
        "role": "Frontend Dev",
        "company": None,
        "requirements": [
            {"skill": "JavaScript", "level_required": 3, "priority": "must", "note": ""},
        ],
        "tools": ["npm", "Git"],
        "certs": [],
        "interview_process": [],
        "confidence": "curated",
        "disclaimer": "Some disclaimer",
    }
    monkeypatch.setattr(company_intel, "get_role", lambda role: fake_role_data)

    req_none = company_intel.get_requirements("Frontend Dev", None)
    assert req_none.confidence == "curated"
    assert req_none.disclaimer == ""
    assert req_none.company is None
    assert len(req_none.requirements) == 1

    req_empty = company_intel.get_requirements("Frontend Dev", "   ")
    assert req_empty.confidence == "curated"
    assert req_empty.disclaimer == ""
    assert req_empty.company is None


def test_get_requirements_ai_estimated_path_has_disclaimer(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_role_data = {
        "role": "Backend Dev",
        "company": None,
        "requirements": [
            {"skill": "Go", "level_required": 3, "priority": "must", "note": "Concurrency"},
        ],
        "tools": ["Go", "Git"],
        "certs": [],
        "interview_process": [],
        "confidence": "curated",
    }
    monkeypatch.setattr(company_intel, "get_role", lambda role: fake_role_data)
    monkeypatch.setattr(company_intel, "get_company_override", lambda comp, role: None)

    req = company_intel.get_requirements("Backend Dev", "UnicornStartup")

    assert req.confidence == "ai_estimated"
    assert req.disclaimer == "Estimated by AI from general knowledge; verify against the official job posting."
    assert req.company == "UnicornStartup"
    assert req.role == "Backend Dev"
    assert len(req.requirements) >= 1
    assert len(req.interview_process) > 0


def test_get_requirements_unknown_company_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_role_data = {
        "role": "Data Engineer",
        "company": None,
        "requirements": [
            {"skill": "SQL", "level_required": 3, "priority": "must", "note": ""},
            {"skill": "Python", "level_required": 3, "priority": "must", "note": ""},
        ],
        "tools": ["PostgreSQL"],
        "certs": [],
        "interview_process": [],
        "confidence": "curated",
    }
    monkeypatch.setattr(company_intel, "get_role", lambda role: fake_role_data)
    monkeypatch.setattr(company_intel, "get_company_override", lambda comp, role: None)

    req = company_intel.get_requirements("Data Engineer", "CompletelyRandomUnknownCompany12345")
    assert req is not None
    assert req.confidence == "ai_estimated"
    assert req.disclaimer == "Estimated by AI from general knowledge; verify against the official job posting."
    assert req.company == "CompletelyRandomUnknownCompany12345"


# ---------------------------------------------------------------------------
# Recommendation Engine tests
# ---------------------------------------------------------------------------

def test_get_recommendations_count_between_five_and_eight() -> None:
    req = RoleRequirements(
        role="Full Stack Developer",
        company="TechCorp",
        requirements=[
            RoleRequirement(skill="React", level_required=3, priority="must"),
            RoleRequirement(skill="Node.js", level_required=3, priority="must"),
            RoleRequirement(skill="SQL", level_required=3, priority="good"),
        ],
        tools=["Git", "Postman", "Docker"],
        certs=["AWS Certified Cloud Practitioner"],
        interview_process=["Coding Assessment", "System Design"],
        confidence="curated",
        disclaimer="",
    )
    profile = UserProfile(
        name="Alex",
        skills=[Skill(name="HTML", level=3, source="user")],
        certs=[],
        projects=[],
        target_role="Full Stack Developer",
        target_company="TechCorp",
    )

    recs = company_intel.get_recommendations(req, profile)

    assert 5 <= len(recs) <= 8
    for r in recs:
        assert isinstance(r, Recommendation)
        assert r.title.strip() != ""
        assert r.why.strip() != ""
        assert r.effort_hours > 0
        assert r.type in {"project", "cert", "interview_prep", "open_source", "networking"}


def test_get_recommendations_excludes_skills_user_already_has() -> None:
    req = RoleRequirements(
        role="Full Stack Developer",
        company="Zoho",
        requirements=[
            RoleRequirement(skill="Python", level_required=3, priority="must"),
            RoleRequirement(skill="SQL", level_required=4, priority="must"),
            RoleRequirement(skill="React", level_required=3, priority="good"),
            RoleRequirement(skill="Docker", level_required=3, priority="good"),
        ],
        tools=["Git", "Docker", "VS Code"],
        certs=["AWS Certified Cloud Practitioner", "Microsoft Certified: Azure Fundamentals"],
        interview_process=["Technical interview", "HR interview"],
        confidence="curated",
        disclaimer="",
    )

    # User already has Python (level 4), SQL (level 4), the AWS cert, and an e-commerce project
    profile = UserProfile(
        name="Bhavna",
        skills=[
            Skill(name="Python", level=4, source="user"),
            Skill(name="SQL", level=4, source="user"),
        ],
        certs=["AWS Certified Cloud Practitioner"],
        projects=["E-Commerce Product Portal"],
        target_role="Full Stack Developer",
        target_company="Zoho",
    )

    recs = company_intel.get_recommendations(req, profile)

    assert len(recs) >= 5

    user_skills = {"python", "sql"}
    user_certs = {"aws certified cloud practitioner"}
    user_projects = {"e-commerce product portal"}

    for r in recs:
        title_lower = r.title.lower()

        # Should not recommend the certification user already possesses
        for c in user_certs:
            assert c not in title_lower, f"Recommended cert user already has: {r.title}"

        # Should not recommend the project user already completed
        for p in user_projects:
            assert p not in title_lower, f"Recommended project user already built: {r.title}"

        # Should not recommend learning or featuring skills user already mastered
        for s in user_skills:
            assert f"learn {s}" not in title_lower, f"Recommended learning existing skill {s}: {r.title}"
            assert f"featuring {s}" not in title_lower, f"Recommended project featuring existing skill {s}: {r.title}"


def test_get_recommendations_covers_diverse_categories() -> None:
    req = RoleRequirements(
        role="Cybersecurity Analyst",
        company="TCS",
        requirements=[
            RoleRequirement(skill="SIEM", level_required=3, priority="must"),
            RoleRequirement(skill="Network Security", level_required=3, priority="must"),
        ],
        tools=["Wireshark", "Splunk", "Linux"],
        certs=["CompTIA Security+"],
        interview_process=["TCS National Qualifier Test (NQT)", "Technical interview"],
        confidence="curated",
        disclaimer="",
    )
    profile = UserProfile(
        name="Charlie",
        skills=[],
        certs=[],
        projects=[],
        target_role="Cybersecurity Analyst",
        target_company="TCS",
    )

    recs = company_intel.get_recommendations(req, profile)
    types_present = {r.type for r in recs}

    assert "project" in types_present
    assert "cert" in types_present
    assert "interview_prep" in types_present
    assert "open_source" in types_present
    assert "networking" in types_present


def test_get_recommendations_when_user_has_all_skills() -> None:
    req = RoleRequirements(
        role="Data Analyst",
        company="Google",
        requirements=[
            RoleRequirement(skill="SQL", level_required=4, priority="must"),
            RoleRequirement(skill="Python", level_required=3, priority="must"),
        ],
        tools=["SQL", "Python", "BigQuery"],
        certs=["Google Data Analytics Certificate"],
        interview_process=["Technical interview", "Team match"],
        confidence="curated",
        disclaimer="",
    )
    profile = UserProfile(
        name="Deepa",
        skills=[
            Skill(name="SQL", level=5, source="user"),
            Skill(name="Python", level=5, source="user"),
        ],
        certs=["Google Data Analytics Certificate"],
        projects=["BigQuery Revenue Pipeline"],
        target_role="Data Analyst",
        target_company="Google",
    )

    recs = company_intel.get_recommendations(req, profile)
    assert 5 <= len(recs) <= 8
    # Ensure Google Data Analytics is not recommended again
    for r in recs:
        assert "Google Data Analytics Certificate" not in r.title


# ---------------------------------------------------------------------------
# Integration tests with REAL data.loader (Agent 1 real data)
# ---------------------------------------------------------------------------

def test_real_loader_curated_override_integration() -> None:
    """Verify integration against real data.loader with curated Zoho override."""
    req = company_intel.get_requirements("Full Stack Developer", "Zoho")

    assert req.confidence == "curated"
    assert req.disclaimer == ""
    assert req.company == "Zoho"
    assert req.role == "Full Stack Developer"

    skill_map = {r.skill: r for r in req.requirements}
    # Base SQL was level 3; Zoho override raised it to 4
    assert skill_map["SQL"].level_required == 4
    assert "Zoho" in skill_map["SQL"].note or "data-heavy" in skill_map["SQL"].note.lower()

    # Zoho extra skill Java should be present
    assert "Java" in skill_map
    assert skill_map["Java"].level_required == 3

    # Tools should match Zoho override
    assert "Java" in req.tools
    assert "Spring Boot" in req.tools
    assert "Git" in req.tools

    # Interview process should reflect Zoho's written test
    assert any("written test" in step.lower() for step in req.interview_process)


def test_real_loader_base_only_integration() -> None:
    """Verify integration against real data.loader when company is None."""
    req = company_intel.get_requirements("Data Analyst", None)

    assert req.confidence == "curated"
    assert req.disclaimer == ""
    assert req.company is None
    assert req.role == "Data Analyst"
    assert len(req.requirements) >= 4
    skill_names = {r.skill for r in req.requirements}
    assert "SQL" in skill_names
    assert "Spreadsheets" in skill_names


def test_real_loader_ai_estimated_integration() -> None:
    """Verify integration against real data.loader when company is not in curated data."""
    req = company_intel.get_requirements("Full Stack Developer", "Stripe")

    assert req.confidence == "ai_estimated"
    assert req.disclaimer == "Estimated by AI from general knowledge; verify against the official job posting."
    assert req.company == "Stripe"
    assert req.role == "Full Stack Developer"
    assert len(req.requirements) >= 5
    assert len(req.tools) > 0
    assert len(req.interview_process) > 0


def test_real_loader_recommendations_with_sample_profile() -> None:
    """Verify recommendations engine using real requirements and sample profile."""
    req = company_intel.get_requirements("Full Stack Developer", "Zoho")
    recs = company_intel.get_recommendations(req, SAMPLE_PROFILE)

    assert 5 <= len(recs) <= 8

    # SAMPLE_PROFILE certs contains "Google Data Analytics"
    for r in recs:
        assert "Google Data Analytics" not in r.title

    # SAMPLE_PROFILE projects contains "Personal portfolio website" and "Sales dashboard mockup"
    for r in recs:
        assert "Personal portfolio website" not in r.title
        assert "Sales dashboard mockup" not in r.title

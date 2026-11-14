"""Company & Role Intelligence agent.

Provides curated and AI-estimated role requirements and tailored career recommendations.
"""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel, Field

from contracts.llm import call_llm
from contracts.schemas import Recommendation, RoleRequirement, RoleRequirements, UserProfile
from data.loader import get_company_override, get_role

from .prompts import (
    GUARDRAILS,
    RECOMMENDATIONS_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_recommendations_prompt,
    build_requirements_prompt,
)

__all__ = ["get_requirements", "get_recommendations"]

ESTIMATED_DISCLAIMER = (
    "Estimated by AI from general knowledge; verify against the official job posting."
)

VALID_REC_TYPES = {"project", "cert", "interview_prep", "open_source", "networking"}


class RecommendationsResponse(BaseModel):
    """Container schema for structured LLM recommendation outputs."""

    recommendations: list[Recommendation] = Field(default_factory=list)


def _to_role_requirement(item: dict[str, Any] | RoleRequirement) -> RoleRequirement:
    """Normalize raw dictionaries or RoleRequirement instances into a RoleRequirement."""
    if isinstance(item, RoleRequirement):
        return item.model_copy()
    return RoleRequirement(
        skill=str(item["skill"]),
        level_required=int(item["level_required"]),
        priority=item.get("priority", "must"),
        note=str(item.get("note", "") or ""),
    )


def _normalize_name(name: str | None) -> str:
    """Return a lower-cased stripped string for insensitive matching."""
    return str(name or "").strip().casefold()


def _merge_override_data(
    base_requirements: list[RoleRequirement],
    base_tools: list[str],
    base_certs: list[str],
    base_interview_process: list[str],
    override: dict[str, Any],
) -> tuple[list[RoleRequirement], list[str], list[str], list[str]]:
    """Merge curated override payload onto base role requirements (override wins)."""
    req_map: dict[str, RoleRequirement] = {
        _normalize_name(req.skill): req.model_copy() for req in base_requirements
    }

    # 1. Raised skills (override level and optional reason)
    for raised in override.get("raised_skills", []):
        skill_name = str(raised["skill"])
        key = _normalize_name(skill_name)
        new_level = int(raised["level_required"])
        reason = str(raised.get("reason", "") or "")
        if key in req_map:
            req_map[key].level_required = new_level
            if reason:
                req_map[key].note = reason
        else:
            req_map[key] = RoleRequirement(
                skill=skill_name,
                level_required=new_level,
                priority="must",
                note=reason,
            )

    # 2. Extra skills
    for extra in override.get("extra_skills", []):
        skill_name = str(extra["skill"])
        key = _normalize_name(skill_name)
        new_level = int(extra["level_required"])
        priority = extra.get("priority", "good")
        note = str(extra.get("note", "") or "")
        if key in req_map:
            req_map[key].level_required = new_level
            req_map[key].priority = priority
            if note:
                req_map[key].note = note
        else:
            req_map[key] = RoleRequirement(
                skill=skill_name,
                level_required=new_level,
                priority=priority,
                note=note,
            )

    # 3. Direct requirements or skills if present in override
    direct_reqs = override.get("requirements") or override.get("skills") or []
    for item in direct_reqs:
        parsed = _to_role_requirement(item)
        key = _normalize_name(parsed.skill)
        if key in req_map:
            req_map[key].level_required = parsed.level_required
            req_map[key].priority = parsed.priority
            if parsed.note:
                req_map[key].note = parsed.note
        else:
            req_map[key] = parsed

    # 4. Tools, certs, and interview_process: override replaces base if provided
    merged_tools = (
        list(override["tools"]) if "tools" in override else list(base_tools)
    )
    merged_certs = (
        list(override["certs"]) if "certs" in override else list(base_certs)
    )
    merged_interview_process = (
        list(override["interview_process"])
        if "interview_process" in override
        else list(base_interview_process)
    )

    return list(req_map.values()), merged_tools, merged_certs, merged_interview_process


def _merge_estimated_data(
    base_requirements: list[RoleRequirement],
    base_tools: list[str],
    base_certs: list[str],
    base_interview_process: list[str],
    estimated: RoleRequirements,
) -> tuple[list[RoleRequirement], list[str], list[str], list[str]]:
    """Merge an AI estimate onto base role requirements."""
    req_map: dict[str, RoleRequirement] = {
        _normalize_name(req.skill): req.model_copy() for req in base_requirements
    }

    for item in estimated.requirements:
        key = _normalize_name(item.skill)
        if key in req_map:
            req_map[key].level_required = item.level_required
            req_map[key].priority = item.priority
            if item.note:
                req_map[key].note = item.note
        else:
            req_map[key] = item.model_copy()

    # Tools: preserve base tools and append any new distinct estimated tools
    seen_tools = {_normalize_name(t) for t in base_tools}
    merged_tools = list(base_tools)
    for tool in estimated.tools:
        k = _normalize_name(tool)
        if k and k not in seen_tools:
            seen_tools.add(k)
            merged_tools.append(tool.strip())

    # Certs: preserve base certs and append any new distinct estimated certs
    seen_certs = {_normalize_name(c) for c in base_certs}
    merged_certs = list(base_certs)
    for cert in estimated.certs:
        k = _normalize_name(cert)
        if k and k not in seen_certs:
            seen_certs.add(k)
            merged_certs.append(cert.strip())

    # Interview process: estimated takes priority if non-empty, else base
    merged_interview = (
        list(estimated.interview_process)
        if estimated.interview_process
        else list(base_interview_process)
    )
    if not merged_interview:
        merged_interview = [
            "Technical Screen",
            "Technical Deep Dive / Coding",
            "Values and Culture Fit",
        ]

    return list(req_map.values()), merged_tools, merged_certs, merged_interview


def get_requirements(role: str, company: str | None) -> RoleRequirements:
    """Return a role requirement set for a company and target role.

    1. Starts from get_role(role) as base requirements.
    2. If company is provided and get_company_override(company, role) returns data,
       merges it (override wins), setting confidence="curated" and disclaimer="".
    3. If company is provided but no override exists, calls call_llm for a company-specific
       estimate, merges it onto base, setting confidence="ai_estimated" and disclaimer.
    4. If company is None, returns base role only with confidence="curated".
    """
    base_data = get_role(role)

    if isinstance(base_data, RoleRequirements):
        base_role = base_data.role
        base_reqs = [r.model_copy() for r in base_data.requirements]
        base_tools = list(base_data.tools)
        base_certs = list(base_data.certs)
        base_interview_process = list(base_data.interview_process)
    else:
        base_role = str(base_data.get("role", role))
        raw_reqs = base_data.get("requirements") or base_data.get("skills", [])
        base_reqs = [_to_role_requirement(item) for item in raw_reqs]
        base_tools = list(base_data.get("tools", []))
        base_certs = list(base_data.get("certs", []))
        base_interview_process = list(base_data.get("interview_process", []))

    clean_company = company.strip() if company and isinstance(company, str) and company.strip() else None

    # Case d: company is None -> base role only
    if clean_company is None:
        return RoleRequirements(
            role=base_role,
            company=None,
            requirements=base_reqs,
            tools=base_tools,
            certs=base_certs,
            interview_process=base_interview_process,
            confidence="curated",
            disclaimer="",
        )

    # Check for curated company override
    override = get_company_override(clean_company, base_role)
    if override is None and base_role != role:
        override = get_company_override(clean_company, role)

    # Case b: Curated override exists
    if override is not None:
        merged_reqs, merged_tools, merged_certs, merged_interview = _merge_override_data(
            base_requirements=base_reqs,
            base_tools=base_tools,
            base_certs=base_certs,
            base_interview_process=base_interview_process,
            override=override,
        )
        return RoleRequirements(
            role=override.get("role", base_role),
            company=override.get("company", clean_company),
            requirements=merged_reqs,
            tools=merged_tools,
            certs=merged_certs,
            interview_process=merged_interview,
            confidence="curated",
            disclaimer="",
        )

    # Case c: Company given but no curated override exists -> call_llm
    mock_estimate = RoleRequirements(
        role=base_role,
        company=clean_company,
        requirements=[
            RoleRequirement(
                skill=req.skill,
                level_required=req.level_required,
                priority=req.priority,
                note=req.note or f"Required for {clean_company}",
            )
            for req in base_reqs
        ],
        tools=base_tools if base_tools else ["Git"],
        certs=base_certs,
        interview_process=[
            "Online Assessment / Coding Challenge",
            "Technical Problem Solving Screen",
            "System Architecture & Deep Dive Round",
            "Hiring Manager & Team Fit Interview",
        ],
        confidence="ai_estimated",
        disclaimer=ESTIMATED_DISCLAIMER,
    )

    user_prompt = build_requirements_prompt(
        role=base_role,
        company=clean_company,
        base_skills=[r.skill for r in base_reqs],
    )

    estimated = call_llm(
        system=SYSTEM_PROMPT,
        user=user_prompt,
        schema=RoleRequirements,
        mock=mock_estimate,
    )

    if not isinstance(estimated, RoleRequirements):
        estimated = RoleRequirements.model_validate(estimated)

    merged_reqs, merged_tools, merged_certs, merged_interview = _merge_estimated_data(
        base_requirements=base_reqs,
        base_tools=base_tools,
        base_certs=base_certs,
        base_interview_process=base_interview_process,
        estimated=estimated,
    )

    return RoleRequirements(
        role=base_role,
        company=clean_company,
        requirements=merged_reqs,
        tools=merged_tools,
        certs=merged_certs,
        interview_process=merged_interview,
        confidence="ai_estimated",
        disclaimer=ESTIMATED_DISCLAIMER,
    )


# ---------------------------------------------------------------------------
# Recommendation Engine
# ---------------------------------------------------------------------------

def _build_mock_recommendations(
    req: RoleRequirements, profile: UserProfile
) -> list[Recommendation]:
    """Construct 5-8 recommendations tailored to role, company, and learner profile.

    Skips skills, certifications, and projects the user already possesses.
    """
    user_skill_levels = {_normalize_name(s.name): s.level for s in profile.skills}
    user_certs = {_normalize_name(c) for c in profile.certs}
    user_projects = {_normalize_name(p) for p in profile.projects}

    company_name = req.company or profile.target_company or ""
    role_name = req.role or profile.target_role or "Software Engineer"

    # Identify missing skills and gap skills
    missing_reqs = [
        r for r in req.requirements if _normalize_name(r.skill) not in user_skill_levels
    ]
    gap_reqs = [
        r
        for r in req.requirements
        if _normalize_name(r.skill) in user_skill_levels
        and user_skill_levels[_normalize_name(r.skill)] < r.level_required
    ]
    priority_skills = missing_reqs + gap_reqs

    recs: list[Recommendation] = []

    # 1. Project recommendation 1: Portfolio project matching company domain
    company_lower = _normalize_name(company_name)
    if "zoho" in company_lower:
        domain_desc = "multi-tenant business SaaS module (CRM & workplace workflows)"
    elif "tcs" in company_lower:
        domain_desc = "enterprise service portal with automated client reporting"
    elif "infosys" in company_lower:
        domain_desc = "enterprise cloud modernization and analytics dashboard"
    elif "google" in company_lower:
        domain_desc = "high-performance distributed service with observability"
    elif "amazon" in company_lower:
        domain_desc = "scalable cloud-native order processing service"
    elif "freshworks" in company_lower:
        domain_desc = "customer support ticketing and webhook automation system"
    elif company_name:
        domain_desc = f"{company_name}-aligned production service module"
    else:
        domain_desc = f"{role_name} full-stack production application"

    primary_skill = (
        priority_skills[0].skill if priority_skills else "System Architecture"
    )
    p1_title = f"Build a {domain_desc} featuring {primary_skill}"
    if _normalize_name(p1_title) not in user_projects:
        recs.append(
            Recommendation(
                title=p1_title,
                type="project",
                why=(
                    f"Directly showcases hands-on capability in {primary_skill} "
                    f"tailored to {company_name or 'the target role'}'s operational domain."
                ),
                effort_hours=24,
            )
        )

    # 2. Certification recommendation (skip what user already has)
    available_req_certs = [
        c for c in req.certs if _normalize_name(c) not in user_certs
    ]
    chosen_cert: str | None = None
    if available_req_certs:
        chosen_cert = available_req_certs[0]
    else:
        # Fallback certs by domain
        role_lower = _normalize_name(role_name)
        if "data" in role_lower:
            fallbacks = [
                "Microsoft Certified: Power BI Data Analyst Associate",
                "Google Data Analytics Professional Certificate",
            ]
        elif "security" in role_lower or "cyber" in role_lower:
            fallbacks = [
                "CompTIA Security+",
                "Microsoft Certified: Security Operations Analyst Associate",
            ]
        elif "ml" in role_lower or "machine" in role_lower:
            fallbacks = [
                "TensorFlow Developer Certificate",
                "AWS Certified Machine Learning - Specialty",
            ]
        elif "devops" in role_lower or "cloud" in role_lower:
            fallbacks = [
                "Certified Kubernetes Administrator (CKA)",
                "HashiCorp Certified: Terraform Associate",
            ]
        else:
            fallbacks = [
                "AWS Certified Cloud Practitioner",
                "Microsoft Certified: Azure Fundamentals",
                "Meta Front-End Developer Professional Certificate",
            ]
        for candidate in fallbacks:
            if _normalize_name(candidate) not in user_certs:
                chosen_cert = candidate
                break

    if chosen_cert:
        recs.append(
            Recommendation(
                title=f"Earn {chosen_cert} certification",
                type="cert",
                why=(
                    f"Provides recognized, third-party validation for {role_name} "
                    f"standards at {company_name or 'target tech companies'}."
                ),
                effort_hours=28,
            )
        )

    # 3. Interview prep: DSA / Aptitude / Written test
    has_aptitude_or_written = any(
        any(term in stage.lower() for term in ["aptitude", "written", "nqt", "assessment"])
        for stage in req.interview_process
    )
    if company_name and has_aptitude_or_written:
        dsa_title = f"Prepare for {company_name} aptitude, reasoning, and programming assessments"
        dsa_why = (
            f"Directly targets the initial written evaluation stages used by {company_name}."
        )
        dsa_hours = 18
    else:
        dsa_title = "Practice core data structures, algorithms, and technical problem solving"
        dsa_why = (
            "Builds speed, algorithmic efficiency, and edge-case rigor for live coding rounds."
        )
        dsa_hours = 20

    recs.append(
        Recommendation(
            title=dsa_title,
            type="interview_prep",
            why=dsa_why,
            effort_hours=dsa_hours,
        )
    )

    # 4. Interview prep: System Design / Technical Architecture
    recs.append(
        Recommendation(
            title="Prepare for system design, API modeling, and architecture interviews",
            type="interview_prep",
            why=(
                f"Essential for demonstrating trade-off evaluation, scalability, and "
                f"production design principles expected for {role_name}."
            ),
            effort_hours=16,
        )
    )

    # 5. Open-source contribution
    # Target a tool from req.tools that user hasn't mastered yet
    unmatched_tools = [
        t for t in req.tools if _normalize_name(t) not in user_skill_levels
    ]
    target_tool = (
        unmatched_tools[0] if unmatched_tools else (req.tools[0] if req.tools else "developer tooling")
    )
    recs.append(
        Recommendation(
            title=f"Contribute bug fixes or documentation to open-source {target_tool} repositories",
            type="open_source",
            why=(
                "Demonstrates real-world version control collaboration, issue triage, "
                "and clean code contribution in public codebases."
            ),
            effort_hours=14,
        )
    )

    # 6. Networking
    net_target = company_name if company_name else f"{role_name} industry professionals"
    recs.append(
        Recommendation(
            title=f"Connect with engineering practitioners and alumni at {net_target}",
            type="networking",
            why=(
                f"Uncovers team culture insights, interview expectations, and potential "
                f"referral opportunities at {net_target}."
            ),
            effort_hours=6,
        )
    )

    # 7. Additional Project or Mock Drill if needed to enrich portfolio
    if len(priority_skills) >= 2:
        sec_skill = priority_skills[1].skill
        sec_title = f"Develop an automated integration workflow highlighting {sec_skill}"
        if _normalize_name(sec_title) not in user_projects:
            recs.append(
                Recommendation(
                    title=sec_title,
                    type="project",
                    why=(
                        f"Closes your preparation gap in {sec_skill} with a tangible, "
                        "reviewable code repository."
                    ),
                    effort_hours=18,
                )
            )
    else:
        recs.append(
            Recommendation(
                title=f"Conduct mock technical interview sessions tailored to {company_name or role_name}",
                type="interview_prep",
                why="Refines verbal explanation of technical decisions under timed interview conditions.",
                effort_hours=8,
            )
        )

    return recs


def _filter_and_validate_recommendations(
    raw_recommendations: list[Recommendation],
    req: RoleRequirements,
    profile: UserProfile,
    fallback_recs: list[Recommendation],
) -> list[Recommendation]:
    """Validate recommendations, filter out items the user already has, and enforce 5-8 items."""
    user_skill_levels = {_normalize_name(s.name): s.level for s in profile.skills}
    user_certs = {_normalize_name(c) for c in profile.certs}
    user_projects = {_normalize_name(p) for p in profile.projects}

    filtered: list[Recommendation] = []
    seen_titles: set[str] = set()

    def is_acceptable(rec: Recommendation) -> bool:
        if rec.type not in VALID_REC_TYPES:
            return False
        if not rec.title or not rec.why:
            return False

        norm_title = _normalize_name(rec.title)
        if norm_title in seen_titles:
            return False

        # Exclude certs the user already has
        if rec.type == "cert":
            for existing_cert in user_certs:
                if existing_cert and existing_cert in norm_title:
                    return False

        # Exclude projects the user already completed
        if rec.type == "project":
            for existing_proj in user_projects:
                if existing_proj and existing_proj in norm_title:
                    return False

        # Exclude recommendations that advise learning skills the user already has
        for skill_name in user_skill_levels:
            if not skill_name:
                continue
            # Check for patterns like "Learn <skill>", "featuring <skill>", "in <skill>"
            # when user already possesses that skill
            learn_pattern = f"learn {skill_name}"
            feature_pattern = f"featuring {skill_name}"
            if learn_pattern in norm_title or feature_pattern in norm_title:
                return False

        return True

    for item in raw_recommendations:
        if is_acceptable(item):
            seen_titles.add(_normalize_name(item.title))
            filtered.append(
                Recommendation(
                    title=item.title.strip(),
                    type=item.type,
                    why=item.why.strip(),
                    effort_hours=max(1, int(item.effort_hours)),
                )
            )

    # Replenish from fallback recommendations if filtered count < 5
    if len(filtered) < 5:
        for fallback in fallback_recs:
            if is_acceptable(fallback):
                seen_titles.add(_normalize_name(fallback.title))
                filtered.append(
                    Recommendation(
                        title=fallback.title.strip(),
                        type=fallback.type,
                        why=fallback.why.strip(),
                        effort_hours=max(1, int(fallback.effort_hours)),
                    )
                )
            if len(filtered) >= 5:
                break

    # Cap at 8 recommendations
    return filtered[:8]


def get_recommendations(
    req: RoleRequirements, profile: UserProfile
) -> list[Recommendation]:
    """Recommend 5-8 actions based on target role requirements and user profile.

    Tailors recommendations to company domain and user's current skills while
    skipping certifications, projects, and skills the user already has.
    """
    mock_recs = _build_mock_recommendations(req, profile)

    user_prompt = build_recommendations_prompt(req, profile)

    response = call_llm(
        system=RECOMMENDATIONS_SYSTEM_PROMPT,
        user=user_prompt,
        schema=RecommendationsResponse,
        mock=RecommendationsResponse(recommendations=mock_recs),
    )

    if not isinstance(response, RecommendationsResponse):
        response = RecommendationsResponse.model_validate(response)

    return _filter_and_validate_recommendations(
        raw_recommendations=response.recommendations,
        req=req,
        profile=profile,
        fallback_recs=mock_recs,
    )

"""Prompts and guardrails for the Company & Role Intelligence agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contracts.schemas import RoleRequirements, UserProfile

SYSTEM_PROMPT = (
    "You are a career research analyst. Given a role and a company, list the skills, tools, "
    "certifications and interview stages typically expected, using only well-known public "
    "information. If you are not confident about a detail, omit it. "
    "Output ONLY JSON matching the schema."
)

GUARDRAILS = (
    "Guardrails: Never fabricate salaries, internal team names, hiring numbers or deadlines; "
    "speak in skills, tools and interview patterns; omit details you're unsure of."
)

RECOMMENDATIONS_SYSTEM_PROMPT = (
    "You are a career research analyst and technical mentor. Given role requirements and a "
    "learner profile, recommend 5 to 8 concrete actions to close skill gaps and improve readiness. "
    "Include portfolio projects matching the company domain, certifications, interview prep "
    "(DSA, system design, aptitude), open-source ideas, and networking. "
    f"{GUARDRAILS} "
    "Skip skills, certifications, and projects the user already has. "
    "Output ONLY JSON matching the schema."
)


def build_requirements_prompt(role: str, company: str, base_skills: list[str] | None = None) -> str:
    """Build the user prompt for company-specific role requirement estimation."""
    skills_context = f"Base role skills: {', '.join(base_skills)}\n" if base_skills else ""
    return (
        f"Target Role: {role}\n"
        f"Target Company: {company}\n"
        f"{skills_context}"
        f"{GUARDRAILS}\n\n"
        f"Estimate the expected requirements, tools, certs, and interview stages for {role} at {company}."
    )


def build_recommendations_prompt(req: RoleRequirements, profile: UserProfile) -> str:
    """Build the user prompt for generating tailored career recommendations."""
    current_skills = [f"{s.name} (level {s.level})" for s in profile.skills]
    req_skills = [f"{r.skill} (level {r.level_required}, {r.priority})" for r in req.requirements]

    return (
        f"Target Role: {req.role}\n"
        f"Target Company: {req.company or 'General / Industry Standard'}\n"
        f"Required Skills: {', '.join(req_skills)}\n"
        f"Required Tools: {', '.join(req.tools)}\n"
        f"Certifications: {', '.join(req.certs)}\n"
        f"Interview Process: {' -> '.join(req.interview_process)}\n\n"
        f"Learner Name: {profile.name}\n"
        f"Current Skills (already acquired): {', '.join(current_skills) if current_skills else 'None'}\n"
        f"Current Certifications (already acquired): {', '.join(profile.certs) if profile.certs else 'None'}\n"
        f"Completed Projects (already done): {', '.join(profile.projects) if profile.projects else 'None'}\n\n"
        f"{GUARDRAILS}\n"
        "Provide 5-8 actionable recommendations. Do NOT recommend skills, certs, or projects the user already has."
    )

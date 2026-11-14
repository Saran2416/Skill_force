from __future__ import annotations

from contracts.schemas import Resource


def get_role(role: str) -> dict:
    """Return a minimal role dictionary for the requested job title."""
    return {"role": role, "company": None, "tools": [], "certs": []}


def get_company_override(company: str, role: str) -> dict | None:
    """Return an optional override payload for a company and role pair."""
    return None


def get_resources(skill: str) -> list[Resource]:
    """Return sample learning resources for a skill."""
    return [
        Resource(title=f"{skill} fundamentals", url=f"https://example.com/{skill.lower().replace(' ', '-')}-fundamentals"),
        Resource(title=f"Practice {skill}", url=f"https://example.com/practice-{skill.lower().replace(' ', '-')}")
    ]

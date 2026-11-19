"""Profile parsing helpers and dictionaries for the Profile form.

Streamlit-free port of the helpers that used to live in ``ui/tab_profile.py``
when the frontend migrated to React. The parsing rules are unchanged, so the
API produces the same ``Skill``/cert/project lists the old form did.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from contracts.schemas import AppState, Skill

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_skill_dictionary() -> list[str]:
    skills: set[str] = set()
    try:
        resources = json.loads((_DATA_DIR / "resources.json").read_text(encoding="utf-8"))
        skills.update((resources.get("skills") or {}).keys())
    except Exception:
        pass
    try:
        roles = json.loads((_DATA_DIR / "roles.json").read_text(encoding="utf-8"))
        for role in roles.get("roles", []):
            for item in role.get("skills", role.get("requirements", [])):
                name = item.get("skill") or item.get("name")
                if name:
                    skills.add(str(name))
    except Exception:
        pass
    if not skills:
        skills.update(
            [
                "Python",
                "SQL",
                "JavaScript",
                "HTML",
                "CSS",
                "React",
                "Node.js",
                "Git",
                "REST APIs",
                "Pandas",
                "Spreadsheets",
                "Data Visualization",
                "Statistics",
                "Machine Learning",
                "Docker",
                "Linux",
            ]
        )
    return sorted(skills, key=lambda s: s.lower())


def _load_cert_dictionary() -> list[str]:
    certs: set[str] = set()
    try:
        roles = json.loads((_DATA_DIR / "roles.json").read_text(encoding="utf-8"))
        for role in roles.get("roles", []):
            for cert in role.get("certs", []):
                if cert:
                    certs.add(str(cert))
    except Exception:
        pass
    certs.update(
        [
            "AWS Certified Cloud Practitioner",
            "Microsoft Certified: Azure Fundamentals",
            "Google Data Analytics Professional Certificate",
            "CompTIA Security+",
            "CompTIA Network+",
            "Certified Kubernetes Administrator (CKA)",
        ]
    )
    return sorted(certs, key=lambda s: s.lower())


KNOWN_SKILLS = _load_skill_dictionary()
KNOWN_CERTS = _load_cert_dictionary()


def parse_skills_input(text: str, existing_skills: list[Skill] | None = None) -> list[Skill]:
    """Parse free-text skill input into a list of Skill objects.

    Accepts newline- or comma-separated entries such as:
      Python: 3
      SQL: 4
      HTML
      React (3)
    """
    existing_map = {
        s.name.strip().casefold(): s.level for s in (existing_skills or [])
    }
    skills: list[Skill] = []
    seen: set[str] = set()

    # Split by newlines or commas
    tokens = re.split(r"[\n,]+", text)
    for raw in tokens:
        token = raw.strip()
        if not token:
            continue

        # Look for "Name: Level" or "Name (Level)" or bare "Name"
        match = re.match(r"^([^:()]+?)(?:[:(]\s*(\d+)\s*\)?)?$", token)
        if not match:
            continue

        name = match.group(1).strip()
        level_str = match.group(2)
        norm_key = name.casefold()

        if not name or norm_key in seen:
            continue
        seen.add(norm_key)

        if level_str is not None:
            level = max(0, min(5, int(level_str)))
        elif norm_key in existing_map:
            level = existing_map[norm_key]
        else:
            level = 3

        skills.append(Skill(name=name, level=level, source="user"))

    return skills


def parse_list_input(text: str) -> list[str]:
    """Parse newline- or comma-separated text into a clean list of strings."""
    items: list[str] = []
    seen: set[str] = set()
    for token in re.split(r"[\n,]+", text):
        clean = token.strip()
        if clean and clean.casefold() not in seen:
            seen.add(clean.casefold())
            items.append(clean)
    return items


def is_fresh_profile(state: AppState, user_id: str) -> bool:
    """Treat newly created/default profiles as blank so users fill details themselves."""
    profile = state.profile
    name = (profile.name or "").strip()
    has_meaningful_data = bool(
        profile.skills
        or profile.certs
        or profile.projects
        or (profile.target_role or "").strip()
        or profile.target_company
        or state.requirements
        or state.gap
        or state.roadmap
        or state.scores
    )
    return not has_meaningful_data and (not name or name == user_id)


def profile_complete(state: AppState) -> bool:
    """A profile is complete once name, skills, and target role are all set."""
    profile = state.profile
    has_target = bool((profile.target_role or "").strip())
    has_name = bool((profile.name or "").strip())
    has_skills = bool(profile.skills)
    return has_target and has_name and has_skills

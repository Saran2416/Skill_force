"""Curated role, company, and learning-resource data for SkillPath.

The JSON files in this package are the source of truth. Public lookups are
case-insensitive and accept common aliases (for example, "full stack dev",
"k8s", or "Tata Consultancy Services").
"""

from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from contracts.schemas import Resource

_DATA_DIR = Path(__file__).resolve().parent
_ROLES_FILE = _DATA_DIR / "roles.json"
_COMPANIES_FILE = _DATA_DIR / "companies.json"
_RESOURCES_FILE = _DATA_DIR / "resources.json"

_NON_WORD_RE = re.compile(r"[^a-z0-9+#]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(value: str) -> str:
    """Normalize a title for case-, punctuation-, and spacing-insensitive lookup."""

    text = value.strip().lower().replace("&", " and ")
    text = _NON_WORD_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _contains_phrase(haystack: str, needle: str) -> bool:
    """Return True when ``needle`` appears as a whole phrase inside ``haystack``."""

    if not haystack or not needle:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required data file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Data file contains invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Data file must contain a JSON object: {path}")
    return payload


@lru_cache(maxsize=1)
def _roles_payload() -> dict[str, Any]:
    return _read_json(_ROLES_FILE)


@lru_cache(maxsize=1)
def _companies_payload() -> dict[str, Any]:
    return _read_json(_COMPANIES_FILE)


@lru_cache(maxsize=1)
def _resources_payload() -> dict[str, Any]:
    return _read_json(_RESOURCES_FILE)


def _role_records() -> list[dict[str, Any]]:
    records = _roles_payload().get("roles", [])
    return [record for record in records if isinstance(record, dict) and record.get("role")]


def _role_names(record: dict[str, Any]) -> list[str]:
    names = [_normalize(str(record.get("role", "")))]
    names.extend(_normalize(str(alias)) for alias in record.get("aliases", []) if alias)
    return [name for name in dict.fromkeys(names) if name]


def _resolve_role(role: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return ``(record, [])`` for one match or ``(None, candidates)`` otherwise."""

    if not isinstance(role, str):
        return None, []
    query = _normalize(role)
    if not query:
        return None, []

    records = _role_records()

    exact = [record for record in records if query in _role_names(record)]
    if len(exact) == 1:
        return exact[0], []
    if len(exact) > 1:
        return None, exact

    fuzzy: list[dict[str, Any]] = []
    query_has_phrase = len(query.split()) >= 2 and len(query) >= 8
    for record in records:
        names = _role_names(record)
        if any(_contains_phrase(query, name) for name in names):
            fuzzy.append(record)
        elif query_has_phrase and any(_contains_phrase(name, query) for name in names):
            fuzzy.append(record)

    # Keep records unique while preserving order.
    deduped = list({id(record): record for record in fuzzy}.values())
    if len(deduped) == 1:
        return deduped[0], []
    return None, deduped


def _available_roles() -> str:
    return ", ".join(str(record["role"]) for record in _role_records())


def get_role(role: str) -> dict:
    """Return curated requirements for a job title.

    Lookup is case-insensitive and accepts common aliases and extra qualifiers,
    so "full stack dev", "Full-Stack Developer", and "senior full stack
    developer" all resolve to "Full Stack Developer". Unknown or ambiguous
    titles raise ``KeyError`` with the available role names.
    """

    record, candidates = _resolve_role(role)
    if record is None:
        if candidates:
            matches = ", ".join(str(item["role"]) for item in candidates)
            raise KeyError(
                f"Ambiguous role {role!r}; it matches: {matches}. "
                "Please use a more specific job title."
            )
        raise KeyError(
            f"Unknown role {role!r}. Available roles: {_available_roles()}."
        )

    skills = copy.deepcopy(record.get("skills", []))
    return {
        "role": record["role"],
        "company": None,
        "summary": record.get("summary", ""),
        "skills": skills,
        # Convenience alias matching contracts.schemas.RoleRequirements.
        "requirements": copy.deepcopy(skills),
        "tools": copy.deepcopy(record.get("tools", [])),
        "certs": copy.deepcopy(record.get("certs", [])),
        "interview_process": [],
        "confidence": record.get("confidence", "curated"),
        "disclaimer": record.get("disclaimer", ""),
    }


def _company_records() -> list[dict[str, Any]]:
    records = _companies_payload().get("companies", [])
    return [record for record in records if isinstance(record, dict) and record.get("company")]


def _company_names(record: dict[str, Any]) -> list[str]:
    names = [_normalize(str(record.get("company", "")))]
    names.extend(_normalize(str(alias)) for alias in record.get("aliases", []) if alias)
    return [name for name in dict.fromkeys(names) if name]


def _resolve_company(company: str) -> dict[str, Any] | None:
    if not isinstance(company, str):
        return None
    query = _normalize(company)
    if not query:
        return None

    records = _company_records()
    exact = [record for record in records if query in _company_names(record)]
    if len(exact) == 1:
        return exact[0]

    matches = [
        record
        for record in records
        if any(_contains_phrase(query, name) for name in _company_names(record))
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def get_company_override(company: str, role: str) -> dict | None:
    """Return a curated per-company override for a role.

    Company and role names are matched case-insensitively. Unknown companies,
    unknown roles, and company/role pairs without a curated override return
    ``None`` so callers can fall back to the base role data.
    """

    company_record = _resolve_company(company)
    if company_record is None:
        return None

    role_record, _ = _resolve_role(role)
    if role_record is None:
        return None

    overrides = company_record.get("overrides", {})
    if not isinstance(overrides, dict):
        return None
    override = overrides.get(role_record["role"])
    if not isinstance(override, dict):
        return None

    payload = {
        "company": company_record["company"],
        "role": role_record["role"],
        "confidence": company_record.get("confidence", "curated"),
        "last_verified": company_record.get("last_verified", ""),
    }
    payload.update(copy.deepcopy(override))
    if "disclaimer" not in payload and _companies_payload().get("disclaimer"):
        payload["disclaimer"] = _companies_payload()["disclaimer"]
    return payload


def _resource_names(canonical: str, entry: dict[str, Any]) -> list[str]:
    names = [_normalize(canonical)]
    names.extend(_normalize(str(alias)) for alias in entry.get("aliases", []) if alias)
    return [name for name in dict.fromkeys(names) if name]


def get_resources(skill: str) -> list[Resource]:
    """Return curated free learning resources for a skill.

    Lookup is case-insensitive and accepts aliases ("js", "k8s", "powerbi").
    Unknown skills return an empty list rather than inventing links.
    """

    if not isinstance(skill, str):
        return []
    query = _normalize(skill)
    if not query:
        return []

    index = _resources_payload().get("skills", {})
    if not isinstance(index, dict):
        return []

    chosen: dict[str, Any] | None = None
    for canonical, entry in index.items():
        if not isinstance(entry, dict):
            continue
        if query in _resource_names(canonical, entry):
            chosen = entry
            break

    if chosen is None:
        fuzzy: list[tuple[int, str, dict[str, Any]]] = []
        for canonical, entry in index.items():
            if not isinstance(entry, dict):
                continue
            for name in _resource_names(canonical, entry):
                if len(name) >= 3 and _contains_phrase(query, name):
                    fuzzy.append((len(name), canonical, entry))
        if fuzzy:
            best_length = max(item[0] for item in fuzzy)
            best = [item for item in fuzzy if item[0] == best_length]
            unique_entries = {item[1]: item[2] for item in best}
            if len(unique_entries) == 1:
                chosen = next(iter(unique_entries.values()))

    if chosen is None:
        return []

    resources: list[Resource] = []
    seen_urls: set[str] = set()
    for item in chosen.get("resources", []):
        if not isinstance(item, dict):
            continue
        resource = Resource.model_validate(item)
        if resource.url in seen_urls:
            continue
        seen_urls.add(resource.url)
        resources.append(resource)
    return resources

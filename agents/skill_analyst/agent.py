"""Skill Analysis agent.

Turns free-form profile text plus certifications and projects into canonical
:class:`~contracts.schemas.Skill` objects.  Canonicalisation, de-duplication and
the inferred-level cap are deliberately done in plain Python after the LLM call
so the result is deterministic even when the model is imprecise.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from contracts.llm import call_llm
from contracts.schemas import Skill

from .prompts import SYSTEM_PROMPT, inferred_skills_prompt, stated_skills_prompt

__all__ = ["analyze_profile"]


class _SkillDraft(BaseModel):
    """Wire format returned by the LLM before canonicalisation."""

    name: str
    level: int = Field(ge=0, le=5)


class _SkillList(BaseModel):
    """Wrapper schema used because the LLM must return a list."""

    skills: list[_SkillDraft] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical skill vocabulary
# ---------------------------------------------------------------------------

# alias (lower-case) -> canonical display name
SKILL_ALIASES: dict[str, str] = {
    # Languages and markup
    "python": "Python",
    "python3": "Python",
    "sql": "SQL",
    "html": "HTML",
    "html5": "HTML",
    "css": "CSS",
    "css3": "CSS",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "ecmascript": "JavaScript",
    "es6": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "java": "Java",
    "kotlin": "Kotlin",
    "swift": "Swift",
    "scala": "Scala",
    "rust": "Rust",
    "golang": "Go",
    "php": "PHP",
    "ruby": "Ruby",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    # Frontend / backend frameworks
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "expressjs": "Express",
    "express.js": "Express",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    ".net": ".NET",
    "dotnet": ".NET",
    "asp.net": "ASP.NET",
    "aspnet": "ASP.NET",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "graphql": "GraphQL",
    # Data stores
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis": "Redis",
    # Data / ML
    "pandas": "Pandas",
    "numpy": "NumPy",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "tensorflow": "TensorFlow",
    "tensor flow": "TensorFlow",
    "pytorch": "PyTorch",
    "data analysis": "Data Analysis",
    "data analytics": "Data Analysis",
    "data science": "Data Science",
    "tableau": "Tableau",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "excel": "Excel",
    "microsoft excel": "Excel",
    # Cloud / ops
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "google cloud": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "cka": "Kubernetes",
    "ckad": "Kubernetes",
    "terraform": "Terraform",
    "jenkins": "Jenkins",
    "linux": "Linux",
    "bash": "Bash",
    "shell scripting": "Bash",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "continuous integration": "CI/CD",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "restful api": "REST APIs",
    "api": "REST APIs",
    "microservices": "Microservices",
    "agile": "Agile",
    "scrum": "Scrum",
    "unit testing": "Unit Testing",
    "pytest": "Pytest",
    "figma": "Figma",
    "photoshop": "Photoshop",
    "project management": "Project Management",
    "pmp": "Project Management",
    "communication": "Communication",
    "problem solving": "Problem Solving",
    "leadership": "Leadership",
    "teamwork": "Teamwork",
    "english": "English",
}


def _key(name: str) -> str:
    """Normalise a skill name for case/punctuation-insensitive matching."""

    return re.sub(r"[\s._\-]+", "", name.strip().lower())


_CANONICAL_BY_KEY: dict[str, str] = {}
for _alias, _canonical in SKILL_ALIASES.items():
    _CANONICAL_BY_KEY[_key(_alias)] = _canonical
for _canonical in set(SKILL_ALIASES.values()):
    _CANONICAL_BY_KEY[_key(_canonical)] = _canonical


def _canonical_name(name: str) -> str:
    """Return a canonical display name, or the cleaned original when unknown."""

    cleaned = " ".join(str(name).split()).strip(" \t\r\n,;:")
    cleaned = cleaned.rstrip(".").lstrip("-•* ")
    if not cleaned:
        return ""
    return _CANONICAL_BY_KEY.get(_key(cleaned), cleaned)


# ---------------------------------------------------------------------------
# Offline mock helpers
# ---------------------------------------------------------------------------

_SEGMENT_SPLIT_RE = re.compile(r"[,;\n]|\band\b|\.(?=\s|$)", re.IGNORECASE)

_LEVEL_CUES: tuple[tuple[int, re.Pattern[str]], ...] = (
    (
        5,
        re.compile(
            r"\b(?:expert|master|specialist|guru)\b|\b(?:8|9|10)\+?\s*years?\b",
            re.IGNORECASE,
        ),
    ),
    (
        4,
        re.compile(
            r"\b(?:good\s+(?:at|with)|comfortable|proficient|strong|confident|experienced|advanced)\b"
            r"|\b(?:5|6|7)\+?\s*years?\b",
            re.IGNORECASE,
        ),
    ),
    (
        3,
        re.compile(
            r"\b(?:intermediate|working knowledge|small projects?|built|build|develop(?:ed)?|used|using|"
            r"coursework|academic|practiced?)\b|\b(?:2|3|4)\+?\s*years?\b",
            re.IGNORECASE,
        ),
    ),
    (
        2,
        re.compile(
            r"\b(?:basic|beginner|learning|just started|some experience|fundamentals|intro(?:ductory)?|"
            r"a little|limited|know)\b|\b(?:0|1)\+?\s*years?\b",
            re.IGNORECASE,
        ),
    ),
    (
        1,
        re.compile(
            r"\b(?:heard of|aware of|know of|familiar with|no experience|never used)\b",
            re.IGNORECASE,
        ),
    ),
)

_ALIAS_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = tuple(
    (
        alias,
        re.compile(rf"(?<![\w.+#]){re.escape(alias)}(?![\w+#])", re.IGNORECASE),
        SKILL_ALIASES[alias],
    )
    for alias in sorted(SKILL_ALIASES, key=len, reverse=True)
)

# Skills that are reasonably implied by common project/cert wording.
_DOMAIN_HINTS: tuple[tuple[re.Pattern[str], tuple[tuple[str, int], ...]], ...] = (
    (
        re.compile(
            r"\b(?:portfolio|website|web site|web app|web application|web page|landing page|frontend|front-end)\b",
            re.IGNORECASE,
        ),
        (("HTML", 2), ("CSS", 2), ("JavaScript", 2)),
    ),
    (
        re.compile(r"\b(?:dashboard|data analytics|data analysis)\b", re.IGNORECASE),
        (("Data Analysis", 2), ("SQL", 2)),
    ),
    (
        re.compile(r"\b(?:machine learning|deep learning|ml model|neural network)\b", re.IGNORECASE),
        (("Machine Learning", 2), ("Python", 2)),
    ),
    (
        re.compile(r"\b(?:rest api|restful api|api|apis)\b", re.IGNORECASE),
        (("REST APIs", 2),),
    ),
    (
        re.compile(r"\b(?:database|databases|db)\b", re.IGNORECASE),
        (("SQL", 2),),
    ),
    (
        re.compile(r"\b(?:unit tests?|test suite|automated tests?)\b", re.IGNORECASE),
        (("Unit Testing", 2),),
    ),
)


def _segments(text: str) -> list[str]:
    return [part.strip() for part in _SEGMENT_SPLIT_RE.split(text) if part.strip()]


def _level_for_segment(segment: str, default_level: int) -> int:
    levels = [level for level, pattern in _LEVEL_CUES if pattern.search(segment)]
    return min(levels) if levels else default_level


def _skill_mentions(text: str, default_level: int) -> list[tuple[str, int]]:
    """Extract (surface name, level) pairs from free text."""

    mentions: list[tuple[str, int]] = []
    for segment in _segments(text):
        level = _level_for_segment(segment, default_level)
        matches: list[tuple[int, int, str, str]] = []
        for _alias, pattern, canonical in _ALIAS_PATTERNS:
            for match in pattern.finditer(segment):
                matches.append((match.start(), -len(match.group(0)), match.group(0), canonical))
        matches.sort()
        seen: set[str] = set()
        for _start, _length, surface, canonical in matches:
            if canonical in seen:
                continue
            seen.add(canonical)
            mentions.append((surface, level))
    return mentions


def _domain_mentions(text: str) -> list[tuple[str, int]]:
    mentions: list[tuple[str, int]] = []
    for pattern, inferred in _DOMAIN_HINTS:
        if pattern.search(text):
            mentions.extend(inferred)
    return mentions


def _clamp(level: int) -> int:
    return max(0, min(5, int(level)))


def _mock_stated_payload(raw_text: str) -> _SkillList:
    """Deterministic stand-in for the live model in stated-skills mode."""

    return _SkillList(
        skills=[
            _SkillDraft(name=surface, level=_clamp(level))
            for surface, level in _skill_mentions(raw_text, default_level=3)
        ]
    )


def _mock_inferred_payload(certs: list[str], projects: list[str]) -> _SkillList:
    """Deterministic stand-in for the live model in inferred-skills mode."""

    drafts: list[_SkillDraft] = []
    seen: set[str] = set()
    for item in [*certs, *projects]:
        if not item.strip():
            continue
        combined = [*_skill_mentions(item, default_level=3), *_domain_mentions(item)]
        for name, level in combined:
            key = _key(_canonical_name(name))
            if not key or key in seen:
                continue
            seen.add(key)
            drafts.append(_SkillDraft(name=name, level=min(3, _clamp(level))))
    return _SkillList(skills=drafts)


# ---------------------------------------------------------------------------
# LLM orchestration and post-processing
# ---------------------------------------------------------------------------


def _assess_stated_skills(raw_text: str) -> list[Skill]:
    text = (raw_text or "").strip()
    if not text:
        return []
    payload = call_llm(
        SYSTEM_PROMPT,
        stated_skills_prompt(text),
        _SkillList,
        mock=_mock_stated_payload(text),
    )
    return [
        Skill(name=str(draft.name).strip(), level=_clamp(draft.level), source="user")
        for draft in getattr(payload, "skills", [])
        if str(draft.name).strip()
    ]


def _infer_extra_skills(certs: list[str], projects: list[str]) -> list[Skill]:
    cert_list = [str(cert).strip() for cert in (certs or []) if str(cert).strip()]
    project_list = [str(project).strip() for project in (projects or []) if str(project).strip()]
    if not cert_list and not project_list:
        return []
    payload = call_llm(
        SYSTEM_PROMPT,
        inferred_skills_prompt(cert_list, project_list),
        _SkillList,
        mock=_mock_inferred_payload(cert_list, project_list),
    )
    return [
        Skill(
            name=str(draft.name).strip(),
            level=min(3, _clamp(draft.level)),
            source="inferred",
        )
        for draft in getattr(payload, "skills", [])
        if str(draft.name).strip()
    ]


def _merge_and_canonicalize(skills: list[Skill]) -> list[Skill]:
    """Canonicalise names and de-duplicate, keeping the highest level."""

    merged: dict[str, Skill] = {}
    order: list[str] = []
    for skill in skills:
        display = _canonical_name(skill.name)
        key = _key(display)
        if not key:
            continue
        level = _clamp(skill.level)
        if key not in merged:
            order.append(key)
            merged[key] = Skill(name=display, level=level, source=skill.source)
            continue
        existing = merged[key]
        source = "user" if "user" in {existing.source, skill.source} else existing.source
        merged[key] = Skill(
            name=existing.name,
            level=max(existing.level, level),
            source=source,
        )
    return [merged[key] for key in order]


def analyze_profile(raw_text: str, certs: list[str], projects: list[str]) -> list[Skill]:
    """Analyze a raw profile and API-provided metadata to infer skills."""

    stated = _assess_stated_skills(raw_text)
    inferred = _infer_extra_skills(certs, projects)
    return _merge_and_canonicalize([*stated, *inferred])

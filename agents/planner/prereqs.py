"""Prerequisite graph and topological sorting for SkillPath curriculum planner.

Covers core skills across all 5 roles:
- Full Stack Developer
- Data Analyst
- Cybersecurity Analyst
- ML Engineer
- DevOps Engineer
"""

from __future__ import annotations

from typing import Iterable


PREREQUISITES: dict[str, list[str]] = {
    # Full Stack & Web Development
    # HTML/CSS -> JavaScript -> React
    # JavaScript -> Node.js -> Express -> databases / REST APIs
    "HTML": [],
    "CSS": ["HTML"],
    "JavaScript": ["HTML", "CSS"],
    "React": ["JavaScript"],
    "Node.js": ["JavaScript"],
    "Express": ["Node.js"],
    "SQL": [],
    "Git": [],
    "REST APIs": ["Node.js", "SQL"],
    "databases": ["SQL"],
    "Databases": ["SQL"],

    # Data Analyst
    # Python -> Pandas -> Data Visualization -> Power BI
    # SQL + Pandas -> Data Cleaning
    "Spreadsheets": [],
    "Python": [],
    "Pandas": ["Python"],
    "Data Visualization": ["Python", "Pandas"],
    "Statistics": [],
    "Data Cleaning": ["SQL", "Pandas"],
    "Power BI": ["Data Visualization"],

    # ML Engineer
    # Python + Linear Algebra + Statistics -> Machine Learning -> Deep Learning
    # Python -> NumPy
    # Python + Machine Learning -> MLOps
    "Linear Algebra": [],
    "NumPy": ["Python"],
    "Machine Learning": ["Python", "Linear Algebra", "Statistics"],
    "Deep Learning": ["Machine Learning"],
    "MLOps": ["Python", "Machine Learning"],

    # Cybersecurity Analyst
    # Networking -> Security Fundamentals -> Web Security / Incident Response / Cryptography
    # Networking + Linux -> SIEM
    "Networking": [],
    "Linux": [],
    "Security Fundamentals": ["Networking"],
    "SIEM": ["Networking", "Linux"],
    "Incident Response": ["Security Fundamentals"],
    "Cryptography": ["Security Fundamentals"],
    "Web Security": ["Networking", "Security Fundamentals"],

    # DevOps Engineer
    # Linux -> Docker -> Kubernetes -> Monitoring
    # Git -> CI/CD
    # Networking -> Cloud Platforms
    "Docker": ["Linux"],
    "Kubernetes": ["Docker"],
    "CI/CD": ["Git"],
    "Terraform": [],
    "Cloud Platforms": ["Networking"],
    "Monitoring": ["Linux", "Kubernetes"],

    # Additional common skills / languages
    "Java": [],
}

# Alias for convenience
PREREQS: dict[str, list[str]] = PREREQUISITES

# Case-insensitive canonical map
_CANONICAL_BY_NORM: dict[str, str] = {
    skill.strip().casefold(): skill for skill in PREREQUISITES
}

_PREREQS_BY_NORM: dict[str, list[str]] = {
    skill.strip().casefold(): list(prereqs)
    for skill, prereqs in PREREQUISITES.items()
}


def normalize_skill_name(skill: str) -> str:
    """Return normalized casefold string for skill lookup."""
    return str(skill or "").strip().casefold()


def canonical_skill_name(skill: str) -> str:
    """Return canonical casing for a known skill, or stripped original."""
    norm = normalize_skill_name(skill)
    return _CANONICAL_BY_NORM.get(norm, str(skill or "").strip())


def get_prerequisites(skill: str) -> list[str]:
    """Return the prerequisite skill names for a given skill (case-insensitive)."""
    norm = normalize_skill_name(skill)
    return list(_PREREQS_BY_NORM.get(norm, []))


def has_cycle(nodes: Iterable[str], prereqs_map: dict[str, list[str]] | None = None) -> bool:
    """Check if the prerequisite dependencies among the given nodes contain a cycle."""
    node_set = {normalize_skill_name(n) for n in nodes if normalize_skill_name(n)}
    if not node_set:
        return False

    graph: dict[str, list[str]] = {n: [] for n in node_set}
    in_degree: dict[str, int] = {n: 0 for n in node_set}

    for n in node_set:
        prereqs = (
            prereqs_map.get(n, [])
            if prereqs_map is not None
            else get_prerequisites(n)
        )
        for p in prereqs:
            p_norm = normalize_skill_name(p)
            if p_norm in node_set:
                graph[p_norm].append(n)
                in_degree[n] += 1

    queue = [n for n in node_set if in_degree[n] == 0]
    visited_count = 0

    while queue:
        curr = queue.pop(0)
        visited_count += 1
        for dep in graph[curr]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    return visited_count < len(node_set)


def topological_sort_skills(
    skills_to_learn: list[str],
    prereqs_map: dict[str, list[str]] | None = None,
) -> list[str]:
    """Topologically sort skills so that prerequisites appear before dependent skills.

    Detects cycles safely without crashing or infinite loops; if a cycle exists,
    remaining nodes are appended safely while preserving their relative order.
    """
    if not skills_to_learn:
        return []

    # Preserve canonical representation and initial order
    ordered_unique: list[str] = []
    norm_to_orig: dict[str, str] = {}
    seen: set[str] = set()

    for s in skills_to_learn:
        norm = normalize_skill_name(s)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        canonical = canonical_skill_name(s)
        ordered_unique.append(norm)
        norm_to_orig[norm] = canonical

    node_set = set(ordered_unique)
    in_degree: dict[str, int] = {n: 0 for n in ordered_unique}
    graph: dict[str, list[str]] = {n: [] for n in ordered_unique}

    for n in ordered_unique:
        raw_prereqs = (
            prereqs_map.get(n, [])
            if prereqs_map is not None
            else get_prerequisites(n)
        )
        for p in raw_prereqs:
            p_norm = normalize_skill_name(p)
            if p_norm in node_set:
                graph[p_norm].append(n)
                in_degree[n] += 1

    # Ready queue with initial in-degree == 0, preserving input order
    ready: list[str] = [n for n in ordered_unique if in_degree[n] == 0]
    sorted_norm: list[str] = []

    while ready:
        curr = ready.pop(0)
        sorted_norm.append(curr)
        for dep in graph[curr]:
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                ready.append(dep)

    # Safe cycle resolution: if any nodes remain due to a cycle, break cycle safely
    if len(sorted_norm) < len(ordered_unique):
        remaining = [n for n in ordered_unique if n not in sorted_norm]
        while remaining:
            # Pick node with lowest in-degree
            remaining.sort(key=lambda n: in_degree[n])
            curr = remaining.pop(0)
            sorted_norm.append(curr)
            for dep in graph[curr]:
                in_degree[dep] -= 1

    return [norm_to_orig[n] for n in sorted_norm]


__all__ = [
    "PREREQUISITES",
    "PREREQS",
    "canonical_skill_name",
    "get_prerequisites",
    "has_cycle",
    "normalize_skill_name",
    "topological_sort_skills",
]

"""The set of skill names the dashboard treats as programming languages.

Kept deliberately small and dependency-free so it can be imported by pure
logic and unit tests without pulling in Streamlit.
"""

from __future__ import annotations

# Lower-cased canonical names. Membership checks should be case-insensitive.
LANGUAGES: frozenset[str] = frozenset(
    {
        "python",
        "javascript",
        "typescript",
        "java",
        "c",
        "c++",
        "c#",
        "go",
        "rust",
        "sql",
        "html",
        "css",
        "bash",
        "r",
        "kotlin",
        "swift",
        "php",
        "ruby",
    }
)

# A stable, human-readable ordering for display fallbacks.
LANGUAGE_NAMES: tuple[str, ...] = (
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C",
    "C++",
    "C#",
    "Go",
    "Rust",
    "SQL",
    "HTML",
    "CSS",
    "Bash",
    "R",
    "Kotlin",
    "Swift",
    "PHP",
    "Ruby",
)

__all__ = ["LANGUAGES", "LANGUAGE_NAMES"]

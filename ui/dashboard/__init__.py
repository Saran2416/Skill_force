"""Pure, Streamlit-free dashboard read models (consumed by the React frontend
via the API in ``server/app.py``)."""

from .logic import (
    advantages,
    disadvantages,
    known_languages,
    progress,
    required_skills_table,
)

__all__ = [
    "advantages",
    "disadvantages",
    "known_languages",
    "progress",
    "required_skills_table",
]

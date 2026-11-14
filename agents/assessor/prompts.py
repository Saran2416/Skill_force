"""Prompts used by the assessment engine."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You write fair, unambiguous multiple-choice questions. Each has exactly 4 options and exactly one correct "
    "answer. Match difficulty to the stated level (1 basic ... 5 expert). Output ONLY JSON matching the schema."
)

LEVEL_DESCRIPTIONS = {
    1: "basic",
    2: "beginner",
    3: "intermediate",
    4: "advanced",
    5: "expert",
}


def build_user_prompt(skill: str, level: int) -> str:
    """Build the per-request prompt describing the quiz to generate."""

    difficulty = LEVEL_DESCRIPTIONS.get(level, "intermediate")
    return (
        f"Create a 5-question multiple-choice quiz for the skill '{skill}' "
        f"at difficulty level {level} ({difficulty}).\n"
        "Requirements:\n"
        "- Exactly 5 questions.\n"
        "- Exactly 4 distinct options per question.\n"
        "- Exactly one correct answer per question, recorded as answer_index from 0 to 3.\n"
        "- Include a one-line explanation for every question.\n"
        "- Give every question a stable, unique id.\n"
        "Return JSON with a top-level 'skill' string and a 'questions' array. "
        "Each question must contain id, q, options, answer_index, and explanation."
    )

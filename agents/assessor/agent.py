"""Assessment engine: quiz generation, scoring, and score simulation."""

from __future__ import annotations

import json
import os
from pathlib import Path

from contracts.llm import call_llm
from contracts.schemas import Quiz, QuizQuestion, ScoreResult

from .prompts import SYSTEM_PROMPT, build_user_prompt

CACHE_DIR = Path(__file__).resolve().parent / "cache"

__all__ = ["generate_quiz", "score_quiz", "simulate_score", "validate_quiz"]


def _cache_stem(skill: str) -> str:
    """Turn a skill name into a safe file stem without changing common names."""

    cleaned = "".join(
        character if (character.isalnum() or character in "-_.") else "_"
        for character in str(skill).strip()
    )
    return cleaned.strip("._") or "unknown"


def _cache_path(skill: str) -> Path:
    return CACHE_DIR / f"{_cache_stem(skill)}.json"


def _read_quiz(path: Path) -> Quiz | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return validate_quiz(Quiz.model_validate(payload))
    except (OSError, TypeError, ValueError):
        return None


def _load_cache(skill: str) -> Quiz | None:
    """Load a cached quiz by file name, then by case-insensitive skill name."""

    path = _cache_path(skill)
    if path.is_file():
        cached = _read_quiz(path)
        if cached is not None:
            return cached

    try:
        candidates = sorted(CACHE_DIR.glob("*.json"))
    except OSError:
        return None

    wanted = str(skill).strip().casefold()
    for candidate in candidates:
        if candidate == path:
            continue
        cached = _read_quiz(candidate)
        if cached is not None and cached.skill.strip().casefold() == wanted:
            return cached
    return None


def _write_cache(skill: str, quiz: Quiz) -> None:
    """Persist a validated quiz for later offline fallback."""

    path = _cache_path(skill)
    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = quiz.model_dump(mode="json")
        temp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temp_path, path)
    except OSError:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def validate_quiz(quiz: Quiz) -> Quiz:
    """Validate the structural quiz rules, raising ValueError when malformed."""

    problems: list[str] = []

    if not isinstance(quiz, Quiz):
        raise ValueError("Invalid quiz: expected a Quiz object")

    skill = getattr(quiz, "skill", "")
    if not str(skill or "").strip():
        problems.append("skill must not be empty")

    questions = getattr(quiz, "questions", None)
    if not isinstance(questions, list):
        problems.append("questions must be a list")
    elif len(questions) != 5:
        problems.append(f"expected 5 questions, found {len(questions)}")

    seen_ids: set[str] = set()
    for number, question in enumerate(questions if isinstance(questions, list) else [], start=1):
        label = f"question {number}"

        question_id = str(getattr(question, "id", "") or "").strip()
        if not question_id:
            problems.append(f"{label} has no id")
        elif question_id in seen_ids:
            problems.append(f"{label} repeats id {question_id!r}")
        seen_ids.add(question_id)

        if not str(getattr(question, "q", "") or "").strip():
            problems.append(f"{label} has no text")

        options = getattr(question, "options", None)
        if not isinstance(options, list) or len(options) != 4:
            problems.append(f"{label} must have exactly 4 options")
        else:
            normalized = [str(option).strip().casefold() for option in options]
            if any(not option for option in normalized):
                problems.append(f"{label} has a blank option")
            if len(set(normalized)) != len(normalized):
                problems.append(f"{label} has duplicate options")

        answer_index = getattr(question, "answer_index", None)
        if (
            not isinstance(answer_index, int)
            or isinstance(answer_index, bool)
            or not 0 <= answer_index <= 3
        ):
            problems.append(f"{label} answer_index must be between 0 and 3")

        if not str(getattr(question, "explanation", "") or "").strip():
            problems.append(f"{label} has no explanation")

    if problems:
        raise ValueError("Invalid quiz: " + "; ".join(problems))
    return quiz


def _level_task(level: int) -> tuple[str, str]:
    """Return a level-appropriate prompt fragment and its correct answer."""

    if level <= 2:
        return (
            f"Which task best fits a level {level} learner",
            "Practise core syntax with small guided examples",
        )
    if level == 3:
        return (
            "Which task best demonstrates intermediate ability",
            "Build a small end-to-end feature with minimal guidance",
        )
    return (
        f"Which task best demonstrates level {level} expertise",
        "Diagnose a subtle production issue and justify the trade-off",
    )


def _build_generic_quiz(skill: str, level: int) -> Quiz:
    """Build a deterministic, valid quiz used for offline mock mode."""

    stem = _cache_stem(skill)
    task_question, task_answer = _level_task(level)
    questions = [
        QuizQuestion(
            id=f"{stem}-1",
            q=f"What is the main purpose of {skill}?",
            options=[
                "To solve problems within its own domain",
                "To replace every other tool",
                "To manage unrelated business finances",
                "To design physical hardware",
            ],
            answer_index=0,
            explanation=f"{skill} exists to address problems within its own domain.",
        ),
        QuizQuestion(
            id=f"{stem}-2",
            q=f"What is the best way to confirm a change to {skill} work is safe?",
            options=[
                "Write automated tests around the behaviour",
                "Delete the existing tests",
                "Skip code review to save time",
                "Assume it works if it runs once",
            ],
            answer_index=0,
            explanation="Automated tests give repeatable evidence that behaviour is preserved.",
        ),
        QuizQuestion(
            id=f"{stem}-3",
            q=f"{task_question} in {skill}?",
            options=[
                task_answer,
                "Lead architecture reviews for a large team",
                "Optimise undocumented production bottlenecks",
                "Mentor experts on advanced trade-offs",
            ],
            answer_index=0,
            explanation=f"That task matches the expectations of level {level}.",
        ),
        QuizQuestion(
            id=f"{stem}-4",
            q=f"What is the best first step when debugging a {skill} problem?",
            options=[
                "Rewrite the project from scratch",
                "Reproduce the issue with a minimal example",
                "Ignore the error and deploy",
                "Change unrelated configuration until it works",
            ],
            answer_index=1,
            explanation="A minimal reproduction makes the cause easier to isolate.",
        ),
        QuizQuestion(
            id=f"{stem}-5",
            q=f"Which habit best supports steady improvement in {skill}?",
            options=[
                "Only read tutorials without practising",
                "Memorise answers without understanding",
                "Review feedback and practise deliberately",
                "Avoid unfamiliar problems",
            ],
            answer_index=2,
            explanation="Deliberate practice with feedback turns knowledge into skill.",
        ),
    ]
    return Quiz(skill=skill, questions=questions)


def _mock_quiz(skill: str, level: int) -> Quiz:
    """Return the offline mock, preferring a hand-seeded cache entry."""

    cached = _load_cache(skill)
    if cached is not None:
        return cached
    return _build_generic_quiz(skill, level)


def generate_quiz(skill: str, level: int) -> Quiz:
    """Generate a skill quiz appropriate to the target level."""

    skill = str(skill or "").strip() or "General"
    try:
        safe_level = max(1, min(5, int(level)))
    except (TypeError, ValueError):
        safe_level = 3

    try:
        generated = call_llm(
            SYSTEM_PROMPT,
            build_user_prompt(skill, safe_level),
            Quiz,
            mock=_mock_quiz(skill, safe_level),
        )
        quiz = validate_quiz(generated)
        _write_cache(skill, quiz)
        return quiz
    except Exception:
        cached = _load_cache(skill)
        if cached is not None:
            return cached
        return validate_quiz(_build_generic_quiz(skill, safe_level))


def _band_result(skill: str, percent: float, previous_level: int) -> ScoreResult:
    """Apply the shared score bands and build a ScoreResult."""

    score = max(0.0, min(100.0, float(percent)))
    try:
        previous = int(previous_level)
    except (TypeError, ValueError):
        previous = 0
    previous = max(0, min(5, previous))

    if score < 60:
        weak = True
        new_level = max(0, previous - 1)
    elif score > 80:
        weak = False
        new_level = min(5, previous + 1)
    else:
        weak = False
        new_level = previous

    return ScoreResult(
        skill=str(skill or "").strip() or "General",
        score_percent=score,
        new_level=new_level,
        weak=weak,
    )


def score_quiz(quiz: Quiz, answers: list[int], previous_level: int) -> ScoreResult:
    """Score a submitted quiz and return a result with the next level estimate."""

    questions = quiz.questions if isinstance(quiz.questions, list) else []
    total = len(questions)
    submitted = list(answers or [])

    correct = sum(
        1
        for index, question in enumerate(questions)
        if index < len(submitted) and submitted[index] == question.answer_index
    )
    percent = (correct / total * 100.0) if total else 0.0
    return _band_result(quiz.skill, percent, previous_level)


def simulate_score(skill: str, percent: int, previous_level: int) -> ScoreResult:
    """Return a score result for a simulated skill test."""

    return _band_result(skill, percent, previous_level)

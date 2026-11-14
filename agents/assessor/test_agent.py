"""Tests for the assessment engine (agent 6)."""

from __future__ import annotations

import pytest

import agents.assessor.agent as assessor
from contracts.llm import LLMError
from contracts.schemas import Quiz, QuizQuestion

SEEDED_SKILLS = ["JavaScript", "React", "Node.js"]


def _make_quiz(skill: str = "Python") -> Quiz:
    return Quiz(
        skill=skill,
        questions=[
            QuizQuestion(
                id=f"q{index}",
                q=f"Question {index}",
                options=[f"Option {index}A", f"Option {index}B", f"Option {index}C", f"Option {index}D"],
                answer_index=index % 4,
                explanation="Because it is correct.",
            )
            for index in range(5)
        ],
    )


def _answers_with(quiz: Quiz, correct_count: int) -> list[int]:
    answers = []
    for index, question in enumerate(quiz.questions):
        if index < correct_count:
            answers.append(question.answer_index)
        else:
            answers.append((question.answer_index + 1) % 4)
    return answers


def _correct_answers(quiz: Quiz) -> list[int]:
    return [question.answer_index for question in quiz.questions]


@pytest.mark.parametrize(
    ("correct_count", "expected_percent", "expected_level", "expected_weak"),
    [
        (2, 40.0, 2, True),
        (4, 80.0, 3, False),
        (5, 100.0, 4, False),
    ],
)
def test_score_quiz_bands(
    correct_count: int,
    expected_percent: float,
    expected_level: int,
    expected_weak: bool,
) -> None:
    quiz = _make_quiz()
    result = assessor.score_quiz(quiz, _answers_with(quiz, correct_count), previous_level=3)

    assert result.skill == "Python"
    assert result.score_percent == expected_percent
    assert result.new_level == expected_level
    assert result.weak is expected_weak


def test_score_quiz_exactly_sixty_is_unchanged() -> None:
    quiz = _make_quiz()
    result = assessor.score_quiz(quiz, _answers_with(quiz, 3), previous_level=2)

    assert result.score_percent == 60.0
    assert result.new_level == 2
    assert result.weak is False


def test_score_quiz_short_answers_count_as_wrong() -> None:
    quiz = _make_quiz()
    result = assessor.score_quiz(quiz, _correct_answers(quiz)[:1], previous_level=3)

    assert result.score_percent == 20.0
    assert result.new_level == 2
    assert result.weak is True


def test_score_quiz_missing_answers_count_as_wrong() -> None:
    quiz = _make_quiz()
    result = assessor.score_quiz(quiz, [], previous_level=1)

    assert result.score_percent == 0.0
    assert result.new_level == 0
    assert result.weak is True


@pytest.mark.parametrize(
    ("percent", "expected_level", "expected_weak"),
    [
        (59, 2, True),
        (60, 3, False),
        (80, 3, False),
        (81, 4, False),
    ],
)
def test_simulate_score_boundaries(
    percent: int,
    expected_level: int,
    expected_weak: bool,
) -> None:
    result = assessor.simulate_score("Python", percent, previous_level=3)

    assert result.score_percent == float(percent)
    assert result.new_level == expected_level
    assert result.weak is expected_weak


def test_simulate_score_clamps_to_schema_range() -> None:
    low = assessor.simulate_score("Python", -10, previous_level=0)
    high = assessor.simulate_score("Python", 150, previous_level=5)

    assert low.score_percent == 0.0
    assert low.new_level == 0
    assert high.score_percent == 100.0
    assert high.new_level == 5


def test_validate_quiz_accepts_seeded_cache() -> None:
    for skill in SEEDED_SKILLS:
        quiz = assessor._load_cache(skill)
        assert quiz is not None
        assert assessor.validate_quiz(quiz) is quiz


@pytest.mark.parametrize(
    "mutate",
    [
        lambda quiz: quiz.model_copy(
            update={
                "questions": [
                    quiz.questions[0].model_copy(
                        update={"options": ["same", "same", "other", "another"]}
                    ),
                    *quiz.questions[1:],
                ]
            }
        ),
        lambda quiz: quiz.model_copy(update={"questions": quiz.questions[:4]}),
        lambda quiz: quiz.model_copy(
            update={
                "questions": [
                    QuizQuestion.model_construct(
                        id="bad",
                        q="Bad question?",
                        options=["A", "B", "C", "D"],
                        answer_index=7,
                        explanation="Out of range.",
                    ),
                    *quiz.questions[1:],
                ]
            }
        ),
        lambda quiz: quiz.model_copy(update={"questions": [
            quiz.questions[0].model_copy(update={"q": ""}),
            *quiz.questions[1:],
        ]}),
    ],
)
def test_validate_quiz_rejects_malformed_quizzes(mutate) -> None:
    with pytest.raises(ValueError):
        assessor.validate_quiz(mutate(_make_quiz()))


@pytest.mark.parametrize("skill", SEEDED_SKILLS)
def test_cache_fallback_when_llm_raises(monkeypatch: pytest.MonkeyPatch, skill: str) -> None:
    def boom(*args, **kwargs):
        raise LLMError("offline")

    monkeypatch.setattr(assessor, "call_llm", boom)
    quiz = assessor.generate_quiz(skill, level=2)

    assert quiz.skill == skill
    assert len(quiz.questions) == 5
    assert assessor.validate_quiz(quiz) is quiz


def test_generate_quiz_mock_mode_writes_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    monkeypatch.setattr(assessor, "CACHE_DIR", tmp_path)

    quiz = assessor.generate_quiz("TypeScript", level=4)

    assert quiz.skill == "TypeScript"
    assert len(quiz.questions) == 5
    assert assessor.validate_quiz(quiz) is quiz
    cached = tmp_path / "TypeScript.json"
    assert cached.is_file()
    restored = Quiz.model_validate_json(cached.read_text(encoding="utf-8"))
    assert assessor.validate_quiz(restored) is restored

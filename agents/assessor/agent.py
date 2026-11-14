from contracts.schemas import Quiz, ScoreResult


def generate_quiz(skill: str, level: int) -> Quiz:
    """Generate a skill quiz appropriate to the target level."""
    raise NotImplementedError


def score_quiz(quiz: Quiz, answers: list[int], previous_level: int) -> ScoreResult:
    """Score a submitted quiz and return a result with the next level estimate."""
    raise NotImplementedError


def simulate_score(skill: str, percent: int, previous_level: int) -> ScoreResult:
    """Return a score result for a simulated skill test."""
    raise NotImplementedError

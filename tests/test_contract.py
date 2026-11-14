import pytest
from pydantic import ValidationError

from contracts.llm import call_llm
from contracts.sample import SAMPLE_STATE
from contracts.schemas import AppState, Skill


def test_sample_state_round_trip() -> None:
    payload = SAMPLE_STATE.model_dump_json()
    restored = AppState.model_validate_json(payload)
    assert restored == SAMPLE_STATE


def test_call_llm_mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    mock = {"name": "Python", "level": 2, "source": "assessment"}
    result = call_llm("system", "user", Skill, mock=mock)
    assert result == Skill(**mock)


def test_skill_level_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError):
        Skill(name="Python", level=6, source="user")

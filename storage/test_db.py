from __future__ import annotations

import sqlite3

import pytest

from contracts.sample import SAMPLE_STATE
from contracts.schemas import AppState, UserProfile
from storage import db


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    path = tmp_path / "skillforce-test.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.delenv("SKILLFORCE_DB_PATH", raising=False)
    return path


def test_save_and_load_round_trip(isolated_db) -> None:
    db.save_state("learner-1", SAMPLE_STATE)
    restored = db.load_state("learner-1")
    assert restored == SAMPLE_STATE


def test_new_user_gets_a_fresh_default_state(isolated_db) -> None:
    state = db.load_state("brand-new-user")
    assert state == AppState(profile=UserProfile(name="brand-new-user"))
    assert state.profile.skills == []
    assert state.requirements is None
    assert state.roadmap is None
    assert state.recommendations == []


def test_saving_again_updates_the_single_row(isolated_db) -> None:
    db.save_state("learner-2", SAMPLE_STATE)

    updated = SAMPLE_STATE.model_copy(deep=True)
    updated.profile.name = "Updated Name"
    updated.profile.target_role = "Data Analyst"
    db.save_state("learner-2", updated)

    assert db.load_state("learner-2") == updated
    with sqlite3.connect(isolated_db) as connection:
        count = connection.execute("SELECT COUNT(*) FROM app_state").fetchone()[0]
    assert count == 1


def test_users_are_isolated(isolated_db) -> None:
    db.save_state("alice", SAMPLE_STATE)
    state = db.load_state("bob")
    assert state.profile.name == "bob"
    assert state.profile.target_role == ""


def test_blank_user_id_is_rejected(isolated_db) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        db.load_state("   ")
    with pytest.raises(ValueError, match="non-empty"):
        db.save_state("", SAMPLE_STATE)

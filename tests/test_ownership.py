from scripts.check_ownership import OWNERSHIP


def test_ownership_dict_covers_all_agents() -> None:
    assert set(OWNERSHIP) == {"agent1", "agent2", "agent3", "agent4", "agent5", "agent6", "agent7", "agent8", "agent9"}


def test_agent8_does_not_own_dashboard_files() -> None:
    assert "ui/dashboard/" not in OWNERSHIP["agent8"]

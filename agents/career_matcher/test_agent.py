from contracts.schemas import GapItem, GapReport, RoleRequirement, RoleRequirements, Skill
from agents.career_matcher.agent import compute_gap, radar_data


def _requirements(items: list[tuple[str, int, str]]) -> RoleRequirements:
    return RoleRequirements(
        role="Full Stack Developer",
        company="Acme",
        requirements=[
            RoleRequirement(skill=skill, level_required=level, priority=priority)
            for skill, level, priority in items
        ],
        confidence="curated",
    )


def _full_stack() -> RoleRequirements:
    return _requirements(
        [
            ("Python", 3, "must"),
            ("SQL", 3, "must"),
            ("HTML", 2, "bonus"),
            ("JavaScript", 3, "must"),
            ("React", 3, "good"),
            ("Node.js", 3, "good"),
        ]
    )


def _sample_skills() -> list[Skill]:
    return [
        Skill(name="Python", level=3, source="assessment"),
        Skill(name="SQL", level=3, source="assessment"),
        Skill(name="HTML", level=2, source="user"),
    ]


def test_sample_top_gaps() -> None:
    gap = compute_gap(_sample_skills(), _full_stack())

    assert [item.skill for item in gap.gaps][:3] == ["JavaScript", "React", "Node.js"]
    assert all(item.gap > 0 for item in gap.gaps)
    assert gap.match_percent == 48.8


def test_empty_skills_and_requirements() -> None:
    empty_req = _requirements([])
    report = compute_gap([], empty_req)
    assert report.match_percent == 100.0
    assert report.gaps == []
    assert report.strengths == []

    no_skills = compute_gap([], _full_stack())
    assert len(no_skills.gaps) == 6
    assert all(item.current == 0 for item in no_skills.gaps)
    assert no_skills.match_percent == 0.0
    assert no_skills.strengths == []


def test_missing_skill_counts_as_level_zero() -> None:
    gap = compute_gap([Skill(name="Python", level=5, source="user")], _full_stack())

    sql = next(item for item in gap.gaps if item.skill == "SQL")
    assert sql.current == 0
    assert sql.required == 3
    assert sql.gap == 3
    assert "Python" in gap.strengths


def test_matching_is_case_insensitive() -> None:
    skills = [
        Skill(name="python", level=3, source="user"),
        Skill(name="  sql ", level=4, source="user"),
        Skill(name="html", level=2, source="user"),
        Skill(name="JAVASCRIPT", level=1, source="user"),
    ]
    gap = compute_gap(skills, _full_stack())

    by_skill = {item.skill: item for item in gap.gaps}
    assert "Python" not in by_skill
    assert "SQL" not in by_skill
    assert "HTML" not in by_skill
    assert by_skill["JavaScript"].current == 1
    assert by_skill["JavaScript"].gap == 2
    assert "Python" in gap.strengths
    assert "SQL" in gap.strengths


def test_strengths_are_at_or_above_required() -> None:
    gap = compute_gap(
        [
            Skill(name="Python", level=4, source="user"),
            Skill(name="SQL", level=3, source="assessment"),
        ],
        _requirements([("Python", 3, "must"), ("SQL", 3, "must")]),
    )

    assert gap.gaps == []
    assert gap.strengths == ["Python", "SQL"]
    assert gap.match_percent == 100.0


def test_gap_sorting_ties_prefer_must_over_good_over_bonus() -> None:
    req = _requirements(
        [
            ("BonusLow", 3, "bonus"),
            ("GoodTie", 3, "good"),
            ("MustTie", 2, "must"),
            ("MustLow", 1, "must"),
            ("BigMust", 5, "must"),
        ]
    )
    gap = compute_gap([], req)

    assert [item.skill for item in gap.gaps] == [
        "BigMust",
        "MustTie",
        "GoodTie",
        "MustLow",
        "BonusLow",
    ]


def test_radar_data_lists_are_aligned() -> None:
    gap = compute_gap(_sample_skills(), _full_stack())
    radar = radar_data(gap)

    assert len(radar["labels"]) == len(radar["current"]) == len(radar["required"])
    assert radar["labels"] == ["JavaScript", "React", "Node.js"]
    assert radar["current"] == [0, 0, 0]
    assert radar["required"] == [3, 3, 3]


def test_radar_data_orders_by_priority() -> None:
    gap = GapReport(
        match_percent=25.0,
        gaps=[
            GapItem(skill="Bonus", current=0, required=2, gap=2, priority="bonus"),
            GapItem(skill="Must", current=1, required=3, gap=2, priority="must"),
            GapItem(skill="Good", current=0, required=2, gap=2, priority="good"),
        ],
    )

    radar = radar_data(gap)

    assert radar["labels"] == ["Must", "Good", "Bonus"]
    assert radar["current"] == [1, 0, 0]
    assert radar["required"] == [3, 2, 2]


def test_radar_data_empty_report() -> None:
    radar = radar_data(GapReport(match_percent=100.0))

    assert radar == {"labels": [], "current": [], "required": []}


def test_radar_data_with_req_and_skills_includes_strengths() -> None:
    gap = compute_gap(_sample_skills(), _full_stack())
    radar = radar_data(gap, req=_full_stack(), skills=_sample_skills())

    assert radar["labels"] == ["Python", "SQL", "JavaScript", "React", "Node.js", "HTML"]
    assert radar["current"] == [3, 3, 0, 0, 0, 2]
    assert radar["required"] == [3, 3, 3, 3, 3, 2]
    assert len(radar["labels"]) == len(radar["current"]) == len(radar["required"])

    strength = radar["labels"].index("Python")
    assert "Python" in gap.strengths
    assert radar["current"][strength] == radar["required"][strength]


def test_radar_data_with_req_and_skills_is_case_insensitive() -> None:
    skills = [
        Skill(name="python", level=4, source="user"),
        Skill(name="  REACT ", level=2, source="assessment"),
    ]
    radar = radar_data(
        GapReport(match_percent=50.0),
        req=_requirements([("Python", 3, "must"), ("React", 3, "good"), ("SQL", 3, "must")]),
        skills=skills,
    )

    assert radar["labels"] == ["Python", "SQL", "React"]
    assert radar["current"] == [4, 0, 2]
    assert radar["required"] == [3, 3, 3]


def test_radar_data_partial_args_keep_gap_only_behavior() -> None:
    gap = compute_gap(_sample_skills(), _full_stack())
    expected = radar_data(gap)

    assert radar_data(gap, req=_full_stack()) == expected
    assert radar_data(gap, skills=_sample_skills()) == expected
    assert radar_data(gap, req=None, skills=None) == expected


def test_radar_data_with_empty_requirements() -> None:
    radar = radar_data(
        GapReport(match_percent=100.0),
        req=_requirements([]),
        skills=_sample_skills(),
    )

    assert radar == {"labels": [], "current": [], "required": []}

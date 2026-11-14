from __future__ import annotations

from contracts.schemas import (
    AppState,
    GapItem,
    GapReport,
    LogEntry,
    Recommendation,
    Resource,
    Roadmap,
    RoadmapStep,
    RoleRequirement,
    RoleRequirements,
    ScoreResult,
    Skill,
    UserProfile,
)

SAMPLE_PROFILE = UserProfile(
    name="Aarav",
    skills=[
        Skill(name="Python", level=3, source="user"),
        Skill(name="SQL", level=3, source="user"),
        Skill(name="HTML", level=2, source="user"),
        Skill(name="JavaScript", level=2, source="user"),
    ],
    certs=["Google Data Analytics"],
    projects=["Personal portfolio website", "Sales dashboard mockup"],
    target_role="Full Stack Developer",
    target_company="Zoho",
)

SAMPLE_STATE = AppState(
    profile=SAMPLE_PROFILE,
    requirements=RoleRequirements(
        role="Full Stack Developer",
        company="Zoho",
        requirements=[
            RoleRequirement(skill="Python", level_required=3, priority="must", note="Core backend work."),
            RoleRequirement(skill="SQL", level_required=4, priority="must", note="Data modeling and querying."),
            RoleRequirement(skill="HTML", level_required=3, priority="good", note="UI structure basics."),
            RoleRequirement(skill="JavaScript", level_required=3, priority="must", note="Frontend interaction."),
            RoleRequirement(skill="Project Delivery", level_required=2, priority="bonus", note="Production mindset."),
        ],
        tools=["Python", "SQL", "HTML", "JavaScript", "Git"],
        certs=["Azure Fundamentals"],
        interview_process=["Technical screen", "Pair programming", "Behavioral round"],
        confidence="curated",
        disclaimer="Example data for the scaffold only.",
    ),
    gap=GapReport(
        match_percent=72.0,
        gaps=[
            GapItem(skill="SQL", current=3, required=4, gap=1, priority="must"),
            GapItem(skill="HTML", current=2, required=3, gap=1, priority="good"),
            GapItem(skill="JavaScript", current=2, required=3, gap=1, priority="must"),
        ],
        strengths=["Python", "Project ownership"],
    ),
    roadmap=Roadmap(
        steps=[
            RoadmapStep(
                order=1,
                skill="Python",
                target_level=4,
                resources=[
                    Resource(title="Python Crash Course", url="https://example.com/python-crash-course"),
                    Resource(title="Real Python", url="https://example.com/real-python"),
                ],
                mini_project="Build a small Flask API with CRUD endpoints.",
                practice_tasks=["Create endpoints", "Add validation", "Write tests"],
                status="doing",
            ),
            RoadmapStep(
                order=2,
                skill="SQL",
                target_level=4,
                resources=[
                    Resource(title="SQLBolt", url="https://example.com/sqlbolt"),
                ],
                mini_project="Design a retail schema and answer business queries.",
                practice_tasks=["Write joins", "Create indexes", "Analyze query plans"],
            ),
            RoadmapStep(
                order=3,
                skill="HTML",
                target_level=3,
                resources=[
                    Resource(title="MDN HTML Guide", url="https://example.com/mdn-html"),
                ],
                mini_project="Create a responsive landing page for a portfolio.",
                practice_tasks=["Build layout", "Test accessibility", "Use semantic markup"],
            ),
            RoadmapStep(
                order=4,
                skill="JavaScript",
                target_level=3,
                resources=[
                    Resource(title="JavaScript.info", url="https://example.com/javascript-info"),
                ],
                mini_project="Add interactive dashboard widgets to a sample app.",
                practice_tasks=["Handle DOM events", "Use fetch", "Manage state"],
            ),
        ],
        est_hours=18,
    ),
    recommendations=[
        Recommendation(
            title="Build a small full-stack portfolio app",
            type="project",
            why="Showcases Python, SQL, and frontend skills in one deployable example.",
            effort_hours=12,
        ),
        Recommendation(
            title="Prepare for Azure Fundamentals",
            type="cert",
            why="The target company values cloud literacy and this cert aligns with the role.",
            effort_hours=8,
        ),
        Recommendation(
            title="Practice behavioral storytelling",
            type="interview_prep",
            why="Help explain your projects and trade-offs in product and team settings.",
            effort_hours=4,
        ),
    ],
    scores=[
        ScoreResult(skill="Python", score_percent=82.0, new_level=4, weak=False),
    ],
    log=[
        LogEntry(agent="system", action="seed_profile", reason="Loaded the sample learner profile."),
        LogEntry(agent="company_intel", action="requirements_loaded", reason="Curated a sample role for a Full Stack Developer."),
        LogEntry(agent="planner", action="roadmap_created", reason="Built an initial learning plan for the target role."),
    ],
)

__all__ = ["SAMPLE_PROFILE", "SAMPLE_STATE"]

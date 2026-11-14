from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A user skill with a proficiency level and origin."""

    name: str
    level: int = Field(ge=0, le=5)
    source: Literal["user", "assessment", "inferred"]


class UserProfile(BaseModel):
    """Basic profile data for a learner and their target role."""

    name: str
    skills: list[Skill] = Field(default_factory=list)
    certs: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    target_role: str = ""
    target_company: str | None = None


class RoleRequirement(BaseModel):
    """A role requirement describing a target skill and its priority."""

    skill: str
    level_required: int = Field(ge=1, le=5)
    priority: Literal["must", "good", "bonus"]
    note: str = ""


class RoleRequirements(BaseModel):
    """A curated or AI-estimated job requirement summary."""

    role: str
    company: str | None
    requirements: list[RoleRequirement]
    tools: list[str] = Field(default_factory=list)
    certs: list[str] = Field(default_factory=list)
    interview_process: list[str] = Field(default_factory=list)
    confidence: Literal["curated", "ai_estimated"]
    disclaimer: str = ""


class Recommendation(BaseModel):
    """A recommended action to close a gap or improve readiness."""

    title: str
    type: Literal["project", "cert", "interview_prep", "open_source", "networking"]
    why: str
    effort_hours: int


class GapItem(BaseModel):
    """A mismatch between current and required skill level."""

    skill: str
    current: int
    required: int
    gap: int
    priority: Literal["must", "good", "bonus"]


class GapReport(BaseModel):
    """A summary of a learner's readiness against a target role."""

    match_percent: float
    gaps: list[GapItem] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)


class Resource(BaseModel):
    """An educational resource for a skill or roadmap step."""

    title: str
    url: str


class RoadmapStep(BaseModel):
    """A concrete step toward a target skill level."""

    order: int
    skill: str
    target_level: int = Field(ge=0, le=5)
    resources: list[Resource] = Field(default_factory=list)
    mini_project: str = ""
    practice_tasks: list[str] = Field(default_factory=list)
    status: Literal["todo", "doing", "done", "revision"] = "todo"


class Roadmap(BaseModel):
    """The planned training roadmap for the learner."""

    steps: list[RoadmapStep] = Field(default_factory=list)
    est_hours: int = 0


class QuizQuestion(BaseModel):
    """A single multiple-choice question for a skill assessment."""

    id: str
    q: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer_index: int = Field(ge=0, le=3)
    explanation: str


class Quiz(BaseModel):
    """A skill quiz with multiple questions and answers."""

    skill: str
    questions: list[QuizQuestion]


class ScoreResult(BaseModel):
    """The outcome of a skill score or simulated assessment."""

    skill: str
    score_percent: float = Field(ge=0, le=100)
    new_level: int = Field(ge=0, le=5)
    weak: bool


class LogEntry(BaseModel):
    """An audit log entry tracking agent actions."""

    agent: str
    action: str
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AppState(BaseModel):
    """Global app state for the learner experience."""

    profile: UserProfile
    requirements: RoleRequirements | None = None
    gap: GapReport | None = None
    roadmap: Roadmap | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    scores: list[ScoreResult] = Field(default_factory=list)
    log: list[LogEntry] = Field(default_factory=list)

    def add_log(self, agent: str, action: str, reason: str) -> None:
        self.log.append(LogEntry(agent=agent, action=action, reason=reason))

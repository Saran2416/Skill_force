from contracts.schemas import GapReport, Roadmap, RoleRequirements


def build_roadmap(
    gap: GapReport,
    req: RoleRequirements,
    weak_skills: list[str] = [],
    completed: list[str] = [],
) -> Roadmap:
    """Build a roadmap for a user's gap report and role requirements."""
    raise NotImplementedError

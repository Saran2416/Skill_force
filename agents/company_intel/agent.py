from contracts.schemas import Recommendation, RoleRequirements, UserProfile


def get_requirements(role: str, company: str | None) -> RoleRequirements:
    """Return a role requirement set for a company and target role."""
    raise NotImplementedError


def get_recommendations(req: RoleRequirements, profile: UserProfile) -> list[Recommendation]:
    """Recommend actions based on the target role requirements and profile."""
    raise NotImplementedError

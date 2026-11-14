from contracts.schemas import Skill


def analyze_profile(raw_text: str, certs: list[str], projects: list[str]) -> list[Skill]:
    """Analyze a raw profile and API-provided metadata to infer skills."""
    raise NotImplementedError

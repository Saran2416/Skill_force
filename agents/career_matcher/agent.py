from contracts.schemas import GapReport


def compute_gap(skills: list, req: object) -> GapReport:
    """Compare a learner's skills against a job requirement set."""
    raise NotImplementedError


def radar_data(gap: GapReport) -> dict:
    """Return radar chart data for the current gap report."""
    raise NotImplementedError

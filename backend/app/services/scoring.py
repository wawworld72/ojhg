from __future__ import annotations

from app.models.problem import AttemptScoreTier


def find_score_tier(attempt_count: int, tiers: list[AttemptScoreTier]) -> AttemptScoreTier | None:
    """Return matching score tier for the given attempt count, or None if no match."""
    for tier in sorted(tiers, key=lambda t: t.min_attempts):
        if attempt_count < tier.min_attempts:
            continue
        if tier.max_attempts is None or attempt_count <= tier.max_attempts:
            return tier
    return None


def compute_final_score(max_points: float, tier: AttemptScoreTier | None) -> float:
    if tier is None:
        return 0.0
    return round(float(max_points) * float(tier.score_ratio) / 100.0, 2)

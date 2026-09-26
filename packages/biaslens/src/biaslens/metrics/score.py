"""Information Inequality Score (0-100).

A single documented number summarizing how unequally a query's information
landscape is served across the audited (city, language) variants. Formula
and weight rationale are mirrored in docs/methodology.md -- keep both in
sync if you change the weights here.

Each component is normalized to [0, 1] before weighting so the final score
is always in [0, 100], where 0 = identical, equally-served information
across every variant, and 100 = maximally divergent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_WEIGHTS: dict[str, float] = {
    "overlap": 0.40,      # how different the actual result sets are
    "quality": 0.20,      # how differently trustworthy the sources are
    "language": 0.25,     # how unevenly results match the query's language
    "diversity": 0.15,    # how unevenly diverse the source mix is
}


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float
    overlap_component: float
    quality_component: float
    language_component: float
    diversity_component: float
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


def _spread(values: list[float], *, value_range: float = 1.0) -> float:
    """Normalized (max - min) / value_range, clamped to [0, 1]. 0.0 for <2 values."""
    if len(values) < 2:
        return 0.0
    spread = (max(values) - min(values)) / value_range
    return max(0.0, min(1.0, spread))


def information_inequality_score(
    *,
    pairwise_rbo: list[float],
    quality_scores_0_100: list[float],
    language_match_rates_0_1: list[float],
    normalized_entropies_0_1: list[float],
    weights: dict[str, float] | None = None,
) -> ScoreBreakdown:
    """Combine overlap, quality, language, and diversity into one 0-100 score.

    - overlap_component = 1 - mean(pairwise_rbo): low overlap -> more unequal.
    - quality_component = spread of per-variant quality scores (0-100 scale).
    - language_component = spread of per-variant language match rates.
    - diversity_component = spread of per-variant normalized entropy.

    All *_component values sit in [0, 1] before weighting. Missing inputs
    (empty lists) contribute 0 to their component rather than raising, so a
    partial audit still produces a (conservative) score.
    """
    w = weights or DEFAULT_WEIGHTS

    overlap_component = 1.0 - (sum(pairwise_rbo) / len(pairwise_rbo)) if pairwise_rbo else 0.0
    overlap_component = max(0.0, min(1.0, overlap_component))

    quality_component = _spread(quality_scores_0_100, value_range=100.0)
    language_component = _spread(language_match_rates_0_1, value_range=1.0)
    diversity_component = _spread(normalized_entropies_0_1, value_range=1.0)

    total = 100 * (
        w["overlap"] * overlap_component
        + w["quality"] * quality_component
        + w["language"] * language_component
        + w["diversity"] * diversity_component
    )

    return ScoreBreakdown(
        total=round(total, 2),
        overlap_component=round(overlap_component, 4),
        quality_component=round(quality_component, 4),
        language_component=round(language_component, 4),
        diversity_component=round(diversity_component, 4),
        weights=dict(w),
    )

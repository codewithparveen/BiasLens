"""Output-side models: what Auditor.audit() actually returns.

Kept separate from models.py's request/response layer so the "what SerpApi
gave us" models and the "what we computed" models don't blur together.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from .metrics.score import DEFAULT_WEIGHTS
from .models import AuditPlan, BiasLensModel, SearchVariant


class VariantMetrics(BiasLensModel):
    """All computed metrics for one (query, city, language) variant."""

    variant: SearchVariant
    label: str  # e.g. "Chennai/ta" -- used as the pairwise-comparison key
    result_count: int
    domains: list[str]
    quality_mix: dict[str, dict[str, float | int | str]]
    quality_score: float = Field(description="Weighted mean tier quality, 0-100.")
    normalized_entropy: float = Field(description="Source diversity, 0-1.")
    language_match_rate: float = Field(description="Share of results in the expected language, 0-1.")
    ad_count: int
    ai_overview_present: bool
    is_empty: bool
    reliability: dict[str, Any] = Field(
        default_factory=dict,
        description="metric name -> {n, mean, stdev, coefficient_of_variation} across runs_per_variant.",
    )
    warnings: list[str] = Field(default_factory=list)


class PairwiseComparisonResult(BiasLensModel):
    variant_a: str
    variant_b: str
    jaccard: float
    rbo: float


class QueryAuditResult(BiasLensModel):
    """Everything computed for a single query across all its variants."""

    query: str
    variants: list[VariantMetrics]
    pairwise: list[PairwiseComparisonResult]
    inequality_score: float
    score_breakdown: dict[str, float]
    score_weights: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


class AuditReport(BiasLensModel):
    """Public return type of Auditor.audit()."""

    plan: AuditPlan
    queries: list[QueryAuditResult]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    credits_used: int = 0
    cache_hits: int = 0
    is_demo_data: bool = Field(
        default=False,
        description="True for pre-recorded demo fixtures rather than a live SerpApi run.",
    )
    warnings: list[str] = Field(default_factory=list)

    def to_json(self, *, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def summary(self) -> dict[str, Any]:
        """A short, dashboard-ready digest: overall average and the most/least equal query."""
        if not self.queries:
            return {"query_count": 0, "average_inequality_score": 0.0}
        scores = [(q.query, q.inequality_score) for q in self.queries]
        avg = sum(s for _, s in scores) / len(scores)
        most_unequal = max(scores, key=lambda item: item[1])
        most_equal = min(scores, key=lambda item: item[1])
        return {
            "query_count": len(self.queries),
            "average_inequality_score": round(avg, 2),
            "most_unequal_query": {"query": most_unequal[0], "score": most_unequal[1]},
            "most_equal_query": {"query": most_equal[0], "score": most_equal[1]},
            "credits_used": self.credits_used,
            "is_demo_data": self.is_demo_data,
        }

    def to_html(self) -> str:
        """A minimal, dependency-free HTML render -- a real template lives in the frontend."""
        rows = []
        for q in self.queries:
            variant_rows = "".join(
                f"<tr><td>{v.label}</td><td>{v.result_count}</td>"
                f"<td>{v.quality_score:.1f}</td><td>{v.language_match_rate:.0%}</td>"
                f"<td>{v.normalized_entropy:.2f}</td></tr>"
                for v in q.variants
            )
            rows.append(
                f"<h3>{q.query} &mdash; Inequality Score: {q.inequality_score:.1f}/100</h3>"
                f"<table border='1' cellpadding='4'>"
                f"<tr><th>Variant</th><th>Results</th><th>Quality</th>"
                f"<th>Language Match</th><th>Diversity</th></tr>{variant_rows}</table>"
            )
        demo_note = "<p><em>Demo data (synthetic fixtures).</em></p>" if self.is_demo_data else ""
        return (
            "<html><head><title>BiasLens Audit Report</title></head><body>"
            f"<h1>BiasLens Audit Report</h1>{demo_note}{''.join(rows)}</body></html>"
        )

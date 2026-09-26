"""Turns an AuditPlan into a concrete credit cost, and enforces limits.

Every Google Search call and every Google Trends call costs 1 SerpApi
credit. The Locations API is free and never counted here. This module is
deliberately dumb and synchronous -- it never makes a network call, so
`estimate()` is instant and always safe to call.
"""

from __future__ import annotations

from typing import Protocol

from .cache import make_cache_key
from .exceptions import CreditBudgetExceeded
from .models import AuditPlan, CreditBudget, SearchVariant


class SQLiteCacheLike(Protocol):
    def get(self, key: str) -> dict[str, object] | None: ...


class CreditGuard:
    """Estimates cost and enforces `max_credits` before any spend happens."""

    def __init__(self, cache: SQLiteCacheLike | None = None) -> None:
        self._cache = cache

    def estimate(
        self,
        plan: AuditPlan,
        *,
        max_credits: int | None = None,
        include_trends: bool = True,
    ) -> CreditBudget:
        variants = plan.variants()
        cache_hits = self._count_cache_hits(variants, plan.runs_per_variant) if self._cache else 0

        raw_search_calls = plan.total_calls()
        search_calls = max(raw_search_calls - cache_hits, 0)

        trends_calls = len(plan.queries) if include_trends else 0

        total = search_calls + trends_calls
        budget = CreditBudget(
            search_calls=search_calls,
            trends_calls=trends_calls,
            total_credits=total,
            cache_hits_expected=cache_hits,
            max_credits=max_credits,
            within_budget=(max_credits is None) or (total <= max_credits),
        )
        return budget

    def enforce(self, budget: CreditBudget, *, override: bool = False) -> None:
        """Raise CreditBudgetExceeded unless the budget fits or override=True."""
        if budget.max_credits is None:
            return
        if budget.total_credits > budget.max_credits and not override:
            raise CreditBudgetExceeded(budget.total_credits, budget.max_credits)

    def _count_cache_hits(self, variants: list[SearchVariant], runs_per_variant: int) -> int:
        assert self._cache is not None
        hits = 0
        for v in variants:
            for run_idx in range(runs_per_variant):
                key = make_cache_key(
                    "search",
                    {
                        "query": v.query,
                        "city": v.city,
                        "language": v.language,
                        "google_domain": v.google_domain,
                        "country": v.country,
                        "num_results": v.num_results,
                        "run_idx": run_idx,
                    },
                )
                if self._cache.get(key) is not None:
                    hits += 1
        return hits

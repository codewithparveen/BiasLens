import pytest

from biaslens.cache import SQLiteCache, make_cache_key
from biaslens.credit_guard import CreditGuard
from biaslens.exceptions import CreditBudgetExceeded
from biaslens.models import AuditPlan


def _plan() -> AuditPlan:
    return AuditPlan(
        queries=["diabetes home remedy", "crop loan"],
        cities=["Chennai", "Delhi", "Bengaluru"],
        languages=["ta", "hi", "en"],
        runs_per_variant=2,
    )


def test_estimate_without_cache_counts_everything() -> None:
    guard = CreditGuard(cache=None)
    plan = _plan()
    budget = guard.estimate(plan, max_credits=None)
    # 2 queries x 3 cities x 3 languages x 2 runs = 36 search calls
    assert budget.search_calls == 36
    assert budget.trends_calls == 2  # one per unique query
    assert budget.total_credits == 38
    assert budget.cache_hits_expected == 0
    assert budget.within_budget is True


def test_estimate_respects_max_credits() -> None:
    guard = CreditGuard(cache=None)
    plan = _plan()
    budget = guard.estimate(plan, max_credits=10)
    assert budget.within_budget is False
    assert budget.total_credits == 38


def test_enforce_raises_when_over_budget() -> None:
    guard = CreditGuard(cache=None)
    plan = _plan()
    budget = guard.estimate(plan, max_credits=10)
    with pytest.raises(CreditBudgetExceeded):
        guard.enforce(budget)


def test_enforce_allows_override() -> None:
    guard = CreditGuard(cache=None)
    plan = _plan()
    budget = guard.estimate(plan, max_credits=10)
    guard.enforce(budget, override=True)  # should not raise


def test_estimate_discounts_cache_hits(tmp_path) -> None:
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    plan = AuditPlan(queries=["q1"], cities=["Chennai"], languages=["ta"], runs_per_variant=2)
    # Pre-populate the cache for run_idx=0 only.
    key = make_cache_key(
        "search",
        {
            "query": "q1",
            "city": "Chennai",
            "language": "ta",
            "google_domain": "google.co.in",
            "country": "in",
            "num_results": 10,
            "run_idx": 0,
        },
    )
    cache.set(key, {"organic_results": []})

    guard = CreditGuard(cache=cache)
    budget = guard.estimate(plan, max_credits=None)
    assert budget.cache_hits_expected == 1
    assert budget.search_calls == 1  # 2 total - 1 cache hit
    cache.close()

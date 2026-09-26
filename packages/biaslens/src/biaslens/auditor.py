"""The public, high-level entry point: ``Auditor``.

Everything below this is plumbing -- Auditor is what a library user (and
the CLI, and the FastAPI backend) actually calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .cache import SQLiteCache
from .client import SerpApiClient
from .credit_guard import CreditGuard
from .metrics.diversity import normalized_entropy
from .metrics.overlap import pairwise_overlap
from .metrics.quality import DomainTierClassifier
from .metrics.reliability import variance_report
from .metrics.score import information_inequality_score
from .models import AuditPlan, EstimateResult, SearchResponse, SearchVariant
from .report import AuditReport, PairwiseComparisonResult, QueryAuditResult, VariantMetrics

ProgressCallback = Callable[[dict[str, Any]], None]


def _variant_label(city: str, language: str) -> str:
    return f"{city}/{language}"


class Auditor:
    """High-level orchestrator: estimate a plan's cost, or run it end to end."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        cache: str | SQLiteCache | None = "sqlite",
        cache_path: str | Path = "biaslens_cache.sqlite3",
        domain_tiers_path: str | Path | None = None,
    ) -> None:
        self._api_key = api_key
        if isinstance(cache, SQLiteCache):
            self._cache: SQLiteCache | None = cache
        elif cache == "sqlite":
            self._cache = SQLiteCache(cache_path)
        elif cache is None:
            self._cache = None
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported cache option: {cache!r}")
        self._quality = DomainTierClassifier(domain_tiers_path)

    # ------------------------------------------------------------------
    # Estimation -- never touches the network.
    # ------------------------------------------------------------------

    def estimate(
        self,
        queries: list[str],
        cities: list[str],
        languages: list[str],
        *,
        runs_per_variant: int = 2,
        max_credits: int | None = None,
        include_trends: bool = True,
    ) -> EstimateResult:
        plan = AuditPlan(
            queries=queries, cities=cities, languages=languages, runs_per_variant=runs_per_variant
        )
        guard = CreditGuard(cache=self._cache)
        budget = guard.estimate(plan, max_credits=max_credits, include_trends=include_trends)
        return EstimateResult(plan=plan, budget=budget, variants_preview=plan.variants()[:10])

    # ------------------------------------------------------------------
    # Audit -- the real thing.
    # ------------------------------------------------------------------

    def audit(
        self,
        queries: list[str],
        cities: list[str],
        languages: list[str],
        *,
        runs_per_variant: int = 2,
        max_credits: int | None = None,
        override: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> AuditReport:
        """Synchronous convenience wrapper around audit_async()."""
        return asyncio.run(
            self.audit_async(
                queries,
                cities,
                languages,
                runs_per_variant=runs_per_variant,
                max_credits=max_credits,
                override=override,
                on_progress=on_progress,
            )
        )

    async def audit_async(
        self,
        queries: list[str],
        cities: list[str],
        languages: list[str],
        *,
        runs_per_variant: int = 2,
        max_credits: int | None = None,
        override: bool = False,
        on_progress: ProgressCallback | None = None,
    ) -> AuditReport:
        plan = AuditPlan(
            queries=queries, cities=cities, languages=languages, runs_per_variant=runs_per_variant
        )
        guard = CreditGuard(cache=self._cache)
        # Trends integration is not wired into this version of audit_async, so
        # the enforced/reported budget only counts what actually gets called:
        # Google Search. estimate() still defaults to include_trends=True for
        # up-front planning purposes.
        budget = guard.estimate(plan, max_credits=max_credits, include_trends=False)
        guard.enforce(budget, override=override)

        client = SerpApiClient(api_key=self._api_key, cache=self._cache)
        report_warnings: list[str] = []
        query_results: list[QueryAuditResult] = []

        try:
            for q_idx, query in enumerate(queries):
                variants = [
                    SearchVariant(
                        query=query,
                        city=city,
                        language=lang,
                        google_domain=plan.google_domain,
                        country=plan.country,
                        num_results=plan.num_results,
                    )
                    for city in cities
                    for lang in languages
                ]
                responses = await client.search_many(variants, runs_per_variant=runs_per_variant)

                grouped: dict[str, list[SearchResponse]] = {}
                for resp in responses:
                    label = _variant_label(resp.variant.city, resp.variant.language)
                    grouped.setdefault(label, []).append(resp)

                variant_metrics: list[VariantMetrics] = []
                domains_by_label: dict[str, list[str]] = {}
                for variant in variants:
                    label = _variant_label(variant.city, variant.language)
                    runs = grouped.get(label, [])
                    vm, warnings = self._build_variant_metrics(variant, label, runs)
                    variant_metrics.append(vm)
                    domains_by_label[label] = vm.domains
                    report_warnings.extend(warnings)

                pairwise_raw = pairwise_overlap(domains_by_label)
                pairwise = [
                    PairwiseComparisonResult(
                        variant_a=str(p["variant_a"]),
                        variant_b=str(p["variant_b"]),
                        jaccard=float(p["jaccard"]),  # type: ignore[arg-type]
                        rbo=float(p["rbo"]),  # type: ignore[arg-type]
                    )
                    for p in pairwise_raw
                ]

                score = information_inequality_score(
                    pairwise_rbo=[p.rbo for p in pairwise],
                    quality_scores_0_100=[v.quality_score for v in variant_metrics],
                    language_match_rates_0_1=[v.language_match_rate for v in variant_metrics],
                    normalized_entropies_0_1=[v.normalized_entropy for v in variant_metrics],
                )

                query_results.append(
                    QueryAuditResult(
                        query=query,
                        variants=variant_metrics,
                        pairwise=pairwise,
                        inequality_score=score.total,
                        score_breakdown={
                            "overlap": score.overlap_component,
                            "quality": score.quality_component,
                            "language": score.language_component,
                            "diversity": score.diversity_component,
                        },
                    )
                )

                if on_progress is not None:
                    on_progress(
                        {
                            "completed_queries": q_idx + 1,
                            "total_queries": len(queries),
                            "current_query": query,
                        }
                    )
        finally:
            await client.aclose()

        return AuditReport(
            plan=plan,
            queries=query_results,
            credits_used=budget.total_credits,
            cache_hits=budget.cache_hits_expected,
            is_demo_data=False,
            warnings=report_warnings,
        )

    def cache_stats(self) -> dict[str, int]:
        if self._cache is None:
            return {"total_entries": 0, "expired_entries": 0, "live_entries": 0}
        return self._cache.stats()

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_variant_metrics(
        self, variant: SearchVariant, label: str, runs: list[SearchResponse]
    ) -> tuple[VariantMetrics, list[str]]:
        warnings: list[str] = [w.message for r in runs for w in r.warnings]

        primary = runs[0] if runs else None
        domains = primary.domains if primary else []
        snippets = [r.snippet for r in (primary.organic_results if primary else []) if r.snippet]

        result_counts = [float(len(r.organic_results)) for r in runs]
        quality_scores_per_run = [self._quality.weighted_quality_score(r.domains) for r in runs]

        vm = VariantMetrics(
            variant=variant,
            label=label,
            result_count=len(domains),
            domains=domains,
            quality_mix=self._quality.quality_mix(domains),
            quality_score=self._quality.weighted_quality_score(domains),
            normalized_entropy=normalized_entropy(domains),
            language_match_rate=self._language_match_rate(snippets, variant.language),
            ad_count=len(primary.ads) if primary else 0,
            ai_overview_present=primary.ai_overview.present if primary else False,
            is_empty=primary.is_empty if primary else True,
            reliability={
                "result_count": self._variance_dict(result_counts),
                "quality_score": self._variance_dict(quality_scores_per_run),
            },
            warnings=warnings,
        )
        return vm, warnings

    @staticmethod
    def _variance_dict(values: list[float]) -> dict[str, Any]:
        r = variance_report(values)
        return {
            "n": r.n,
            "mean": round(r.mean, 3),
            "stdev": round(r.stdev, 3),
            "coefficient_of_variation": (
                round(r.coefficient_of_variation, 3) if r.coefficient_of_variation is not None else None
            ),
        }

    @staticmethod
    def _language_match_rate(snippets: list[str], language: str) -> float:
        from .metrics.language import language_match_rate

        return language_match_rate(snippets, language)


__all__ = ["Auditor", "AuditReport"]

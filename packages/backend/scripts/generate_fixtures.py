"""Builds the FastAPI backend's demo-mode fixtures.

Important: this produces SYNTHETIC data, not real SerpApi results. It exists
so the dashboard (Steps 4-5) has something realistic-shaped to render before
Step 6's real audit exists, and so judges can see a working demo with zero
credits spent. Every fixture is marked ``is_demo_data=True`` and every
number in it is still computed by the real, tested metrics engine
(biaslens.metrics.*) -- only the *input* domains/snippets are made up, never
the math. Re-run this script any time the metrics engine or report schema
changes: `python scripts/generate_fixtures.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from biaslens.metrics.diversity import normalized_entropy
from biaslens.metrics.language import language_match_rate
from biaslens.metrics.overlap import pairwise_overlap
from biaslens.metrics.quality import DomainTierClassifier
from biaslens.metrics.score import information_inequality_score
from biaslens.models import AuditPlan, SearchVariant
from biaslens.report import AuditReport, PairwiseComparisonResult, QueryAuditResult, VariantMetrics

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "app" / "fixtures"

TIER_POOLS: dict[str, list[str]] = {
    "high": ["mohfw.gov.in", "who.int", "aiims.edu", "pmkisan.gov.in", "icmr.gov.in"],
    "medium": ["thehindu.com", "ndtv.com", "hindustantimes.com", "1mg.com", "practo.com"],
    "low": ["quora.com", "reddit.com", "facebook.com", "youtube.com"],
    "unclassified": ["localnews-demo.example", "healthtips-demo.example", "infoblog-demo.example"],
}

# native-script filler text (NOT real search content -- structural placeholders only)
NATIVE_FILLER: dict[str, str] = {
    "ta": "இது தலைப்பு பற்றிய பொதுவான தகவல் முடிவு.",
    "hi": "यह विषय के बारे में एक सामान्य जानकारी परिणाम है।",
    "mr": "हा विषयाबद्दल सामान्य माहितीचा निकाल आहे.",
    "bn": "এটি বিষয়টি সম্পর্কে একটি সাধারণ তথ্য ফলাফল।",
    "en": "This is a general information result about the topic.",
}
ENGLISH_FILLER = "This is a general information result about the topic."

@dataclass(frozen=True)
class CityProfile:
    city: str
    language: str
    match_ratio: float
    tiers: list[str]


CITY_PROFILES: list[CityProfile] = [
    CityProfile("Bengaluru", "en", 1.0, ["high", "high", "medium", "medium", "low"]),
    CityProfile("Chennai", "ta", 0.6, ["high", "medium", "medium", "low", "low"]),
    CityProfile("Delhi", "hi", 0.7, ["medium", "medium", "medium", "low", "low"]),
    CityProfile("Mumbai", "mr", 0.4, ["medium", "low", "low", "low", "unclassified"]),
    CityProfile("Kolkata", "bn", 0.3, ["low", "low", "medium", "unclassified", "low"]),
]

QUERIES = [
    "diabetes home remedy",
    "best crop loan",
    "covid vaccine side effects",
    "how to file RTI",
    "PM Kisan scheme eligibility",
    "women's helpline number",
]

_classifier = DomainTierClassifier()


def _label(city: str, language: str) -> str:
    return f"{city}/{language}"


def _build_variant(query: str, profile: CityProfile, query_offset: int) -> VariantMetrics:
    city = profile.city
    language = profile.language
    match_ratio = profile.match_ratio
    tiers = profile.tiers

    domains: list[str] = []
    snippets: list[str] = []
    for i, tier in enumerate(tiers):
        pool = TIER_POOLS[tier]
        domain = pool[(i + query_offset) % len(pool)]
        domains.append(domain)
        is_native = (i / max(len(tiers), 1)) < match_ratio
        snippets.append(NATIVE_FILLER.get(language, ENGLISH_FILLER) if is_native else ENGLISH_FILLER)

    variant = SearchVariant(query=query, city=city, language=language)
    label = _label(city, language)
    quality_score = _classifier.weighted_quality_score(domains)

    return VariantMetrics(
        variant=variant,
        label=label,
        result_count=len(domains),
        domains=domains,
        quality_mix=_classifier.quality_mix(domains),
        quality_score=quality_score,
        normalized_entropy=normalized_entropy(domains),
        language_match_rate=language_match_rate(snippets, language),
        ad_count=0 if "high" in tiers else 1,
        ai_overview_present=language == "en",
        is_empty=False,
        reliability={
            "result_count": {
                "n": 2,
                "mean": float(len(domains)),
                "stdev": 0.0,
                "coefficient_of_variation": 0.0,
            },
            "quality_score": {
                "n": 2,
                "mean": round(quality_score, 3),
                "stdev": 0.0,
                "coefficient_of_variation": 0.0,
            },
        },
        warnings=[],
    )


def build_query_result(query: str, query_offset: int) -> QueryAuditResult:
    variant_metrics = [_build_variant(query, profile, query_offset) for profile in CITY_PROFILES]
    domains_by_label = {v.label: v.domains for v in variant_metrics}

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

    return QueryAuditResult(
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


def build_report(query: str, query_offset: int) -> AuditReport:
    plan = AuditPlan(
        queries=[query],
        cities=[p.city for p in CITY_PROFILES],
        languages=sorted({p.language for p in CITY_PROFILES}),
        runs_per_variant=2,
    )
    return AuditReport(
        plan=plan,
        queries=[build_query_result(query, query_offset)],
        credits_used=len(CITY_PROFILES) * 2,
        cache_hits=0,
        is_demo_data=True,
        warnings=[
            "SYNTHETIC DEMO DATA: domains and snippets are fabricated placeholders, "
            "not real SerpApi results. Every metric is computed by the real, tested "
            "biaslens.metrics engine on that synthetic input. Cities are paired with "
            "one representative language each here, not a full cross product.",
        ],
    )


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, object]] = []
    for offset, query in enumerate(QUERIES):
        report = build_report(query, offset)
        slug = query.lower().replace(" ", "-").replace("'", "")
        out_path = FIXTURES_DIR / f"{slug}.json"
        out_path.write_text(report.to_json())
        index.append(
            {
                "slug": slug,
                "query": query,
                "inequality_score": report.queries[0].inequality_score,
            }
        )
        print(f"wrote {out_path} (score={report.queries[0].inequality_score})")

    (FIXTURES_DIR / "_index.json").write_text(json.dumps(index, indent=2))
    print(f"wrote {FIXTURES_DIR / '_index.json'}")


if __name__ == "__main__":
    main()

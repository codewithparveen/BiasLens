import pytest
from pydantic import ValidationError

from biaslens.models import AuditPlan, OrganicResult, SearchResponse, SearchVariant


def test_search_variant_strips_and_rejects_blank() -> None:
    v = SearchVariant(query="  diabetes home remedy  ", city="Chennai", language="ta")
    assert v.query == "diabetes home remedy"
    with pytest.raises(ValidationError):
        SearchVariant(query="   ", city="Chennai", language="ta")


def test_audit_plan_expands_variants_correctly() -> None:
    plan = AuditPlan(
        queries=["q1", "q2"],
        cities=["Chennai", "Delhi"],
        languages=["ta", "hi"],
        runs_per_variant=2,
    )
    variants = plan.variants()
    assert len(variants) == 2 * 2 * 2  # queries x cities x languages
    assert plan.total_calls() == 2 * 2 * 2 * 2  # x runs_per_variant


def test_search_response_domains_property() -> None:
    variant = SearchVariant(query="q", city="Chennai", language="ta")
    resp = SearchResponse(
        variant=variant,
        organic_results=[
            OrganicResult(link="https://www.who.int/x", domain="who.int"),
            OrganicResult(link="https://example.com/y", domain=None),
        ],
    )
    assert resp.domains == ["who.int"]


def test_search_response_defaults_are_empty_not_none() -> None:
    variant = SearchVariant(query="q", city="Chennai", language="ta")
    resp = SearchResponse(variant=variant)
    assert resp.organic_results == []
    assert resp.ads == []
    assert resp.ai_overview.present is False
    assert resp.is_empty is False  # default, client sets this explicitly

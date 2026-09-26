import httpx
import pytest
import respx

from biaslens.auditor import Auditor

SEARCH_URL = "https://serpapi.com/search"


def _fake_response(domains: list[str]) -> dict:
    return {
        "organic_results": [
            {"position": i + 1, "title": f"Result {i}", "link": f"https://{d}/page", "snippet": f"About {d}"}
            for i, d in enumerate(domains)
        ]
    }


@pytest.mark.asyncio
@respx.mock
async def test_audit_async_end_to_end_produces_scored_report(tmp_path) -> None:
    # Chennai and Delhi get identical domains (perfect overlap); Bengaluru diverges.
    respx.get(SEARCH_URL).mock(
        side_effect=[
            httpx.Response(200, json=_fake_response(["who.int", "thehindu.com"])),  # Chennai run 1
            httpx.Response(200, json=_fake_response(["who.int", "thehindu.com"])),  # Chennai run 2
            httpx.Response(200, json=_fake_response(["who.int", "thehindu.com"])),  # Delhi run 1
            httpx.Response(200, json=_fake_response(["who.int", "thehindu.com"])),  # Delhi run 2
            httpx.Response(200, json=_fake_response(["quora.com", "amazon.in"])),  # Bengaluru run 1
            httpx.Response(200, json=_fake_response(["quora.com", "amazon.in"])),  # Bengaluru run 2
        ]
    )

    auditor = Auditor(api_key="fake-key", cache=None)
    report = await auditor.audit_async(
        queries=["diabetes home remedy"],
        cities=["Chennai", "Delhi", "Bengaluru"],
        languages=["en"],
        runs_per_variant=2,
        max_credits=None,
    )

    assert len(report.queries) == 1
    result = report.queries[0]
    assert result.query == "diabetes home remedy"
    assert len(result.variants) == 3
    assert len(result.pairwise) == 3  # 3 choose 2
    assert 0.0 <= result.inequality_score <= 100.0

    chennai = next(v for v in result.variants if v.variant.city == "Chennai")
    bengaluru = next(v for v in result.variants if v.variant.city == "Bengaluru")
    assert chennai.quality_score > bengaluru.quality_score  # who.int/thehindu.com beat quora/amazon
    assert report.credits_used == 6  # 3 cities x 1 lang x 2 runs, no trends counted here
    assert report.is_demo_data is False


@pytest.mark.asyncio
async def test_audit_async_respects_max_credits_without_override() -> None:
    from biaslens.exceptions import CreditBudgetExceeded

    auditor = Auditor(api_key="fake-key", cache=None)
    with pytest.raises(CreditBudgetExceeded):
        await auditor.audit_async(
            queries=["q1", "q2"],
            cities=["Chennai", "Delhi"],
            languages=["en", "hi"],
            runs_per_variant=2,
            max_credits=1,
        )


def test_estimate_does_not_require_network_or_valid_key() -> None:
    # api_key is never validated for estimate() -- no SerpApiClient is built.
    auditor = Auditor(api_key=None, cache=None)
    result = auditor.estimate(queries=["q1"], cities=["Chennai"], languages=["ta"], runs_per_variant=2)
    assert result.budget.search_calls == 2
    assert result.budget.trends_calls == 1


@pytest.mark.asyncio
@respx.mock
async def test_audit_async_handles_empty_results_gracefully() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"organic_results": []}))
    auditor = Auditor(api_key="fake-key", cache=None)
    report = await auditor.audit_async(
        queries=["obscure query"], cities=["Chennai"], languages=["ta"], runs_per_variant=1
    )
    variant = report.queries[0].variants[0]
    assert variant.is_empty is True
    assert variant.result_count == 0
    assert variant.quality_score == 0.0
    assert any("no organic results" in w for w in report.warnings)

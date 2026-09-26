import httpx
import pytest
import respx

from biaslens.cache import SQLiteCache
from biaslens.client import SerpApiClient
from biaslens.exceptions import AuthError, InvalidLocation, UpstreamError
from biaslens.models import SearchVariant

SEARCH_URL = "https://serpapi.com/search"


def _variant(**overrides: object) -> SearchVariant:
    base = dict(query="diabetes home remedy", city="Chennai", language="ta")
    base.update(overrides)
    return SearchVariant(**base)  # type: ignore[arg-type]


@pytest.mark.asyncio
@respx.mock
async def test_search_parses_organic_results_and_domain() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "search_metadata": {"id": "abc123"},
                "organic_results": [
                    {"position": 1, "title": "T", "link": "https://www.who.int/health", "snippet": "s"}
                ],
            },
        )
    )
    client = SerpApiClient(api_key="fake-key")
    resp = await client.search(_variant())
    assert resp.search_id == "abc123"
    assert len(resp.organic_results) == 1
    assert resp.organic_results[0].domain == "who.int"
    assert resp.is_empty is False
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_empty_organic_results_is_valid_not_an_error() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(200, json={"organic_results": []}))
    client = SerpApiClient(api_key="fake-key")
    resp = await client.search(_variant())
    assert resp.is_empty is True
    assert any(w.code == "empty_result" for w in resp.warnings)
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_in_body_error_field_raises_auth_error() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"error": "Invalid API key."})
    )
    client = SerpApiClient(api_key="fake-key")
    with pytest.raises(AuthError):
        await client.search(_variant())
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_in_body_location_error_raises_invalid_location() -> None:
    respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"error": "location not found"})
    )
    client = SerpApiClient(api_key="fake-key")
    with pytest.raises(InvalidLocation):
        await client.search(_variant(city="Atlantis"))
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_http_401_raises_auth_error_without_retry() -> None:
    route = respx.get(SEARCH_URL).mock(return_value=httpx.Response(401, json={}))
    client = SerpApiClient(api_key="bad-key")
    with pytest.raises(AuthError):
        await client.search(_variant())
    assert route.call_count == 1  # never retried
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_transient_500_is_retried_then_succeeds() -> None:
    route = respx.get(SEARCH_URL).mock(
        side_effect=[
            httpx.Response(500, json={}),
            httpx.Response(200, json={"organic_results": [{"position": 1, "link": "https://a.com"}]}),
        ]
    )
    client = SerpApiClient(api_key="fake-key", max_retries=3)
    # speed up the test: patch backoff sleep to be near-instant
    client._sleep_backoff = _fast_sleep.__get__(client)  # type: ignore[attr-defined]
    resp = await client.search(_variant())
    assert route.call_count == 2
    assert len(resp.organic_results) == 1
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_persistent_500_raises_upstream_error_after_max_retries() -> None:
    respx.get(SEARCH_URL).mock(return_value=httpx.Response(500, json={}))
    client = SerpApiClient(api_key="fake-key", max_retries=1)
    client._sleep_backoff = _fast_sleep.__get__(client)  # type: ignore[attr-defined]
    with pytest.raises(UpstreamError):
        await client.search(_variant())
    await client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_cache_hit_skips_network_call(tmp_path) -> None:
    route = respx.get(SEARCH_URL).mock(
        return_value=httpx.Response(200, json={"organic_results": [{"position": 1, "link": "https://a.com"}]})
    )
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    client = SerpApiClient(api_key="fake-key", cache=cache)

    resp1 = await client.search(_variant())
    assert resp1.from_cache is False
    assert route.call_count == 1

    resp2 = await client.search(_variant())
    assert resp2.from_cache is True
    assert route.call_count == 1  # no second network call

    await client.aclose()
    cache.close()


async def _fast_sleep(self, attempt: int) -> None:  # pragma: no cover - test helper
    return None

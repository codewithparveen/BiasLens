"""Async SerpApi client.

Handles every edge case explicitly rather than trusting the payload shape:
SerpApi's own "error" field inside a 200 response, a valid empty result set,
missing keys anywhere in organic_results, absent ads/ai_overview, invalid
locations, and partial failures (returned as warnings, never a crash).
"""

from __future__ import annotations

import asyncio
import os
import random
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from .cache import SQLiteCache, make_cache_key
from .exceptions import AuthError, InvalidLocation, RateLimited, UpstreamError
from .models import (
    AdResult,
    AIOverview,
    KnowledgeGraph,
    LocalResult,
    OrganicResult,
    RelatedQuestion,
    SearchResponse,
    SearchResponseWarning,
    SearchVariant,
)

_SEARCH_URL = "https://serpapi.com/search"
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _load_env_key(dotenv_path: str | Path = ".env") -> str | None:
    """Read SERPAPI_KEY from the environment, falling back to a .env file.

    Implemented without an extra dependency: a plain KEY=VALUE line parser,
    skipping blanks and comments. The environment always wins over .env.
    """
    key = os.environ.get("SERPAPI_KEY")
    if key:
        return key
    path = Path(dotenv_path)
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() == "SERPAPI_KEY":
            return v.strip().strip('"').strip("'")
    return None


def _domain_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc
        return netloc.removeprefix("www.") or None
    except ValueError:
        return None


class SerpApiClient:
    """Thin, typed, async wrapper around the SerpApi Google Search + Trends endpoints."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        cache: SQLiteCache | None = None,
        timeout: float = 15.0,
        max_retries: int = 3,
        concurrency_limit: int = 5,
        base_url: str = _SEARCH_URL,
    ) -> None:
        resolved_key = api_key or _load_env_key()
        if not resolved_key:
            raise AuthError("No SerpApi key found (pass api_key= or set SERPAPI_KEY).")
        self._api_key = resolved_key
        self._cache = cache
        self._timeout = timeout
        self._max_retries = max_retries
        self._base_url = base_url
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> SerpApiClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        variant: SearchVariant,
        *,
        run_idx: int = 0,
        ttl: float | None = None,
    ) -> SearchResponse:
        """Run (or replay from cache) a single Google Search variant."""
        params = {
            "engine": "google",
            "q": variant.query,
            "location": variant.city,
            "hl": variant.language,
            "gl": variant.country,
            "google_domain": variant.google_domain,
            "num": variant.num_results,
            "api_key": self._api_key,
        }
        cache_key = make_cache_key(
            "search",
            {
                "query": variant.query,
                "city": variant.city,
                "language": variant.language,
                "google_domain": variant.google_domain,
                "country": variant.country,
                "num_results": variant.num_results,
                "run_idx": run_idx,
            },
        )

        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return SearchResponse.model_validate({**cached, "variant": variant, "from_cache": True})

        raw = await self._request_with_retry(params)
        response = self._parse_search_response(raw, variant)

        if self._cache is not None:
            # Store the normalized, not the raw, payload -- cheaper to reload.
            to_store = response.model_dump(mode="json", exclude={"variant", "from_cache"})
            self._cache.set(cache_key, to_store, ttl=ttl)

        return response

    async def search_many(
        self, variants: list[SearchVariant], *, runs_per_variant: int = 1
    ) -> list[SearchResponse]:
        """Fan out search() calls under the client's concurrency limit."""

        async def _bounded(v: SearchVariant, run_idx: int) -> SearchResponse:
            async with self._semaphore:
                return await self.search(v, run_idx=run_idx)

        tasks = [
            _bounded(v, run_idx)
            for v in variants
            for run_idx in range(runs_per_variant)
        ]
        return await asyncio.gather(*tasks)

    async def trends(self, query: str, *, geo: str = "IN") -> dict[str, Any]:
        """Fetch Google Trends GEO_MAP data for a query. Returns the raw payload
        (metrics engine in Step 3 will normalize this further)."""
        params = {
            "engine": "google_trends",
            "q": query,
            "geo": geo,
            "data_type": "GEO_MAP",
            "api_key": self._api_key,
        }
        cache_key = make_cache_key("trends", {"query": query, "geo": geo})
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        raw = await self._request_with_retry(params)
        if self._cache is not None:
            self._cache.set(cache_key, raw)
        return raw

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _request_with_retry(self, params: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        while True:
            attempt += 1
            try:
                resp = await self._client.get(self._base_url, params=params)
            except httpx.TimeoutException as exc:
                if attempt > self._max_retries:
                    raise UpstreamError(f"SerpApi request timed out after {attempt} attempts.") from exc
                await self._sleep_backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                if attempt > self._max_retries:
                    raise UpstreamError(f"SerpApi request failed: {exc}") from exc
                await self._sleep_backoff(attempt)
                continue

            if resp.status_code in (401, 403):
                raise AuthError(f"SerpApi rejected the request (HTTP {resp.status_code}).")

            if resp.status_code == 429:
                if attempt > self._max_retries:
                    raise RateLimited("SerpApi rate limit exceeded after retries.")
                await self._sleep_backoff(attempt)
                continue

            if resp.status_code in _RETRYABLE_STATUS and resp.status_code != 429:
                if attempt > self._max_retries:
                    raise UpstreamError(
                        f"SerpApi returned HTTP {resp.status_code} after retries.",
                        status_code=resp.status_code,
                    )
                await self._sleep_backoff(attempt)
                continue

            if resp.status_code >= 400:
                raise UpstreamError(
                    f"SerpApi returned HTTP {resp.status_code}: {resp.text[:200]}",
                    status_code=resp.status_code,
                )

            try:
                data: dict[str, Any] = resp.json()
            except ValueError as exc:
                if attempt > self._max_retries:
                    raise UpstreamError("SerpApi returned non-JSON response.") from exc
                await self._sleep_backoff(attempt)
                continue

            # SerpApi can return HTTP 200 with an "error" field in the body.
            if isinstance(data, dict) and data.get("error"):
                error_msg = str(data["error"])
                if "invalid api key" in error_msg.lower():
                    raise AuthError(error_msg)
                if "location" in error_msg.lower():
                    raise InvalidLocation(str(params.get("location", "")))
                if attempt > self._max_retries:
                    raise UpstreamError(f"SerpApi error: {error_msg}")
                await self._sleep_backoff(attempt)
                continue

            return data

    async def _sleep_backoff(self, attempt: int) -> None:
        base = min(2 ** attempt, 20)
        jitter = random.uniform(0, base * 0.25)
        await asyncio.sleep(base + jitter)

    def _parse_search_response(self, raw: dict[str, Any], variant: SearchVariant) -> SearchResponse:
        warnings: list[SearchResponseWarning] = []

        organic_raw = raw.get("organic_results") or []
        organic: list[OrganicResult] = []
        for item in organic_raw:
            if not isinstance(item, dict):
                warnings.append(SearchResponseWarning(code="malformed_organic_item", message=str(item)[:100]))
                continue
            link = item.get("link")
            organic.append(
                OrganicResult(
                    position=item.get("position"),
                    title=item.get("title"),
                    link=link,
                    displayed_link=item.get("displayed_link"),
                    snippet=item.get("snippet"),
                    domain=_domain_of(link),
                )
            )

        ads_raw = raw.get("ads") or []
        ads = [
            AdResult(
                position=a.get("position"),
                title=a.get("title"),
                link=a.get("link"),
                displayed_link=a.get("displayed_link"),
                tracking_link=a.get("tracking_link"),
            )
            for a in ads_raw
            if isinstance(a, dict)
        ]

        ai_raw = raw.get("ai_overview")
        if isinstance(ai_raw, dict):
            text_blocks = [b.get("snippet", "") for b in ai_raw.get("text_blocks", []) if isinstance(b, dict)]
            source_links = [s.get("link", "") for s in ai_raw.get("references", []) if isinstance(s, dict)]
            ai_overview = AIOverview(text_blocks=text_blocks, source_links=source_links, present=True)
        else:
            ai_overview = AIOverview(present=False)

        local_results_raw = raw.get("local_results")
        if isinstance(local_results_raw, dict):
            local_raw = local_results_raw.get("places")
        else:
            local_raw = local_results_raw or []
        local_results = [
            LocalResult(
                title=p.get("title"),
                address=p.get("address"),
                rating=p.get("rating"),
                reviews=p.get("reviews"),
            )
            for p in (local_raw or [])
            if isinstance(p, dict)
        ]

        related_raw = raw.get("related_questions") or []
        related_questions = [
            RelatedQuestion(
                question=q.get("question"),
                snippet=q.get("snippet"),
                link=q.get("link"),
                domain=_domain_of(q.get("link")),
            )
            for q in related_raw
            if isinstance(q, dict)
        ]

        kg_raw = raw.get("knowledge_graph")
        knowledge_graph = None
        if isinstance(kg_raw, dict):
            kg_source = kg_raw.get("source")
            source_link = kg_source.get("link") if isinstance(kg_source, dict) else None
            knowledge_graph = KnowledgeGraph(
                title=kg_raw.get("title"),
                type=kg_raw.get("type"),
                description=kg_raw.get("description"),
                source_link=source_link,
            )

        is_empty = len(organic) == 0 and not raw.get("error")
        if is_empty:
            warnings.append(
                SearchResponseWarning(
                    code="empty_result",
                    message="Google returned no organic results for this variant (valid, not a failure).",
                )
            )

        search_id = None
        search_meta = raw.get("search_metadata")
        if isinstance(search_meta, dict):
            search_id = search_meta.get("id")

        return SearchResponse(
            variant=variant,
            organic_results=organic,
            ads=ads,
            ai_overview=ai_overview,
            local_results=local_results,
            related_questions=related_questions,
            knowledge_graph=knowledge_graph,
            search_id=search_id,
            from_cache=False,
            is_empty=is_empty,
            warnings=warnings,
        )

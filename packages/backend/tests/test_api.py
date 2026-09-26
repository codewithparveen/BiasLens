import time

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "live_mode_available" in body


@pytest.mark.asyncio
async def test_locations_returns_curated_list(client: AsyncClient) -> None:
    resp = await client.get("/api/locations")
    assert resp.status_code == 200
    cities = {loc["city"] for loc in resp.json()}
    assert "Chennai" in cities
    assert "Delhi" in cities


@pytest.mark.asyncio
async def test_featured_reads_bundled_fixtures(client: AsyncClient) -> None:
    resp = await client.get("/api/featured")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_demo_data"] is True
    assert len(body["queries"]) == 6
    assert all("inequality_score" in q for q in body["queries"])


@pytest.mark.asyncio
async def test_estimate_endpoint_no_network_needed(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/estimate",
        json={
            "queries": ["q1", "q2"],
            "cities": ["Chennai", "Delhi"],
            "languages": ["ta", "hi"],
            "runs_per_variant": 2,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["budget"]["search_calls"] == 2 * 2 * 2 * 2


@pytest.mark.asyncio
async def test_estimate_endpoint_rejects_empty_queries(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/estimate",
        json={"queries": [], "cities": ["Chennai"], "languages": ["ta"]},
    )
    assert resp.status_code == 422  # pydantic validation, min_length=1


@pytest.mark.asyncio
async def test_demo_audit_full_flow(client: AsyncClient) -> None:
    start = await client.post(
        "/api/audits",
        json={
            "queries": ["diabetes home remedy"],
            "cities": ["Chennai", "Delhi", "Bengaluru", "Mumbai", "Kolkata"],
            "languages": ["ta", "hi", "en", "mr", "bn"],
            "demo": True,
        },
    )
    assert start.status_code == 200
    job_id = start.json()["id"]
    assert start.json()["status"] == "pending"

    # Poll until completed (demo jobs finish in ~1s).
    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        poll = await client.get(f"/api/audits/{job_id}")
        assert poll.status_code == 200
        status = poll.json()["status"]
        if status == "completed":
            break
        await _sleep(0.1)

    assert status == "completed"
    result = poll.json()["result"]
    assert result["is_demo_data"] is True
    assert len(result["queries"]) == 1
    assert result["queries"][0]["query"] == "diabetes home remedy"


@pytest.mark.asyncio
async def test_audit_defaults_to_demo_when_no_live_key(client: AsyncClient) -> None:
    # No SERPAPI_KEY is set in the test environment, so demo=None should
    # still resolve to demo mode automatically -- never a raw failure.
    start = await client.post(
        "/api/audits",
        json={"queries": ["crop loan"], "cities": ["Chennai"], "languages": ["ta"]},
    )
    assert start.status_code == 200
    job_id = start.json()["id"]

    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        poll = await client.get(f"/api/audits/{job_id}")
        status = poll.json()["status"]
        if status == "completed":
            break
        await _sleep(0.1)
    assert status == "completed"
    assert poll.json()["result"]["is_demo_data"] is True


@pytest.mark.asyncio
async def test_get_audit_unknown_id_is_404(client: AsyncClient) -> None:
    resp = await client.get("/api/audits/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "error"


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)

"""POST /api/audits starts a background job and returns its id immediately;
GET /api/audits/{id} polls status/progress/result. Demo mode (the default
whenever no server-side SERPAPI_KEY is configured, or when explicitly
requested) replays a bundled fixture instead of calling SerpApi, so the
dashboard always has something to show judges with zero credits spent and
never surfaces a raw error for lack of a key.
"""

from __future__ import annotations

import asyncio
import json

from biaslens.auditor import Auditor
from biaslens.exceptions import BiasLensError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import FIXTURES_DIR, LIVE_MODE_AVAILABLE, SERPAPI_KEY
from ..jobs import JobStatus, job_store

router = APIRouter()


class AuditRequest(BaseModel):
    queries: list[str] = Field(min_length=1)
    cities: list[str] = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    runs_per_variant: int = Field(default=2, ge=1, le=5)
    max_credits: int | None = None
    demo: bool | None = Field(
        default=None, description="Force demo mode. Defaults to True whenever no live key is configured."
    )


def _pick_fixture(query: str) -> dict[str, object]:
    index_path = FIXTURES_DIR / "_index.json"
    entries: list[dict[str, object]] = json.loads(index_path.read_text()) if index_path.exists() else []
    query_lower = query.lower()
    for entry in entries:
        if str(entry["query"]).lower() in query_lower or query_lower in str(entry["query"]).lower():
            fixture_path = FIXTURES_DIR / f"{entry['slug']}.json"
            result: dict[str, object] = json.loads(fixture_path.read_text())
            return result
    # No close match -- fall back to the first fixture rather than erroring.
    if entries:
        fixture_path = FIXTURES_DIR / f"{entries[0]['slug']}.json"
        result = json.loads(fixture_path.read_text())
        return result
    raise HTTPException(status_code=503, detail="No demo fixtures available.")


async def _run_demo_job(job_id: str, query: str) -> None:
    # A short delay so the frontend's progress stepper has something to show,
    # rather than the job completing before the client's first poll.
    await asyncio.sleep(0.5)
    job_store.update_progress(job_id, {"completed_queries": 0, "total_queries": 1, "current_query": query})
    await asyncio.sleep(0.5)
    result = _pick_fixture(query)
    job_store.complete(job_id, result)


async def _run_live_job(job_id: str, body: AuditRequest) -> None:
    auditor = Auditor(api_key=SERPAPI_KEY, cache="sqlite")

    def on_progress(progress: dict[str, object]) -> None:
        job_store.update_progress(job_id, progress)

    try:
        report = await auditor.audit_async(
            queries=body.queries,
            cities=body.cities,
            languages=body.languages,
            runs_per_variant=body.runs_per_variant,
            max_credits=body.max_credits,
            on_progress=on_progress,
        )
        job_store.complete(job_id, report.model_dump(mode="json"))
    except BiasLensError as exc:
        job_store.fail(job_id, exc.message)
    finally:
        auditor.close()


@router.post("/audits")
async def start_audit(body: AuditRequest) -> dict[str, str]:
    use_demo = body.demo if body.demo is not None else not LIVE_MODE_AVAILABLE
    job = job_store.create()
    if use_demo:
        job_store.run_in_background(job.id, _run_demo_job(job.id, body.queries[0]))
    else:
        job_store.run_in_background(job.id, _run_live_job(job.id, body))
    return {"id": job.id, "status": job.status.value}


@router.get("/audits/{job_id}")
def get_audit(job_id: str) -> dict[str, object]:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="No such audit job.")
    return {
        "id": job.id,
        "status": job.status.value,
        "progress": job.progress,
        "result": job.result,
        "error": job.error,
    }


__all__ = ["router", "JobStatus"]

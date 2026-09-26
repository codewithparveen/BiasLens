from __future__ import annotations

from biaslens.auditor import Auditor
from biaslens.exceptions import BiasLensError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class EstimateRequest(BaseModel):
    queries: list[str] = Field(min_length=1)
    cities: list[str] = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    runs_per_variant: int = Field(default=2, ge=1, le=5)
    max_credits: int | None = None


@router.post("/estimate")
def estimate(body: EstimateRequest) -> dict[str, object]:
    auditor = Auditor(api_key=None, cache=None)
    try:
        result = auditor.estimate(
            queries=body.queries,
            cities=body.cities,
            languages=body.languages,
            runs_per_variant=body.runs_per_variant,
            max_credits=body.max_credits,
        )
    except BiasLensError as exc:
        raise HTTPException(
            status_code=422, detail={"code": "estimate_failed", "message": exc.message, "hint": exc.hint}
        ) from exc
    return result.model_dump(mode="json")

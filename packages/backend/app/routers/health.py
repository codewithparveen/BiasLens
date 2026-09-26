from __future__ import annotations

from fastapi import APIRouter

from ..config import LIVE_MODE_AVAILABLE

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "live_mode_available": LIVE_MODE_AVAILABLE}

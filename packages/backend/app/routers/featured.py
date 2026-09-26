"""GET /api/featured -- headline numbers for the landing page's "Featured
findings" cards, read straight from the bundled demo fixtures index.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from ..config import FIXTURES_DIR

router = APIRouter()


@router.get("/featured")
def featured() -> dict[str, object]:
    index_path = FIXTURES_DIR / "_index.json"
    if not index_path.exists():
        raise HTTPException(status_code=503, detail="Demo fixtures not generated yet.")
    entries = json.loads(index_path.read_text())
    return {"is_demo_data": True, "queries": entries}

"""BiasLens backend entrypoint. Run with:

    uvicorn app.main:app --reload --port 8000

All error responses share {code, message, hint} so the frontend's typed
API client only needs one error shape to handle everywhere.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ALLOWED_ORIGINS
from .routers import audits, estimate, featured, health, locations

app = FastAPI(title="BiasLens API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(featured.router, prefix="/api")
app.include_router(estimate.router, prefix="/api")
app.include_router(audits.router, prefix="/api")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        body: dict[str, Any] = {
            "code": detail.get("code", "error"),
            "message": detail.get("message", ""),
            "hint": detail.get("hint"),
        }
    else:
        body = {"code": "error", "message": str(detail), "hint": None}
    return JSONResponse(status_code=exc.status_code, content=body)

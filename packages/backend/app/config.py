"""Shared backend configuration."""

from __future__ import annotations

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Live mode only turns on if a real key is configured server-side. Judges
# with no key configured always see demo mode -- the dashboard must never
# error out for lack of a key.
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
LIVE_MODE_AVAILABLE = bool(SERPAPI_KEY)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("BIASLENS_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]

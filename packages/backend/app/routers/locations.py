"""GET /api/locations.

Returns the curated set of Indian cities and language codes BiasLens
supports today (the ones with a language-match heuristic in
biaslens.metrics.language and used in the demo fixtures). This is a
static list rather than a live SerpApi Locations API call, since the
Locations API is free but still an extra round trip the dashboard
doesn't need to pay for on every page load.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Location(BaseModel):
    city: str
    default_language: str
    supported_languages: list[str]


LOCATIONS: list[Location] = [
    Location(city="Chennai", default_language="ta", supported_languages=["ta", "en"]),
    Location(city="Delhi", default_language="hi", supported_languages=["hi", "en"]),
    Location(city="Bengaluru", default_language="en", supported_languages=["en", "kn"]),
    Location(city="Mumbai", default_language="mr", supported_languages=["mr", "en", "hi"]),
    Location(city="Kolkata", default_language="bn", supported_languages=["bn", "en"]),
    Location(city="Hyderabad", default_language="te", supported_languages=["te", "en"]),
    Location(city="Ahmedabad", default_language="gu", supported_languages=["gu", "en"]),
]


@router.get("/locations", response_model=list[Location])
def list_locations() -> list[Location]:
    return LOCATIONS

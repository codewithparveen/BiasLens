"""Typed models for everything that crosses the biaslens boundary.

Two families live here:

* Request/plan models (``SearchVariant``, ``AuditPlan``, ``EstimateResult``,
  ``CreditBudget``) -- built before any network call is made.
* Response models (``OrganicResult`` ... ``SearchResponse``) -- a
  normalized, typed view over the parts of a raw SerpApi JSON payload that
  biaslens cares about. Fields SerpApi may omit are always ``Optional`` with
  a default, never assumed present.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BiasLensModel(BaseModel):
    """Shared base: forbid silent typos in kwargs, allow extra raw fields."""

    model_config = ConfigDict(extra="ignore", frozen=False, validate_assignment=True)


# --------------------------------------------------------------------------
# Request / plan side
# --------------------------------------------------------------------------


class SearchVariant(BiasLensModel):
    """One (query, city, language) combination to be audited."""

    query: str
    city: str
    language: str = Field(description="SerpApi `hl` param, e.g. 'ta', 'hi', 'en'.")
    google_domain: str = "google.co.in"
    country: str = Field(default="in", description="SerpApi `gl` param.")
    num_results: int = Field(default=10, ge=1, le=100)

    @field_validator("query", "city", "language")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


class AuditPlan(BiasLensModel):
    """The full set of variants + reliability runs a user wants to execute."""

    queries: list[str]
    cities: list[str]
    languages: list[str]
    runs_per_variant: int = Field(default=2, ge=1, le=5)
    google_domain: str = "google.co.in"
    country: str = "in"
    num_results: int = Field(default=10, ge=1, le=100)

    def variants(self) -> list[SearchVariant]:
        """Expand queries x cities x languages into concrete variants."""
        return [
            SearchVariant(
                query=q,
                city=c,
                language=lang,
                google_domain=self.google_domain,
                country=self.country,
                num_results=self.num_results,
            )
            for q in self.queries
            for c in self.cities
            for lang in self.languages
        ]

    def total_calls(self) -> int:
        """Search calls implied by this plan, ignoring cache hits."""
        return len(self.queries) * len(self.cities) * len(self.languages) * self.runs_per_variant


class CreditBudget(BiasLensModel):
    """Result of estimate(): what a plan would cost, before spending anything."""

    search_calls: int
    trends_calls: int
    total_credits: int
    cache_hits_expected: int = 0
    max_credits: int | None = None
    within_budget: bool = True


class EstimateResult(BiasLensModel):
    """Public return type of ``Auditor.estimate()``."""

    plan: AuditPlan
    budget: CreditBudget
    variants_preview: list[SearchVariant]


# --------------------------------------------------------------------------
# Response side -- normalized SerpApi payload
# --------------------------------------------------------------------------


class OrganicResult(BiasLensModel):
    position: int | None = None
    title: str | None = None
    link: str | None = None
    displayed_link: str | None = None
    snippet: str | None = None
    domain: str | None = None

    @field_validator("domain", mode="before")
    @classmethod
    def _derive_domain(cls, v: str | None, info: Any) -> str | None:
        return v  # populated explicitly by the client from `link`; kept simple here


class AdResult(BiasLensModel):
    position: int | None = None
    title: str | None = None
    link: str | None = None
    displayed_link: str | None = None
    tracking_link: str | None = None


class AIOverview(BiasLensModel):
    text_blocks: list[str] = Field(default_factory=list)
    source_links: list[str] = Field(default_factory=list)
    present: bool = False


class LocalResult(BiasLensModel):
    title: str | None = None
    address: str | None = None
    rating: float | None = None
    reviews: int | None = None


class RelatedQuestion(BiasLensModel):
    question: str | None = None
    snippet: str | None = None
    link: str | None = None
    domain: str | None = None


class KnowledgeGraph(BiasLensModel):
    title: str | None = None
    type: str | None = None
    description: str | None = None
    source_link: str | None = None


class SearchResponseWarning(BiasLensModel):
    code: str
    message: str


class SearchResponse(BiasLensModel):
    """Normalized result of a single SerpApi Google Search call."""

    variant: SearchVariant
    organic_results: list[OrganicResult] = Field(default_factory=list)
    ads: list[AdResult] = Field(default_factory=list)
    ai_overview: AIOverview = Field(default_factory=AIOverview)
    local_results: list[LocalResult] = Field(default_factory=list)
    related_questions: list[RelatedQuestion] = Field(default_factory=list)
    knowledge_graph: KnowledgeGraph | None = None
    search_id: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    from_cache: bool = False
    is_empty: bool = False
    warnings: list[SearchResponseWarning] = Field(default_factory=list)

    @property
    def domains(self) -> list[str]:
        return [r.domain for r in self.organic_results if r.domain]

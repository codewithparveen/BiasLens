"""biaslens: audit how Google search results vary across Indian cities and languages."""

from .auditor import Auditor
from .cache import SQLiteCache, make_cache_key
from .client import SerpApiClient
from .credit_guard import CreditGuard
from .exceptions import (
    AuthError,
    BiasLensError,
    CacheError,
    CreditBudgetExceeded,
    InvalidLocation,
    QuotaExceeded,
    RateLimited,
    UpstreamError,
)
from .models import (
    AdResult,
    AIOverview,
    AuditPlan,
    CreditBudget,
    EstimateResult,
    KnowledgeGraph,
    LocalResult,
    OrganicResult,
    RelatedQuestion,
    SearchResponse,
    SearchVariant,
)
from .report import AuditReport, PairwiseComparisonResult, QueryAuditResult, VariantMetrics

__version__ = "0.1.0"

__all__ = [
    "Auditor",
    "SerpApiClient",
    "SQLiteCache",
    "make_cache_key",
    "CreditGuard",
    "AuditPlan",
    "SearchVariant",
    "SearchResponse",
    "CreditBudget",
    "EstimateResult",
    "OrganicResult",
    "AdResult",
    "AIOverview",
    "LocalResult",
    "RelatedQuestion",
    "KnowledgeGraph",
    "AuditReport",
    "QueryAuditResult",
    "VariantMetrics",
    "PairwiseComparisonResult",
    "BiasLensError",
    "AuthError",
    "QuotaExceeded",
    "RateLimited",
    "InvalidLocation",
    "UpstreamError",
    "CreditBudgetExceeded",
    "CacheError",
]

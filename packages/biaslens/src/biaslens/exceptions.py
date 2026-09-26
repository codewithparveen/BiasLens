"""Exception hierarchy for biaslens.

All exceptions carry a human-readable ``message`` and, where useful, a
``hint`` telling the caller what to do next. Never raised for expected
"empty result" states -- those are represented as data (see models.py),
not errors.
"""

from __future__ import annotations


class BiasLensError(Exception):
    """Base class for every exception raised by biaslens."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        self.message = message
        self.hint = hint
        full = message if hint is None else f"{message} (hint: {hint})"
        super().__init__(full)


class AuthError(BiasLensError):
    """The SerpApi key is missing, malformed, or rejected by the API."""

    def __init__(self, message: str = "SerpApi authentication failed.") -> None:
        super().__init__(
            message,
            hint="Check that SERPAPI_KEY is set and valid, e.g. via a .env file.",
        )


class QuotaExceeded(BiasLensError):
    """The account has run out of SerpApi search credits."""

    def __init__(self, message: str = "SerpApi search credit quota exhausted.") -> None:
        super().__init__(
            message,
            hint="Wait for the plan to reset, upgrade the plan, or rely on the cache.",
        )


class RateLimited(BiasLensError):
    """SerpApi returned HTTP 429; caller should back off and retry."""

    def __init__(
        self,
        message: str = "SerpApi rate limit hit.",
        *,
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, hint="This is retried automatically with backoff.")


class InvalidLocation(BiasLensError):
    """The supplied city/location string could not be resolved."""

    def __init__(self, location: str) -> None:
        self.location = location
        super().__init__(
            f"Could not resolve location: {location!r}",
            hint="Use the SerpApi Locations API to find a canonical name.",
        )


class UpstreamError(BiasLensError):
    """SerpApi returned a 5xx, a malformed payload, or an in-body error field."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message, hint="Retried automatically for 5xx/timeouts.")


class CreditBudgetExceeded(BiasLensError):
    """An audit would cost more credits than the configured max_credits allows."""

    def __init__(self, estimated: int, max_credits: int) -> None:
        self.estimated = estimated
        self.max_credits = max_credits
        super().__init__(
            f"Estimated cost {estimated} credits exceeds max_credits={max_credits}.",
            hint="Pass override=True to auditor.audit() to proceed anyway, "
            "or reduce queries/cities/languages/runs.",
        )


class CacheError(BiasLensError):
    """The SQLite cache could not be read from or written to."""

    def __init__(self, message: str) -> None:
        super().__init__(message, hint="Check the cache_path is writable.")

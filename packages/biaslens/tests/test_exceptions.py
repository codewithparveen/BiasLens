from biaslens.exceptions import (
    AuthError,
    BiasLensError,
    CreditBudgetExceeded,
    InvalidLocation,
    QuotaExceeded,
    RateLimited,
    UpstreamError,
)


def test_all_exceptions_are_biaslens_errors() -> None:
    for exc_cls in (AuthError, QuotaExceeded, RateLimited, UpstreamError):
        assert issubclass(exc_cls, BiasLensError)


def test_invalid_location_carries_location() -> None:
    exc = InvalidLocation("Atlantis, India")
    assert exc.location == "Atlantis, India"
    assert "Atlantis" in str(exc)


def test_credit_budget_exceeded_message() -> None:
    exc = CreditBudgetExceeded(estimated=120, max_credits=100)
    assert exc.estimated == 120
    assert exc.max_credits == 100
    assert "120" in str(exc) and "100" in str(exc)


def test_rate_limited_optional_retry_after() -> None:
    exc = RateLimited(retry_after=2.5)
    assert exc.retry_after == 2.5

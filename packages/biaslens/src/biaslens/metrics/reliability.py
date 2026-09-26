"""Reliability: separate real cross-variant bias from Google's own run-to-run
noise by looking at variance across N repeated runs of the *same* variant.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass


@dataclass(frozen=True)
class VarianceReport:
    n: int
    mean: float
    stdev: float
    coefficient_of_variation: float | None  # stdev / mean; None if mean == 0


def variance_report(values: list[float]) -> VarianceReport:
    """Summarize repeated-run variance for one numeric metric.

    stdev is 0.0 for n<2 (nothing to vary against). coefficient_of_variation
    is None when mean is 0, to avoid a division-by-zero producing a
    misleadingly precise number.
    """
    if not values:
        return VarianceReport(n=0, mean=0.0, stdev=0.0, coefficient_of_variation=None)
    n = len(values)
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values) if n >= 2 else 0.0
    cv = (stdev / mean) if mean != 0 else None
    return VarianceReport(n=n, mean=mean, stdev=stdev, coefficient_of_variation=cv)

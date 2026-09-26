"""Source diversity: Shannon entropy over the domains in a result set.

Higher entropy means results are spread across more distinct domains;
lower entropy means a handful of domains dominate. Reported in bits.
"""

from __future__ import annotations

import math
from collections import Counter


def shannon_entropy(domains: list[str]) -> float:
    """Shannon entropy (bits) of the domain frequency distribution.

    0.0 for an empty list or a list where every result is the same domain
    (no diversity). Maximum entropy for N distinct domains, each appearing
    once, is log2(N).
    """
    if not domains:
        return 0.0
    counts = Counter(domains)
    total = sum(counts.values())
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
    return entropy


def max_possible_entropy(domains: list[str]) -> float:
    """log2(number of distinct domains) -- the ceiling shannon_entropy could hit."""
    n_distinct = len(set(domains))
    if n_distinct <= 1:
        return 0.0
    return math.log2(n_distinct)


def normalized_entropy(domains: list[str]) -> float:
    """shannon_entropy / max_possible_entropy, in [0, 1]. 0.0 if undefined."""
    max_e = max_possible_entropy(domains)
    if max_e == 0.0:
        return 0.0
    return shannon_entropy(domains) / max_e

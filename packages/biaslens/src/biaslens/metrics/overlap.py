"""Result-overlap metrics: Jaccard and rank-biased overlap (RBO) on domains.

Both are pure functions over ranked lists of domain strings -- no network,
no LLM, fully deterministic and unit-testable. Lower overlap between two
(city, language) variants for the same query is read as higher information
inequality: see metrics/score.py and docs/methodology.md.
"""

from __future__ import annotations


def jaccard(domains_a: list[str], domains_b: list[str]) -> float:
    """Jaccard similarity of the two domain SETS (order ignored).

    Returns 0.0 if both lists are empty (no information to compare) and
    treats one-empty-one-not as fully dissimilar (0.0).
    """
    set_a, set_b = set(domains_a), set(domains_b)
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def rbo(list_a: list[str], list_b: list[str], p: float = 0.9) -> float:
    """Extrapolated rank-biased overlap (Webber, Moffat & Zobel, 2010).

    ``p`` is the persistence parameter: higher p weights deeper ranks more
    (0.9 means the first ~10 ranks account for ~86% of the score, a
    reasonable default when comparing top-10 SERPs). Only defined over the
    depth both lists actually share -- if the two variants were fetched at
    different depths, this compares them at ``min(len_a, len_b)`` and that
    truncation is a documented simplification, not the full uneven-length
    RBO extrapolation from the original paper.

    Returns 1.0 for two identical non-empty lists, 0.0 if either is empty
    or the lists share no elements within the compared depth.
    """
    if not list_a or not list_b:
        return 0.0
    k = min(len(list_a), len(list_b))
    if k == 0:
        return 0.0

    seen_a: set[str] = set()
    seen_b: set[str] = set()
    overlap_at_depth: list[int] = []
    for d in range(1, k + 1):
        seen_a.add(list_a[d - 1])
        seen_b.add(list_b[d - 1])
        overlap_at_depth.append(len(seen_a & seen_b))

    x_k = overlap_at_depth[-1]
    term1 = (x_k / k) * (p**k)
    term2 = ((1 - p) / p) * sum(
        (overlap_at_depth[d - 1] / d) * (p**d) for d in range(1, k + 1)
    )
    score = term1 + term2
    # Guard float drift outside [0, 1] from accumulated rounding.
    return max(0.0, min(1.0, score))


def pairwise_overlap(
    variant_domains: dict[str, list[str]], *, p: float = 0.9
) -> list[dict[str, object]]:
    """Compute jaccard + rbo for every unordered pair of labeled variants.

    ``variant_domains`` maps a display label (e.g. "Chennai/ta") to its
    ranked domain list. Returns one dict per pair with both scores.
    """
    labels = list(variant_domains.keys())
    results: list[dict[str, object]] = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            results.append(
                {
                    "variant_a": a,
                    "variant_b": b,
                    "jaccard": jaccard(variant_domains[a], variant_domains[b]),
                    "rbo": rbo(variant_domains[a], variant_domains[b], p=p),
                }
            )
    return results

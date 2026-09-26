from biaslens.metrics.overlap import jaccard, pairwise_overlap, rbo


def test_jaccard_identical_lists_is_one() -> None:
    assert jaccard(["a.com", "b.com"], ["a.com", "b.com"]) == 1.0


def test_jaccard_disjoint_lists_is_zero() -> None:
    assert jaccard(["a.com"], ["b.com"]) == 0.0


def test_jaccard_partial_overlap() -> None:
    # {a,b,c} vs {b,c,d}: intersection=2, union=4
    assert jaccard(["a", "b", "c"], ["b", "c", "d"]) == 0.5


def test_jaccard_both_empty_is_zero_not_nan() -> None:
    assert jaccard([], []) == 0.0


def test_rbo_identical_lists_is_one() -> None:
    domains = ["a.com", "b.com", "c.com", "d.com"]
    assert abs(rbo(domains, domains, p=0.9) - 1.0) < 1e-9


def test_rbo_disjoint_lists_is_zero() -> None:
    assert rbo(["a", "b", "c"], ["x", "y", "z"]) == 0.0


def test_rbo_empty_list_is_zero() -> None:
    assert rbo([], ["a"]) == 0.0
    assert rbo(["a"], []) == 0.0


def test_rbo_partial_overlap_between_zero_and_one() -> None:
    score = rbo(["a", "b", "c"], ["a", "x", "y"], p=0.9)
    assert 0.0 < score < 1.0


def test_rbo_higher_when_overlap_is_earlier_in_ranking() -> None:
    # top-heavy agreement should score higher than bottom-heavy agreement
    early_agreement = rbo(["a", "x", "y"], ["a", "p", "q"], p=0.9)
    late_agreement = rbo(["x", "y", "a"], ["p", "q", "a"], p=0.9)
    assert early_agreement > late_agreement


def test_pairwise_overlap_covers_every_unordered_pair() -> None:
    variant_domains = {
        "Chennai/ta": ["a.com", "b.com"],
        "Delhi/hi": ["a.com", "c.com"],
        "Bengaluru/en": ["a.com", "b.com"],
    }
    results = pairwise_overlap(variant_domains)
    pairs = {(r["variant_a"], r["variant_b"]) for r in results}
    assert len(results) == 3  # 3 choose 2
    assert ("Chennai/ta", "Delhi/hi") in pairs
    assert ("Chennai/ta", "Bengaluru/en") in pairs
    assert ("Delhi/hi", "Bengaluru/en") in pairs
    for r in results:
        assert 0.0 <= r["jaccard"] <= 1.0  # type: ignore[operator]
        assert 0.0 <= r["rbo"] <= 1.0  # type: ignore[operator]

import math

from biaslens.metrics.diversity import (
    max_possible_entropy,
    normalized_entropy,
    shannon_entropy,
)


def test_empty_list_is_zero_entropy() -> None:
    assert shannon_entropy([]) == 0.0


def test_single_domain_repeated_is_zero_entropy() -> None:
    assert shannon_entropy(["a.com", "a.com", "a.com"]) == 0.0


def test_all_distinct_domains_is_max_entropy() -> None:
    domains = ["a.com", "b.com", "c.com", "d.com"]
    assert math.isclose(shannon_entropy(domains), math.log2(4))


def test_max_possible_entropy_matches_distinct_count() -> None:
    domains = ["a.com", "b.com", "b.com", "c.com"]
    assert math.isclose(max_possible_entropy(domains), math.log2(3))


def test_max_possible_entropy_single_domain_is_zero() -> None:
    assert max_possible_entropy(["a.com", "a.com"]) == 0.0


def test_normalized_entropy_is_one_when_all_distinct() -> None:
    domains = ["a.com", "b.com", "c.com"]
    assert math.isclose(normalized_entropy(domains), 1.0)


def test_normalized_entropy_zero_when_undefined() -> None:
    assert normalized_entropy([]) == 0.0
    assert normalized_entropy(["a.com"]) == 0.0


def test_normalized_entropy_between_zero_and_one() -> None:
    domains = ["a.com", "a.com", "b.com", "c.com"]
    n = normalized_entropy(domains)
    assert 0.0 < n < 1.0

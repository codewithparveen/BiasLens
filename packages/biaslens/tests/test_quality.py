from pathlib import Path

import pytest

from biaslens.metrics.quality import DomainTierClassifier

_FIXTURE_YAML = """
tiers:
  government_official:
    weight: 1.0
    label: "Government"
    domains:
      - ".gov.in"
  health_medical_authority:
    weight: 0.9
    label: "Health Authority"
    domains:
      - "who.int"
  commercial:
    weight: 0.4
    label: "Commercial"
    domains:
      - "amazon.in"
unclassified:
  weight: 0.5
  label: "Unclassified"
"""


@pytest.fixture
def classifier(tmp_path: Path) -> DomainTierClassifier:
    path = tmp_path / "tiers.yaml"
    path.write_text(_FIXTURE_YAML)
    return DomainTierClassifier(path)


def test_loads_default_package_yaml() -> None:
    # Exercises the real domain_tiers.yaml shipped with the package.
    classifier = DomainTierClassifier()
    match = classifier.classify("who.int")
    assert match.tier == "health_medical_authority"


def test_exact_domain_match(classifier: DomainTierClassifier) -> None:
    match = classifier.classify("amazon.in")
    assert match.tier == "commercial"
    assert match.weight == 0.4


def test_suffix_match(classifier: DomainTierClassifier) -> None:
    match = classifier.classify("mohfw.gov.in")
    assert match.tier == "government_official"
    assert match.weight == 1.0


def test_unmatched_domain_is_unclassified(classifier: DomainTierClassifier) -> None:
    match = classifier.classify("some-random-blog.example")
    assert match.tier == "unclassified"
    assert match.weight == 0.5


def test_none_domain_is_unclassified(classifier: DomainTierClassifier) -> None:
    assert classifier.classify(None).tier == "unclassified"


def test_www_prefix_is_stripped(classifier: DomainTierClassifier) -> None:
    match = classifier.classify("www.who.int")
    assert match.tier == "health_medical_authority"


def test_quality_mix_counts_and_shares(classifier: DomainTierClassifier) -> None:
    mix = classifier.quality_mix(["who.int", "who.int", "amazon.in", "unknown.example"])
    assert mix["health_medical_authority"]["count"] == 2
    assert mix["health_medical_authority"]["share"] == 0.5
    assert mix["commercial"]["count"] == 1
    assert mix["unclassified"]["count"] == 1


def test_weighted_quality_score_empty_is_zero(classifier: DomainTierClassifier) -> None:
    assert classifier.weighted_quality_score([]) == 0.0


def test_weighted_quality_score_all_government_is_100(classifier: DomainTierClassifier) -> None:
    score = classifier.weighted_quality_score(["mohfw.gov.in", "pmkisan.gov.in"])
    assert score == 100.0

from biaslens.metrics.score import information_inequality_score


def test_perfectly_equal_variants_score_zero() -> None:
    result = information_inequality_score(
        pairwise_rbo=[1.0, 1.0, 1.0],
        quality_scores_0_100=[80.0, 80.0, 80.0],
        language_match_rates_0_1=[0.9, 0.9, 0.9],
        normalized_entropies_0_1=[0.7, 0.7, 0.7],
    )
    assert result.total == 0.0
    assert result.overlap_component == 0.0
    assert result.quality_component == 0.0


def test_maximally_unequal_variants_score_near_100() -> None:
    result = information_inequality_score(
        pairwise_rbo=[0.0, 0.0, 0.0],
        quality_scores_0_100=[0.0, 100.0],
        language_match_rates_0_1=[0.0, 1.0],
        normalized_entropies_0_1=[0.0, 1.0],
    )
    assert result.total == 100.0


def test_score_is_between_zero_and_hundred_for_mixed_inputs() -> None:
    result = information_inequality_score(
        pairwise_rbo=[0.3, 0.6, 0.9],
        quality_scores_0_100=[40.0, 90.0, 70.0],
        language_match_rates_0_1=[0.2, 0.8, 0.5],
        normalized_entropies_0_1=[0.1, 0.9, 0.5],
    )
    assert 0.0 < result.total < 100.0


def test_empty_inputs_do_not_raise_and_yield_zero() -> None:
    result = information_inequality_score(
        pairwise_rbo=[],
        quality_scores_0_100=[],
        language_match_rates_0_1=[],
        normalized_entropies_0_1=[],
    )
    assert result.total == 0.0


def test_single_variant_has_zero_spread_components() -> None:
    # No pair to compare against -> quality/language/diversity spread is 0
    result = information_inequality_score(
        pairwise_rbo=[],
        quality_scores_0_100=[55.0],
        language_match_rates_0_1=[0.4],
        normalized_entropies_0_1=[0.6],
    )
    assert result.quality_component == 0.0
    assert result.language_component == 0.0
    assert result.diversity_component == 0.0


def test_custom_weights_are_respected() -> None:
    result = information_inequality_score(
        pairwise_rbo=[0.0],
        quality_scores_0_100=[0.0, 0.0],
        language_match_rates_0_1=[0.0, 0.0],
        normalized_entropies_0_1=[0.0, 0.0],
        weights={"overlap": 1.0, "quality": 0.0, "language": 0.0, "diversity": 0.0},
    )
    assert result.total == 100.0  # overlap_component=1.0, fully weighted

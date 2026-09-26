from biaslens.metrics.reliability import variance_report


def test_empty_values_returns_zeroed_report() -> None:
    r = variance_report([])
    assert r.n == 0
    assert r.mean == 0.0
    assert r.stdev == 0.0
    assert r.coefficient_of_variation is None


def test_single_value_has_zero_stdev() -> None:
    r = variance_report([5.0])
    assert r.n == 1
    assert r.mean == 5.0
    assert r.stdev == 0.0


def test_identical_values_have_zero_stdev() -> None:
    r = variance_report([3.0, 3.0, 3.0])
    assert r.stdev == 0.0
    assert r.coefficient_of_variation == 0.0


def test_varying_values_have_positive_stdev() -> None:
    r = variance_report([1.0, 5.0])
    assert r.mean == 3.0
    assert r.stdev > 0.0
    assert r.coefficient_of_variation is not None
    assert r.coefficient_of_variation > 0.0


def test_zero_mean_gives_none_cv_not_zero_division() -> None:
    r = variance_report([-2.0, 2.0])
    assert r.mean == 0.0
    assert r.coefficient_of_variation is None

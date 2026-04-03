from __future__ import annotations

from signified_bench.score import SCORE_WEIGHTS, _collect_metrics, compute_score


def test_collect_metrics_extracts_parametrized_names() -> None:
    payload = {
        "benchmarks": [
            {"name": "test_steady_state_scenarios[shared_clock_reads]", "stats": {"mean": 0.010}},
            {"fullname": "tests/test_benchmarks.py::test_steady_state_scenarios[stacked_layers]", "stats": {"mean": 0.020}},
            {"name": "test_steady_state_scenarios[ignored_case]", "stats": {"mean": 99.0}},
        ]
    }

    metrics = _collect_metrics(payload, "mean")

    assert metrics == {
        "shared_clock_reads": 0.010,
        "stacked_layers": 0.020,
    }


def test_compute_score_uses_weighted_geometric_mean() -> None:
    baseline = {name: 1.0 for name in SCORE_WEIGHTS}
    current = {name: 1.0 for name in SCORE_WEIGHTS}
    current["shared_clock_reads"] = 0.8
    current["stacked_layers"] = 0.9

    summary = compute_score(current=current, baseline=baseline, metric="mean")

    assert summary.score > 100.0
    assert round(summary.weighted_ratio, 4) == 0.9404
    assert round(summary.score, 2) == 106.34


def test_compute_score_requires_all_weighted_scenarios() -> None:
    baseline = {name: 1.0 for name in SCORE_WEIGHTS}
    current = dict(baseline)
    current.pop("signal_read_write")

    try:
        compute_score(current=current, baseline=baseline, metric="mean")
    except ValueError as exc:
        assert "signal_read_write" in str(exc)
    else:
        raise AssertionError("Expected missing weighted scenario to raise ValueError.")

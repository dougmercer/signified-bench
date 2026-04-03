"""Pytest benchmark suite for signified performance tracking."""

from __future__ import annotations

import importlib.util

import pytest

from signified_bench.scenarios import CONSTRUCTION_SCENARIOS, STEADY_STATE_SCENARIOS, ScenarioSpec

HAS_PYTEST_BENCHMARK = importlib.util.find_spec("pytest_benchmark") is not None
BENCHMARK_MARK = pytest.mark.skipif(
    not HAS_PYTEST_BENCHMARK,
    reason="Install benchmark tooling with `uv sync --group bench`.",
)


@BENCHMARK_MARK
@pytest.mark.benchmark(disable_gc=True, min_rounds=20, warmup=True, warmup_iterations=1)
@pytest.mark.parametrize("spec", STEADY_STATE_SCENARIOS, ids=[spec.name for spec in STEADY_STATE_SCENARIOS])
def test_steady_state_scenarios(benchmark, spec: ScenarioSpec) -> None:
    """Benchmark hot-path update and read workloads."""
    runner = spec.make_runner()
    benchmark.extra_info["description"] = spec.description
    benchmark(runner)


@BENCHMARK_MARK
@pytest.mark.benchmark(disable_gc=True, min_rounds=10, warmup=True, warmup_iterations=1)
@pytest.mark.parametrize("spec", CONSTRUCTION_SCENARIOS, ids=[spec.name for spec in CONSTRUCTION_SCENARIOS])
def test_construction_scenarios(benchmark, spec: ScenarioSpec) -> None:
    """Benchmark graph construction costs."""
    runner = spec.make_runner()
    benchmark.extra_info["description"] = spec.description
    benchmark(runner)

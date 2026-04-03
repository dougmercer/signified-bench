"""Pytest compare-suite entrypoints shipped with the package.

Keeping these inside ``src/signified_bench`` lets the CLI run table-mode
benchmarks from an installed wheel, not just from a source checkout.
"""

from __future__ import annotations

import importlib.util

import pytest

from signified_bench.compare import (
    COMPARE_BACKENDS,
    COMPARE_CONSTRUCTION_SCENARIOS,
    COMPARE_STEADY_STATE_SCENARIOS,
    CompareBackendSpec,
    CompareScenarioSpec,
)

HAS_PYTEST_BENCHMARK = importlib.util.find_spec("pytest_benchmark") is not None
BENCHMARK_MARK = pytest.mark.skipif(
    not HAS_PYTEST_BENCHMARK,
    reason="Install benchmark tooling with `uv sync` first.",
)


def _make_backend_or_skip(spec: CompareBackendSpec):
    if not spec.is_available():
        pytest.skip(f"{spec.name} is not installed. Run `uv sync --group compare` first.")
    try:
        return spec.make_backend()
    except RuntimeError as exc:
        pytest.skip(str(exc))


@BENCHMARK_MARK
@pytest.mark.benchmark(disable_gc=True, min_rounds=12, warmup=True, warmup_iterations=1)
@pytest.mark.parametrize("backend_spec", COMPARE_BACKENDS, ids=[spec.name for spec in COMPARE_BACKENDS])
@pytest.mark.parametrize(
    "scenario_spec",
    COMPARE_STEADY_STATE_SCENARIOS,
    ids=[spec.name for spec in COMPARE_STEADY_STATE_SCENARIOS],
)
def test_compare_steady_state_scenarios(benchmark, backend_spec: CompareBackendSpec, scenario_spec: CompareScenarioSpec) -> None:
    """Benchmark portable steady-state workloads across reactive backends."""
    backend = _make_backend_or_skip(backend_spec)
    runner = scenario_spec.make_runner(backend)
    benchmark.extra_info["backend"] = backend_spec.name
    benchmark.extra_info["description"] = scenario_spec.description
    benchmark(runner)


@BENCHMARK_MARK
@pytest.mark.benchmark(disable_gc=True, min_rounds=8, warmup=True, warmup_iterations=1)
@pytest.mark.parametrize("backend_spec", COMPARE_BACKENDS, ids=[spec.name for spec in COMPARE_BACKENDS])
@pytest.mark.parametrize(
    "scenario_spec",
    COMPARE_CONSTRUCTION_SCENARIOS,
    ids=[spec.name for spec in COMPARE_CONSTRUCTION_SCENARIOS],
)
def test_compare_construction_scenarios(benchmark, backend_spec: CompareBackendSpec, scenario_spec: CompareScenarioSpec) -> None:
    """Benchmark portable graph-construction workloads across reactive backends."""
    backend = _make_backend_or_skip(backend_spec)
    runner = scenario_spec.make_runner(backend)
    benchmark.extra_info["backend"] = backend_spec.name
    benchmark.extra_info["description"] = scenario_spec.description
    benchmark(runner)

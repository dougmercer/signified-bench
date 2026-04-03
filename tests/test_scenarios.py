from __future__ import annotations

from signified_bench.scenarios import (
    CONSTRUCTION_SCENARIOS,
    STEADY_STATE_SCENARIOS,
    SCENARIOS_BY_NAME,
    get_scenarios,
)


def test_get_scenarios_exposes_both_groups() -> None:
    assert get_scenarios("steady-state") == STEADY_STATE_SCENARIOS
    assert get_scenarios("construction") == CONSTRUCTION_SCENARIOS
    assert len(get_scenarios("all")) == len(STEADY_STATE_SCENARIOS) + len(CONSTRUCTION_SCENARIOS)


def test_signal_read_write_runner_returns_int() -> None:
    runner = SCENARIOS_BY_NAME["signal_read_write"].make_runner()

    assert isinstance(runner(), int)

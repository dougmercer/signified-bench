from __future__ import annotations

import sys
from pathlib import Path

from signified_bench.run import _build_table_command, _selection_expr, parse_args


def test_parse_args_supports_compare_defaults() -> None:
    args, passthrough = parse_args(["--compare", "--table", "--group", "construction", "--codspeed", "--codspeed-mode", "simulation", "-q"])

    assert args.table is True
    assert args.compare is True
    assert args.group == "construction"
    assert args.suite == "compare"
    assert args.codspeed is True
    assert args.codspeed_mode == "simulation"
    assert passthrough == ["-q"]


def test_selection_expr_prefers_named_scenarios() -> None:
    expr = _selection_expr(
        group="steady-state",
        scenario_names=["fanout_updates", "diamond_updates"],
        backend_names=None,
    )

    assert expr == "(fanout_updates or diamond_updates)"


def test_selection_expr_uses_group_when_no_scenarios_are_named() -> None:
    assert _selection_expr(group="steady-state", scenario_names=None, backend_names=None) == "test_compare_steady_state_scenarios"
    assert _selection_expr(group="construction", scenario_names=None, backend_names=None) == "test_compare_construction_scenarios"
    assert _selection_expr(group="all", scenario_names=None, backend_names=None) is None


def test_selection_expr_can_include_compare_backends() -> None:
    expr = _selection_expr(
        group="steady-state",
        scenario_names=["signal_read_write"],
        backend_names=["signified", "reaktiv"],
    )

    assert expr == "(signal_read_write) and (signified or reaktiv)"


def test_build_table_command_targets_only_benchmark_suite() -> None:
    cmd = _build_table_command(
        group="construction",
        scenario_names=None,
        backend_names=None,
        codspeed=False,
        codspeed_mode=None,
        pytest_args=["-q"],
    )

    assert cmd[:6] == [sys.executable, "-m", "pytest", "-o", "addopts=", "-m"]
    assert cmd[6] == "benchmark"
    assert Path(cmd[7]).name == "_pytest_compare_benchmarks.py"
    assert cmd[8:] == ["-k", "test_compare_construction_scenarios", "-q"]


def test_build_table_command_defaults_to_quiet_output() -> None:
    cmd = _build_table_command(
        group="all",
        scenario_names=None,
        backend_names=None,
        codspeed=False,
        codspeed_mode=None,
        pytest_args=[],
    )

    assert cmd[-1] == "-q"


def test_build_table_command_can_filter_compare_backends() -> None:
    cmd = _build_table_command(
        group="steady-state",
        scenario_names=["shared_clock_reads"],
        backend_names=["reaktiv"],
        codspeed=True,
        codspeed_mode="simulation",
        pytest_args=["--benchmark-sort=name"],
    )

    assert Path(cmd[7]).name == "_pytest_compare_benchmarks.py"
    assert cmd[8:] == [
        "-k",
        "(shared_clock_reads) and (reaktiv)",
        "--codspeed",
        "--codspeed-mode",
        "simulation",
        "-q",
        "--benchmark-sort=name",
    ]

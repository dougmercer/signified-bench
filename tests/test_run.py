from __future__ import annotations

import sys
from pathlib import Path

from signified_bench.run import _build_table_command, _selection_expr, parse_args


def test_parse_args_supports_table_flag() -> None:
    args, passthrough = parse_args(["--table", "--group", "construction", "-q"])

    assert args.table is True
    assert args.group == "construction"
    assert args.suite == "signified"
    assert passthrough == ["-q"]


def test_selection_expr_prefers_named_scenarios() -> None:
    expr = _selection_expr(
        suite="signified",
        group="steady-state",
        scenario_names=["fanout_updates", "diamond_updates"],
        backend_names=None,
    )

    assert expr == "(fanout_updates or diamond_updates)"


def test_selection_expr_uses_group_when_no_scenarios_are_named() -> None:
    assert _selection_expr(suite="signified", group="steady-state", scenario_names=None, backend_names=None) == "test_steady_state_scenarios"
    assert _selection_expr(suite="signified", group="construction", scenario_names=None, backend_names=None) == "test_construction_scenarios"
    assert _selection_expr(suite="signified", group="all", scenario_names=None, backend_names=None) is None


def test_selection_expr_can_include_compare_backends() -> None:
    expr = _selection_expr(
        suite="compare",
        group="steady-state",
        scenario_names=["signal_read_write"],
        backend_names=["signified", "reaktiv"],
    )

    assert expr == "(signal_read_write) and (signified or reaktiv)"


def test_selection_expr_uses_compare_group_names() -> None:
    assert (
        _selection_expr(suite="compare", group="steady-state", scenario_names=None, backend_names=None)
        == "test_compare_steady_state_scenarios"
    )
    assert (
        _selection_expr(suite="compare", group="construction", scenario_names=None, backend_names=None)
        == "test_compare_construction_scenarios"
    )


def test_build_table_command_targets_only_benchmark_suite() -> None:
    cmd = _build_table_command(
        suite="signified",
        group="construction",
        scenario_names=None,
        backend_names=None,
        pytest_args=["-q"],
    )

    assert cmd[:6] == [sys.executable, "-m", "pytest", "-o", "addopts=", "-m"]
    assert cmd[6] == "benchmark"
    assert Path(cmd[7]).name == "_pytest_benchmarks.py"
    assert cmd[8:] == ["-k", "test_construction_scenarios", "-q"]


def test_build_table_command_defaults_to_quiet_output() -> None:
    cmd = _build_table_command(
        suite="signified",
        group="all",
        scenario_names=None,
        backend_names=None,
        pytest_args=[],
    )

    assert cmd[-1] == "-q"


def test_build_compare_table_command_targets_compare_suite() -> None:
    cmd = _build_table_command(
        suite="compare",
        group="steady-state",
        scenario_names=["shared_clock_reads"],
        backend_names=["param"],
        pytest_args=["--benchmark-sort=name"],
    )

    assert Path(cmd[7]).name == "_pytest_compare_benchmarks.py"
    assert cmd[8:] == ["-k", "(shared_clock_reads) and (param)", "-q", "--benchmark-sort=name"]

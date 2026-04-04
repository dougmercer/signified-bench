"""Run cross-library signified compare benchmarks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from signified_bench._benchmarking import BENCHMARK_TOOLING_ERROR, has_pytest_benchmark_tooling
from signified_bench.compare import COMPARE_BACKENDS_BY_NAME, COMPARE_SCENARIOS_BY_NAME


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run cross-library signified compare benchmarks with pytest benchmark plugins.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--group",
        choices=("steady-state", "construction", "all"),
        default="steady-state",
        help="Which benchmark group to run if --scenario is not provided.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        help="Run only the named scenario (can be passed multiple times).",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare mode is the default; this flag is accepted for readability.",
    )
    parser.add_argument(
        "--suite",
        choices=("compare",),
        default="compare",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--backend",
        action="append",
        choices=sorted(COMPARE_BACKENDS_BY_NAME),
        help="Run only the named compare-suite backend.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available compare scenarios and exit.",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Run the pytest compare benchmark suite and print the benchmark table.",
    )
    parser.add_argument(
        "--codspeed",
        action="store_true",
        help="Enable CodSpeed when running table mode.",
    )
    parser.add_argument(
        "--codspeed-mode",
        choices=("auto", "simulation", "walltime", "memory"),
        help="Select the CodSpeed instrument when running table mode.",
    )
    return parser.parse_known_args(argv)


def _selection_expr(
    *,
    group: str,
    scenario_names: Sequence[str] | None,
    backend_names: Sequence[str] | None,
) -> str | None:
    """Build a pytest -k expression that mirrors CLI selection flags."""
    parts: list[str] = []

    if scenario_names:
        parts.append("(" + " or ".join(scenario_names) + ")")
    elif group == "steady-state":
        parts.append("test_compare_steady_state_scenarios")
    elif group == "construction":
        parts.append("test_compare_construction_scenarios")

    if backend_names:
        parts.append("(" + " or ".join(backend_names) + ")")

    return " and ".join(parts) if parts else None


def _build_table_command(
    *,
    group: str,
    scenario_names: Sequence[str] | None,
    backend_names: Sequence[str] | None,
    codspeed: bool,
    codspeed_mode: str | None,
    pytest_args: list[str],
) -> list[str]:
    """Build the pytest command used for table-mode benchmark runs."""
    benchmark_test = Path(__file__).resolve().with_name("_pytest_compare_benchmarks.py")
    cmd = [sys.executable, "-m", "pytest", "-o", "addopts=", "-m", "benchmark", str(benchmark_test)]
    selection_expr = _selection_expr(
        group=group,
        scenario_names=scenario_names,
        backend_names=backend_names,
    )
    if selection_expr is not None:
        cmd.extend(("-k", selection_expr))
    if codspeed:
        cmd.append("--codspeed")
    if codspeed_mode is not None:
        cmd.extend(("--codspeed-mode", codspeed_mode))
    if not any(arg in {"-q", "--quiet"} for arg in pytest_args):
        cmd.append("-q")
    cmd.extend(pytest_args)
    return cmd


def _run_table_mode(
    *,
    group: str,
    scenario_names: Sequence[str] | None,
    backend_names: Sequence[str] | None,
    codspeed: bool,
    codspeed_mode: str | None,
    pytest_args: list[str],
) -> int:
    """Run the pytest benchmark suite and print its summary table."""
    if not has_pytest_benchmark_tooling():
        raise SystemExit(BENCHMARK_TOOLING_ERROR)

    cmd = _build_table_command(
        group=group,
        scenario_names=scenario_names,
        backend_names=backend_names,
        codspeed=codspeed,
        codspeed_mode=codspeed_mode,
        pytest_args=pytest_args,
    )
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args, pytest_args = parse_args(sys.argv[1:] if argv is None else argv)
    scenario_names = COMPARE_SCENARIOS_BY_NAME

    if args.scenario:
        unknown = sorted(name for name in args.scenario if name not in scenario_names)
        if unknown:
            raise SystemExit(f"Unknown compare scenario(s): {', '.join(unknown)}")

    if args.list:
        for name in sorted(scenario_names):
            scenario = scenario_names[name]
            print(f"{scenario.name:24} [{scenario.group}] {scenario.description}")
        print()
        print("Compare backends")
        for backend in COMPARE_BACKENDS_BY_NAME.values():
            print(f"{backend.name:24} {backend.description}")
        return 0

    if args.table:
        return _run_table_mode(
            group=args.group,
            scenario_names=args.scenario,
            backend_names=args.backend,
            codspeed=args.codspeed,
            codspeed_mode=args.codspeed_mode,
            pytest_args=pytest_args,
        )

    raise SystemExit("Compare benchmarks currently support only --table mode.")


if __name__ == "__main__":
    raise SystemExit(main())

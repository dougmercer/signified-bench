"""Run signified benchmarks via pyperf or pytest-benchmark."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from signified_bench.compare import COMPARE_BACKENDS_BY_NAME, COMPARE_SCENARIOS_BY_NAME
from signified_bench.scenarios import SCENARIOS_BY_NAME, get_scenarios


def parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Run signified benchmarks with pyperf or pytest-benchmark.",
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
        "--suite",
        choices=("signified", "compare"),
        default="signified",
        help="Which benchmark suite to target in table mode.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        choices=sorted(COMPARE_BACKENDS_BY_NAME),
        help="Run only the named compare-suite backend (table mode, compare suite only).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scenarios and exit.",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Run the pytest-benchmark suite and print the benchmark table.",
    )
    return parser.parse_known_args(argv)


def _add_selection_args(cmd: list[str], *, group: str, scenario_names: Sequence[str] | None) -> None:
    """Preserve local scenario selection when pyperf spawns worker processes."""
    if scenario_names:
        for name in scenario_names:
            cmd.extend(("--scenario", name))
        return
    cmd.extend(("--group", group))


def _selection_expr(
    *,
    suite: str,
    group: str,
    scenario_names: Sequence[str] | None,
    backend_names: Sequence[str] | None,
) -> str | None:
    """Build a pytest -k expression that mirrors CLI selection flags."""
    parts: list[str] = []

    if scenario_names:
        parts.append("(" + " or ".join(scenario_names) + ")")
    elif group == "steady-state":
        parts.append("test_compare_steady_state_scenarios" if suite == "compare" else "test_steady_state_scenarios")
    elif group == "construction":
        parts.append("test_compare_construction_scenarios" if suite == "compare" else "test_construction_scenarios")

    if backend_names:
        parts.append("(" + " or ".join(backend_names) + ")")

    return " and ".join(parts) if parts else None


def _build_table_command(
    *,
    suite: str,
    group: str,
    scenario_names: Sequence[str] | None,
    backend_names: Sequence[str] | None,
    pytest_args: list[str],
) -> list[str]:
    """Build the pytest command used for table-mode benchmark runs."""
    benchmark_module = (
        "signified_bench._pytest_compare_benchmarks"
        if suite == "compare"
        else "signified_bench._pytest_benchmarks"
    )
    benchmark_test = Path(__file__).resolve().with_name(f"{benchmark_module.rsplit('.', 1)[-1]}.py")
    cmd = [sys.executable, "-m", "pytest", "-o", "addopts=", "-m", "benchmark", str(benchmark_test)]
    selection_expr = _selection_expr(
        suite=suite,
        group=group,
        scenario_names=scenario_names,
        backend_names=backend_names,
    )
    if selection_expr is not None:
        cmd.extend(("-k", selection_expr))
    if not any(arg in {"-q", "--quiet"} for arg in pytest_args):
        cmd.append("-q")
    cmd.extend(pytest_args)
    return cmd


def _run_table_mode(
    *,
    suite: str,
    group: str,
    scenario_names: Sequence[str] | None,
    backend_names: Sequence[str] | None,
    pytest_args: list[str],
) -> int:
    """Run the pytest-benchmark suite and print its summary table."""
    if importlib.util.find_spec("pytest_benchmark") is None:
        raise SystemExit("pytest-benchmark is not installed. Run `uv sync` first.")

    cmd = _build_table_command(
        suite=suite,
        group=group,
        scenario_names=scenario_names,
        backend_names=backend_names,
        pytest_args=pytest_args,
    )
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args, pyperf_args = parse_args(sys.argv[1:] if argv is None else argv)
    scenario_names = COMPARE_SCENARIOS_BY_NAME if args.suite == "compare" else SCENARIOS_BY_NAME

    if args.scenario:
        unknown = sorted(name for name in args.scenario if name not in scenario_names)
        if unknown:
            raise SystemExit(f"Unknown {args.suite} scenario(s): {', '.join(unknown)}")

    if args.list:
        for name in sorted(scenario_names):
            scenario = scenario_names[name]
            print(f"{scenario.name:24} [{scenario.group}] {scenario.description}")
        if args.suite == "compare":
            print()
            print("Compare backends")
            for backend in COMPARE_BACKENDS_BY_NAME.values():
                print(f"{backend.name:24} {backend.description}")
        return 0

    if args.table:
        return _run_table_mode(
            suite=args.suite,
            group=args.group,
            scenario_names=args.scenario,
            backend_names=args.backend,
            pytest_args=pyperf_args,
        )

    if args.suite == "compare":
        raise SystemExit("The compare suite currently supports only --table mode.")

    if args.backend:
        raise SystemExit("`--backend` is only supported with `--table --suite compare`.")

    selected = [SCENARIOS_BY_NAME[name] for name in args.scenario] if args.scenario else list(get_scenarios(args.group))
    if not selected:
        raise SystemExit("No benchmark scenarios selected.")

    try:
        import pyperf
    except ImportError as exc:
        raise SystemExit("pyperf is not installed. Run `uv sync --group bench` first.") from exc

    def add_cmdline_args(cmd: list[str], _pyperf_ns: argparse.Namespace) -> None:
        _add_selection_args(cmd, group=args.group, scenario_names=args.scenario)

    sys.argv = [sys.argv[0], *pyperf_args]
    runner = pyperf.Runner(
        program_args=("-m", "signified_bench.run"),
        add_cmdline_args=add_cmdline_args,
    )

    for scenario in selected:
        benchmark = scenario.make_runner()
        runner.bench_func(scenario.name, benchmark)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

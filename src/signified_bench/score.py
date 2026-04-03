"""Compute a weighted workload score from pytest-benchmark JSON output."""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

SCORE_WEIGHTS: Final[dict[str, float]] = {
    "shared_clock_reads": 0.20,       # broadcast invalidation + partial reads (reactive render tick)
    "animation_stack": 0.18,          # frame-driven animation chains (primary key3d pattern)
    "stacked_layers": 0.16,           # deep affine stack with two sources
    "scoped_context_reads": 0.12,     # scoped frame override + multiple downstream reads
    "shared_dependency_branches": 0.10,  # shared intermediate subgraph evaluated once per tick
    "multi_input_computed": 0.08,     # wide computed with heterogeneous input update rates
    "dynamic_dependency_switch": 0.05,  # per-update subscription reconciliation
    "computed_signal_at": 0.05,       # raw Signal.at() context-manager overhead
    "signal_read_write": 0.03,        # baseline read/write primitive cost
    "subscription_churn": 0.02,       # observer-set mutation overhead
    "fanout_updates": 0.01,           # simple 1→N fan-out propagation
}

_PARAMETRIZED_NAME = re.compile(r"\[([^\[\]]+)\]$")


@dataclass(frozen=True, slots=True)
class ScenarioComparison:
    name: str
    weight: float
    baseline: float
    current: float

    @property
    def ratio(self) -> float:
        """Return current / baseline, where smaller is faster."""
        return self.current / self.baseline

    @property
    def delta_percent(self) -> float:
        """Return percentage change where negative is faster."""
        return (self.ratio - 1.0) * 100.0


@dataclass(frozen=True, slots=True)
class ScoreSummary:
    metric: str
    weighted_ratio: float
    score: float
    comparisons: tuple[ScenarioComparison, ...]


def _resolve_benchmark_name(entry: dict[str, Any]) -> str | None:
    """Extract a stable benchmark name from pytest-benchmark JSON fields."""
    for key in ("name", "fullname", "fullfunc", "group"):
        value = entry.get(key)
        if not isinstance(value, str):
            continue
        if value in SCORE_WEIGHTS:
            return value
        match = _PARAMETRIZED_NAME.search(value)
        if match and match.group(1) in SCORE_WEIGHTS:
            return match.group(1)
    return None


def _collect_metrics(payload: dict[str, Any], metric: str) -> dict[str, float]:
    """Collect weighted benchmark metrics from pytest-benchmark JSON payloads."""
    metrics: dict[str, float] = {}
    for entry in payload.get("benchmarks", []):
        if not isinstance(entry, dict):
            continue
        name = _resolve_benchmark_name(entry)
        if name is None:
            continue
        stats = entry.get("stats")
        if not isinstance(stats, dict):
            raise ValueError(f"Benchmark entry for {name!r} is missing stats.")
        value = stats.get(metric)
        if not isinstance(value, int | float):
            raise ValueError(f"Benchmark entry for {name!r} is missing stats[{metric!r}].")
        metrics[name] = float(value)
    return metrics


def _load_metrics(path: Path, metric: str) -> dict[str, float]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark JSON at {path} must contain an object root.")
    return _collect_metrics(payload, metric)


def compute_score(
    current: dict[str, float],
    baseline: dict[str, float],
    metric: str,
    weights: dict[str, float] | None = None,
) -> ScoreSummary:
    """Compute a weighted geometric-mean score from benchmark metrics."""
    resolved_weights = SCORE_WEIGHTS if weights is None else weights

    missing_current = sorted(name for name in resolved_weights if name not in current)
    missing_baseline = sorted(name for name in resolved_weights if name not in baseline)
    if missing_current or missing_baseline:
        missing_parts = []
        if missing_current:
            missing_parts.append(f"current missing {', '.join(missing_current)}")
        if missing_baseline:
            missing_parts.append(f"baseline missing {', '.join(missing_baseline)}")
        raise ValueError("; ".join(missing_parts))

    comparisons = tuple(
        ScenarioComparison(
            name=name,
            weight=weight,
            baseline=baseline[name],
            current=current[name],
        )
        for name, weight in resolved_weights.items()
    )

    weighted_log_ratio = sum(item.weight * math.log(item.ratio) for item in comparisons)
    weighted_ratio = math.exp(weighted_log_ratio)
    return ScoreSummary(
        metric=metric,
        weighted_ratio=weighted_ratio,
        score=100.0 / weighted_ratio,
        comparisons=comparisons,
    )


def _format_microseconds(seconds: float) -> str:
    return f"{seconds * 1_000_000:.1f}"


def _print_weights() -> None:
    print("Scenario weights")
    for name, weight in SCORE_WEIGHTS.items():
        print(f"{name:28} {weight:.2f}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute a weighted workload score from pytest-benchmark JSON output.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("current", type=Path, nargs="?", help="Current pytest-benchmark JSON file.")
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Baseline pytest-benchmark JSON file used as the 100-point reference.",
    )
    parser.add_argument(
        "--metric",
        choices=("mean", "median"),
        default="mean",
        help="Which pytest-benchmark stats metric to compare.",
    )
    parser.add_argument(
        "--list-weights",
        action="store_true",
        help="Print the workload score weights and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.list_weights:
        _print_weights()
        return 0

    if args.current is None or args.baseline is None:
        raise SystemExit("Pass both CURRENT_JSON and --baseline BASELINE_JSON, or use --list-weights.")

    summary = compute_score(
        current=_load_metrics(args.current, args.metric),
        baseline=_load_metrics(args.baseline, args.metric),
        metric=args.metric,
    )

    print(f"Weighted workload score ({summary.metric}, 100 = baseline): {summary.score:.2f}")
    print(f"Weighted geometric mean ratio (current / baseline): {summary.weighted_ratio:.4f}")
    print()
    print("Included scenarios")
    print(f"{'scenario':28} {'weight':>6} {'baseline us':>12} {'current us':>12} {'ratio':>8} {'delta %':>9}")
    for item in summary.comparisons:
        print(
            f"{item.name:28} {item.weight:6.2f} {_format_microseconds(item.baseline):>12} "
            f"{_format_microseconds(item.current):>12} {item.ratio:8.3f} {item.delta_percent:9.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Compatibility helpers for benchmark runners and pytest plugins."""

from __future__ import annotations

import importlib.util

BENCHMARK_TOOLING_ERROR = "Install benchmark tooling with `uv sync` first."


def has_pytest_benchmark_tooling() -> bool:
    """Return whether either supported pytest benchmark plugin is installed."""
    return importlib.util.find_spec("pytest_benchmark") is not None or importlib.util.find_spec("pytest_codspeed") is not None

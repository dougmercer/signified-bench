# signified-bench

Benchmarking and performance-scoring tools for `signified`.

This repo keeps the benchmark harness separate from the main library while still
targeting a sibling checkout at `../signified` by default. The CLI's table-mode
pytest entrypoints live inside the package so `uv run --with ../signified-bench`
works both from a checkout and from an installed wheel.

## Layout

- `src/signified_bench/` contains the reusable benchmark package.
- `tests/` contains pytest benchmark entrypoints, score tests, and heavier stress checks.

## Common commands

```bash
uv sync --group test --group bench
uv run signified-bench --list
uv run signified-bench --group steady-state --fast
uv run pytest
```

To run the cross-library compare suite against `signified`, `reaktiv`,
`signals`, and `param`:

```bash
uv sync --group test --group compare
uv run signified-bench --suite compare --list
uv run signified-bench --table --suite compare --backend signified --backend reaktiv
uv run signified-bench --table --suite compare --scenario shared_clock_reads
```

To score two `pytest-benchmark` JSON outputs:

```bash
uv run signified-bench-score current.json --baseline baseline.json
```

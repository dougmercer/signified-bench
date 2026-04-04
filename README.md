# signified-bench

Cross-library compare benchmarks for `signified`.

The signified-only CodSpeed benchmarks now live in the main `signified`
repository. This repo keeps only the reusable compare harness so you can run
portable scenarios against `signified` and other reactive libraries from a
separate checkout.

## Layout

- `src/signified_bench/` contains the compare package and CLI.
- `tests/` contains compare-suite pytest entrypoints and CLI tests.

## Common commands

```bash
uv sync --group test
uv run signified-bench --list
uv run signified-bench --table --codspeed
uv run signified-bench --table --codspeed --scenario shared_clock_reads
uv run pytest
```

From a local `signified` checkout, layer this repo in just like CI does:

```bash
uv run --with-editable ../signified-bench --with-editable . signified-bench --table --codspeed
```

To run the compare suite against `signified` and `reaktiv`:

```bash
uv sync --group test --extra compare
uv run signified-bench --list
uv run signified-bench --table --codspeed --backend signified --backend reaktiv
uv run signified-bench --table --codspeed --scenario shared_clock_reads
```

Compare mode is the default CLI behavior, so `--compare` is optional and kept
only as a readability alias.

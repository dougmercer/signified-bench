"""Portable cross-library compare benchmarks for ``signified``."""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from typing import Any, Callable, Final, Protocol

type ScenarioRunner = Callable[[], int]


@dataclass(frozen=True, slots=True)
class ReactiveNode:
    """Backend-owned reactive value wrapper."""

    handle: Any


class ReactiveBackend(Protocol):
    """Operations required by portable benchmark scenarios."""

    name: str

    def signal(self, value: Any) -> ReactiveNode: ...

    def computed(self, func: Callable[..., Any], *deps: Any) -> ReactiveNode: ...

    def effect(self, func: Callable[..., None], *deps: Any) -> object: ...

    def get(self, node: ReactiveNode) -> Any: ...

    def set(self, node: ReactiveNode, value: Any) -> None: ...


@dataclass(frozen=True, slots=True)
class CompareScenarioSpec:
    """Benchmark metadata for the portable compare suite."""

    name: str
    group: str
    description: str
    make_runner: Callable[[ReactiveBackend], ScenarioRunner]


@dataclass(frozen=True, slots=True)
class CompareBackendSpec:
    """Metadata for an optional compare backend."""

    name: str
    module_name: str
    description: str
    make_backend: Callable[[], ReactiveBackend]

    def is_available(self) -> bool:
        return importlib.util.find_spec(self.module_name) is not None


class _BaseBackend:
    """Shared helpers for concrete backend adapters."""

    name: str

    def __init__(self) -> None:
        self._effects: list[object] = []

    def _remember_effect(self, handle: object) -> object:
        self._effects.append(handle)
        return handle


class _SignifiedBackend(_BaseBackend):
    name = "signified"

    def __init__(self) -> None:
        super().__init__()
        module = importlib.import_module("signified")
        self._signal_type = module.Signal
        self._computed_type = module.Computed
        self._effect_type = module.Effect

    def signal(self, value: Any) -> ReactiveNode:
        return ReactiveNode(self._signal_type(value))

    def computed(self, func: Callable[..., Any], *deps: Any) -> ReactiveNode:
        return ReactiveNode(self._computed_type(lambda: func(*(self._resolve(dep) for dep in deps))))

    def effect(self, func: Callable[..., None], *deps: Any) -> object:
        return self._remember_effect(self._effect_type(lambda: func(*(self._resolve(dep) for dep in deps))))

    def get(self, node: ReactiveNode) -> Any:
        return node.handle.value

    def set(self, node: ReactiveNode, value: Any) -> None:
        node.handle.value = value

    def _resolve(self, dep: Any) -> Any:
        return self.get(dep) if isinstance(dep, ReactiveNode) else dep


class _ReaktivBackend(_BaseBackend):
    name = "reaktiv"

    def __init__(self) -> None:
        super().__init__()
        module = importlib.import_module("reaktiv")
        self._signal_type = module.Signal
        self._computed_type = module.Computed
        self._effect_type = module.Effect

    def signal(self, value: Any) -> ReactiveNode:
        return ReactiveNode(self._signal_type(value))

    def computed(self, func: Callable[..., Any], *deps: Any) -> ReactiveNode:
        return ReactiveNode(self._computed_type(lambda: func(*(self._resolve(dep) for dep in deps))))

    def effect(self, func: Callable[..., None], *deps: Any) -> object:
        return self._remember_effect(self._effect_type(lambda: func(*(self._resolve(dep) for dep in deps))))

    def get(self, node: ReactiveNode) -> Any:
        return node.handle()

    def set(self, node: ReactiveNode, value: Any) -> None:
        node.handle.set(value)

    def _resolve(self, dep: Any) -> Any:
        return self.get(dep) if isinstance(dep, ReactiveNode) else dep


def make_signal_read_write_runner(backend: ReactiveBackend, batch_size: int = 8_000) -> ScenarioRunner:
    """Single-signal write and read hot loop."""
    signal = backend.signal(0)

    def run() -> int:
        total = 0
        for i in range(batch_size):
            backend.set(signal, i)
            total += backend.get(signal)
        return total

    return run


def make_deep_chain_updates_runner(
    backend: ReactiveBackend,
    depth: int = 24,
    updates: int = 3_000,
) -> ScenarioRunner:
    """Propagate changes through a long dependency chain."""
    source = backend.signal(0)
    sink = source
    for _ in range(depth):
        sink = backend.computed(lambda value: value + 1, sink)
    _ = backend.get(sink)

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            backend.set(source, i)
            checksum += backend.get(sink)
        return checksum

    return run


def make_fanout_updates_runner(
    backend: ReactiveBackend,
    fanout: int = 64,
    updates: int = 1_500,
) -> ScenarioRunner:
    """One source update invalidates many downstream nodes."""
    source = backend.signal(0)
    leaves = [backend.computed(lambda value, offset: value + offset, source, offset) for offset in range(fanout)]
    sink = backend.computed(lambda *values: sum(values), *leaves)
    _ = backend.get(sink)

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            backend.set(source, i)
            checksum += backend.get(sink)
        return checksum

    return run


def make_diamond_updates_runner(
    backend: ReactiveBackend,
    branches: int = 24,
    updates: int = 1_500,
) -> ScenarioRunner:
    """Branch and merge topology with a single shared source."""
    source = backend.signal(0)
    left = [backend.computed(lambda value, factor: value * factor, source, factor) for factor in range(1, branches + 1)]
    right = [backend.computed(lambda value, bias: value + bias, source, bias) for bias in range(branches)]
    merged = [backend.computed(lambda lhs, rhs: lhs - rhs, lhs, rhs) for lhs, rhs in zip(left, right, strict=True)]
    sink = backend.computed(lambda *values: sum(values), *merged)
    _ = backend.get(sink)

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            backend.set(source, i)
            checksum += backend.get(sink)
        return checksum

    return run


def make_multi_input_computed_runner(backend: ReactiveBackend, updates: int = 5_000) -> ScenarioRunner:
    """One computed value combining six independently updating sources."""
    pos_x = backend.signal(0.0)
    pos_y = backend.signal(0.0)
    pos_z = backend.signal(5.0)
    radius = backend.signal(5.0)
    horizontal = backend.signal(0.0)
    vertical = backend.signal(0.3)

    result = backend.computed(
        lambda x, y, z, r, h, v: x + y + z + r * h + r * v,
        pos_x,
        pos_y,
        pos_z,
        radius,
        horizontal,
        vertical,
    )
    _ = backend.get(result)

    def run() -> int:
        checksum = 0.0
        for i in range(updates):
            backend.set(horizontal, (i % 60) * 0.01)
            if i % 3 == 0:
                backend.set(vertical, (i // 3 % 30) * 0.005)
            if i % 10 == 0:
                backend.set(radius, 5.0 + (i // 10 % 5))
            if i % 30 == 0:
                backend.set(pos_x, float(i % 5))
            checksum += backend.get(result)
        return int(checksum)

    return run


def make_shared_clock_reads_runner(
    backend: ReactiveBackend,
    unit_count: int = 32,
    reads_per_update: int = 8,
    updates: int = 1_200,
) -> ScenarioRunner:
    """Shared source invalidation followed by partial downstream reads."""
    clock = backend.signal(0)
    bases = [backend.signal(i) for i in range(unit_count)]

    leaves = []
    for index, base in enumerate(bases):
        staged = backend.computed(lambda value, scale, offset: value * scale + offset, clock, (index % 3) + 1, index)
        leaves.append(backend.computed(lambda stage, local_base, bias: stage + local_base + bias, staged, base, index % 5))

    _ = [backend.get(leaf) for leaf in leaves]

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            backend.set(clock, i)
            backend.set(bases[i % unit_count], i * 2)
            start = (i * reads_per_update) % unit_count
            for offset in range(reads_per_update):
                checksum += backend.get(leaves[(start + offset) % unit_count])
        return checksum

    return run


def make_shared_dependency_branches_runner(backend: ReactiveBackend, updates: int = 1_800) -> ScenarioRunner:
    """Several downstream branches share an intermediate computed node."""
    left = backend.signal(1)
    right = backend.signal(2)
    selector = backend.signal(0)

    shared = backend.computed(lambda lhs, rhs: lhs + rhs + 3, left, right)
    branch_a = backend.computed(lambda value: value * 2 + 1, shared)
    branch_b = backend.computed(lambda value, selected: value + selected + 2, shared, selector)
    branch_c = backend.computed(lambda value, selected: value - selected, branch_a, selector)
    combined = backend.computed(lambda first, second: first + second + 4, branch_b, branch_c)
    _ = backend.get(combined)

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            backend.set(selector, i)
            backend.set(left, (i % 13) + 1)
            backend.set(right, (i % 17) + 2)
            checksum += backend.get(branch_b) + backend.get(branch_c) + backend.get(combined)
        return checksum

    return run


def make_effect_fanout_runner(
    backend: ReactiveBackend,
    effect_count: int = 192,
    updates: int = 1_500,
) -> ScenarioRunner:
    """Many effects listening to one source."""
    source = backend.signal(0)
    accumulator = [0]
    effects = [
        backend.effect(
            lambda value, offset, accumulator=accumulator: accumulator.__setitem__(0, accumulator[0] + value + offset),
            source,
            offset,
        )
        for offset in range(effect_count)
    ]
    _ = len(effects)

    def run() -> int:
        baseline = accumulator[0]
        for i in range(1, updates + 1):
            backend.set(source, i)
        return accumulator[0] - baseline

    return run


def make_build_chain_runner(backend: ReactiveBackend, depth: int = 160) -> ScenarioRunner:
    """Construct a long dependency chain each invocation."""

    def run() -> int:
        source = backend.signal(0)
        sink = source
        for _ in range(depth):
            sink = backend.computed(lambda value: value + 1, sink)
        return int(backend.get(sink))

    return run


def make_build_fanout_runner(backend: ReactiveBackend, fanout: int = 256) -> ScenarioRunner:
    """Construct a high fan-out graph each invocation."""

    def run() -> int:
        source = backend.signal(0)
        leaves = [backend.computed(lambda value, offset: value + offset, source, offset) for offset in range(fanout)]
        sink = backend.computed(lambda *values: sum(values), *leaves)
        return int(backend.get(sink))

    return run


def make_build_diamond_runner(backend: ReactiveBackend, branches: int = 192) -> ScenarioRunner:
    """Construct a branch-and-merge graph each invocation."""

    def run() -> int:
        source = backend.signal(1)
        left = [backend.computed(lambda value, factor: value * factor, source, factor) for factor in range(1, branches + 1)]
        right = [backend.computed(lambda value, bias: value + bias, source, bias) for bias in range(branches)]
        merged = [backend.computed(lambda lhs, rhs: lhs - rhs, lhs, rhs) for lhs, rhs in zip(left, right, strict=True)]
        sink = backend.computed(lambda *values: sum(values), *merged)
        return int(backend.get(sink))

    return run


COMPARE_STEADY_STATE_SCENARIOS: Final[tuple[CompareScenarioSpec, ...]] = (
    CompareScenarioSpec(
        name="signal_read_write",
        group="steady-state",
        description="Baseline cost of a signal write followed by a read.",
        make_runner=make_signal_read_write_runner,
    ),
    CompareScenarioSpec(
        name="deep_chain_updates",
        group="steady-state",
        description="Write propagates through a long linear dependency chain.",
        make_runner=make_deep_chain_updates_runner,
    ),
    CompareScenarioSpec(
        name="fanout_updates",
        group="steady-state",
        description="One source invalidates many independent derived nodes and an aggregate sink.",
        make_runner=make_fanout_updates_runner,
    ),
    CompareScenarioSpec(
        name="diamond_updates",
        group="steady-state",
        description="Branch and merge graph stressing shared-source scheduling.",
        make_runner=make_diamond_updates_runner,
    ),
    CompareScenarioSpec(
        name="multi_input_computed",
        group="steady-state",
        description="Wide computed value fed by inputs updating at different rates.",
        make_runner=make_multi_input_computed_runner,
    ),
    CompareScenarioSpec(
        name="shared_clock_reads",
        group="steady-state",
        description="Shared invalidation followed by repeated partial downstream reads.",
        make_runner=make_shared_clock_reads_runner,
    ),
    CompareScenarioSpec(
        name="shared_dependency_branches",
        group="steady-state",
        description="Several branches sharing an intermediate computed node.",
        make_runner=make_shared_dependency_branches_runner,
    ),
    CompareScenarioSpec(
        name="effect_fanout_updates",
        group="steady-state",
        description="Many effects re-running from a single source update.",
        make_runner=make_effect_fanout_runner,
    ),
)

COMPARE_CONSTRUCTION_SCENARIOS: Final[tuple[CompareScenarioSpec, ...]] = (
    CompareScenarioSpec(
        name="build_deep_chain",
        group="construction",
        description="Graph construction cost for a deep chain.",
        make_runner=make_build_chain_runner,
    ),
    CompareScenarioSpec(
        name="build_fanout_graph",
        group="construction",
        description="Graph construction cost for a wide fan-out.",
        make_runner=make_build_fanout_runner,
    ),
    CompareScenarioSpec(
        name="build_diamond_graph",
        group="construction",
        description="Graph construction cost for a branch and merge topology.",
        make_runner=make_build_diamond_runner,
    ),
)

COMPARE_ALL_SCENARIOS: Final[tuple[CompareScenarioSpec, ...]] = (
    *COMPARE_STEADY_STATE_SCENARIOS,
    *COMPARE_CONSTRUCTION_SCENARIOS,
)
COMPARE_SCENARIOS_BY_NAME: Final[dict[str, CompareScenarioSpec]] = {
    scenario.name: scenario for scenario in COMPARE_ALL_SCENARIOS
}

COMPARE_BACKENDS: Final[tuple[CompareBackendSpec, ...]] = (
    CompareBackendSpec(
        name="signified",
        module_name="signified",
        description="Local signified checkout under benchmark.",
        make_backend=_SignifiedBackend,
    ),
    CompareBackendSpec(
        name="reaktiv",
        module_name="reaktiv",
        description="Signal/Computed/Effect API with lazy automatic dependency tracking.",
        make_backend=_ReaktivBackend,
    ),
)
COMPARE_BACKENDS_BY_NAME: Final[dict[str, CompareBackendSpec]] = {
    backend.name: backend for backend in COMPARE_BACKENDS
}


def get_compare_scenarios(group: str = "all") -> tuple[CompareScenarioSpec, ...]:
    """Return compare-suite scenarios by group."""
    if group == "steady-state":
        return COMPARE_STEADY_STATE_SCENARIOS
    if group == "construction":
        return COMPARE_CONSTRUCTION_SCENARIOS
    if group == "all":
        return COMPARE_ALL_SCENARIOS
    raise ValueError(f"Unknown compare benchmark group: {group}")


def get_compare_backends(names: list[str] | None = None) -> tuple[CompareBackendSpec, ...]:
    """Return compare backends, optionally filtered by name."""
    if names is None:
        return COMPARE_BACKENDS
    return tuple(COMPARE_BACKENDS_BY_NAME[name] for name in names)

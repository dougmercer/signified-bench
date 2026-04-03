"""Reusable benchmark scenarios for signified.

The ``make_*`` helpers return zero-argument callables. This keeps graph setup out
of steady-state benchmarks so results reflect update and read performance instead
of construction cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final

from signified import Computed, Effect, Signal, computed

type ScenarioRunner = Callable[[], int]


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """Benchmark metadata and factory."""

    name: str
    group: str
    description: str
    make_runner: Callable[[], ScenarioRunner]


def make_signal_read_write_runner(batch_size: int = 8_000) -> ScenarioRunner:
    """Single-signal write and read hot loop."""
    signal = Signal(0)

    def run() -> int:
        total = 0
        for i in range(batch_size):
            signal.value = i
            total += signal.value
        return total

    return run


def make_deep_chain_updates_runner(depth: int = 24, updates: int = 3_000) -> ScenarioRunner:
    """Propagate changes through a long dependency chain."""
    source = Signal(0)
    sink = source
    for _ in range(depth):
        sink = sink + 1
    _ = sink.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            source.value = i
            checksum += sink.value
        return checksum

    return run


def make_fanout_updates_runner(fanout: int = 64, updates: int = 1_500) -> ScenarioRunner:
    """One source updates many downstream nodes."""
    source = Signal(0)
    leaves = [source + offset for offset in range(fanout)]
    sink = computed(sum)(leaves)
    _ = sink.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            source.value = i
            checksum += sink.value
        return checksum

    return run


def make_diamond_updates_runner(branches: int = 24, updates: int = 1_500) -> ScenarioRunner:
    """Diamond-shaped graph with multiple branches and merge nodes."""
    source = Signal(0)
    left = [source * factor for factor in range(1, branches + 1)]
    right = [source + bias for bias in range(branches)]
    merged = [lhs - rhs for lhs, rhs in zip(left, right, strict=True)]
    sink = computed(sum)(merged)
    _ = sink.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            source.value = i
            checksum += sink.value
        return checksum

    return run


def make_animation_stack_runner(object_count: int = 12, updates: int = 1_500) -> ScenarioRunner:
    """Shared frame signal drives stacked animation chains across multiple objects.

    Models key3d's per-frame reactive update pass: one ``frame`` signal advances
    and every animated object must re-evaluate a stack of computed animation nodes
    (easing + interpolation) before the aggregate sink is read.  Each object has
    three stacked animations, giving a 73-node graph (12 × 3 ease + 12 × 3 apply
    + 1 sum) that is fully invalidated on every tick.
    """
    frame = Signal(0)
    clamp_ease = computed(lambda start, end, f: max(0.0, min(1.0, (f - start) / max(end - start, 1))))
    apply_step = computed(lambda value, ease, delta: value + ease * delta)

    leaves = []
    for i in range(object_count):
        v: Signal | Computed = Signal(float(i))
        for j in range(3):
            offset = i * 3 + j
            ease = clamp_ease(offset * 4, offset * 4 + 24, frame)
            v = apply_step(v, ease, float(j + 1))
        leaves.append(v)

    sink = computed(sum)(leaves)
    _ = sink.value

    def run() -> int:
        checksum = 0.0
        for i in range(updates):
            frame.value = i % 120
            checksum += sink.value
        return int(checksum)

    return run


def make_multi_input_computed_runner(updates: int = 5_000) -> ScenarioRunner:
    """One computed combining six reactive inputs that update at different rates.

    Models key3d's camera-orbit and object-transform computations where several
    independent signals (position components, radius, angles) feed a single
    computed node.  Different inputs update at different frequencies—horizontal
    every tick, vertical every 3rd, radius every 10th, position every 30th—so
    the computed is always stale but the dependency set never changes, stressing
    the lazy-recomputation path without subscription churn.
    """
    pos_x = Signal(0.0)
    pos_y = Signal(0.0)
    pos_z = Signal(5.0)
    radius = Signal(5.0)
    horizontal = Signal(0.0)
    vertical = Signal(0.3)

    result = computed(lambda x, y, z, r, h, v: x + y + z + r * h + r * v)(
        pos_x, pos_y, pos_z, radius, horizontal, vertical
    )
    _ = result.value

    def run() -> int:
        checksum = 0.0
        for i in range(updates):
            horizontal.value = (i % 60) * 0.01
            if i % 3 == 0:
                vertical.value = (i // 3 % 30) * 0.005
            if i % 10 == 0:
                radius.value = 5.0 + (i // 10 % 5)
            if i % 30 == 0:
                pos_x.value = float(i % 5)
            checksum += result.value
        return int(checksum)

    return run


def make_computed_signal_at_runner(updates: int = 3_000) -> ScenarioRunner:
    """Repeated scoped overrides through nested ``Signal.at()`` contexts."""
    left = Signal(1)
    right = Signal(2)
    bias = Signal(3)
    subtotal = left * 2 + right
    total = subtotal + bias * 3
    _ = total.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            with left.at(i), right.at(i + 1), bias.at(i & 7):
                checksum += total.value
        return checksum

    return run


def make_shared_clock_reads_runner(
    unit_count: int = 32,
    reads_per_update: int = 8,
    updates: int = 1_200,
) -> ScenarioRunner:
    """Invalidate many derived values from one shared source before repeated reads."""
    clock = Signal(0)
    bases = [Signal(i) for i in range(unit_count)]
    affine_step = computed(lambda value, scale, offset: value * scale + offset)
    mix_pair = computed(lambda left, right, bias: left + right + bias)

    leaves = []
    for index, base in enumerate(bases):
        staged = affine_step(clock, (index % 3) + 1, index)
        leaves.append(mix_pair(staged, base, index % 5))
    _ = [leaf.value for leaf in leaves]

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            clock.value = i
            bases[i % unit_count].value = i * 2
            start = (i * reads_per_update) % unit_count
            for offset in range(reads_per_update):
                checksum += leaves[(start + offset) % unit_count].value
        return checksum

    return run


def make_subscription_churn_runner(observer_count: int = 48, cycles: int = 250) -> ScenarioRunner:
    """Repeated subscribe and unsubscribe cycles to measure observer churn."""
    source = Signal(0)
    observers = [source + offset for offset in range(observer_count)]
    sink = computed(sum)(observers)
    _ = sink.value

    def run() -> int:
        checksum = 0
        for _ in range(cycles):
            for observer in observers:
                source.unsubscribe(observer)
            for observer in observers:
                source.subscribe(observer)
            source.value = source.value + 1
            checksum += sink.value
        return checksum

    return run


def make_dynamic_dependency_switch_runner(branch_count: int = 128, updates: int = 4_000) -> ScenarioRunner:
    """Switch dependencies every update to stress dynamic subscription reconciliation."""
    selector = Signal(0)
    branches = [Signal(i) for i in range(branch_count)]
    active_value = computed(lambda selected: branches[selected].value)
    active = active_value(selector)
    sink = active * 2 + selector
    _ = sink.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            idx = i % branch_count
            selector.value = idx
            branches[idx].value = i
            checksum += sink.value
        return checksum

    return run


def make_stacked_layers_runner(depth: int = 14, updates: int = 2_200) -> ScenarioRunner:
    """Build a long stack of derived values with repeated reads from the tail."""
    source = Signal(1)
    driver = Signal(0)
    affine_step = computed(lambda value, scale, offset: value * scale + offset)

    node = source
    for index in range(depth):
        step = affine_step(node, (index % 3) + 1, index)
        node = step + driver + (index % 7)

    tail = node - source
    summary = tail + driver + depth
    _ = summary.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            driver.value = i
            source.value = (i % 11) + 1
            checksum += summary.value
            checksum += tail.value
        return checksum

    return run


def make_scoped_context_reads_runner(updates: int = 2_200) -> ScenarioRunner:
    """Repeated scoped overrides with several dependent reads inside each scope."""
    left = Signal(1)
    right = Signal(2)
    selector = Signal(0)
    bias = Signal(3)
    affine_step = computed(lambda value, scale, offset: value * scale + offset)

    primary = left + right + 1
    selected = affine_step(selector, 3, 2)
    merged = primary + selected + 4
    total = merged + bias + 5
    _ = total.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            with selector.at(i), left.at(i + 1), right.at(i + 2), bias.at(i & 7):
                checksum += primary.value + merged.value + total.value
        return checksum

    return run


def make_shared_dependency_branches_runner(updates: int = 1_800) -> ScenarioRunner:
    """Several downstream branches share an intermediate subgraph."""
    left = Signal(1)
    right = Signal(2)
    selector = Signal(0)
    affine_step = computed(lambda value, scale, offset: value * scale + offset)

    shared = left + right + 3
    branch_a = affine_step(shared, 2, 1)
    branch_b = shared + selector + 2
    branch_c = branch_a - selector
    combined = branch_b + branch_c + 4
    _ = combined.value

    def run() -> int:
        checksum = 0
        for i in range(1, updates + 1):
            selector.value = i
            left.value = (i % 13) + 1
            right.value = (i % 17) + 2
            checksum += branch_b.value + branch_c.value + combined.value
        return checksum

    return run


def make_effect_fanout_runner(effect_count: int = 192, updates: int = 1_500) -> ScenarioRunner:
    """Many effects listening to one source, exercising eager fan-out update costs."""
    source = Signal(0)
    accumulator = [0]
    effects = [
        Effect(
            lambda source=source, offset=offset, accumulator=accumulator: accumulator.__setitem__(
                0,
                accumulator[0] + source.value + offset,
            )
        )
        for offset in range(effect_count)
    ]
    _ = len(effects)

    def run() -> int:
        baseline = accumulator[0]
        for i in range(1, updates + 1):
            source.value = i
        return accumulator[0] - baseline

    return run


def make_build_chain_runner(depth: int = 160) -> ScenarioRunner:
    """Construct a long chain each invocation."""

    def run() -> int:
        source = Signal(0)
        sink = source
        for _ in range(depth):
            sink = sink + 1
        return sink.value

    return run


def make_build_fanout_runner(fanout: int = 256) -> ScenarioRunner:
    """Construct a high fan-out graph each invocation."""

    def run() -> int:
        source = Signal(0)
        leaves = [source + offset for offset in range(fanout)]
        sink = computed(sum)(leaves)
        return sink.value

    return run


def make_build_diamond_runner(branches: int = 192) -> ScenarioRunner:
    """Construct a branch and merge graph each invocation."""

    def run() -> int:
        source = Signal(1)
        left = [source * factor for factor in range(1, branches + 1)]
        right = [source + bias for bias in range(branches)]
        merged = [lhs - rhs for lhs, rhs in zip(left, right, strict=True)]
        sink = computed(sum)(merged)
        return sink.value

    return run


STEADY_STATE_SCENARIOS: Final[tuple[ScenarioSpec, ...]] = (
    ScenarioSpec(
        name="signal_read_write",
        group="steady-state",
        description="Baseline cost of a single signal write followed by a read with no downstream computed nodes.",
        make_runner=make_signal_read_write_runner,
    ),
    ScenarioSpec(
        name="deep_chain_updates",
        group="steady-state",
        description="Write propagates through a long linear dependency chain; isolates per-level invalidation overhead.",
        make_runner=make_deep_chain_updates_runner,
    ),
    ScenarioSpec(
        name="fanout_updates",
        group="steady-state",
        description="One source write triggers re-evaluation of many independent leaf computeds and a single aggregate.",
        make_runner=make_fanout_updates_runner,
    ),
    ScenarioSpec(
        name="diamond_updates",
        group="steady-state",
        description="Two-level branching graph: source fans out to N parallel branches that re-merge; stresses shared-source scheduling.",
        make_runner=make_diamond_updates_runner,
    ),
    ScenarioSpec(
        name="animation_stack",
        group="steady-state",
        description="Shared frame signal drives three stacked animation computeds per object across 12 objects; models key3d's per-frame reactive update pass.",
        make_runner=make_animation_stack_runner,
    ),
    ScenarioSpec(
        name="multi_input_computed",
        group="steady-state",
        description="Single computed with six reactive inputs updating at different rates; models key3d camera-orbit and object-transform computations.",
        make_runner=make_multi_input_computed_runner,
    ),
    ScenarioSpec(
        name="computed_signal_at",
        group="steady-state",
        description="Repeated Signal.at() scoped overrides on a three-signal graph; isolates context-manager enter/exit overhead.",
        make_runner=make_computed_signal_at_runner,
    ),
    ScenarioSpec(
        name="shared_clock_reads",
        group="steady-state",
        description="Clock signal invalidates 32 derived affine-mix nodes before partial reads each tick; models a reactive rendering pass.",
        make_runner=make_shared_clock_reads_runner,
    ),
    ScenarioSpec(
        name="subscription_churn",
        group="steady-state",
        description="Rapid subscribe/unsubscribe cycles followed by a propagating write; measures observer-set mutation cost.",
        make_runner=make_subscription_churn_runner,
    ),
    ScenarioSpec(
        name="stacked_layers",
        group="steady-state",
        description="Two source signals drive a long affine-step chain; both the tail and a mid-point node are read each update.",
        make_runner=make_stacked_layers_runner,
    ),
    ScenarioSpec(
        name="scoped_context_reads",
        group="steady-state",
        description="Four signals overridden via Signal.at() with three downstream reads inside each scope; models key3d's frame-scoped snapshot evaluation.",
        make_runner=make_scoped_context_reads_runner,
    ),
    ScenarioSpec(
        name="dynamic_dependency_switch",
        group="steady-state",
        description="Conditional computed switches its active dependency every update; stresses per-update subscription reconciliation.",
        make_runner=make_dynamic_dependency_switch_runner,
    ),
    ScenarioSpec(
        name="shared_dependency_branches",
        group="steady-state",
        description="Three downstream branches share one intermediate computed subgraph; tests that the shared node is evaluated only once per update cycle.",
        make_runner=make_shared_dependency_branches_runner,
    ),
    ScenarioSpec(
        name="effect_fanout_updates",
        group="steady-state",
        description="Many Effects subscribe to one source and run eagerly on each write; measures Effect fan-out dispatch cost.",
        make_runner=make_effect_fanout_runner,
    ),
)

CONSTRUCTION_SCENARIOS: Final[tuple[ScenarioSpec, ...]] = (
    ScenarioSpec(
        name="build_deep_chain",
        group="construction",
        description="Graph construction cost for a deep chain.",
        make_runner=make_build_chain_runner,
    ),
    ScenarioSpec(
        name="build_fanout_graph",
        group="construction",
        description="Graph construction cost for a wide fan-out.",
        make_runner=make_build_fanout_runner,
    ),
    ScenarioSpec(
        name="build_diamond_graph",
        group="construction",
        description="Graph construction cost for a branch and merge topology.",
        make_runner=make_build_diamond_runner,
    ),
)

ALL_SCENARIOS: Final[tuple[ScenarioSpec, ...]] = (*STEADY_STATE_SCENARIOS, *CONSTRUCTION_SCENARIOS)
SCENARIOS_BY_NAME: Final[dict[str, ScenarioSpec]] = {scenario.name: scenario for scenario in ALL_SCENARIOS}


def get_scenarios(group: str = "all") -> tuple[ScenarioSpec, ...]:
    """Return scenario specs by group."""
    if group == "steady-state":
        return STEADY_STATE_SCENARIOS
    if group == "construction":
        return CONSTRUCTION_SCENARIOS
    if group == "all":
        return ALL_SCENARIOS
    raise ValueError(f"Unknown benchmark group: {group}")

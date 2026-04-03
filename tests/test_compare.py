from __future__ import annotations

from dataclasses import dataclass

from signified_bench.compare import (
    COMPARE_BACKENDS_BY_NAME,
    COMPARE_CONSTRUCTION_SCENARIOS,
    COMPARE_SCENARIOS_BY_NAME,
    COMPARE_STEADY_STATE_SCENARIOS,
    ReactiveNode,
    get_compare_backends,
    get_compare_scenarios,
)


@dataclass
class _FakeSignal:
    value: int | float


@dataclass
class _FakeComputed:
    func: object
    deps: tuple[object, ...]


class _FakeBackend:
    name = "fake"

    def signal(self, value: int | float) -> ReactiveNode:
        return ReactiveNode(_FakeSignal(value))

    def computed(self, func, *deps) -> ReactiveNode:
        return ReactiveNode(_FakeComputed(func, deps))

    def effect(self, func, *deps):
        return (func, deps)

    def get(self, node: ReactiveNode):
        handle = node.handle
        if isinstance(handle, _FakeSignal):
            return handle.value
        return handle.func(*[self.get(dep) if isinstance(dep, ReactiveNode) else dep for dep in handle.deps])

    def set(self, node: ReactiveNode, value):
        node.handle.value = value


def test_get_compare_scenarios_exposes_both_groups() -> None:
    assert get_compare_scenarios("steady-state") == COMPARE_STEADY_STATE_SCENARIOS
    assert get_compare_scenarios("construction") == COMPARE_CONSTRUCTION_SCENARIOS
    assert len(get_compare_scenarios("all")) == len(COMPARE_STEADY_STATE_SCENARIOS) + len(COMPARE_CONSTRUCTION_SCENARIOS)


def test_get_compare_backends_can_filter_by_name() -> None:
    backends = get_compare_backends(["signified", "param"])

    assert [backend.name for backend in backends] == ["signified", "param"]


def test_compare_registry_contains_requested_backends_and_scenarios() -> None:
    assert {"signified", "reaktiv", "signals", "param"} <= set(COMPARE_BACKENDS_BY_NAME)
    assert {"signal_read_write", "shared_clock_reads", "build_diamond_graph"} <= set(COMPARE_SCENARIOS_BY_NAME)


def test_compare_signal_read_write_runner_returns_int() -> None:
    backend = _FakeBackend()
    runner = COMPARE_SCENARIOS_BY_NAME["signal_read_write"].make_runner(backend)

    assert isinstance(runner(), int)


def test_compare_build_deep_chain_runner_returns_int() -> None:
    backend = _FakeBackend()
    runner = COMPARE_SCENARIOS_BY_NAME["build_deep_chain"].make_runner(backend)

    assert isinstance(runner(), int)

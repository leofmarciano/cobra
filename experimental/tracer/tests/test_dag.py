"""Dependency DAG builder tests for the disposable tracer (S03-T2).

Synthetic event streams verify that the builder connects events by value
identity, orders mutating producers, and conservatively fences unknown-effect
(opaque) nodes against their neighbors.
"""

from __future__ import annotations

from tracer.dag import build_dag, to_dot, to_json
from tracer.events import Event


def _ev(
    id: int,
    kind: str,
    op: str,
    inputs: tuple[str, ...] = (),
    outputs: tuple[str, ...] = (),
) -> Event:
    return Event(
        id=id,
        kind=kind,  # type: ignore[arg-type]
        op=op,
        args_summary="",
        input_handles=inputs,
        output_handles=outputs,
    )


def _edges(dag: dict) -> set[tuple[int, int, str]]:
    return {(e["from"], e["to"], e["kind"]) for e in dag["edges"]}


def test_chain_produces_single_data_edge() -> None:
    events = [
        _ev(0, "torch", "torch.relu", outputs=("tensor:0",)),
        _ev(1, "torch", "torch.mean", inputs=("tensor:0",), outputs=("tensor:1",)),
    ]
    dag = build_dag(events)
    assert len(dag["nodes"]) == 2
    assert _edges(dag) == {(0, 1, "data")}


def test_fan_out_fan_in() -> None:
    events = [
        _ev(0, "torch", "input", outputs=("tensor:0",)),
        _ev(1, "torch", "branch_a", inputs=("tensor:0",), outputs=("tensor:1",)),
        _ev(2, "torch", "branch_b", inputs=("tensor:0",), outputs=("tensor:2",)),
        _ev(3, "torch", "add", inputs=("tensor:1", "tensor:2"), outputs=("tensor:3",)),
    ]
    dag = build_dag(events)
    assert _edges(dag) == {
        (0, 1, "data"),
        (0, 2, "data"),
        (1, 3, "data"),
        (2, 3, "data"),
    }


def test_mutation_forces_ordering_between_producers() -> None:
    events = [
        _ev(0, "torch", "torch.randn", outputs=("tensor:0",)),
        _ev(1, "torch", "torch.add_", outputs=("tensor:0",)),
        _ev(2, "torch", "torch.mean", inputs=("tensor:0",), outputs=("tensor:1",)),
    ]
    dag = build_dag(events)
    assert _edges(dag) == {
        (0, 1, "order"),
        (1, 2, "data"),
    }


def test_mutation_waits_for_intervening_reader() -> None:
    events = [
        _ev(0, "torch", "produce", outputs=("tensor:0",)),
        _ev(1, "torch", "read", inputs=("tensor:0",), outputs=("tensor:1",)),
        _ev(2, "torch", "mutate_", inputs=("tensor:0",), outputs=("tensor:0",)),
    ]

    edges = _edges(build_dag(events))

    assert (0, 1, "data") in edges
    assert (1, 2, "order") in edges


def test_opaque_node_gets_ordering_edges_to_neighbors() -> None:
    # Pure side-effect opaque nodes with no data dependencies to/from their
    # neighbors: only program-order edges should connect them.
    events = [
        _ev(0, "opaque", "opaque:load_config", outputs=("opaque:cfg",)),
        _ev(1, "torch", "torch.relu", inputs=("tensor:0",), outputs=("tensor:1",)),
        _ev(2, "opaque", "opaque:log_metric"),
    ]
    dag = build_dag(events)
    edges = _edges(dag)
    assert (0, 1, "order") in edges
    assert (1, 2, "order") in edges


def test_isolated_nodes_are_roots_and_leaves() -> None:
    events = [
        _ev(0, "torch", "torch.randn", outputs=("tensor:0",)),
        _ev(1, "torch", "torch.randn", outputs=("tensor:1",)),
    ]
    dag = build_dag(events)
    assert _edges(dag) == set()
    assert dag["roots"] == [0, 1]
    assert dag["leaves"] == [0, 1]


def test_json_roundtrip_preserves_dag() -> None:
    events = [
        _ev(0, "torch", "torch.relu", outputs=("tensor:0",)),
        _ev(1, "torch", "torch.mean", inputs=("tensor:0",), outputs=("tensor:1",)),
    ]
    dag = build_dag(events)
    json_str = to_json(dag)
    assert '"nodes"' in json_str
    assert '"edges"' in json_str
    assert '"from": 0' in json_str
    assert '"to": 1' in json_str
    assert '"kind": "data"' in json_str


def test_dot_contains_expected_nodes_and_edges() -> None:
    events = [
        _ev(0, "torch", "torch.relu", outputs=("tensor:0",)),
        _ev(1, "torch", "torch.mean", inputs=("tensor:0",), outputs=("tensor:1",)),
    ]
    dag = build_dag(events)
    dot = to_dot(dag)
    assert "digraph" in dot
    assert 'label="torch.relu' in dot
    assert 'label="torch.mean' in dot
    assert "0 -> 1" in dot

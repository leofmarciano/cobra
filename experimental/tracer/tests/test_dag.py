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


def test_read_only_alias_does_not_become_storage_producer() -> None:
    events = [
        _ev(0, "torch", "produce", outputs=("tensor:0",)),
        _ev(1, "torch", "view", inputs=("tensor:0",), outputs=("tensor:0",)),
        _ev(2, "torch", "read", inputs=("tensor:0",), outputs=("tensor:1",)),
    ]

    edges = _edges(build_dag(events))

    assert (0, 1, "data") in edges
    assert (0, 2, "data") in edges
    assert (1, 2, "data") not in edges
    assert (1, 2, "order") not in edges


def test_logical_view_lineage_orders_view_consumer() -> None:
    events = [
        Event(
            id=0,
            kind="torch",
            op="torch.zeros",
            args_summary="",
            output_handles=("storage:0",),
            metadata={"logical_output_handles": ["logical:0"]},
        ),
        Event(
            id=1,
            kind="torch",
            op="torch.Tensor.permute",
            args_summary="",
            input_handles=("storage:0",),
            output_handles=("storage:0",),
            metadata={
                "logical_input_handles": ["logical:0"],
                "logical_output_handles": ["logical:view"],
            },
        ),
        Event(
            id=2,
            kind="torch",
            op="torch.Tensor.to",
            args_summary="",
            input_handles=("storage:0",),
            output_handles=("storage:1",),
            metadata={
                "logical_input_handles": ["logical:view"],
                "logical_output_handles": ["logical:1"],
            },
        ),
    ]

    edges = _edges(build_dag(events))

    assert (0, 1, "data") in edges
    assert (1, 2, "data") in edges


def test_descriptor_attribute_read_does_not_advance_storage_producer() -> None:
    events = [
        _ev(0, "torch", "torch.zeros", outputs=("tensor:0",)),
        _ev(
            1,
            "torch",
            "torch.getset_descriptor.__get__",
            inputs=("tensor:0",),
            outputs=("tensor:0",),
        ),
        _ev(2, "torch", "torch.mean", inputs=("tensor:0",), outputs=("tensor:1",)),
    ]

    edges = _edges(build_dag(events))

    assert (0, 1, "data") in edges
    assert (0, 2, "data") in edges
    assert (1, 2, "order") not in edges


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


def test_opaque_node_fences_all_live_branches() -> None:
    events = [
        _ev(0, "torch", "before_a", outputs=("tensor:a",)),
        _ev(1, "torch", "before_b", outputs=("tensor:b",)),
        _ev(2, "opaque", "opaque:unknown"),
        _ev(3, "torch", "after_a", inputs=("tensor:a",), outputs=("tensor:a2",)),
        _ev(4, "torch", "after_b", inputs=("tensor:b",), outputs=("tensor:b2",)),
    ]

    edges = _edges(build_dag(events))

    assert (0, 2, "order") in edges
    assert (1, 2, "order") in edges
    assert (2, 3, "order") in edges
    assert (2, 4, "order") in edges


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

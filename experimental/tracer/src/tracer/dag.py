"""Dependency DAG builder for the disposable tracer (S03-T2).

Takes the flat ``Event`` stream produced by ``tracer.session`` and builds a
directed acyclic graph by value identity:

* **data edges** connect the last producer of a handle to a consumer.
* **order edges** connect successive producers of the same handle, modeling
  mutations that reuse a storage identity (``x.add_(...)``).
* **order edges** fence every unknown-effect (``opaque``) node against the
  live predecessor and successor frontiers, matching §6.3's conservative
  treatment of graph breaks.

The resulting graph is exported as JSON (for S10's later IR lowering) and as
Graphviz DOT (for human review).
"""

from __future__ import annotations

import json
import textwrap
from collections.abc import Iterable
from typing import Any

from tracer.events import Event


def build_dag(events: Iterable[Event]) -> dict[str, Any]:
    """Build a dependency DAG from a recorded event stream.

    Args:
        events: Program-ordered ``Event`` records. ``event.id`` is used as the
            stable node id and is assumed to be monotonically increasing.

    Returns:
        A dict with ``nodes``, ``edges``, ``roots`` (no incoming edges),
        and ``leaves`` (no outgoing edges).
    """
    events = list(events)
    nodes = [_node_from_event(e) for e in events]
    edges: set[tuple[int, int, str]] = set()
    last_producer: dict[str, int] = {}
    readers_since_write: dict[str, set[int]] = {}

    for event in events:
        eid = event.id
        for handle in event.input_handles:
            producer = last_producer.get(handle)
            if producer is not None and producer != eid:
                edges.add((producer, eid, "data"))
            readers_since_write.setdefault(handle, set()).add(eid)

        mutates_inputs = _event_mutates_inputs(event)
        for handle in event.output_handles:
            # Storage identity is shared by read-only views (view/reshape/
            # permute/detach and their equivalents). Those operations consume
            # a value but do not replace its producer. In-place operations are
            # marked by the adapter (or inferred from the conventional
            # trailing-underscore name) and still advance the producer chain.
            if handle in event.input_handles and not mutates_inputs:
                continue
            previous = last_producer.get(handle)
            if previous is not None and previous != eid:
                edges.add((previous, eid, "order"))
            for reader in readers_since_write.get(handle, set()):
                if reader != eid:
                    edges.add((reader, eid, "order"))
            last_producer[handle] = eid
            readers_since_write.pop(handle, None)

    _add_opaque_ordering_edges(events, edges)

    incoming: set[int] = set()
    outgoing: set[int] = set()
    edge_list = []
    for src, dst, kind in sorted(edges):
        edge_list.append({"from": src, "to": dst, "kind": kind})
        incoming.add(dst)
        outgoing.add(src)

    all_ids = [e.id for e in events]
    roots = sorted(i for i in all_ids if i not in incoming)
    leaves = sorted(i for i in all_ids if i not in outgoing)

    return {
        "nodes": nodes,
        "edges": edge_list,
        "roots": roots,
        "leaves": leaves,
    }


def _node_from_event(event: Event) -> dict[str, Any]:
    return {
        "id": event.id,
        "kind": event.kind,
        "op": event.op,
        "args_summary": event.args_summary,
        "metadata": event.metadata,
        "duration_ns": event.duration_ns,
        "thread_id": event.thread_id,
        "source": event.source,
    }


def _event_mutates_inputs(event: Event) -> bool:
    """Return whether an event writes storage already present in its inputs.

    Adapters set ``metadata['mutates_inputs']`` when they know the operation's
    semantics. The name fallback keeps synthetic/manual events useful and
    covers the conventional in-place Python/Torch spelling (``add_`` and
    ``__setitem__``).
    """
    explicit = event.metadata.get("mutates_inputs")
    if isinstance(explicit, bool):
        return explicit
    operation = event.op.rsplit(".", 1)[-1]
    if operation in {"__setitem__", "__delitem__"}:
        return True
    return operation.endswith("_") and not operation.startswith("__")


def _add_opaque_ordering_edges(events: list[Event], edges: set[tuple[int, int, str]]) -> None:
    """Fence opaque nodes against every live program-order frontier.

    An ``opaque`` node is never assumed independent of surrounding code. An
    immediate-neighbor edge is insufficient when two independent branches
    meet the opaque call, because one branch can otherwise remain unordered.
    Connect every leaf in the prefix to the opaque node and the opaque node to
    every root in the suffix. This is the smallest conservative frontier for
    the partial dependency graph available at this stage.
    """
    if not events:
        return
    for idx, event in enumerate(events):
        if event.kind != "opaque":
            continue
        prefix_ids = {candidate.id for candidate in events[:idx]}
        suffix_ids = {candidate.id for candidate in events[idx + 1 :]}
        prefix_leaves = _frontier_ids(prefix_ids, edges, leaves=True)
        suffix_roots = _frontier_ids(suffix_ids, edges, leaves=False)
        for predecessor in prefix_leaves:
            edges.add((predecessor, event.id, "order"))
        for successor in suffix_roots:
            edges.add((event.id, successor, "order"))


def _frontier_ids(
    node_ids: set[int],
    edges: set[tuple[int, int, str]],
    *,
    leaves: bool,
) -> list[int]:
    """Return leaves or roots of ``node_ids`` using the current graph edges."""
    if not node_ids:
        return []
    linked = {
        (src if leaves else dst) for src, dst, _kind in edges if src in node_ids and dst in node_ids
    }
    return sorted(node_ids - linked)


def to_json(dag: dict[str, Any], *, indent: int | None = 2) -> str:
    """Serialize a DAG to JSON."""
    return json.dumps(dag, indent=indent, sort_keys=True)


def to_dot(dag: dict[str, Any], *, label_by: str = "op") -> str:
    """Render a DAG as a Graphviz DOT string.

    Args:
        dag: DAG produced by ``build_dag``.
        label_by: Node attribute to use in the visible label (default ``op``).
    """
    lines = ["digraph cobra_trace {"]
    lines.append("  rankdir=LR;")

    for node in dag["nodes"]:
        nid = node["id"]
        label = _dot_label(str(node.get(label_by, nid)))
        kind = node.get("kind", "unknown")
        shape = "box"
        if kind == "opaque":
            shape = "octagon"
        elif kind == "pandas":
            shape = "cylinder"
        elif kind == "numpy":
            shape = "ellipse"
        lines.append(f'  {nid} [label="{label}" shape={shape}];')

    for edge in dag["edges"]:
        style = "dashed" if edge["kind"] == "order" else "solid"
        lines.append(f"  {edge['from']} -> {edge['to']} [style={style}];")

    lines.append("}")
    return "\n".join(lines)


def _dot_label(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return textwrap.shorten(escaped, width=80, placeholder="...")

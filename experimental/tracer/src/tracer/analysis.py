"""Critical-path and available-parallelism analysis for the disposable tracer (S03-T3).

Computes:

* total recorded work and the longest dependency path (span).
* theoretical speedup (work / span).
* the top contributors on the critical path.
* host/device transfer boundaries inferred from op names and metadata.
* a coarse device residency timeline.
* candidate parallel regions: fork/join subgraphs where multiple branches
  have no ordering dependencies between them.

All times are in nanoseconds and are based on the wall-clock durations recorded
by the tracer, so they reflect observed eager Python execution rather than a
perfect schedule.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def analyze(dag: dict[str, Any]) -> dict[str, Any]:
    """Return a dict of derived metrics and observations for ``dag``.

    Args:
        dag: DAG produced by ``tracer.dag.build_dag``.

    Returns:
        A dict with ``total_work_ns``, ``critical_path_ns``,
        ``max_speedup``, ``critical_path_node_ids``, ``top5_critical_ops``,
        ``transfer_boundaries``, ``transfer_count_estimate``,
        ``device_timeline``, and ``parallel_regions``.
    """
    nodes = dag["nodes"]
    node_map = {n["id"]: n for n in nodes}
    preds, succs = _build_adjacency(dag["edges"])
    topo = _topo_sort(nodes, preds, succs)

    total_work_ns = sum(int(n["duration_ns"]) for n in nodes)
    critical_path_ns, critical_path_node_ids = _longest_path(node_map, preds, succs, topo)

    max_speedup = total_work_ns / critical_path_ns if critical_path_ns > 0 else 1.0

    top5 = _top_critical_ops(node_map, critical_path_node_ids, limit=5)
    transfers = _detect_transfers(nodes)
    device_timeline = _device_timeline(nodes)

    return {
        "total_work_ns": total_work_ns,
        "critical_path_ns": critical_path_ns,
        "max_speedup": max_speedup,
        "critical_path_node_ids": critical_path_node_ids,
        "top5_critical_ops": top5,
        "transfer_boundaries": transfers,
        "transfer_count_estimate": len(transfers),
        "device_timeline": device_timeline,
        "parallel_regions": _find_parallel_regions(dag, node_map, preds, succs),
    }


def _build_adjacency(
    edges: list[dict[str, Any]],
) -> tuple[dict[int, set[int]], dict[int, set[int]]]:
    preds: dict[int, set[int]] = defaultdict(set)
    succs: dict[int, set[int]] = defaultdict(set)
    for edge in edges:
        src = int(edge["from"])
        dst = int(edge["to"])
        preds[dst].add(src)
        succs[src].add(dst)
    return preds, succs


def _topo_sort(
    nodes: list[dict[str, Any]],
    preds: dict[int, set[int]],
    succs: dict[int, set[int]],
) -> list[int]:
    in_degree = {n["id"]: len(preds[n["id"]]) for n in nodes}
    queue = deque(nid for nid in in_degree if in_degree[nid] == 0)
    order: list[int] = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for s in succs[nid]:
            in_degree[s] -= 1
            if in_degree[s] == 0:
                queue.append(s)
    if len(order) != len(nodes):
        raise ValueError("DAG contains a cycle")
    return order


def _longest_path(
    node_map: dict[int, dict[str, Any]],
    preds: dict[int, set[int]],
    succs: dict[int, set[int]],
    topo: list[int],
) -> tuple[int, list[int]]:
    """Return (span_ns, node_ids_on_the_path)."""
    dist = {nid: int(node_map[nid]["duration_ns"]) for nid in topo}
    prev: dict[int, int | None] = dict.fromkeys(topo, None)

    for nid in topo:
        base = dist[nid]
        for s in succs[nid]:
            candidate = base + int(node_map[s]["duration_ns"])
            if candidate > dist[s]:
                dist[s] = candidate
                prev[s] = nid

    end = max(dist, key=dist.get)
    path: list[int] = []
    cur: int | None = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return dist[end], path


def _top_critical_ops(
    node_map: dict[int, dict[str, Any]],
    path_ids: list[int],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    items = [
        {
            "rank": 0,
            "id": nid,
            "op": node_map[nid]["op"],
            "duration_ns": int(node_map[nid]["duration_ns"]),
            "pct_of_span": 0.0,
        }
        for nid in path_ids
    ]
    items.sort(key=lambda x: x["duration_ns"], reverse=True)
    span = sum(it["duration_ns"] for it in items) or 1
    for idx, it in enumerate(items[:limit], start=1):
        it["rank"] = idx
        it["pct_of_span"] = round(100.0 * it["duration_ns"] / span, 2)
    return items[:limit]


def _detect_transfers(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify events that look like host/device data movement.

    Heuristics used:
    * explicit ``torch.Tensor.to`` / ``.cpu`` / ``.cuda`` calls.
    * ``torch.from_numpy`` (NumPy CPU array -> torch tensor).
    * ``torch.Tensor.numpy`` (torch tensor -> NumPy CPU array).
    """
    transfers: list[dict[str, Any]] = []
    for node in nodes:
        op = node.get("op", "")
        if not _is_transfer_op(op):
            continue
        meta = node.get("metadata", {})
        inputs = meta.get("inputs") or []
        output = meta.get("output") or {}
        source = _device_of(inputs[0]) if inputs else "host"
        target = _device_of(output) or source
        if not _looks_like_device_change(source, target):
            continue
        transfers.append(
            {
                "id": node["id"],
                "op": op,
                "source": source,
                "target": target,
                "duration_ns": int(node["duration_ns"]),
            }
        )
    return transfers


def _is_transfer_op(op: str) -> bool:
    return any(op.endswith(suffix) for suffix in (".to", ".cpu", ".cuda", "from_numpy", "numpy"))


def _device_of(desc: Any) -> str:
    """Best-effort device extraction from a metadata descriptor."""
    if isinstance(desc, list):
        for d in desc:
            dev = _device_of(d)
            if dev != "host":
                return dev
        return "host"
    if not isinstance(desc, dict):
        return "host"
    kind = desc.get("kind")
    if kind == "tensor":
        return str(desc.get("device", "cpu"))
    if kind == "ndarray":
        return str(desc.get("device", "cpu"))
    return "host"


def _looks_like_device_change(source: str, target: str) -> bool:
    if source == target:
        return False
    # Count as a host/device transfer only when one side is a GPU device.
    source_gpu = "cuda" in source
    target_gpu = "cuda" in target
    return source_gpu or target_gpu


def _device_timeline(
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a list of coarse (node_id, op, device) residency markers.

    Only nodes that *produce* a tracked tensor/dataframe/ndarray value are
    considered, because those are the points where a live value changes
    residency.  ``host`` and ``cpu`` are treated as the same CPU residency
    bucket; any ``cuda:*`` device becomes ``GPU``.  Only the first event at a
    device boundary is recorded, so the timeline reflects phases rather than
    every single internal op.
    """
    timeline: list[dict[str, Any]] = []
    current: str | None = None
    for node in nodes:
        meta = node.get("metadata", {})
        output = meta.get("output")
        if not _is_tracked_value(output):
            continue
        device = _device_of(output)
        bucket = "GPU" if "cuda" in device else "CPU"
        if bucket != current:
            timeline.append({"id": node["id"], "op": node["op"], "device": bucket})
            current = bucket
    return timeline


def _is_tracked_value(desc: Any) -> bool:
    """True when ``desc`` is a metadata descriptor for a tensor/dataframe/ndarray."""
    return isinstance(desc, dict) and desc.get("kind") in {
        "tensor",
        "dataframe",
        "series",
        "ndarray",
    }


def _find_parallel_regions(
    dag: dict[str, Any],
    node_map: dict[int, dict[str, Any]],
    preds: dict[int, set[int]],
    succs: dict[int, set[int]],
) -> list[dict[str, Any]]:
    """Find fork/join subgraphs where multiple branches are mutually independent.

    A candidate region is identified by:
    * a fork node with at least two data-dependent children,
    * those children are not ordered with respect to each other,
    * they share a common descendant that acts as a join.

    The reported ``span_ns`` is the sum of durations of all nodes between the
    fork and join (inclusive), and ``parallelizable_ns`` estimates the work
    that could overlap (total exclusive branch work minus the longest branch).
    """
    data_edges = [e for e in dag["edges"] if e["kind"] == "data"]
    data_succs: dict[int, list[int]] = defaultdict(list)
    for e in data_edges:
        data_succs[int(e["from"])].append(int(e["to"]))

    regions: list[dict[str, Any]] = []
    seen: set[tuple[int, int, frozenset[int]]] = set()
    reachable_cache: dict[int, set[int]] = {}
    for fork_id, children in data_succs.items():
        if len(children) < 2:
            continue

        # Consider every unordered pair of data children as a potential
        # parallel branch pair.  This avoids discarding a valid fork just
        # because one of its children is a short side chain.
        for i, c1 in enumerate(children):
            reach1 = _reachable_cached(c1, succs, reachable_cache)
            for c2 in children[i + 1 :]:
                if c1 == c2 or c2 in reach1 or c1 in _reachable_cached(c2, succs, reachable_cache):
                    continue
                joins = _minimal_common_descendants([c1, c2], succs, reachable_cache)
                for join_id in joins:
                    key = (fork_id, join_id, frozenset([c1, c2]))
                    if key in seen:
                        continue
                    seen.add(key)
                    between = _nodes_between(fork_id, join_id, succs, preds, reachable_cache)
                    branch1 = set(_nodes_between(c1, join_id, succs, preds, reachable_cache)) - {
                        join_id
                    }
                    branch2 = set(_nodes_between(c2, join_id, succs, preds, reachable_cache)) - {
                        join_id
                    }
                    shared = branch1 & branch2
                    branch1 -= shared
                    branch2 -= shared
                    branch_work = [
                        sum(int(node_map[nid]["duration_ns"]) for nid in branch1),
                        sum(int(node_map[nid]["duration_ns"]) for nid in branch2),
                    ]
                    regions.append(
                        {
                            "fork_id": fork_id,
                            "fork_op": node_map[fork_id]["op"],
                            "join_id": join_id,
                            "join_op": node_map[join_id]["op"],
                            "branch_ids": [c1, c2],
                            "nodes": between,
                            "span_ns": sum(int(node_map[nid]["duration_ns"]) for nid in between),
                            "parallelizable_ns": sum(branch_work) - max(branch_work, default=0),
                        }
                    )

    # Prefer the most valuable regions first.
    regions.sort(key=lambda r: r["parallelizable_ns"], reverse=True)
    return regions


def _reachable(start: int, succs: dict[int, set[int]]) -> set[int]:
    seen: set[int] = set()
    stack = [start]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(s for s in succs[nid] if s not in seen)
    return seen


def _reachable_cached(
    start: int,
    succs: dict[int, set[int]],
    cache: dict[int, set[int]],
) -> set[int]:
    """Return reachability for ``start``, computing it at most once."""
    if start not in cache:
        cache[start] = _reachable(start, succs)
    return cache[start]


def _minimal_common_descendants(
    sources: list[int],
    succs: dict[int, set[int]],
    reachable_cache: dict[int, set[int]] | None = None,
) -> list[int]:
    """Return earliest common descendants in the graph."""
    cache = {} if reachable_cache is None else reachable_cache
    reachable_sets = [_reachable_cached(s, succs, cache) for s in sources]
    common = set.intersection(*reachable_sets) if reachable_sets else set()
    nonminimal: set[int] = set()
    for other in common:
        nonminimal.update((_reachable_cached(other, succs, cache) - {other}) & common)
    return sorted(common - nonminimal)


def _nodes_between(
    start: int,
    end: int,
    succs: dict[int, set[int]],
    preds: dict[int, set[int]],
    reachable_cache: dict[int, set[int]] | None = None,
) -> list[int]:
    """All nodes that lie on a path from ``start`` to ``end`` (inclusive)."""
    if start == end:
        return [start]
    cache = {} if reachable_cache is None else reachable_cache
    forward = _reachable_cached(start, succs, cache)
    if end not in forward:
        return []
    backward: set[int] = {end}
    stack = [end]
    while stack:
        nid = stack.pop()
        for p in preds[nid]:
            if p in forward and p not in backward:
                backward.add(p)
                stack.append(p)
    return sorted(backward)

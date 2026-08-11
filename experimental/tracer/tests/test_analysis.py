"""Critical-path / parallelism analyzer tests for the disposable tracer (S03-T3)."""

from __future__ import annotations

import tracer.analysis as analysis_module
from tracer.analysis import analyze
from tracer.dag import build_dag
from tracer.events import Event


def _ev(
    id: int,
    kind: str,
    op: str,
    inputs: tuple[str, ...] = (),
    outputs: tuple[str, ...] = (),
    duration_ns: int = 1,
) -> Event:
    return Event(
        id=id,
        kind=kind,  # type: ignore[arg-type]
        op=op,
        args_summary="",
        input_handles=inputs,
        output_handles=outputs,
        start_ns=0,
        end_ns=duration_ns,
    )


def test_chain_critical_path_is_sum() -> None:
    events = [
        _ev(0, "torch", "input", outputs=("t:0",), duration_ns=5),
        _ev(1, "torch", "relu", inputs=("t:0",), outputs=("t:1",), duration_ns=10),
        _ev(2, "torch", "mean", inputs=("t:1",), outputs=("t:2",), duration_ns=3),
    ]
    result = analyze(build_dag(events))
    assert result["total_work_ns"] == 18
    assert result["critical_path_ns"] == 18
    assert result["max_speedup"] == 1.0
    assert result["critical_path_node_ids"] == [0, 1, 2]


def test_fan_out_fan_in_speedup() -> None:
    events = [
        _ev(0, "torch", "input", outputs=("t:0",), duration_ns=5),
        _ev(1, "torch", "a", inputs=("t:0",), outputs=("t:1",), duration_ns=20),
        _ev(2, "torch", "b", inputs=("t:0",), outputs=("t:2",), duration_ns=15),
        _ev(3, "torch", "add", inputs=("t:1", "t:2"), outputs=("t:3",), duration_ns=2),
    ]
    result = analyze(build_dag(events))
    assert result["total_work_ns"] == 42
    # longest path is input(5) + a(20) + add(2) = 27
    assert result["critical_path_ns"] == 27
    assert round(result["max_speedup"], 2) == round(42 / 27, 2)
    assert result["top5_critical_ops"][0]["op"] == "a"


def test_top5_ops_sorted_by_duration() -> None:
    events = [
        _ev(0, "torch", "tiny", outputs=("t:0",), duration_ns=1),
        _ev(1, "torch", "huge", inputs=("t:0",), outputs=("t:1",), duration_ns=100),
        _ev(2, "torch", "medium", inputs=("t:1",), outputs=("t:2",), duration_ns=10),
    ]
    result = analyze(build_dag(events))
    tops = result["top5_critical_ops"]
    assert len(tops) == 3
    assert tops[0]["op"] == "huge"
    assert abs(tops[0]["pct_of_span"] - (100.0 * 100 / 111)) < 0.01


def test_detects_torch_to_transfer() -> None:
    events = [
        Event(
            id=0,
            kind="torch",
            op="torch.Tensor.to",
            args_summary="",
            input_handles=("t:0",),
            output_handles=("t:1",),
            start_ns=0,
            end_ns=5,
            metadata={
                "inputs": [{"kind": "tensor", "device": "cpu"}],
                "output": {"kind": "tensor", "device": "cuda:0"},
            },
        ),
    ]
    result = analyze(build_dag(events))
    assert result["transfer_count_estimate"] == 1
    assert result["transfer_boundaries"][0]["op"] == "torch.Tensor.to"
    assert result["transfer_boundaries"][0]["source"] == "cpu"
    assert result["transfer_boundaries"][0]["target"] == "cuda:0"


def test_detects_device_change_in_metadata() -> None:
    # Only explicit transfer op names should be flagged, not arbitrary
    # torch ops whose input/output devices happen to differ.
    events = [
        Event(
            id=0,
            kind="torch",
            op="torch.relu",
            args_summary="",
            input_handles=("t:0",),
            output_handles=("t:1",),
            start_ns=0,
            end_ns=4,
            metadata={
                "inputs": [{"kind": "tensor", "device": "cpu"}],
                "output": {"kind": "tensor", "device": "cuda:0"},
            },
        ),
        Event(
            id=1,
            kind="torch",
            op="torch.Tensor.to",
            args_summary="",
            input_handles=("t:1",),
            output_handles=("t:2",),
            start_ns=0,
            end_ns=2,
            metadata={
                "inputs": [{"kind": "tensor", "device": "cpu"}],
                "output": {"kind": "tensor", "device": "cuda:0"},
            },
        ),
    ]
    result = analyze(build_dag(events))
    assert result["transfer_count_estimate"] == 1
    assert result["transfer_boundaries"][0]["source"] == "cpu"
    assert result["transfer_boundaries"][0]["target"] == "cuda:0"


def test_parallel_region_found_for_independent_branches() -> None:
    events = [
        _ev(0, "torch", "input", outputs=("t:0",), duration_ns=5),
        _ev(1, "torch", "branch_a", inputs=("t:0",), outputs=("t:1",), duration_ns=20),
        _ev(2, "torch", "branch_b", inputs=("t:0",), outputs=("t:2",), duration_ns=15),
        _ev(3, "torch", "add", inputs=("t:1", "t:2"), outputs=("t:3",), duration_ns=2),
    ]
    result = analyze(build_dag(events))
    regions = result["parallel_regions"]
    assert len(regions) == 1
    region = regions[0]
    assert region["fork_op"] == "input"
    assert region["join_op"] == "add"
    assert sorted(region["branch_ids"]) == [1, 2]
    assert region["parallelizable_ns"] == 15  # min(a,b) saved if overlapped


def test_parallel_region_uses_earliest_common_join() -> None:
    events = [
        _ev(0, "torch", "input", outputs=("t:0",), duration_ns=5),
        _ev(1, "torch", "branch_a", inputs=("t:0",), outputs=("t:1",), duration_ns=20),
        _ev(2, "torch", "branch_b", inputs=("t:0",), outputs=("t:2",), duration_ns=15),
        _ev(3, "torch", "add", inputs=("t:1", "t:2"), outputs=("t:3",), duration_ns=2),
        _ev(4, "torch", "summary", inputs=("t:3",), outputs=("t:4",), duration_ns=7),
    ]

    regions = analyze(build_dag(events))["parallel_regions"]

    assert len(regions) == 1
    assert regions[0]["join_op"] == "add"
    assert regions[0]["nodes"] == [0, 1, 2, 3]


def test_parallelizable_work_is_summed_per_branch() -> None:
    events = [
        _ev(0, "torch", "input", outputs=("t:0",), duration_ns=1),
        _ev(1, "torch", "branch_a", inputs=("t:0",), outputs=("t:1",), duration_ns=10),
        _ev(2, "torch", "branch_b", inputs=("t:0",), outputs=("t:2",), duration_ns=5),
        _ev(3, "torch", "branch_a_tail", inputs=("t:1",), outputs=("t:3",), duration_ns=10),
        _ev(4, "torch", "join", inputs=("t:3", "t:2"), outputs=("t:4",), duration_ns=2),
    ]

    regions = analyze(build_dag(events))["parallel_regions"]

    assert len(regions) == 1
    assert regions[0]["parallelizable_ns"] == 5


def test_no_parallel_region_for_sequential_chain() -> None:
    events = [
        _ev(0, "torch", "a", outputs=("t:0",), duration_ns=1),
        _ev(1, "torch", "b", inputs=("t:0",), outputs=("t:1",), duration_ns=1),
    ]
    result = analyze(build_dag(events))
    assert result["parallel_regions"] == []


def test_reachability_cache_reuses_traversals(monkeypatch) -> None:
    calls = 0
    original = analysis_module._reachable

    def counted(start, succs):
        nonlocal calls
        calls += 1
        return original(start, succs)

    monkeypatch.setattr(analysis_module, "_reachable", counted)
    succs = {0: {1}, 1: {2}, 2: set()}
    cache = {}

    assert analysis_module._reachable_cached(0, succs, cache) == {0, 1, 2}
    assert analysis_module._reachable_cached(0, succs, cache) == {0, 1, 2}
    assert calls == 1


def test_device_timeline_reports_devices() -> None:
    events = [
        Event(
            id=0,
            kind="torch",
            op="torch.from_numpy",
            args_summary="",
            input_handles=("n:0",),
            output_handles=("t:0",),
            start_ns=0,
            end_ns=2,
            metadata={
                "inputs": [{"kind": "ndarray", "device": "cpu"}],
                "output": {"kind": "tensor", "device": "cpu"},
            },
        ),
        Event(
            id=1,
            kind="torch",
            op="torch.Tensor.to",
            args_summary="",
            input_handles=("t:0",),
            output_handles=("t:1",),
            start_ns=0,
            end_ns=3,
            metadata={
                "inputs": [{"kind": "tensor", "device": "cpu"}],
                "output": {"kind": "tensor", "device": "cuda:0"},
            },
        ),
    ]
    result = analyze(build_dag(events))
    timeline = result["device_timeline"]
    assert timeline[0]["device"] == "CPU"
    assert timeline[1]["device"] == "GPU"

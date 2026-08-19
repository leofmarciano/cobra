"""Unit tests for the torch recorder (S03-T1)."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import numpy as np
import torch
from tracer.handles import handle_for
from tracer.session import TraceSession, trace
from tracer.torch_mode import TracingTorchFunctionMode, _mutates_inputs


def test_records_torch_ops_with_metadata() -> None:
    with trace(enable_pandas=False, enable_numpy=False) as session:
        x = torch.zeros(4)
        y = torch.relu(x)

    ops = [e.op for e in session.events]
    assert any("relu" in op for op in ops)
    relu_event = next(e for e in session.events if "relu" in e.op)
    assert relu_event.metadata["output"]["kind"] == "tensor"
    assert relu_event.metadata["output"]["shape"] == tuple(y.shape)
    assert relu_event.thread_id == threading.get_ident()


def test_distinct_storage_lineages_for_independent_branches() -> None:
    """Two independent tensor branches must not share value-identity handles."""
    with trace(enable_pandas=False, enable_numpy=False) as session:
        a = torch.zeros(4)
        b = torch.ones(4)
        branch_a = torch.relu(a)
        branch_b = torch.sigmoid(b)

    handle_a = handle_for(branch_a)
    handle_b = handle_for(branch_b)
    assert handle_a is not None
    assert handle_b is not None
    assert handle_a != handle_b

    events_touching_a = [e for e in session.events if handle_a in e.output_handles]
    events_touching_b = [e for e in session.events if handle_b in e.output_handles]
    assert events_touching_a
    assert events_touching_b
    assert {e.id for e in events_touching_a}.isdisjoint({e.id for e in events_touching_b})


def test_tracer_overhead_under_10x_eager() -> None:
    """Plan/sprint acceptance: overhead <10x eager — it's a tracer, not a product."""
    x = torch.randn(64, 64)

    def run() -> None:
        for _ in range(50):
            torch.relu(x @ x)

    start = time.perf_counter()
    run()
    eager_elapsed = time.perf_counter() - start

    with trace(enable_pandas=False, enable_numpy=False):
        start = time.perf_counter()
        run()
        traced_elapsed = time.perf_counter() - start

    # Guard against a near-zero eager baseline making the ratio noisy.
    eager_elapsed = max(eager_elapsed, 1e-4)
    assert traced_elapsed < eager_elapsed * 10


def test_tensor_numpy_boundary_crosses_into_numpy_tracing() -> None:
    with trace(enable_pandas=False) as session:
        array = torch.arange(4).numpy()
        np.mean(array)

    assert any(event.kind == "numpy" and event.op.endswith("mean") for event in session.events)


def test_from_numpy_boundary_preserves_array_to_tensor_lineage() -> None:
    with trace(enable_pandas=False) as session:
        array = np.array([1.0, 2.0, 3.0])
        tensor = torch.from_numpy(array)
        converted = tensor.to(dtype=torch.float32)

    from_numpy = next(event for event in session.events if event.op == "torch.from_numpy")
    converted_event = next(event for event in session.events if event.op.endswith(".to"))
    assert handle_for(array) in from_numpy.input_handles
    assert handle_for(tensor) in from_numpy.output_handles
    assert handle_for(tensor) in converted_event.input_handles
    assert handle_for(converted) in converted_event.output_handles
    assert not any(
        "getset_descriptor" in event.op or "untyped_storage" in event.op for event in session.events
    )


def test_torch_descriptor_reads_are_not_recorded_as_program_operations() -> None:
    with trace(enable_pandas=False, enable_numpy=False) as session:
        tensor = torch.zeros(1)
        _ = tensor.dtype

    assert not any("getset_descriptor" in event.op for event in session.events)


def test_descriptor_attribute_read_is_not_an_inplace_write() -> None:
    class DescriptorRead:
        __name__ = "__get__"

    assert not _mutates_inputs(DescriptorRead(), {})


def test_cuda_results_are_synchronized_before_timing(monkeypatch) -> None:
    class FakeCudaValue:
        is_cuda = True

    sync = MagicMock()
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "synchronize", sync)

    def fake_cuda_op() -> FakeCudaValue:
        return FakeCudaValue()

    mode = TracingTorchFunctionMode(TraceSession())
    mode.__torch_function__(fake_cuda_op, (), (), {})

    sync.assert_called_once_with()


def test_cuda_availability_is_cached_for_a_trace_session(monkeypatch) -> None:
    is_available = MagicMock(return_value=False)
    monkeypatch.setattr(torch.cuda, "is_available", is_available)

    session = TraceSession()
    mode = TracingTorchFunctionMode(session)

    class FakeCudaValue:
        is_cuda = True

    def fake_op() -> FakeCudaValue:
        return FakeCudaValue()

    mode.__torch_function__(fake_op, (), (), {})
    mode.__torch_function__(fake_op, (), (), {})

    assert is_available.call_count == 1

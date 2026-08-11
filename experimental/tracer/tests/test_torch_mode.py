"""Unit tests for the torch recorder (S03-T1)."""

from __future__ import annotations

import threading
import time

import torch
from tracer.handles import handle_for
from tracer.session import trace


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

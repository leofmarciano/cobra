"""Unit tests for the numpy recorder (S03-T1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from tracer.handles import handle_for
from tracer.numpy_wrap import wrap
from tracer.session import trace


def test_records_array_function_calls() -> None:
    with trace(enable_torch=False, enable_pandas=False) as session:
        arr = wrap(np.array([1.0, 2.0, 3.0, 4.0]))
        total = np.sum(arr)
        mean = np.mean(arr)

    ops = [e.op for e in session.events]
    assert any(op.endswith("sum") for op in ops)
    assert any(op.endswith("mean") for op in ops)
    assert float(total) == 10.0
    assert float(mean) == 2.5


def test_tracing_propagates_through_chained_calls() -> None:
    with trace(enable_torch=False, enable_pandas=False) as session:
        arr = wrap(np.array([1.0, 2.0, 3.0]))
        stacked = np.concatenate([arr, arr])
        np.sum(stacked)

    ops = [e.op for e in session.events]
    assert any(op.endswith("concatenate") for op in ops)
    assert any(op.endswith("sum") for op in ops)


def test_untraced_array_is_not_recorded() -> None:
    with trace(enable_torch=False, enable_pandas=False) as session:
        plain = np.array([1.0, 2.0])
        np.sum(plain)

    assert session.events == []


def test_pandas_numpy_boundary_preserves_array_lineage() -> None:
    with trace(enable_torch=False) as session:
        array = pd.DataFrame({"a": [1.0, 2.0]}).to_numpy()
        np.mean(array)

    boundary = next(event for event in session.events if event.op == "pandas.DataFrame.to_numpy")
    numpy_event = next(event for event in session.events if event.op == "numpy.mean")
    assert handle_for(array) in boundary.output_handles
    assert handle_for(array) in numpy_event.input_handles

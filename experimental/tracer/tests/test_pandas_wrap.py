"""Unit tests for the pandas recorder (S03-T1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from tracer.dag import build_dag
from tracer.session import trace


def test_records_supported_methods() -> None:
    with trace(enable_torch=False, enable_numpy=False) as session:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, None]})
        df2 = df.fillna(0)
        df3 = df2.astype({"b": "int64"})
        df3.sort_values("a")

    ops = [e.op for e in session.events]
    assert "pandas.DataFrame.fillna" in ops
    assert "pandas.DataFrame.astype" in ops
    assert "pandas.DataFrame.sort_values" in ops


def test_dependency_chain_shares_handles() -> None:
    with trace(enable_torch=False, enable_numpy=False) as session:
        df = pd.DataFrame({"a": [1, 2, 3]})
        out = df.fillna(0)

    fillna_event = next(e for e in session.events if e.op == "pandas.DataFrame.fillna")
    assert fillna_event.output_handles
    # The output handle should identify `out` by object identity.
    from tracer.handles import handle_for

    assert handle_for(out) in fillna_event.output_handles


def test_unwrapping_restores_originals() -> None:
    original = pd.DataFrame.fillna
    with trace(enable_torch=False, enable_numpy=False):
        assert pd.DataFrame.fillna is not original
    assert pd.DataFrame.fillna is original


def test_to_numpy_crosses_into_numpy_tracing() -> None:
    with trace(enable_torch=False) as session:
        array = pd.DataFrame({"a": [1.0, 2.0]}).to_numpy()
        np.mean(array)

    assert any(event.kind == "numpy" and event.op.endswith("mean") for event in session.events)


def test_records_feature_engineering_mutations_and_module_functions() -> None:
    with trace(enable_torch=False, enable_numpy=False) as session:
        df = pd.DataFrame({"a": [1.0, 2.0], "category": ["x", "y"]})
        df["interaction"] = df["a"] * 2.0 + 1.0
        one_hot = pd.get_dummies(df["category"], dtype=np.float64)
        pd.concat([df, one_hot], axis=1)

    ops = [event.op for event in session.events]
    assert "pandas.DataFrame.__setitem__" in ops
    assert "pandas.Series.__mul__" in ops
    assert "pandas.Series.__add__" in ops
    assert "pandas.get_dummies" in ops
    assert "pandas.concat" in ops

    assignment = next(
        event for event in session.events if event.op == "pandas.DataFrame.__setitem__"
    )
    from tracer.handles import handle_for

    assert handle_for(df) in assignment.output_handles
    dag = build_dag(session.events)
    assert any(edge["from"] != edge["to"] and edge["to"] == assignment.id for edge in dag["edges"])

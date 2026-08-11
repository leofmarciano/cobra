"""Unit tests for the pandas recorder (S03-T1)."""

from __future__ import annotations

import pandas as pd
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

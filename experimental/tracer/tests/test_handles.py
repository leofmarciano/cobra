"""Unit tests for tracer.handles (S03-T1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from tracer.handles import collect_handles, handle_for


def test_scalar_has_no_handle() -> None:
    assert handle_for(1) is None
    assert handle_for("hello") is None
    assert handle_for(None) is None


def test_tensor_handle_shared_across_views() -> None:
    t = torch.zeros(4)
    view = t.view(-1)
    assert handle_for(t) == handle_for(view)


def test_tensor_handle_differs_across_storages() -> None:
    a = torch.zeros(4)
    b = torch.zeros(4)
    assert handle_for(a) != handle_for(b)


def test_dataframe_handle_is_object_identity() -> None:
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert handle_for(df) == handle_for(df)
    other = pd.DataFrame({"a": [1, 2, 3]})
    assert handle_for(df) != handle_for(other)


def test_ndarray_handle_shared_with_view() -> None:
    arr = np.zeros(4)
    view = arr[:2]
    assert handle_for(arr) == handle_for(view)


def test_collect_handles_flattens_and_filters() -> None:
    t = torch.zeros(2)
    handles = collect_handles([1, "x", t, None])
    assert handles == (handle_for(t),)


def test_collect_handles_recurses_nested_containers_and_mappings() -> None:
    first = torch.zeros(2)
    second = torch.ones(2)
    values = {"batch": [(first,)], "other": {"tensor": second}}

    handles = collect_handles(values)

    assert handles == (handle_for(first), handle_for(second))

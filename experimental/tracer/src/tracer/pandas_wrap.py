"""Pandas method-wrapping recorder (S03-T1).

Wraps the supported-operation list from plan §10.1 by patching bound
methods on ``pandas.DataFrame``/``pandas.Series`` for the duration of a
trace, restoring the originals on exit. Unlisted methods are not traced
(they fall through to ordinary, unrecorded pandas execution — consistent
with plan §10.1: "unsupported operations materialize and fall back").
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import numpy as np
import pandas as pd

from tracer.numpy_wrap import wrap as wrap_numpy
from tracer.session import TraceSession

# plan §10.1 v0.1 supported operations, mapped to the pandas API names that
# implement them for DataFrame/Series.
_DATAFRAME_METHODS = (
    "__getitem__",  # column projection / boolean filtering
    "__setitem__",  # in-place column mutation
    "assign",
    "astype",
    "fillna",
    "dropna",
    "groupby",
    "merge",
    "join",
    "sort_values",
    "to_numpy",
)
_SERIES_METHODS = (
    "__add__",
    "__mul__",
    "astype",
    "fillna",
    "dropna",
    "sort_values",
    "to_numpy",
)
_MODULE_FUNCTIONS = ("concat", "get_dummies", "read_parquet")


def _wrap_method(cls: type, name: str, session: TraceSession) -> tuple[str, Any] | None:
    original = getattr(cls, name, None)
    if original is None or not callable(original):
        return None

    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        start_ns = session.clock()
        result = original(self, *args, **kwargs)
        end_ns = session.clock()
        if isinstance(result, np.ndarray):
            result = wrap_numpy(result)
        recorded_result = self if name == "__setitem__" else result
        session.record(
            "pandas",
            f"pandas.{cls.__name__}.{name}",
            args=(self, *args),
            kwargs=kwargs,
            # ``DataFrame.__setitem__`` returns None, but mutates ``self``.
            # Record the mutated frame as the output so the DAG can fence the
            # write against readers and later mutations of that same frame.
            result=recorded_result,
            start_ns=start_ns,
            end_ns=end_ns,
        )
        return result

    setattr(cls, name, wrapper)
    return name, original


def _wrap_function(module: Any, name: str, session: TraceSession, op_prefix: str) -> Any:
    original = getattr(module, name)

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_ns = session.clock()
        result = original(*args, **kwargs)
        end_ns = session.clock()
        session.record(
            "pandas",
            f"{op_prefix}.{name}",
            args=args,
            kwargs=kwargs,
            result=result,
            start_ns=start_ns,
            end_ns=end_ns,
        )
        return result

    setattr(module, name, wrapper)
    return original


@contextmanager
def pandas_recorder(session: TraceSession) -> Iterator[None]:
    """Activate pandas call-boundary recording for the ``with`` block's lifetime."""
    patched_df: list[tuple[str, Any]] = []
    patched_series: list[tuple[str, Any]] = []
    original_functions: dict[str, Any] = {}

    for name in _DATAFRAME_METHODS:
        patched = _wrap_method(pd.DataFrame, name, session)
        if patched is not None:
            patched_df.append(patched)
    for name in _SERIES_METHODS:
        patched = _wrap_method(pd.Series, name, session)
        if patched is not None:
            patched_series.append(patched)
    for name in _MODULE_FUNCTIONS:
        original_functions[name] = _wrap_function(pd, name, session, "pandas")

    try:
        yield
    finally:
        for name, original in patched_df:
            setattr(pd.DataFrame, name, original)
        for name, original in patched_series:
            setattr(pd.Series, name, original)
        for name, original in original_functions.items():
            setattr(pd, name, original)

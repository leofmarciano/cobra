"""NumPy op recorder using the ``__array_function__`` protocol (S03-T1).

Unlike the pandas recorder (which patches methods globally for the trace's
lifetime), NumPy dispatch through ``__array_function__`` is *per-value*: an
ndarray only participates in dispatch once it looks like a
``TracedArray``. ``numpy_recorder`` marks values crossing known boundaries
(``pandas.DataFrame.to_numpy``, ``torch.Tensor.numpy``, ...) as traced by
wrapping them; from then on, every ``numpy.*`` call touching that array is
recorded via the real protocol, and results are re-wrapped so tracing
propagates through chains of numpy calls.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import numpy as np

from tracer.session import TraceSession

_ACTIVE_SESSION: contextvars.ContextVar[TraceSession | None] = contextvars.ContextVar(
    "tracer_numpy_active_session", default=None
)


class TracedArray(np.ndarray):
    """An ``ndarray`` subclass that records every dispatched NumPy call."""

    def __array_function__(
        self,
        func: Any,
        types: tuple[type, ...],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        session = _ACTIVE_SESSION.get()
        raw_args = tuple(_unwrap(a) for a in args)
        raw_kwargs = {k: _unwrap(v) for k, v in kwargs.items()}

        if session is None:
            return func(*raw_args, **raw_kwargs)

        start_ns = session.clock()
        result = func(*raw_args, **raw_kwargs)
        end_ns = session.clock()

        op = getattr(func, "__module__", "numpy") + "." + getattr(func, "__name__", str(func))
        session.record(
            "numpy",
            op,
            args=raw_args,
            kwargs=raw_kwargs,
            result=result,
            start_ns=start_ns,
            end_ns=end_ns,
            extra_metadata={"mutates_inputs": raw_kwargs.get("out") is not None},
        )
        return _wrap(result)


def _unwrap(value: Any) -> Any:
    if isinstance(value, TracedArray):
        return value.view(np.ndarray)
    if isinstance(value, list | tuple):
        return type(value)(_unwrap(v) for v in value)
    return value


def _wrap(value: Any) -> Any:
    if isinstance(value, np.ndarray) and not isinstance(value, TracedArray):
        return value.view(TracedArray)
    return value


def wrap(array: np.ndarray) -> TracedArray:
    """Mark ``array`` so subsequent ``numpy.*`` calls on it are traced."""
    return array.view(TracedArray)


@contextmanager
def numpy_recorder(session: TraceSession) -> Iterator[None]:
    """Activate NumPy call-boundary recording for ``TracedArray`` values."""
    token = _ACTIVE_SESSION.set(session)
    try:
        yield
    finally:
        _ACTIVE_SESSION.reset(token)

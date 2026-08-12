"""Trace session: the shared event sink for all per-library recorders (S03-T1)."""

from __future__ import annotations

import contextvars
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, TypeVar

from tracer.events import Event, EventKind
from tracer.handles import collect_handles, collect_logical_handles
from tracer.metadata import describe, summarize_args

_THIS_DIR = str(Path(__file__).resolve().parent)
_ACTIVE_SESSION: contextvars.ContextVar[TraceSession | None] = contextvars.ContextVar(
    "tracer_active_session", default=None
)
_SUPPRESS_DISPATCH: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tracer_suppress_dispatch", default=False
)
_T = TypeVar("_T")


def _source_location(skip_dirs: tuple[str, ...] = (_THIS_DIR,)) -> str:
    """Walk the call stack to the first frame outside ``skip_dirs``.

    Compares raw ``co_filename`` values against pre-resolved ``skip_dirs``
    rather than resolving every frame's filename: frame filenames are
    already absolute for installed/importable modules, and resolving them
    on every recorded call is a hot-loop cost this tracer cannot afford
    (plan/sprint overhead budget: <10x eager, see S03-T1 acceptance).
    """
    frame = sys._getframe(1)
    while frame is not None:
        filename = frame.f_code.co_filename
        if not any(filename.startswith(d) for d in skip_dirs):
            return f"{filename}:{frame.f_lineno}"
        frame = frame.f_back
    return ""


class TraceSession:
    """Collects ``Event`` records for one traced program run.

    Not thread-safe beyond ``threading.Lock``-guarded appends: recorders may
    be invoked from multiple threads (e.g. traced code launching a thread
    pool), and each event records its own ``thread_id`` for later analysis.
    """

    def __init__(self) -> None:
        self.events: list[Event] = []
        self._next_id = 0
        self._lock = threading.Lock()

    @property
    def dispatch_suppressed(self) -> bool:
        """Whether recorder-internal metadata reads must not become events."""
        return _SUPPRESS_DISPATCH.get()

    @contextmanager
    def suppress_dispatch(self) -> Iterator[None]:
        """Temporarily disable recorder dispatch for internal value inspection."""
        token = _SUPPRESS_DISPATCH.set(True)
        try:
            yield
        finally:
            _SUPPRESS_DISPATCH.reset(token)

    def record(
        self,
        kind: EventKind,
        op: str,
        *,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        result: Any = None,
        start_ns: int,
        end_ns: int,
        extra_metadata: dict[str, Any] | None = None,
        skip_source_dirs: tuple[str, ...] = (_THIS_DIR,),
    ) -> Event:
        """Append and return a new ``Event`` describing one call boundary."""
        kwargs = kwargs or {}
        # Metadata extraction reads tensor attributes and storage identities.
        # Keep those implementation details out of the active TorchFunction
        # mode while still allowing nested user operations to be recorded.
        with self.suppress_dispatch():
            input_values = list(args) + list(kwargs.values())
            metadata: dict[str, Any] = {
                "inputs": [describe(a) for a in args],
                "output": describe(result),
            }
            logical_inputs = collect_logical_handles(input_values)
            logical_outputs = collect_logical_handles(result)
            if logical_inputs:
                metadata["logical_input_handles"] = logical_inputs
            if logical_outputs:
                metadata["logical_output_handles"] = logical_outputs
            if extra_metadata:
                metadata.update(extra_metadata)

            event = Event(
                id=0,
                kind=kind,
                op=op,
                args_summary=summarize_args(args, kwargs),
                input_handles=collect_handles(input_values),
                output_handles=collect_handles(result),
                metadata=metadata,
                start_ns=start_ns,
                end_ns=end_ns,
                thread_id=threading.get_ident(),
                source=_source_location(skip_source_dirs),
            )
        with self._lock:
            event.id = self._next_id
            self._next_id += 1
            self.events.append(event)
        return event

    @staticmethod
    def clock() -> int:
        """Monotonic nanosecond clock used consistently across recorders."""
        return time.perf_counter_ns()


def active_session() -> TraceSession | None:
    """Return the session active in the current context, if any."""
    return _ACTIVE_SESSION.get()


def run_boundary(
    op_name: str,
    func: Callable[..., _T],
    *args: Any,
    **kwargs: Any,
) -> _T:
    """Run an unsupported boundary and record it when tracing is active."""
    session = active_session()
    if session is None:
        return func(*args, **kwargs)

    start_ns = session.clock()
    result = func(*args, **kwargs)
    end_ns = session.clock()
    session.record(
        "opaque",
        f"opaque:{op_name}",
        args=args,
        kwargs=kwargs,
        result=result,
        start_ns=start_ns,
        end_ns=end_ns,
    )
    return result


@contextmanager
def trace(
    *,
    enable_torch: bool = True,
    enable_pandas: bool = True,
    enable_numpy: bool = True,
) -> Iterator[TraceSession]:
    """Context manager: activate all requested recorders against a fresh session.

    Example:
        with trace() as session:
            model(x)
        events = session.events
    """
    from tracer.numpy_wrap import numpy_recorder
    from tracer.pandas_wrap import pandas_recorder
    from tracer.torch_mode import TracingTorchFunctionMode, torch_numpy_boundary_recorder

    session = TraceSession()
    token = _ACTIVE_SESSION.set(session)
    try:
        with ExitStack() as stack:
            if enable_torch:
                stack.enter_context(TracingTorchFunctionMode(session))
                stack.enter_context(torch_numpy_boundary_recorder(session))
            if enable_pandas:
                stack.enter_context(pandas_recorder(session))
            if enable_numpy:
                stack.enter_context(numpy_recorder(session))
            yield session
    finally:
        _ACTIVE_SESSION.reset(token)

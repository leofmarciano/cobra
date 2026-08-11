"""Opaque-node wrapper for calls with no adapter (S03-T1, plan §6.2/§6.3).

Any callable can be wrapped with ``opaque()`` to record it as an opaque
node: the tracer observes the call boundary (inputs, outputs, timing,
source) without understanding the operation's semantics. Per plan §6.3,
opaque nodes are conservative — the DAG builder (S03-T2) gives them
ordering edges to their program-order neighbors rather than assuming
independence.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from tracer.session import TraceSession

F = TypeVar("F", bound=Callable[..., Any])


def opaque(session: TraceSession, name: str | None = None) -> Callable[[F], F]:
    """Return a decorator that records calls to the wrapped function as opaque nodes."""

    def decorator(func: F) -> F:
        op_name = name or f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
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

        return wrapper  # type: ignore[return-value]

    return decorator


def call_opaque(
    session: TraceSession,
    func: Callable[..., Any],
    *args: Any,
    op_name: str | None = None,
    **kwargs: Any,
) -> Any:
    """Call ``func`` once, recording it as an opaque node. Convenience for call sites."""
    name = op_name or f"{getattr(func, '__module__', '?')}.{getattr(func, '__qualname__', func)}"
    start_ns = session.clock()
    result = func(*args, **kwargs)
    end_ns = session.clock()
    session.record(
        "opaque",
        f"opaque:{name}",
        args=args,
        kwargs=kwargs,
        result=result,
        start_ns=start_ns,
        end_ns=end_ns,
    )
    return result

"""Event schema recorded by the disposable tracer (S03-T1).

Every recorded call boundary — torch op, pandas method, numpy function, or
opaque Python call — is normalized into one ``Event``. Events reference
"handles" (see ``tracer.handles``) rather than raw Python objects so the
dependency-DAG builder (S03-T2) can connect events by value identity without
keeping live references to potentially large tensors/dataframes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EventKind = Literal["torch", "pandas", "numpy", "opaque"]


@dataclass(slots=True)
class Event:
    """A single recorded call-boundary.

    Attributes:
        id: Monotonically increasing sequence number in program order.
        kind: Which recorder produced this event.
        op: Fully-qualified operation name (e.g. ``"torch.relu"``,
            ``"pandas.DataFrame.merge"``, ``"numpy.mean"``,
            ``"opaque:mypkg.myfunc"``).
        args_summary: Human-readable, non-sensitive summary of arguments
            (shapes/dtypes/scalars — never full tensor/dataframe contents).
        input_handles: Value-identity handles (see ``tracer.handles``) for
            every traced input, in call order.
        output_handles: Value-identity handles for every traced output.
        metadata: Per-event metadata (dtype, shape/schema, device, storage
            id, ...). Keys vary by ``kind``.
        start_ns: ``time.perf_counter_ns()`` at call entry.
        end_ns: ``time.perf_counter_ns()`` at call return.
        thread_id: ``threading.get_ident()`` of the calling thread.
        source: ``"<file>:<line>"`` of the call site, or ``""`` if unknown.
    """

    id: int
    kind: EventKind
    op: str
    args_summary: str
    input_handles: tuple[str, ...] = ()
    output_handles: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    start_ns: int = 0
    end_ns: int = 0
    thread_id: int = 0
    source: str = ""

    @property
    def duration_ns(self) -> int:
        """Wall-clock duration of the call in nanoseconds."""
        return max(0, self.end_ns - self.start_ns)

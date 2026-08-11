"""cobra-tracer — DISPOSABLE whole-program tracer spike.

See ``experimental/tracer/README.md``: this package is not release code
(plan §18.4) and exists only to de-risk the whole-program capture thesis
for S03 (plan §29 Days 11-20).
"""

from __future__ import annotations

from tracer.events import Event
from tracer.session import TraceSession, trace

__all__ = ["Event", "TraceSession", "trace"]

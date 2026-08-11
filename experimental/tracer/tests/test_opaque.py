"""Unit tests for the opaque-node wrapper (S03-T1, plan §6.2/§6.3)."""

from __future__ import annotations

from tracer.opaque import call_opaque, opaque
from tracer.session import TraceSession


def _unsupported_call(x: int, y: int) -> int:
    return x + y


def test_opaque_decorator_records_call() -> None:
    session = TraceSession()
    wrapped = opaque(session)(_unsupported_call)

    result = wrapped(2, 3)

    assert result == 5
    assert len(session.events) == 1
    event = session.events[0]
    assert event.kind == "opaque"
    assert event.op.startswith("opaque:")
    assert "_unsupported_call" in event.op


def test_call_opaque_convenience() -> None:
    session = TraceSession()
    result = call_opaque(session, _unsupported_call, 4, 5)
    assert result == 9
    assert session.events[0].kind == "opaque"


def test_call_opaque_custom_name() -> None:
    session = TraceSession()
    call_opaque(session, _unsupported_call, 1, 1, op_name="third_party.mystery")
    assert session.events[0].op == "opaque:third_party.mystery"

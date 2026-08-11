"""Torch op recorder using ``torch.overrides.TorchFunctionMode`` (S03-T1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from torch.overrides import TorchFunctionMode

from tracer.session import TraceSession

_THIS_DIR = str(Path(__file__).resolve().parent)


class TracingTorchFunctionMode(TorchFunctionMode):
    """Records every dispatched ``torch.*`` call as an ``Event``.

    ``TorchFunctionMode`` intercepts calls at the Python API boundary (the
    level plan §6.2 calls "tensor graph"), which is sufficient for the
    tracer's goal of observing tensor operations, their metadata, and
    dependencies — it does not need kernel-level (ATen) granularity.
    """

    def __init__(self, session: TraceSession) -> None:
        super().__init__()
        self._session = session

    def __torch_function__(
        self,
        func: Any,
        types: Any,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        kwargs = kwargs or {}
        start_ns = self._session.clock()
        result = func(*args, **kwargs)
        end_ns = self._session.clock()

        name = getattr(func, "__qualname__", None) or getattr(func, "__name__", str(func))
        module = getattr(func, "__module__", "torch")
        op = f"{module}.{name}" if module else f"torch.{name}"

        self._session.record(
            "torch",
            op,
            args=args,
            kwargs=kwargs,
            result=result,
            start_ns=start_ns,
            end_ns=end_ns,
            skip_source_dirs=(_THIS_DIR,),
        )
        return result

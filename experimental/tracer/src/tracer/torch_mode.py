"""Torch op recorder using ``torch.overrides.TorchFunctionMode`` (S03-T1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.overrides import TorchFunctionMode

from tracer.numpy_wrap import wrap as wrap_numpy
from tracer.session import TraceSession

_THIS_DIR = str(Path(__file__).resolve().parent)


def _contains_cuda_value(value: Any) -> bool:
    """Return whether a value or nested container carries CUDA work."""
    if isinstance(value, dict):
        return any(_contains_cuda_value(nested) for nested in value.values())
    if isinstance(value, list | tuple | set):
        return any(_contains_cuda_value(nested) for nested in value)
    if isinstance(value, torch.Tensor):
        return bool(value.is_cuda)
    return bool(getattr(value, "is_cuda", False))


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
        if isinstance(result, np.ndarray):
            result = wrap_numpy(result)
        if torch.cuda.is_available() and _contains_cuda_value((args, kwargs, result)):
            # CUDA calls are asynchronous.  Synchronize before taking the end
            # timestamp so analyzer durations include device completion.
            torch.cuda.synchronize()
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

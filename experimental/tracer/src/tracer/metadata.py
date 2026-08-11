"""Per-value metadata extraction for recorded events (S03-T1).

Captures the fields the sprint requires: dtype, shape/schema, device, and
storage id, without ever serializing tensor/dataframe *contents*.
"""

from __future__ import annotations

from typing import Any

from tracer.handles import tensor_storage_identity

try:
    import torch
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore[assignment]

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]


def describe(value: Any) -> dict[str, Any]:
    """Return a small dict of identity/shape metadata for ``value``.

    Returns ``{"kind": "scalar", "value": repr(...)}`` for anything without
    richer structure so ``args_summary`` stays informative without dumping
    large buffers.
    """
    if torch is not None and isinstance(value, torch.Tensor):
        storage_id = tensor_storage_identity(value)
        return {
            "kind": "tensor",
            "dtype": str(value.dtype),
            "shape": tuple(value.shape),
            "device": str(value.device),
            "storage_id": storage_id,
            "requires_grad": bool(value.requires_grad),
        }
    if pd is not None and isinstance(value, pd.DataFrame):
        return {
            "kind": "dataframe",
            "schema": {str(c): str(dt) for c, dt in value.dtypes.items()},
            "shape": tuple(value.shape),
        }
    if pd is not None and isinstance(value, pd.Series):
        return {"kind": "series", "dtype": str(value.dtype), "shape": tuple(value.shape)}
    if np is not None and isinstance(value, np.ndarray):
        return {
            "kind": "ndarray",
            "dtype": str(value.dtype),
            "shape": tuple(value.shape),
            "device": "cpu",
        }
    if isinstance(value, int | float | bool | str | bytes | type(None)):
        return {"kind": "scalar", "value": repr(value)[:120]}
    return {"kind": type(value).__name__}


def summarize_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Build a compact, human-readable summary of a call's arguments."""
    parts = [_short(a) for a in args]
    parts += [f"{k}={_short(v)}" for k, v in kwargs.items()]
    return ", ".join(parts)


def _short(value: Any) -> str:
    desc = describe(value)
    kind = desc.get("kind")
    if kind == "tensor":
        return f"Tensor(dtype={desc['dtype']}, shape={desc['shape']}, device={desc['device']})"
    if kind == "dataframe":
        return f"DataFrame(shape={desc['shape']})"
    if kind == "series":
        return f"Series(dtype={desc['dtype']}, shape={desc['shape']})"
    if kind == "ndarray":
        return f"ndarray(dtype={desc['dtype']}, shape={desc['shape']})"
    if kind == "scalar":
        return str(desc["value"])
    return f"<{kind}>"

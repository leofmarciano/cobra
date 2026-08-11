"""Value-identity handles for the disposable tracer (S03-T1).

A "handle" is a short string that identifies *storage identity*, not object
identity: two different tensor objects that alias the same underlying
storage (e.g. a view) map to the same tensor handle, matching plan §6.4's
guard model (storage/allocation identity) and enabling S03-T2's DAG builder
to connect producer/consumer events correctly even across views.
"""

from __future__ import annotations

import threading
import weakref
from collections.abc import Mapping
from typing import Any

try:
    import torch
except ImportError:  # pragma: no cover - torch is a hard dependency of this package
    torch = None  # type: ignore[assignment]

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore[assignment]

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]


# ``data_ptr()`` identifies an address, not an allocation lifetime: PyTorch's
# allocator can recycle an address after the previous tensor is destroyed.
# ``UntypedStorage._cdata`` identifies the live StorageImpl.  The generation
# counter handles the rare case where even that native identity is recycled,
# while the weak reference lets simultaneously-live views retain one handle.
_tensor_storage_generations: dict[int, tuple[weakref.ReferenceType[Any], int]] = {}
_tensor_storage_lock = threading.Lock()


def tensor_storage_identity(value: Any) -> str | None:
    """Return a generation-aware identity for a tensor's live allocation.

    Views share the same ``UntypedStorage``/StorageImpl and therefore the same
    identity.  Once that storage is gone, a reused native key receives a new
    generation instead of aliasing the old value in the dependency DAG.
    """
    if torch is None or not isinstance(value, torch.Tensor):
        return None
    try:
        storage = value.untyped_storage()
        raw_key = getattr(storage, "_cdata", None)
        key = int(raw_key) if raw_key is not None else id(storage)
        with _tensor_storage_lock:
            previous = _tensor_storage_generations.get(key)
            if previous is None:
                generation = 0
            elif previous[0]() is None:
                generation = previous[1] + 1
            else:
                generation = previous[1]
            _tensor_storage_generations[key] = (weakref.ref(storage), generation)
        return f"{key}:{generation}"
    except (AttributeError, RuntimeError, NotImplementedError, TypeError):
        return f"obj:{id(value)}"


def handle_for(value: Any) -> str | None:
    """Return a stable value-identity handle for ``value``, or ``None``.

    Returns ``None`` for values with no useful identity to track (Python
    scalars, strings, ``None``, small tuples of scalars, ...) so callers can
    omit them from ``input_handles``/``output_handles``.
    """
    if torch is not None and isinstance(value, torch.Tensor):
        identity = tensor_storage_identity(value)
        return f"tensor:{identity}" if identity is not None else f"tensor:obj:{id(value)}"
    if pd is not None and isinstance(value, pd.DataFrame | pd.Series):
        return f"pandas:{id(value)}"
    if np is not None and isinstance(value, np.ndarray):
        base = value.base if value.base is not None else value
        return f"ndarray:{id(base)}"
    if isinstance(value, list | tuple | dict | set) and not _is_scalar_container(value):
        return f"opaque:{id(value)}"
    if hasattr(value, "__dict__") and not isinstance(value, str | bytes | int | float | bool):
        return f"opaque:{id(value)}"
    return None


def _is_scalar_container(value: Any) -> bool:
    """True for small containers of only scalars (not worth tracking)."""
    items = value.values() if isinstance(value, dict) else value
    return all(isinstance(v, int | float | bool | str | bytes | type(None)) for v in items)


def collect_handles(values: Any) -> tuple[str, ...]:
    """Recursively collect value handles from nested operation arguments."""
    handles: list[str] = []
    seen: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for nested in value.values():
                visit(nested)
            return
        if isinstance(value, list | tuple):
            for nested in value:
                visit(nested)
            return
        h = handle_for(value)
        if h is not None and h not in seen:
            seen.add(h)
            handles.append(h)

    visit(values)
    return tuple(handles)

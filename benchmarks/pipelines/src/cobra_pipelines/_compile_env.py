"""Environment setup for torch.compile with CUDA Inductor backend.

The Inductor backend's repro/debug infrastructure calls `nvcc --version` via
subprocess during compilation.  When nvcc is installed via pip wheels
(nvidia-cuda-nvcc package) rather than a system CUDA toolkit, its binary lives
in a non-standard location that is not on PATH by default.

This module detects the pip-installed nvcc location and adds it to PATH so that
torch.compile works correctly.  It is idempotent and safe to call multiple
times.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _find_pip_nvcc_dir() -> Path | None:
    """Find the directory containing the pip-wheel-installed nvcc binary."""
    # The nvidia-cuda-nvcc pip package installs nvcc under:
    # site-packages/nvidia/cu<ver>/bin/nvcc
    for site_dir in sys.path:
        nvidia_dir = Path(site_dir) / "nvidia"
        if nvidia_dir.is_dir():
            for cuda_dir in nvidia_dir.iterdir():
                if cuda_dir.is_dir() and cuda_dir.name.startswith("cu"):
                    nvcc_bin = cuda_dir / "bin" / "nvcc"
                    if nvcc_bin.is_file():
                        return cuda_dir / "bin"
    return None


_patched = False


def ensure_nvcc_in_path() -> None:
    """Ensure nvcc is discoverable via PATH for torch.compile/inductor.

    Idempotent: safe to call multiple times; only modifies PATH once.
    """
    global _patched
    if _patched:
        return
    _patched = True

    # If nvcc is already on PATH, nothing to do
    import shutil

    if shutil.which("nvcc") is not None:
        return

    nvcc_dir = _find_pip_nvcc_dir()
    if nvcc_dir is not None:
        os.environ["PATH"] = str(nvcc_dir) + os.pathsep + os.environ.get("PATH", "")

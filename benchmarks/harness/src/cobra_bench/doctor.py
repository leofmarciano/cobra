"""Machine metadata collector for ``cobra-bench doctor`` (plan §33.2).

Captures OS/kernel/CPU/NUMA/RAM, GPU info via ``nvidia-smi``, and
Python/framework versions via ``importlib.metadata``.  All external
commands are called through ``subprocess.run`` so they can be patched
with fakes in CI (no GPU).

``--strict`` fails when required fields are missing (e.g. GPU absent).
Output is ``artifacts/environment.json``.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Host metadata
# ---------------------------------------------------------------------------


def _get_total_memory_gb() -> float:
    """Return total physical memory in GiB (cross-platform)."""
    system = platform.system()
    if system == "Linux":
        try:
            with Path("/proc/meminfo").open() as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        # Value is in kB
                        kb = int(line.split()[1])
                        return round(kb / (1024 * 1024), 2)
        except OSError:
            pass
    elif system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return round(int(result.stdout.strip()) / (1024**3), 2)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    # Fallback: os.sysconf (POSIX)
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page_size > 0:
            return round((pages * page_size) / (1024**3), 2)
    except (ValueError, OSError, AttributeError):
        pass
    return 0.0


def _get_numa_node_count() -> int:
    """Return the number of NUMA nodes (Linux: /sys, else default 1)."""
    try:
        numa_dir = Path("/sys/devices/system/node")
        if numa_dir.is_dir():
            return len([d for d in numa_dir.iterdir() if d.name.startswith("node")])
    except OSError:
        pass
    return 1


def collect_cpu_info() -> str:
    """Return a human-readable CPU model string."""
    system = platform.system()

    # Linux: parse /proc/cpuinfo
    if system == "Linux":
        try:
            with Path("/proc/cpuinfo").open() as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass

    # macOS: sysctl
    if system == "Darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass

    # Fallback
    return platform.processor() or platform.machine()


def collect_host_info() -> dict[str, Any]:
    """Collect OS, kernel, CPU, NUMA, RAM metadata."""
    return {
        "hostname_alias": platform.node() or "unknown",
        "os": f"{platform.system()} {platform.release()}",
        "kernel": platform.release(),
        "cpu": collect_cpu_info(),
        "numa_nodes": _get_numa_node_count(),
        "memory_gb": _get_total_memory_gb(),
        "manual": False,
    }


# ---------------------------------------------------------------------------
# GPU metadata (nvidia-smi)
# ---------------------------------------------------------------------------

_NVIDIA_SMI_QUERY = (
    "gpu_name,driver_version,compute_cap,"
    "gpu_uuid,clocks_throttle_reasons.active,"
    "power.limit,persistence_mode,mig.mode.current"
)


def _hash_uuid(uuid_str: str) -> str:
    """SHA-256 hash of the GPU UUID for privacy."""
    return hashlib.sha256(uuid_str.encode()).hexdigest()[:16]


def collect_gpu_info() -> dict[str, Any]:
    """Collect GPU metadata via ``nvidia-smi``.

    Returns ``{"status": "absent", ...}`` when nvidia-smi is unavailable or
    fails, so CI without a GPU still works.
    """
    absent: dict[str, Any] = {
        "status": "absent",
        "gpu_name": None,
        "driver": None,
        "compute_capability": None,
        "gpu_uuid_hash": None,
        "clocks_policy": None,
        "power_limit_watts": None,
        "persistence_mode": None,
        "mig": None,
        "manual": False,
    }

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=" + _NVIDIA_SMI_QUERY,
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError):
        return absent

    if result.returncode != 0:
        return absent

    line = result.stdout.strip()
    if not line:
        return absent

    parts = [p.strip() for p in line.split(",")]

    def _safe_get(idx: int) -> str | None:
        if idx < len(parts):
            val = parts[idx].strip()
            return val if val and val.lower() not in ("[not supported]", "n/a", "") else None
        return None

    gpu_name = _safe_get(0)
    driver = _safe_get(1)
    compute_cap = _safe_get(2)
    gpu_uuid = _safe_get(3)
    clocks_policy = _safe_get(4)
    power_limit_str = _safe_get(5)
    persistence_str = _safe_get(6)
    mig_str = _safe_get(7)

    power_limit: float | None = None
    if power_limit_str is not None:
        with contextlib.suppress(ValueError):
            power_limit = float(power_limit_str)

    persistence: bool | None = None
    if persistence_str is not None:
        persistence = persistence_str.lower() in ("enabled", "on", "true", "1")

    return {
        "status": "present",
        "gpu_name": gpu_name,
        "driver": driver,
        "compute_capability": compute_cap,
        "gpu_uuid_hash": _hash_uuid(gpu_uuid) if gpu_uuid else None,
        "clocks_policy": clocks_policy,
        "power_limit_watts": power_limit,
        "persistence_mode": persistence,
        "mig": mig_str,
        "manual": False,
    }


# ---------------------------------------------------------------------------
# Software versions (importlib.metadata)
# ---------------------------------------------------------------------------

_TRACKED_PACKAGES: dict[str, str] = {
    # key in output -> PyPI / importlib.metadata distribution name
    "pytorch": "torch",
    "triton": "triton",
    "pandas": "pandas",
    "cudf": "cudf",
    "numpy": "numpy",
    "pyarrow": "pyarrow",
}


def collect_software_info() -> dict[str, Any]:
    """Collect Python and framework versions via ``importlib.metadata``."""
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "manual": False,
    }
    for key, dist_name in _TRACKED_PACKAGES.items():
        try:
            info[key] = pkg_version(dist_name)
        except PackageNotFoundError:
            info[key] = None
    return info


# ---------------------------------------------------------------------------
# Strict-mode validation (§33.2)
# ---------------------------------------------------------------------------

_REQUIRED_HOST_FIELDS = ("os", "kernel", "cpu", "numa_nodes", "memory_gb")
_REQUIRED_GPU_FIELDS = (
    "gpu_name",
    "driver",
    "compute_capability",
    "clocks_policy",
    "power_limit_watts",
    "persistence_mode",
)


def validate_strict(report: dict[str, Any]) -> list[str]:
    """Return a list of errors for strict-mode validation.

    Strict mode (plan §33.2) requires all host fields populated, GPU
    present with full metadata, and Python version recorded.
    """
    errors: list[str] = []

    # Host fields
    host = report.get("host", {})
    for fld in _REQUIRED_HOST_FIELDS:
        if host.get(fld) is None:
            errors.append(f"host.{fld}: required field is missing")

    # GPU must be present
    gpu = report.get("gpu", {})
    if gpu.get("status") != "present":
        errors.append("gpu: GPU is absent; strict mode requires GPU metadata (§33.2)")
    else:
        for fld in _REQUIRED_GPU_FIELDS:
            if gpu.get(fld) is None:
                errors.append(f"gpu.{fld}: required field is missing")

    # Software
    sw = report.get("software", {})
    if not sw.get("python"):
        errors.append("software.python: required field is missing")

    return errors


# ---------------------------------------------------------------------------
# Top-level run_doctor
# ---------------------------------------------------------------------------


@dataclass
class EnvironmentReport:
    """Result of ``run_doctor``."""

    data: dict[str, Any]
    errors: list[str] = field(default_factory=list)
    exit_code: int = 0


def run_doctor(
    *,
    strict: bool = False,
    output: str | Path | None = None,
) -> EnvironmentReport:
    """Run the full metadata collection pipeline.

    If ``strict`` is True, validation errors are collected and the report's
    ``exit_code`` is set to 1 when any validation fails.

    If ``output`` is given, writes the report as JSON to that path.
    """
    data: dict[str, Any] = {
        "host": collect_host_info(),
        "gpu": collect_gpu_info(),
        "software": collect_software_info(),
    }

    errors: list[str] = []
    if strict:
        errors = validate_strict(data)

    exit_code = 1 if errors else 0

    if output is not None:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, indent=2) + "\n")

    return EnvironmentReport(data=data, errors=errors, exit_code=exit_code)

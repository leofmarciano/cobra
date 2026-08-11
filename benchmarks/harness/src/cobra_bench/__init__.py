"""cobra-bench — the Project Cobra benchmark harness (plan §33).

This package has zero dependencies on Cobra internals: it can measure any
Python callable, and is designed to outlive any particular compiler
prototype.
"""

from cobra_bench.doctor import (
    EnvironmentReport,
    collect_gpu_info,
    collect_host_info,
    collect_software_info,
    run_doctor,
    validate_strict,
)
from cobra_bench.manifest import (
    BenchmarkManifest,
    CorrectnessInfo,
    CudaInfo,
    HostInfo,
    ManifestError,
    ProtocolInfo,
    SoftwareInfo,
    VariantSpec,
    WorkloadSpec,
    load_manifest,
)

__version__ = "0.0.1.dev0"

__all__ = [
    "BenchmarkManifest",
    "CorrectnessInfo",
    "CudaInfo",
    "EnvironmentReport",
    "HostInfo",
    "ManifestError",
    "ProtocolInfo",
    "SoftwareInfo",
    "VariantSpec",
    "WorkloadSpec",
    "__version__",
    "collect_gpu_info",
    "collect_host_info",
    "collect_software_info",
    "load_manifest",
    "run_doctor",
    "validate_strict",
]

"""Benchmark manifest schema (plan §33.1): typed dataclasses + YAML loader.

A manifest describes a benchmark run's identity, its host/CUDA/software
metadata, the measurement protocol, and the workloads/variants to execute.
`cobra-bench doctor` captures host/cuda/software metadata directly where
possible; a field that was instead typed in by hand must be marked
``manual: true`` on its section. Strict mode (used for release evidence)
rejects any manifest containing hand-entered metadata (plan §33.1, last
paragraph).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml

_ENTRYPOINT_RE = re.compile(r"^[A-Za-z_][\w]*(\.[A-Za-z_][\w]*)*:[A-Za-z_][\w]*$")


class ManifestError(Exception):
    """Raised when a manifest dict fails validation.

    ``errors`` collects every problem found (as ``"<field.path>: <message>"``
    strings) so callers get field-level feedback in one pass instead of
    stopping at the first mistake.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


@dataclass
class HostInfo:
    """Host metadata (plan §33.1 ``host:`` section)."""

    hostname_alias: str | None = None
    os: str | None = None
    kernel: str | None = None
    cpu: str | None = None
    numa_nodes: int | None = None
    memory_gb: float | None = None
    manual: bool = False


@dataclass
class CudaInfo:
    """CUDA/GPU metadata (plan §33.1 ``cuda:`` section)."""

    driver: str | None = None
    toolkit: str | None = None
    gpu_name: str | None = None
    gpu_uuid_hash: str | None = None
    compute_capability: str | None = None
    clocks_policy: str | None = None
    power_limit_watts: float | None = None
    persistence_mode: bool | None = None
    mig: str | None = None
    manual: bool = False


@dataclass
class SoftwareInfo:
    """Software/framework versions (plan §33.1 ``software:`` section)."""

    python: str | None = None
    pytorch: str | None = None
    triton: str | None = None
    pandas: str | None = None
    cudf: str | None = None
    numpy: str | None = None
    pyarrow: str | None = None
    manual: bool = False


@dataclass
class ProtocolInfo:
    """Measurement protocol configuration (plan §33.1 ``protocol:`` section)."""

    warmup_policy: str = "stability"
    warmup_samples: int = 5
    minimum_samples: int = 30
    configuration_order: str = "randomized"
    correctness_required: bool = True
    confidence_interval: str = "bootstrap-95"


@dataclass
class CorrectnessInfo:
    """Correctness oracle configuration (plan §33.4)."""

    comparator: str | None = None
    rtol_by_dtype: dict[str, float] = field(default_factory=dict)
    atol_by_dtype: dict[str, float] = field(default_factory=dict)
    # ``None`` means that a workload override did not specify a value.  The
    # effective global default is applied by ``BenchmarkManifest.correctness_for``.
    equal_nan: bool | None = None


@dataclass
class VariantSpec:
    """One benchmarked variant of a workload."""

    name: str
    entrypoint: str
    manual: bool = False


@dataclass
class WorkloadSpec:
    """A named workload and the variants to compare."""

    name: str
    variants: list[VariantSpec] = field(default_factory=list)
    input_fingerprint: str | None = None
    correctness: CorrectnessInfo | None = None


@dataclass
class BenchmarkManifest:
    """The full §33.1 manifest: run identity, environment, protocol, workloads."""

    run_id: str
    suite: str
    commit: str | None = None
    workload_commit: str | None = None
    container_digest: str | None = None
    host: HostInfo = field(default_factory=HostInfo)
    cuda: CudaInfo = field(default_factory=CudaInfo)
    software: SoftwareInfo = field(default_factory=SoftwareInfo)
    protocol: ProtocolInfo = field(default_factory=ProtocolInfo)
    correctness: CorrectnessInfo | None = None
    workloads: list[WorkloadSpec] = field(default_factory=list)

    def correctness_for(self, workload: WorkloadSpec) -> CorrectnessInfo:
        """Return global correctness settings merged with workload overrides."""
        base = self.correctness or CorrectnessInfo()
        override = workload.correctness
        equal_nan = base.equal_nan if base.equal_nan is not None else True
        if override is None:
            return CorrectnessInfo(
                comparator=base.comparator,
                rtol_by_dtype=dict(base.rtol_by_dtype),
                atol_by_dtype=dict(base.atol_by_dtype),
                equal_nan=equal_nan,
            )
        return CorrectnessInfo(
            comparator=override.comparator if override.comparator is not None else base.comparator,
            rtol_by_dtype={**base.rtol_by_dtype, **override.rtol_by_dtype},
            atol_by_dtype={**base.atol_by_dtype, **override.atol_by_dtype},
            equal_nan=override.equal_nan if override.equal_nan is not None else equal_nan,
        )


def _type_name(value: Any) -> str:
    return type(value).__name__


def _pop_field(
    data: dict[str, Any],
    key: str,
    expected: type,
    path: str,
    errors: list[str],
    *,
    required: bool = False,
    default: Any = None,
) -> Any:
    """Pop ``key`` from ``data``, validating its type, recording field errors."""
    if key not in data or data[key] is None:
        data.pop(key, None)
        if required:
            errors.append(f"{path}.{key}: required field is missing")
        return default
    value = data.pop(key)
    if expected is float and isinstance(value, int) and not isinstance(value, bool):
        value = float(value)
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        errors.append(f"{path}.{key}: expected {expected.__name__}, got {_type_name(value)}")
        return default
    return value


def _reject_unknown(data: dict[str, Any], path: str, errors: list[str]) -> None:
    for key in data:
        errors.append(f"{path}.{key}: unknown field")


def _build_host(raw: Any, path: str, errors: list[str], *, strict: bool) -> HostInfo:
    data = dict(raw) if isinstance(raw, dict) else {}
    if raw is not None and not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        data = {}
    info = HostInfo(
        hostname_alias=_pop_field(data, "hostname_alias", str, path, errors),
        os=_pop_field(data, "os", str, path, errors),
        kernel=_pop_field(data, "kernel", str, path, errors),
        cpu=_pop_field(data, "cpu", str, path, errors),
        numa_nodes=_pop_field(data, "numa_nodes", int, path, errors),
        memory_gb=_pop_field(data, "memory_gb", float, path, errors),
        manual=bool(_pop_field(data, "manual", bool, path, errors, default=False)),
    )
    _reject_unknown(data, path, errors)
    if strict and info.manual:
        errors.append(
            f"{path}.manual: hand-entered metadata is rejected in strict mode (plan §33.1)"
        )
    return info


def _build_cuda(raw: Any, path: str, errors: list[str], *, strict: bool) -> CudaInfo:
    data = dict(raw) if isinstance(raw, dict) else {}
    if raw is not None and not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        data = {}
    info = CudaInfo(
        driver=_pop_field(data, "driver", str, path, errors),
        toolkit=_pop_field(data, "toolkit", str, path, errors),
        gpu_name=_pop_field(data, "gpu_name", str, path, errors),
        gpu_uuid_hash=_pop_field(data, "gpu_uuid_hash", str, path, errors),
        compute_capability=_pop_field(data, "compute_capability", str, path, errors),
        clocks_policy=_pop_field(data, "clocks_policy", str, path, errors),
        power_limit_watts=_pop_field(data, "power_limit_watts", float, path, errors),
        persistence_mode=_pop_field(data, "persistence_mode", bool, path, errors),
        mig=_pop_field(data, "mig", str, path, errors),
        manual=bool(_pop_field(data, "manual", bool, path, errors, default=False)),
    )
    _reject_unknown(data, path, errors)
    if strict and info.manual:
        errors.append(
            f"{path}.manual: hand-entered metadata is rejected in strict mode (plan §33.1)"
        )
    return info


def _build_software(raw: Any, path: str, errors: list[str], *, strict: bool) -> SoftwareInfo:
    data = dict(raw) if isinstance(raw, dict) else {}
    if raw is not None and not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        data = {}
    info = SoftwareInfo(
        python=_pop_field(data, "python", str, path, errors),
        pytorch=_pop_field(data, "pytorch", str, path, errors),
        triton=_pop_field(data, "triton", str, path, errors),
        pandas=_pop_field(data, "pandas", str, path, errors),
        cudf=_pop_field(data, "cudf", str, path, errors),
        numpy=_pop_field(data, "numpy", str, path, errors),
        pyarrow=_pop_field(data, "pyarrow", str, path, errors),
        manual=bool(_pop_field(data, "manual", bool, path, errors, default=False)),
    )
    _reject_unknown(data, path, errors)
    if strict and info.manual:
        errors.append(
            f"{path}.manual: hand-entered metadata is rejected in strict mode (plan §33.1)"
        )
    return info


_VALID_WARMUP_POLICIES = {"stability", "fixed"}
_VALID_ORDER_POLICIES = {"randomized", "fixed"}


def _build_protocol(raw: Any, path: str, errors: list[str]) -> ProtocolInfo:
    data = dict(raw) if isinstance(raw, dict) else {}
    if raw is not None and not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        data = {}
    defaults = ProtocolInfo()
    info = ProtocolInfo(
        warmup_policy=_pop_field(
            data, "warmup_policy", str, path, errors, default=defaults.warmup_policy
        ),
        warmup_samples=_pop_field(
            data, "warmup_samples", int, path, errors, default=defaults.warmup_samples
        ),
        minimum_samples=_pop_field(
            data, "minimum_samples", int, path, errors, default=defaults.minimum_samples
        ),
        configuration_order=_pop_field(
            data,
            "configuration_order",
            str,
            path,
            errors,
            default=defaults.configuration_order,
        ),
        correctness_required=_pop_field(
            data,
            "correctness_required",
            bool,
            path,
            errors,
            default=defaults.correctness_required,
        ),
        confidence_interval=_pop_field(
            data,
            "confidence_interval",
            str,
            path,
            errors,
            default=defaults.confidence_interval,
        ),
    )
    _reject_unknown(data, path, errors)
    if info.warmup_policy not in _VALID_WARMUP_POLICIES:
        errors.append(
            f"{path}.warmup_policy: must be one of {sorted(_VALID_WARMUP_POLICIES)}, "
            f"got {info.warmup_policy!r}"
        )
    if info.configuration_order not in _VALID_ORDER_POLICIES:
        errors.append(
            f"{path}.configuration_order: must be one of {sorted(_VALID_ORDER_POLICIES)}, "
            f"got {info.configuration_order!r}"
        )
    if info.minimum_samples < 1:
        errors.append(f"{path}.minimum_samples: must be >= 1, got {info.minimum_samples}")
    if info.warmup_samples < 1:
        errors.append(f"{path}.warmup_samples: must be >= 1, got {info.warmup_samples}")
    return info


def _build_correctness(
    raw: Any,
    path: str,
    errors: list[str],
    *,
    default_equal_nan: bool | None = True,
) -> CorrectnessInfo | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        return None
    data = dict(raw)
    rtol = data.pop("rtol_by_dtype", {}) or {}
    atol = data.pop("atol_by_dtype", {}) or {}
    if not isinstance(rtol, dict):
        errors.append(f"{path}.rtol_by_dtype: expected a mapping, got {_type_name(rtol)}")
        rtol = {}
    if not isinstance(atol, dict):
        errors.append(f"{path}.atol_by_dtype: expected a mapping, got {_type_name(atol)}")
        atol = {}
    info = CorrectnessInfo(
        comparator=_pop_field(data, "comparator", str, path, errors),
        rtol_by_dtype={str(k): float(v) for k, v in rtol.items()},
        atol_by_dtype={str(k): float(v) for k, v in atol.items()},
        equal_nan=_pop_field(
            data,
            "equal_nan",
            bool,
            path,
            errors,
            default=default_equal_nan,
        ),
    )
    _reject_unknown(data, path, errors)
    return info


def _build_variant(raw: Any, path: str, errors: list[str]) -> VariantSpec | None:
    if not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        return None
    data = dict(raw)
    name = _pop_field(data, "name", str, path, errors, required=True)
    entrypoint = _pop_field(data, "entrypoint", str, path, errors, required=True)
    manual = bool(_pop_field(data, "manual", bool, path, errors, default=False))
    _reject_unknown(data, path, errors)
    if entrypoint is not None and not _ENTRYPOINT_RE.match(entrypoint):
        errors.append(
            f"{path}.entrypoint: must look like 'package.module:callable', got {entrypoint!r}"
        )
    if name is None or entrypoint is None:
        return None
    return VariantSpec(name=name, entrypoint=entrypoint, manual=manual)


def _build_workload(raw: Any, path: str, errors: list[str]) -> WorkloadSpec | None:
    if not isinstance(raw, dict):
        errors.append(f"{path}: expected a mapping, got {_type_name(raw)}")
        return None
    data = dict(raw)
    name = _pop_field(data, "name", str, path, errors, required=True)
    raw_variants = data.pop("variants", None)
    input_fingerprint = _pop_field(data, "input_fingerprint", str, path, errors)
    correctness = _build_correctness(
        data.pop("correctness", None),
        f"{path}.correctness",
        errors,
        default_equal_nan=None,
    )
    variants: list[VariantSpec] = []
    if raw_variants is None:
        errors.append(f"{path}.variants: required field is missing")
    elif not isinstance(raw_variants, list):
        errors.append(f"{path}.variants: expected a list, got {_type_name(raw_variants)}")
    else:
        for index, raw_variant in enumerate(raw_variants):
            variant = _build_variant(raw_variant, f"{path}.variants[{index}]", errors)
            if variant is not None:
                variants.append(variant)
    _reject_unknown(data, path, errors)
    if name is None:
        return None
    return WorkloadSpec(
        name=name,
        variants=variants,
        input_fingerprint=input_fingerprint,
        correctness=correctness,
    )


def manifest_from_dict(data: dict[str, Any], *, strict: bool = False) -> BenchmarkManifest:
    """Validate a raw manifest dict and build a `BenchmarkManifest`.

    Collects every field-level problem before raising `ManifestError`, so a
    single invalid manifest reports all of its mistakes at once.
    """
    if not isinstance(data, dict):
        raise ManifestError([f"<root>: expected a mapping, got {_type_name(data)}"])

    remaining = dict(data)
    errors: list[str] = []

    run_id = _pop_field(remaining, "run_id", str, "<root>", errors, required=True)
    suite = _pop_field(remaining, "suite", str, "<root>", errors, required=True)
    commit = _pop_field(remaining, "commit", str, "<root>", errors)
    workload_commit = _pop_field(remaining, "workload_commit", str, "<root>", errors)
    container_digest = _pop_field(remaining, "container_digest", str, "<root>", errors)

    host = _build_host(remaining.pop("host", None), "host", errors, strict=strict)
    cuda = _build_cuda(remaining.pop("cuda", None), "cuda", errors, strict=strict)
    software = _build_software(remaining.pop("software", None), "software", errors, strict=strict)
    protocol = _build_protocol(remaining.pop("protocol", None), "protocol", errors)
    correctness = _build_correctness(remaining.pop("correctness", None), "correctness", errors)

    raw_workloads = remaining.pop("workloads", None)
    workloads: list[WorkloadSpec] = []
    if raw_workloads is not None:
        if not isinstance(raw_workloads, list):
            errors.append(f"workloads: expected a list, got {_type_name(raw_workloads)}")
        else:
            for index, raw_workload in enumerate(raw_workloads):
                workload = _build_workload(raw_workload, f"workloads[{index}]", errors)
                if workload is not None:
                    workloads.append(workload)

    _reject_unknown(remaining, "<root>", errors)

    if errors:
        raise ManifestError(errors)

    assert run_id is not None
    assert suite is not None
    return BenchmarkManifest(
        run_id=run_id,
        suite=suite,
        commit=commit,
        workload_commit=workload_commit,
        container_digest=container_digest,
        host=host,
        cuda=cuda,
        software=software,
        protocol=protocol,
        correctness=correctness,
        workloads=workloads,
    )


def _dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        result = {}
        for f in fields(value):
            item = _dataclass_to_dict(getattr(value, f.name))
            if item is not None:
                result[f.name] = item
        return result
    if isinstance(value, list):
        return [_dataclass_to_dict(item) for item in value]
    return value


def manifest_to_dict(manifest: BenchmarkManifest) -> dict[str, Any]:
    """Serialize a `BenchmarkManifest` back to a plain, YAML-safe dict."""
    result = _dataclass_to_dict(manifest)
    assert isinstance(result, dict)
    return result


def load_manifest(path: str | Path, *, strict: bool = False) -> BenchmarkManifest:
    """Load and validate a manifest YAML file.

    Raises `ManifestError` (with field-level messages in `.errors`) if the
    manifest is malformed, or if `strict` is true and the manifest contains
    hand-entered (`manual: true`) metadata.
    """
    text = Path(path).read_text()
    raw = yaml.safe_load(text) or {}
    return manifest_from_dict(raw, strict=strict)


def dump_manifest(manifest: BenchmarkManifest, path: str | Path) -> None:
    """Write a `BenchmarkManifest` to a YAML file."""
    Path(path).write_text(yaml.safe_dump(manifest_to_dict(manifest), sort_keys=False))

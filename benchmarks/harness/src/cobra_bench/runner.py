"""Workload invocation and sample collection for ``cobra-bench run`` (§33.3-33.6).

This module is intentionally independent of Cobra internals: it loads arbitrary
Python entrypoints specified in a manifest and measures them with the timing
protocol engine.
"""

from __future__ import annotations

import importlib
import json
import random
import subprocess
import sys
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from cobra_bench.manifest import BenchmarkManifest, VariantSpec, WorkloadSpec
from cobra_bench.results import SampleRecord, write_jsonl
from cobra_bench.timing import (
    CorrectnessFailed,
    TimingConfig,
    TimingEngine,
    WarmupFailure,
)


def resolve_entrypoint(entrypoint: str) -> Callable[[], Any]:
    """Import ``module.path:callable`` and return the callable object."""
    if ":" not in entrypoint:
        msg = f"entrypoint must look like 'module:callable', got {entrypoint!r}"
        raise ValueError(msg)
    module_name, callable_name = entrypoint.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        msg = f"cannot import module {module_name!r} for entrypoint {entrypoint!r}: {exc}"
        raise ValueError(msg) from exc
    try:
        obj = getattr(module, callable_name)
    except AttributeError as exc:
        msg = f"module {module_name!r} has no callable {callable_name!r}"
        raise ValueError(msg) from exc
    if not callable(obj):
        msg = f"entrypoint {entrypoint!r} resolved to non-callable {type(obj).__name__}"
        raise ValueError(msg)
    return cast(Callable[[], Any], obj)


def _load_expected(variant: VariantSpec) -> Any:
    """Run a variant once outside the timing loop to obtain the expected result."""
    return resolve_entrypoint(variant.entrypoint)()


def _exact_oracle(expected: Any) -> Callable[[Any], bool]:
    def check(result: Any) -> bool:
        return bool(result == expected)

    return check


def build_oracle(
    workload: WorkloadSpec,
    baseline_variant: VariantSpec,
    *,
    comparator: str | None = "exact",
) -> Callable[[Any], bool]:
    """Build a correctness oracle that compares a result to the baseline.

    ``comparator`` currently supports ``"exact"``.  Future comparators (tensor,
    approximate) will be added when real workloads arrive (S02).
    """
    expected = _load_expected(baseline_variant)
    if comparator == "exact":
        return _exact_oracle(expected)
    msg = f"unsupported correctness comparator: {comparator!r}"
    raise ValueError(msg)


@dataclass
class CorrectnessReport:
    """Result of ``cobra-bench verify`` for one workload."""

    workload: str
    passed: bool = False
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload": self.workload,
            "passed": self.passed,
            "results": self.results,
            "errors": self.errors,
        }


def verify_workload(
    workload: WorkloadSpec,
    variants: list[str] | None = None,
    *,
    comparator: str | None = "exact",
) -> CorrectnessReport:
    """Run each requested variant once and compare outputs."""
    report = CorrectnessReport(workload=workload.name)
    selected = _select_variants(workload, variants)
    if not selected:
        report.errors.append("no variants selected")
        report.passed = False
        return report

    baseline_name, baseline_variant = selected[0]
    expected = _load_expected(baseline_variant)
    oracle = _exact_oracle(expected)

    report.results[baseline_name] = expected
    for name, variant in selected:
        actual = resolve_entrypoint(variant.entrypoint)()
        report.results[name] = actual
        if not oracle(actual):
            report.errors.append(f"variant {name!r} output {actual!r} != baseline {expected!r}")

    report.passed = not report.errors
    return report


def _select_variants(
    workload: WorkloadSpec,
    variants: list[str] | None,
) -> list[tuple[str, VariantSpec]]:
    """Return (name, VariantSpec) pairs filtered by ``variants`` if given."""
    selected: list[tuple[str, VariantSpec]] = []
    by_name = {v.name: v for v in workload.variants}
    order = [v.name for v in workload.variants] if variants is None else variants
    for name in order:
        spec = by_name.get(name)
        if spec is None:
            raise ValueError(f"workload {workload.name!r} has no variant {name!r}")
        selected.append((name, spec))
    return selected


@dataclass
class TimingOptions:
    """User-supplied overrides for the timing protocol."""

    phase: str = "warm"
    min_samples: int | None = None
    max_warmup: int | None = None
    no_oracle: bool = False
    seed: int | None = None


def _timing_config(
    manifest: BenchmarkManifest,
    options: TimingOptions,
) -> TimingConfig:
    protocol = manifest.protocol
    return TimingConfig(
        warmup_policy=protocol.warmup_policy,
        minimum_samples=options.min_samples or protocol.minimum_samples,
        max_warmup=options.max_warmup or 100,
        randomize_order=protocol.configuration_order == "randomized",
        correctness_required=not options.no_oracle,
    )


def run_workload(
    manifest: BenchmarkManifest,
    workload: WorkloadSpec,
    variants: list[str] | None,
    options: TimingOptions,
) -> list[SampleRecord]:
    """Collect timing samples for one workload and return sample records."""
    selected = _select_variants(workload, variants)
    if not selected:
        return []

    run_id = manifest.run_id
    phase = options.phase
    fingerprint = workload.input_fingerprint or workload.name
    config = _timing_config(manifest, options)

    records: list[SampleRecord] = []

    if phase == "warm":
        engine = TimingEngine(config=config)
        baseline_name, baseline_variant = selected[0]

        if not options.no_oracle:
            oracle = build_oracle(
                workload,
                baseline_variant,
                comparator=manifest.correctness.comparator if manifest.correctness else "exact",
            )
        else:
            warnings.warn(
                "--no-oracle: timing samples are NOT checked for correctness; "
                "any speedup claim is invalid (plan §33.4, §33.11).",
                stacklevel=2,
            )
            oracle = None

        ordered = engine.randomize_variants(selected, seed=options.seed)
        sample_index = 0
        for _name, variant in ordered:
            try:
                results = engine.run_warm(
                    resolve_entrypoint(variant.entrypoint),
                    oracle=oracle,
                )
            except (WarmupFailure, CorrectnessFailed) as exc:
                msg = (
                    f"{phase} timing failed for workload {workload.name!r} "
                    f"variant {variant.name!r}: {exc}"
                )
                raise RuntimeError(msg) from exc

            for result in results:
                records.append(
                    SampleRecord(
                        run_id=run_id,
                        workload=workload.name,
                        variant=variant.name,
                        phase=phase,
                        sample=sample_index,
                        correct=oracle is not None,
                        wall_time_ns=int(result.elapsed_s * 1_000_000_000),
                        tags={"input_fingerprint": fingerprint},
                    )
                )
                sample_index += 1

    elif phase == "cold":
        if not options.no_oracle:
            msg = (
                "cold-path timing does not yet run per-sample correctness oracles; "
                "pass --no-oracle to proceed without correctness validation "
                "(invalidates any speedup claim)"
            )
            raise ValueError(msg)
        records = _run_cold(workload, selected, run_id, fingerprint, config)

    else:
        msg = f"unsupported phase: {phase!r} (expected 'warm' or 'cold')"
        raise ValueError(msg)

    return records


def _run_cold(
    workload: WorkloadSpec,
    selected: list[tuple[str, VariantSpec]],
    run_id: str,
    fingerprint: str,
    config: TimingConfig,
) -> list[SampleRecord]:
    """Cold-path timing using one subprocess per sample (§33.5)."""
    records: list[SampleRecord] = []
    ordered = list(selected)
    if config.randomize_order:
        random.shuffle(ordered)
    sample_index = 0
    for _name, variant in ordered:
        for _ in range(config.minimum_samples):
            t0 = time.perf_counter()
            proc = subprocess.run(
                [sys.executable, "-c", _cold_invoke(variant.entrypoint)],
                capture_output=True,
                text=True,
                check=False,
            )
            t1 = time.perf_counter()
            elapsed_ns = int((t1 - t0) * 1_000_000_000)
            records.append(
                SampleRecord(
                    run_id=run_id,
                    workload=workload.name,
                    variant=variant.name,
                    phase="cold",
                    sample=sample_index,
                    correct=proc.returncode == 0,
                    wall_time_ns=elapsed_ns,
                    tags={"input_fingerprint": fingerprint},
                )
            )
            sample_index += 1
    return records


def _cold_invoke(entrypoint: str) -> str:
    """Return a Python one-liner that imports and calls the entrypoint."""
    module_name, callable_name = entrypoint.split(":", 1)
    return f"import {module_name}; result = {module_name}.{callable_name}(); print(result)"


def run_suite(
    manifest: BenchmarkManifest,
    variants_by_workload: dict[str, list[str] | None],
    options: TimingOptions,
) -> list[SampleRecord]:
    """Run every requested workload in the manifest and concatenate records."""
    all_records: list[SampleRecord] = []
    for workload in manifest.workloads:
        variants = variants_by_workload.get(workload.name)
        all_records.extend(run_workload(manifest, workload, variants, options))
    return all_records


def run_and_record(
    manifest: BenchmarkManifest,
    variants_by_workload: dict[str, list[str] | None],
    options: TimingOptions,
    output_dir: Path,
) -> list[SampleRecord]:
    """Run the suite and write ``samples.jsonl`` into ``output_dir``."""
    records = run_suite(manifest, variants_by_workload, options)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(records, output_dir / "samples.jsonl")
    return records


def write_correctness_report(
    reports: list[CorrectnessReport],
    output_dir: Path,
) -> None:
    """Write ``correctness.json`` containing all workload correctness reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "passed": all(r.passed for r in reports),
        "workloads": [r.to_dict() for r in reports],
    }
    (output_dir / "correctness.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

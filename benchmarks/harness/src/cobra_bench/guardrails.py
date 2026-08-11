"""Benchmark anti-pattern guardrails (plan §33.11).

These checks catch invalid comparisons and under-powered measurements before
results are used for performance claims.
"""

from __future__ import annotations

import warnings
from typing import Any

from cobra_bench.results import SampleRecord


class GuardrailError(RuntimeError):
    """Raised when an anti-pattern makes a comparison invalid."""

    def __init__(self, rule: str, message: str) -> None:
        self.rule = rule
        self.message = message
        super().__init__(f"guardrail '{rule}' violated: {message}")


def check_mixed_phase(records: list[SampleRecord]) -> None:
    """Refuse comparisons that mix cold and warm samples (§33.11)."""
    phases = {r.phase for r in records if r.phase is not None}
    if len(phases) > 1:
        raise GuardrailError(
            "mixed_phase",
            f"samples contain mixed phases {sorted(phases)}; "
            "comparing cold and warm timings is invalid (§33.11).",
        )


def check_input_fingerprint_consistency(records: list[SampleRecord]) -> None:
    """Refuse comparisons of variants with different input fingerprints."""
    by_workload: dict[str, dict[str, set[str]]] = {}
    for record in records:
        workload = record.workload
        variant = record.variant
        fingerprint = record.tags.get("input_fingerprint")
        if fingerprint is None:
            continue
        by_workload.setdefault(workload, {}).setdefault(variant, set()).add(fingerprint)

    for workload, variants in by_workload.items():
        fingerprints: set[str] = set()
        for variant_fps in variants.values():
            fingerprints.update(variant_fps)
        if len(fingerprints) > 1:
            raise GuardrailError(
                "input_fingerprint",
                f"workload {workload!r} has variants with differing input "
                f"fingerprints {sorted(fingerprints)}; comparing different inputs "
                "is invalid (§33.11).",
            )


def warn_low_sample_count(records: list[SampleRecord], min_samples: int = 30) -> None:
    """Warn when any variant has fewer than ``min_samples`` timed samples."""
    from collections import Counter

    counts: Counter[tuple[str, str]] = Counter()
    for record in records:
        if record.wall_time_ns is not None:
            counts[(record.workload, record.variant)] += 1

    for (workload, variant), n in counts.items():
        if n < min_samples:
            warnings.warn(
                f"variant {variant!r} of workload {workload!r} has only {n} samples; "
                f"{min_samples} are recommended for stable statistics (§33.6).",
                stacklevel=2,
            )


def apply_analysis_guardrails(records: list[SampleRecord]) -> None:
    """Run all anti-pattern checks before analyzing samples."""
    check_mixed_phase(records)
    check_input_fingerprint_consistency(records)
    warn_low_sample_count(records)


def check_summary_phases(candidate: dict[str, Any], baseline: dict[str, Any]) -> None:
    """Refuse comparing summaries from different measurement phases."""
    cand_phase = candidate.get("phase")
    base_phase = baseline.get("phase")
    if cand_phase is not None and base_phase is not None and cand_phase != base_phase:
        raise GuardrailError(
            "mixed_phase",
            f"candidate phase {cand_phase!r} != baseline phase {base_phase!r}; "
            "comparing cold and warm summaries is invalid (§33.11).",
        )


def check_summary_fingerprints(candidate: dict[str, Any], baseline: dict[str, Any]) -> None:
    """Refuse comparing summaries whose workloads used different inputs."""
    cand_fps = _workload_fingerprints(candidate)
    base_fps = _workload_fingerprints(baseline)
    common = set(cand_fps) & set(base_fps)
    for workload in common:
        if cand_fps[workload] != base_fps[workload]:
            raise GuardrailError(
                "input_fingerprint",
                f"workload {workload!r} has different input fingerprints in candidate "
                f"({cand_fps[workload]!r}) and baseline ({base_fps[workload]!r}); "
                "comparing different inputs is invalid (§33.11).",
            )


def _workload_fingerprints(summary: dict[str, Any]) -> dict[str, str]:
    """Extract workload -> input_fingerprint from a summary dict if present."""
    fingerprints: dict[str, str] = {}
    for workload in summary.get("workloads", []):
        name = workload.get("workload")
        fingerprint = workload.get("input_fingerprint")
        if name and fingerprint:
            fingerprints[name] = fingerprint
    return fingerprints


def apply_compare_guardrails(candidate: dict[str, Any], baseline: dict[str, Any]) -> None:
    """Run all anti-pattern checks before comparing two summaries."""
    check_summary_phases(candidate, baseline)
    check_summary_fingerprints(candidate, baseline)

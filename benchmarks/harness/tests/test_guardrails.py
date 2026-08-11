"""Tests for benchmark anti-pattern guardrails (cobra_bench.guardrails)."""

from __future__ import annotations

import warnings

import pytest
from cobra_bench.guardrails import (
    GuardrailError,
    apply_analysis_guardrails,
    apply_compare_guardrails,
    check_input_fingerprint_consistency,
    check_mixed_phase,
    check_summary_fingerprints,
    check_summary_phases,
    warn_low_sample_count,
)
from cobra_bench.results import SampleRecord


def _sample(
    phase: str = "warm",
    fingerprint: str = "f1",
    variant: str = "a",
    sample: int = 0,
) -> SampleRecord:
    return SampleRecord(
        run_id="r1",
        workload="w1",
        variant=variant,
        phase=phase,
        sample=sample,
        correct=True,
        wall_time_ns=100_000,
        tags={"input_fingerprint": fingerprint},
    )


class TestMixedPhaseGuardrail:
    def test_single_phase_is_allowed(self) -> None:
        records = [_sample(phase="warm") for _ in range(2)]
        check_mixed_phase(records)  # should not raise

    def test_mixed_phase_raises(self) -> None:
        records = [_sample(phase="warm"), _sample(phase="cold")]
        with pytest.raises(GuardrailError, match="mixed phases"):
            check_mixed_phase(records)


class TestInputFingerprintGuardrail:
    def test_same_fingerprint_is_allowed(self) -> None:
        records = [
            _sample(variant="a", fingerprint="f1"),
            _sample(variant="b", fingerprint="f1"),
        ]
        check_input_fingerprint_consistency(records)  # should not raise

    def test_different_fingerprints_raises(self) -> None:
        records = [
            _sample(variant="a", fingerprint="f1"),
            _sample(variant="b", fingerprint="f2"),
        ]
        with pytest.raises(GuardrailError, match="differing input fingerprints"):
            check_input_fingerprint_consistency(records)

    def test_missing_fingerprint_is_ignored(self) -> None:
        records = [
            SampleRecord(
                run_id="r1",
                workload="w1",
                variant="a",
                phase="warm",
                sample=0,
                correct=True,
                wall_time_ns=100_000,
            ),
            SampleRecord(
                run_id="r1",
                workload="w1",
                variant="b",
                phase="warm",
                sample=1,
                correct=True,
                wall_time_ns=100_000,
            ),
        ]
        check_input_fingerprint_consistency(records)  # should not raise


class TestLowSampleCountWarning:
    def test_warns_when_samples_below_threshold(self) -> None:
        records = [_sample(variant="a", sample=i) for i in range(5)]
        with pytest.warns(UserWarning, match="only 5 samples"):
            warn_low_sample_count(records, min_samples=30)

    def test_no_warning_when_threshold_met(self) -> None:
        records = [_sample(variant="a", sample=i) for i in range(30)]
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            warn_low_sample_count(records, min_samples=30)


class TestApplyAnalysisGuardrails:
    def test_raises_for_mixed_phase(self) -> None:
        records = [_sample(phase="warm"), _sample(phase="cold")]
        with pytest.raises(GuardrailError, match="mixed phases"):
            apply_analysis_guardrails(records)

    def test_warns_for_low_sample_count(self) -> None:
        records = [_sample(variant="a", sample=i) for i in range(5)]
        with pytest.warns(UserWarning, match="only 5 samples"):
            apply_analysis_guardrails(records)


class TestCompareGuardrails:
    def test_same_phase_allowed(self) -> None:
        candidate = {"phase": "warm"}
        baseline = {"phase": "warm"}
        check_summary_phases(candidate, baseline)  # should not raise

    def test_different_phase_raises(self) -> None:
        candidate = {"phase": "warm"}
        baseline = {"phase": "cold"}
        with pytest.raises(GuardrailError, match="cold"):
            check_summary_phases(candidate, baseline)

    def test_different_fingerprints_raises(self) -> None:
        candidate = {
            "workloads": [
                {"workload": "w1", "input_fingerprint": "f1"},
            ]
        }
        baseline = {
            "workloads": [
                {"workload": "w1", "input_fingerprint": "f2"},
            ]
        }
        with pytest.raises(GuardrailError, match="different input fingerprints"):
            check_summary_fingerprints(candidate, baseline)

    def test_same_fingerprint_allowed(self) -> None:
        candidate = {
            "workloads": [
                {"workload": "w1", "input_fingerprint": "f1"},
            ]
        }
        baseline = {
            "workloads": [
                {"workload": "w1", "input_fingerprint": "f1"},
            ]
        }
        check_summary_fingerprints(candidate, baseline)

    def test_apply_compare_guardrails_propagates(self) -> None:
        candidate = {"phase": "warm", "workloads": []}
        baseline = {"phase": "cold", "workloads": []}
        with pytest.raises(GuardrailError, match="cold and warm"):
            apply_compare_guardrails(candidate, baseline)

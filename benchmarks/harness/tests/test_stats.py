"""Tests for benchmark statistics (plan §20.7, §33.8)."""

from __future__ import annotations

import random
import statistics
from typing import Any

import pytest
from cobra_bench.results import SampleRecord
from cobra_bench.stats import (
    VariantStats,
    analyze_samples,
    bootstrap_ci,
    bootstrap_ratio_ci,
    coefficient_of_variation,
    geometric_mean,
    p95,
    p99,
    percentile,
)


def _records_for_workload(
    variant: str,
    wall_times: list[int],
    workload: str = "dummy_add",
) -> list[SampleRecord]:
    return [
        SampleRecord(
            run_id="r1",
            workload=workload,
            variant=variant,
            phase="warm",
            sample=i,
            correct=True,
            wall_time_ns=t,
        )
        for i, t in enumerate(wall_times)
    ]


class TestDescriptiveStatistics:
    def test_percentile_known_values(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert percentile(values, 0.0) == 1.0
        assert percentile(values, 100.0) == 5.0
        assert percentile(values, 50.0) == 3.0
        # Even-length interpolation
        assert percentile([1.0, 2.0, 3.0, 4.0], 50.0) == 2.5

    def test_p95_and_p99(self) -> None:
        values = list(range(1, 101))
        assert p95(values) == pytest.approx(95.05)
        assert p99(values) == pytest.approx(99.01)

    def test_geometric_mean_known(self) -> None:
        assert geometric_mean([1.0, 10.0, 100.0]) == pytest.approx(10.0, rel=1e-12)

    def test_coefficient_of_variation(self) -> None:
        # sample stdev of [0,10,20,30,40] = sqrt(250) ≈ 15.811, mean = 20 => CV ≈ 0.7906
        values = [0.0, 10.0, 20.0, 30.0, 40.0]
        cv = coefficient_of_variation(values)
        assert cv is not None
        assert cv == pytest.approx(0.7906, rel=1e-3)

    def test_cv_returns_none_for_zero_mean(self) -> None:
        assert coefficient_of_variation([0.0, 0.0, 0.0]) is None


class TestBootstrap:
    def test_bootstrap_ci_median_known_distribution(self) -> None:
        """Median of a tight distribution should have a tight CI."""
        rng = random.Random(12345)
        values = [rng.gauss(100.0, 1.0) for _ in range(100)]
        low, high = bootstrap_ci(
            values,
            statistics.median,
            n_bootstrap=2000,
            confidence=0.95,
            seed=42,
        )
        sample_median = statistics.median(values)
        assert low <= sample_median <= high
        assert high - low < 1.0

    def test_bootstrap_ci_matches_reference_implementation(self) -> None:
        """Our percentile bootstrap should match a simple reference within tolerance."""
        rng = random.Random(42)
        values = [rng.expovariate(0.1) for _ in range(50)]

        def _reference_bootstrap(
            data: list[float],
            stat: Any,
            n: int,
            seed: int,
        ) -> tuple[float, float]:
            ref_rng = random.Random(seed)
            m = len(data)
            estimates = [stat([data[ref_rng.randrange(m)] for _ in range(m)]) for _ in range(n)]
            estimates.sort()
            return (estimates[int(n * 0.025)], estimates[int(n * 0.975)])

        low, high = bootstrap_ci(
            values,
            statistics.median,
            n_bootstrap=5000,
            confidence=0.95,
            seed=7,
        )
        ref_low, ref_high = _reference_bootstrap(values, statistics.median, 5000, 7)
        assert low == pytest.approx(ref_low, rel=1e-2)
        assert high == pytest.approx(ref_high, rel=1e-2)

    def test_bootstrap_ratio_ci_excludes_one_when_different(self) -> None:
        """A 2x speedup with enough samples should produce a CI excluding 1.0."""
        baseline = [100.0] * 40
        candidate = [50.0] * 40
        low, high = bootstrap_ratio_ci(
            baseline,
            candidate,
            n_bootstrap=2000,
            confidence=0.95,
            seed=1,
        )
        assert low > 1.0
        assert high > 1.0

    def test_bootstrap_ratio_ci_includes_one_when_equal(self) -> None:
        """Identical distributions should give a CI that includes 1.0."""
        rng = random.Random(99)
        values = [rng.gauss(100.0, 5.0) for _ in range(60)]
        low, high = bootstrap_ratio_ci(
            values,
            list(values),
            n_bootstrap=2000,
            confidence=0.95,
            seed=2,
        )
        assert low <= 1.0 <= high


class TestAnalyzeSamples:
    def test_analyze_speedup_significance(self) -> None:
        """Variant twice as fast as baseline should be marked significant."""
        baseline = [100_000] * 30
        candidate = [50_000] * 30
        records = _records_for_workload("a", baseline) + _records_for_workload("b", candidate)
        summary = analyze_samples(records, n_bootstrap=2000, seed=1)

        assert summary.suite_geomean_speedup == pytest.approx(2.0, rel=1e-6)

        workload = summary.workloads[0]
        assert workload.baseline_variant == "a"
        a_stats = next(v for v in workload.variants if v.variant == "a")
        b_stats = next(v for v in workload.variants if v.variant == "b")

        assert a_stats.speedup == 1.0
        assert a_stats.significant is False
        assert b_stats.speedup == pytest.approx(2.0, rel=1e-6)
        assert b_stats.significant is True

    def test_analyze_no_significance_for_equal_variants(self) -> None:
        rng = random.Random(10)
        values = [int(rng.gauss(100_000, 5_000)) for _ in range(40)]
        records = _records_for_workload("a", values) + _records_for_workload("b", list(values))
        summary = analyze_samples(records, n_bootstrap=2000, seed=3)
        b_stats = next(v for v in summary.workloads[0].variants if v.variant == "b")
        assert b_stats.significant is False

    def test_analyze_respects_missing_metric_as_none(self) -> None:
        records = [
            SampleRecord(
                run_id="r1",
                workload="w",
                variant="a",
                phase="warm",
                sample=i,
                correct=True,
                wall_time_ns=None,
            )
            for i in range(5)
        ]
        summary = analyze_samples(records, metric="wall_time_ns")
        stats = summary.workloads[0].variants[0]
        assert stats.n_samples == 0
        assert stats.n_missing == 5
        assert stats.median is None

    def test_analyze_multiple_workloads(self) -> None:
        records = (
            _records_for_workload("a", [100] * 30, workload="w1")
            + _records_for_workload("b", [50] * 30, workload="w1")
            + _records_for_workload("a", [200] * 30, workload="w2")
            + _records_for_workload("b", [100] * 30, workload="w2")
        )
        summary = analyze_samples(records, n_bootstrap=2000, seed=4)
        assert summary.suite_geomean_speedup == pytest.approx(2.0, rel=1e-6)

    def test_variant_stats_fields_present(self) -> None:
        records = _records_for_workload("a", [100_000] * 40) + _records_for_workload(
            "b", [80_000] * 40
        )
        summary = analyze_samples(records, n_bootstrap=2000, seed=5)
        stats = summary.workloads[0].variants[0]
        assert isinstance(stats, VariantStats)
        assert stats.median is not None
        assert stats.p95 is not None
        assert stats.p99 is not None
        assert stats.ci_low is not None
        assert stats.ci_high is not None

"""Statistical analysis helpers for benchmark samples (plan §20.7, §33.8).

All implementations use only the Python standard library so the harness stays
lightweight and deterministic given a fixed random seed.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass

from cobra_bench.results import SampleRecord


def _clean(values: list[int | float | None]) -> list[float]:
    """Drop ``None`` values and cast the remainder to float."""
    return [float(v) for v in values if v is not None]


def percentile(values: list[float], p: float) -> float:
    """Return the ``p``-th percentile using linear interpolation.

    ``p`` is expressed as a percentage, e.g. ``95.0`` for the 95th percentile.
    """
    if not values:
        raise ValueError("percentile requires at least one value")
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    lower = sorted_values[f]
    upper = sorted_values[c]
    return lower + (upper - lower) * (k - f)


def p95(values: list[float]) -> float:
    return percentile(values, 95.0)


def p99(values: list[float]) -> float:
    return percentile(values, 99.0)


def coefficient_of_variation(values: list[float]) -> float | None:
    """Return CV (stdev / mean), or ``None`` if the mean is zero."""
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    if mean == 0:
        return None
    return statistics.stdev(values) / mean


def geometric_mean(values: list[float]) -> float:
    """Geometric mean; raises ``StatisticsError`` on empty input."""
    return statistics.geometric_mean(values)


# ---------------------------------------------------------------------------
# Bootstrap confidence intervals
# ---------------------------------------------------------------------------


def bootstrap_ci(
    values: list[float],
    stat: Callable[[list[float]], float],
    *,
    n_bootstrap: int = 10000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float]:
    """Bootstrap percentile confidence interval for a univariate statistic."""
    if not values:
        raise ValueError("bootstrap_ci requires at least one value")
    rng = random.Random(seed)
    n = len(values)
    estimates: list[float] = []
    for _ in range(n_bootstrap):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        estimates.append(stat(resample))
    estimates.sort()
    alpha = 1.0 - confidence
    lower_idx = int(len(estimates) * (alpha / 2))
    upper_idx = int(len(estimates) * (1.0 - alpha / 2))
    # Clamp to valid indices for very small bootstrap counts.
    lower_idx = max(0, min(lower_idx, len(estimates) - 1))
    upper_idx = max(0, min(upper_idx, len(estimates) - 1))
    return (estimates[lower_idx], estimates[upper_idx])


def bootstrap_ratio_ci(
    baseline: list[float],
    candidate: list[float],
    *,
    n_bootstrap: int = 10000,
    confidence: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float]:
    """Bootstrap CI for ``median(baseline) / median(candidate)``.

    A speedup is labeled significant when this interval excludes 1.0.
    """
    if not baseline or not candidate:
        raise ValueError("bootstrap_ratio_ci requires non-empty groups")
    rng = random.Random(seed)
    n_base = len(baseline)
    n_cand = len(candidate)
    estimates: list[float] = []
    for _ in range(n_bootstrap):
        base_resample = [baseline[rng.randrange(n_base)] for _ in range(n_base)]
        cand_resample = [candidate[rng.randrange(n_cand)] for _ in range(n_cand)]
        base_med = statistics.median(base_resample)
        cand_med = statistics.median(cand_resample)
        if cand_med == 0:
            estimates.append(float("inf"))
        else:
            estimates.append(base_med / cand_med)
    estimates.sort()
    alpha = 1.0 - confidence
    lower_idx = int(len(estimates) * (alpha / 2))
    upper_idx = int(len(estimates) * (1.0 - alpha / 2))
    lower_idx = max(0, min(lower_idx, len(estimates) - 1))
    upper_idx = max(0, min(upper_idx, len(estimates) - 1))
    return (estimates[lower_idx], estimates[upper_idx])


# ---------------------------------------------------------------------------
# Sample-record statistics
# ---------------------------------------------------------------------------


@dataclass
class VariantStats:
    """Summary statistics for one workload/variant group."""

    workload: str
    variant: str
    metric: str
    n_samples: int
    n_missing: int
    median: float | None
    p95: float | None
    p99: float | None
    cv: float | None
    ci_low: float | None
    ci_high: float | None
    speedup: float | None
    speedup_ci_low: float | None
    speedup_ci_high: float | None
    significant: bool


@dataclass
class WorkloadSummary:
    """Per-workload summary including baseline-relative speedups."""

    workload: str
    metric: str
    baseline_variant: str
    variants: list[VariantStats]
    geomean_speedup: float | None


@dataclass
class SuiteSummary:
    """Top-level container returned by ``analyze_samples``."""

    metric: str
    confidence: float
    n_bootstrap: int
    seed: int | None
    workloads: list[WorkloadSummary]
    suite_geomean_speedup: float | None


def _variant_speedup(
    baseline_values: list[float],
    candidate_values: list[float],
    confidence: float,
    n_bootstrap: int,
    seed: int | None,
) -> tuple[float | None, float | None, float | None, bool]:
    """Return speedup, CI low, CI high, and significance flag."""
    if not baseline_values or not candidate_values:
        return None, None, None, False
    base_med = statistics.median(baseline_values)
    cand_med = statistics.median(candidate_values)
    if cand_med == 0:
        return None, None, None, False
    speedup = base_med / cand_med
    try:
        ci_low, ci_high = bootstrap_ratio_ci(
            baseline_values,
            candidate_values,
            n_bootstrap=n_bootstrap,
            confidence=confidence,
            seed=seed,
        )
    except ValueError:
        return speedup, None, None, False
    significant = ci_low > 1.0 or ci_high < 1.0
    return speedup, ci_low, ci_high, significant


def analyze_samples(
    records: list[SampleRecord],
    *,
    metric: str = "wall_time_ns",
    confidence: float = 0.95,
    n_bootstrap: int = 10000,
    seed: int | None = None,
    baseline_variant: str | None = None,
) -> SuiteSummary:
    """Compute per-variant and per-workload statistics from sample records.

    Parameters
    ----------
    records:
        Sample records produced by the harness.
    metric:
        Numeric field to summarize (default ``wall_time_ns``).
    confidence:
        Confidence level for bootstrap intervals (default 0.95).
    n_bootstrap:
        Number of bootstrap resamples (default 10_000).
    seed:
        Optional random seed for reproducible bootstrap intervals.
    baseline_variant:
        Variant to use as the baseline.  If ``None``, the first variant
        encountered (sorted by name) for each workload is the baseline.
    """
    if not records:
        return SuiteSummary(
            metric=metric,
            confidence=confidence,
            n_bootstrap=n_bootstrap,
            seed=seed,
            workloads=[],
            suite_geomean_speedup=None,
        )

    # Group records by workload, then variant.
    by_workload: dict[str, dict[str, list[SampleRecord]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        by_workload[record.workload][record.variant].append(record)

    workload_summaries: list[WorkloadSummary] = []
    all_workload_speedups: list[float] = []

    for workload in sorted(by_workload):
        variants = by_workload[workload]
        variant_order = sorted(variants)
        chosen_baseline = baseline_variant if baseline_variant is not None else variant_order[0]
        baseline_values = _clean([getattr(r, metric) for r in variants.get(chosen_baseline, [])])

        variant_stats_list: list[VariantStats] = []
        workload_speedups: list[float] = []

        for variant in variant_order:
            raw_values = [getattr(r, metric) for r in variants[variant]]
            values = _clean(raw_values)
            n_missing = len(raw_values) - len(values)

            if values:
                med = statistics.median(values)
                ci_low, ci_high = bootstrap_ci(
                    values,
                    statistics.median,
                    n_bootstrap=n_bootstrap,
                    confidence=confidence,
                    seed=seed,
                )
                p95_val = p95(values)
                p99_val = p99(values)
                cv_val = coefficient_of_variation(values)
            else:
                med = None
                ci_low = None
                ci_high = None
                p95_val = None
                p99_val = None
                cv_val = None

            speedup: float | None
            speedup_ci_low: float | None
            speedup_ci_high: float | None
            significant: bool
            if variant == chosen_baseline:
                speedup = 1.0
                speedup_ci_low = 1.0
                speedup_ci_high = 1.0
                significant = False
            else:
                speedup, speedup_ci_low, speedup_ci_high, significant = _variant_speedup(
                    baseline_values,
                    values,
                    confidence=confidence,
                    n_bootstrap=n_bootstrap,
                    seed=seed,
                )

            if speedup is not None and variant != chosen_baseline:
                workload_speedups.append(speedup)

            variant_stats_list.append(
                VariantStats(
                    workload=workload,
                    variant=variant,
                    metric=metric,
                    n_samples=len(values),
                    n_missing=n_missing,
                    median=med,
                    p95=p95_val,
                    p99=p99_val,
                    cv=cv_val,
                    ci_low=ci_low,
                    ci_high=ci_high,
                    speedup=speedup,
                    speedup_ci_low=speedup_ci_low,
                    speedup_ci_high=speedup_ci_high,
                    significant=significant,
                )
            )

        geomean = None
        if workload_speedups:
            geomean = geometric_mean(workload_speedups)
            all_workload_speedups.append(geomean)

        workload_summaries.append(
            WorkloadSummary(
                workload=workload,
                metric=metric,
                baseline_variant=chosen_baseline,
                variants=variant_stats_list,
                geomean_speedup=geomean,
            )
        )

    suite_geomean = geometric_mean(all_workload_speedups) if all_workload_speedups else None

    return SuiteSummary(
        metric=metric,
        confidence=confidence,
        n_bootstrap=n_bootstrap,
        seed=seed,
        workloads=workload_summaries,
        suite_geomean_speedup=suite_geomean,
    )

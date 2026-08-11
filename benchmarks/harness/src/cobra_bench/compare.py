"""``cobra-bench compare`` — threshold check between two summary.json files.

Version 0 supports a simple per-workload and suite geometric-mean regression
check.  Release policies with critical-workload p99 thresholds and compilation
overhead checks arrive in S28.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cobra_bench.guardrails import apply_compare_guardrails


@dataclass
class CompareResult:
    """Result of comparing a candidate summary against a baseline."""

    regressions: list[str] = field(default_factory=list)
    report_text: str = ""


def _get_workload_speedups(summary: dict[str, Any]) -> dict[str, float | None]:
    """Return workload-name -> geomean_speedup from a summary dict."""
    speedups: dict[str, float | None] = {}
    for workload in summary.get("workloads", []):
        name = workload.get("workload")
        if name:
            speedups[name] = workload.get("geomean_speedup")
    return speedups


def _format_speedup(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}x"


def run_compare(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
    *,
    regression_threshold: float = 0.05,
) -> CompareResult:
    """Compare candidate and baseline summaries.

    A regression is recorded when a candidate speedup is below the baseline
    speedup by more than ``regression_threshold`` (fractional).  The suite
    geometric mean is also checked.
    """
    apply_compare_guardrails(candidate, baseline)

    regressions: list[str] = []
    lines = ["# Benchmark comparison", ""]
    lines.append(f"- Regression threshold: {regression_threshold * 100:.0f}%")
    lines.append("")

    cand_workloads = _get_workload_speedups(candidate)
    base_workloads = _get_workload_speedups(baseline)
    common = sorted(set(cand_workloads) & set(base_workloads))

    lines.append("## Per-workload speedups")
    lines.append("")
    lines.append("| Workload | Candidate | Baseline | Delta |")
    lines.append("|----------|----------:|---------:|------:|")
    for name in common:
        cand = cand_workloads[name]
        base = base_workloads[name]
        if cand is None or base is None:
            lines.append(f"| {name} | {_format_speedup(cand)} | {_format_speedup(base)} | n/a |")
            continue
        delta = cand - base
        lines.append(
            f"| {name} | {_format_speedup(cand)} | {_format_speedup(base)} | {delta:+.3f}x |"
        )
        if delta < -regression_threshold:
            regressions.append(
                f"workload {name!r} regressed: {cand:.3f}x vs {base:.3f}x "
                f"(delta {delta:+.3f}x < -{regression_threshold:.3f}x)"
            )
    lines.append("")

    cand_suite = candidate.get("suite_geomean_speedup")
    base_suite = baseline.get("suite_geomean_speedup")
    lines.append("## Suite geometric-mean speedup")
    lines.append("")
    lines.append(
        f"| Candidate | Baseline | Delta |\n"
        f"|----------:|---------:|------:|\n"
        f"| {_format_speedup(cand_suite)} | {_format_speedup(base_suite)} | "
        f"{(cand_suite or 0.0) - (base_suite or 0.0):+.3f}x |"
    )
    if cand_suite is not None and base_suite is not None:
        delta = cand_suite - base_suite
        if delta < -regression_threshold:
            regressions.append(f"suite geomean regressed: {cand_suite:.3f}x vs {base_suite:.3f}x")
    lines.append("")

    if regressions:
        lines.append("## Regressions")
        lines.append("")
        for item in regressions:
            lines.append(f"- {item}")
    else:
        lines.append("No regressions detected above the threshold.")

    return CompareResult(regressions=regressions, report_text="\n".join(lines))

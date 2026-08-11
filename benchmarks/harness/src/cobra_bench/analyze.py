"""`cobra-bench analyze` implementation (plan §20.7, §33.8).

Reads raw sample records (JSON-lines or Parquet), computes per-variant
statistics and baseline-relative speedups with bootstrap confidence
intervals, and writes:

- ``summary.md`` — human-readable markdown report
- ``summary.json`` — machine-readable summary
- ``confidence_intervals.csv`` — CSV of CIs by workload/variant
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

from cobra_bench.results import SampleRecord, read_jsonl, read_parquet
from cobra_bench.stats import SuiteSummary, analyze_samples


def _load_samples(input_dir: Path) -> list[SampleRecord]:
    """Load sample records from ``samples.jsonl`` or ``samples.parquet``."""
    jsonl_path = input_dir / "samples.jsonl"
    parquet_path = input_dir / "samples.parquet"

    if jsonl_path.is_file():
        return read_jsonl(jsonl_path)
    if parquet_path.is_file():
        return read_parquet(parquet_path)

    msg = f"No samples found in {input_dir}; expected samples.jsonl or samples.parquet"
    raise FileNotFoundError(msg)


def _format_ns(value: float | None) -> str:
    """Format a nanosecond value as milliseconds with two decimals."""
    if value is None:
        return "n/a"
    return f"{value / 1_000_000.0:.3f}"


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}x"


def _format_ci(low: float | None, high: float | None) -> str:
    if low is None or high is None:
        return "n/a"
    return f"[{low:.3f}x, {high:.3f}x]"


def write_summary_markdown(summary: SuiteSummary, path: Path) -> None:
    """Render ``SuiteSummary`` as a markdown file."""
    lines = [
        "# Benchmark Analysis Summary",
        "",
        f"- Primary metric: `{summary.metric}`",
        f"- Confidence level: {summary.confidence * 100:.0f}%",
        f"- Bootstrap resamples: {summary.n_bootstrap}",
        f"- Random seed: {summary.seed if summary.seed is not None else 'random'}",
        "",
    ]

    if summary.suite_geomean_speedup is not None:
        lines.append(
            f"**Suite geometric-mean speedup:** {_format_ratio(summary.suite_geomean_speedup)}"
        )
        lines.append("")

    for workload in summary.workloads:
        lines.append(f"## Workload: {workload.workload}")
        lines.append("")
        lines.append(f"- Baseline variant: `{workload.baseline_variant}`")
        if workload.geomean_speedup is not None:
            lines.append(
                f"- Workload geometric-mean speedup: {_format_ratio(workload.geomean_speedup)}"
            )
        lines.append("")
        lines.append(
            "| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | "
            "CV | Speedup | Speedup CI | Significant |"
        )
        lines.append(
            "|---------|--------:|------------:|---------:|---------:|"
            "---:|--------:|------------|-------------|"
        )
        for variant in workload.variants:
            lines.append(
                f"| {variant.variant} | "
                f"{variant.n_samples} | "
                f"{_format_ns(variant.median)} | "
                f"{_format_ns(variant.p95)} | "
                f"{_format_ns(variant.p99)} | "
                f"{variant.cv if variant.cv is not None else 'n/a'} | "
                f"{_format_ratio(variant.speedup)} | "
                f"{_format_ci(variant.speedup_ci_low, variant.speedup_ci_high)} | "
                f"{'yes' if variant.significant else 'no'} |"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_json(summary: SuiteSummary, path: Path) -> None:
    """Serialize ``SuiteSummary`` as JSON."""
    payload = asdict(summary)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_confidence_intervals_csv(summary: SuiteSummary, path: Path) -> None:
    """Write a CSV of confidence intervals by workload and variant."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "workload",
                "variant",
                "metric",
                "n_samples",
                "n_missing",
                "median",
                "ci_low",
                "ci_high",
                "speedup",
                "speedup_ci_low",
                "speedup_ci_high",
                "significant",
            ]
        )
        for workload in summary.workloads:
            for variant in workload.variants:
                writer.writerow(
                    [
                        variant.workload,
                        variant.variant,
                        variant.metric,
                        variant.n_samples,
                        variant.n_missing,
                        variant.median,
                        variant.ci_low,
                        variant.ci_high,
                        variant.speedup,
                        variant.speedup_ci_low,
                        variant.speedup_ci_high,
                        variant.significant,
                    ]
                )


def run_analyze(
    input_dir: str | Path,
    output_dir: str | Path,
    *,
    metric: str = "wall_time_ns",
    confidence: float = 0.95,
    n_bootstrap: int = 10_000,
    seed: int | None = None,
    baseline_variant: str | None = None,
) -> SuiteSummary:
    """Load raw samples, analyze them, and write the artifact set."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    records = _load_samples(input_path)
    summary = analyze_samples(
        records,
        metric=metric,
        confidence=confidence,
        n_bootstrap=n_bootstrap,
        seed=seed,
        baseline_variant=baseline_variant,
    )

    write_summary_markdown(summary, output_path / "summary.md")
    write_summary_json(summary, output_path / "summary.json")
    write_confidence_intervals_csv(summary, output_path / "confidence_intervals.csv")

    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cobra-bench analyze",
        description="Analyze raw benchmark samples and produce summary artifacts.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Directory containing samples.jsonl or samples.parquet",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Directory to write summary.md, summary.json, and confidence_intervals.csv",
    )
    parser.add_argument(
        "--metric",
        default="wall_time_ns",
        help="Numeric metric to summarize (default: wall_time_ns)",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.95,
        help="Confidence level for bootstrap intervals (default: 0.95)",
    )
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=10_000,
        help="Number of bootstrap resamples (default: 10000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible bootstrap intervals",
    )
    parser.add_argument(
        "--baseline-variant",
        default=None,
        help="Baseline variant name (default: first variant per workload)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``cobra-bench analyze``."""
    args = _parse_args(argv)
    try:
        run_analyze(
            args.input,
            args.output,
            metric=args.metric,
            confidence=args.confidence,
            n_bootstrap=args.n_bootstrap,
            seed=args.seed,
            baseline_variant=args.baseline_variant,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

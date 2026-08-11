"""Unified ``cobra-bench`` CLI (plan §33 command shapes).

T4 wires the ``analyze`` subcommand; T5 adds ``doctor``, ``verify``, ``run``,
and ``compare``.
"""

from __future__ import annotations

import argparse
import sys

from cobra_bench import analyze as analyze_module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cobra-bench",
        description="Cobra benchmark harness CLI (cobra-bench v0).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze raw benchmark samples and write summary artifacts.",
    )
    analyze_parser.add_argument(
        "--input",
        required=True,
        type=str,
        help="Directory containing samples.jsonl or samples.parquet",
    )
    analyze_parser.add_argument(
        "--output",
        required=True,
        type=str,
        help="Directory to write summary.md, summary.json, and confidence_intervals.csv",
    )
    analyze_parser.add_argument(
        "--metric",
        default="wall_time_ns",
        help="Numeric metric to summarize (default: wall_time_ns)",
    )
    analyze_parser.add_argument(
        "--confidence",
        type=float,
        default=0.95,
        help="Confidence level for bootstrap intervals (default: 0.95)",
    )
    analyze_parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=10_000,
        help="Number of bootstrap resamples (default: 10000)",
    )
    analyze_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible bootstrap intervals",
    )
    analyze_parser.add_argument(
        "--baseline-variant",
        default=None,
        help="Baseline variant name (default: first variant per workload)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``cobra-bench``."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return analyze_module.main(
            [
                "--input",
                args.input,
                "--output",
                args.output,
                "--metric",
                args.metric,
                "--confidence",
                str(args.confidence),
                "--n-bootstrap",
                str(args.n_bootstrap),
            ]
            + (["--seed", str(args.seed)] if args.seed is not None else [])
            + (
                ["--baseline-variant", args.baseline_variant]
                if args.baseline_variant is not None
                else []
            )
        )

    raise AssertionError("unreachable")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

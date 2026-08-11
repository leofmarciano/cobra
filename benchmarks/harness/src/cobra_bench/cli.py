"""Unified ``cobra-bench`` CLI (plan §33 command shapes).

Subcommands:
  doctor   — capture host/GPU/software metadata
  verify   — run correctness oracles only
  run      — collect timing samples (warm or cold)
  analyze  — compute statistics and write summary artifacts
  compare  — threshold check between two summary.json files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cobra_bench import analyze as analyze_module
from cobra_bench import doctor as doctor_module
from cobra_bench.compare import run_compare
from cobra_bench.guardrails import GuardrailError
from cobra_bench.manifest import load_manifest
from cobra_bench.runner import (
    TimingOptions,
    run_and_record,
    verify_workload,
    write_correctness_report,
)
from cobra_bench.timing import CorrectnessFailed, WarmupFailure


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cobra-bench",
        description="Cobra benchmark harness CLI (cobra-bench v0).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # doctor
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Capture machine metadata and write artifacts/environment.json.",
    )
    doctor_parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to write the environment report (e.g. artifacts/environment.json).",
    )
    doctor_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if required fields are missing (plan §33.2).",
    )

    # verify
    verify_parser = subparsers.add_parser(
        "verify",
        help="Run correctness oracles for each variant without timing.",
    )
    verify_parser.add_argument(
        "--suite",
        required=True,
        type=str,
        help="Path to the benchmark suite YAML manifest.",
    )
    verify_parser.add_argument(
        "--variants",
        type=str,
        default=None,
        help="Comma-separated variants to verify (default: all variants in each workload).",
    )
    verify_parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Directory to write correctness.json.",
    )

    # run
    run_parser = subparsers.add_parser(
        "run",
        help="Run the timing protocol and write raw samples.",
    )
    run_parser.add_argument(
        "--suite",
        required=True,
        type=str,
        help="Path to the benchmark suite YAML manifest.",
    )
    run_parser.add_argument(
        "--variants",
        type=str,
        default=None,
        help="Comma-separated variants to run (default: all variants in each workload).",
    )
    run_parser.add_argument(
        "--phase",
        type=str,
        choices=("warm", "cold"),
        default="warm",
        help="Measurement phase (default: warm).",
    )
    run_parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Directory to write samples.jsonl and a copy of the manifest.",
    )
    run_parser.add_argument(
        "--min-samples",
        type=int,
        default=None,
        help="Override the manifest's minimum_samples.",
    )
    run_parser.add_argument(
        "--max-warmup",
        type=int,
        default=None,
        help="Maximum warmup iterations before failing (warm phase only).",
    )
    run_parser.add_argument(
        "--no-oracle",
        action="store_true",
        help="Skip per-sample correctness checks (loud warning; invalidates claims).",
    )
    run_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible variant ordering.",
    )

    # analyze
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

    # compare
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare a candidate summary against a baseline summary.",
    )
    compare_parser.add_argument(
        "--candidate",
        required=True,
        type=str,
        help="Path to candidate summary.json",
    )
    compare_parser.add_argument(
        "--baseline",
        required=True,
        type=str,
        help="Path to baseline summary.json",
    )
    compare_parser.add_argument(
        "--regression-threshold",
        type=float,
        default=0.05,
        help="Fractional regression threshold (default: 0.05 = 5%%).",
    )
    compare_parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero if any regression exceeds the threshold.",
    )

    return parser


def _parse_variant_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [v.strip() for v in value.split(",") if v.strip()]


def _run_doctor(args: argparse.Namespace) -> int:
    report = doctor_module.run_doctor(
        strict=args.strict,
        output=args.output,
    )
    if report.exit_code != 0:
        for error in report.errors:
            print(f"doctor: {error}", file=sys.stderr)
    return report.exit_code


def _run_verify(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.suite)
    variants = _parse_variant_list(args.variants)
    reports = []
    for workload in manifest.workloads:
        selected = variants if variants is not None else [v.name for v in workload.variants]
        correctness = manifest.correctness
        comparator = correctness.comparator if correctness else "exact"
        reports.append(
            verify_workload(
                workload,
                selected,
                comparator=comparator,
                rtol_by_dtype=correctness.rtol_by_dtype if correctness else None,
                atol_by_dtype=correctness.atol_by_dtype if correctness else None,
            )
        )
    write_correctness_report(reports, Path(args.output))
    passed = all(r.passed for r in reports)
    if not passed:
        print("verify: correctness failures detected", file=sys.stderr)
        for report in reports:
            for error in report.errors:
                print(f"  {error}", file=sys.stderr)
    return 0 if passed else 1


def _run_run(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.suite)
    variants = _parse_variant_list(args.variants)
    options = TimingOptions(
        phase=args.phase,
        min_samples=args.min_samples,
        max_warmup=args.max_warmup,
        no_oracle=args.no_oracle,
        seed=args.seed,
    )

    # If user did not specify variants per workload, apply the same list to
    # every workload.  Workloads that do not contain a requested variant will
    # raise a clear error in the runner.
    variants_by_workload = {w.name: variants for w in manifest.workloads}

    output_dir = Path(args.output)
    try:
        run_and_record(manifest, variants_by_workload, options, output_dir)
    except (RuntimeError, ValueError, WarmupFailure, CorrectnessFailed) as exc:
        print(f"run: {exc}", file=sys.stderr)
        return 1
    (output_dir / "manifest.yaml").write_text(Path(args.suite).read_text(), encoding="utf-8")
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
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


def _run_compare(args: argparse.Namespace) -> int:
    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    try:
        result = run_compare(
            candidate,
            baseline,
            regression_threshold=args.regression_threshold,
        )
    except GuardrailError as exc:
        print(f"compare: {exc}", file=sys.stderr)
        return 1
    print(result.report_text)
    return 1 if args.fail_on_regression and result.regressions else 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``cobra-bench``."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    command_map = {
        "doctor": _run_doctor,
        "verify": _run_verify,
        "run": _run_run,
        "analyze": _run_analyze,
        "compare": _run_compare,
    }
    handler = command_map.get(args.command)
    if handler is None:
        parser.error(f"unknown command: {args.command}")
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

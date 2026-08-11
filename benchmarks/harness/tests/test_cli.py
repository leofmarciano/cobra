"""Tests for the unified ``cobra-bench`` CLI (T5)."""

from __future__ import annotations

import json
from pathlib import Path

from cobra_bench.cli import main as cli_main


class TestDoctorSubcommand:
    def test_doctor_writes_environment_json(self, tmp_path: Path) -> None:
        output = tmp_path / "env.json"
        rc = cli_main(["doctor", "--output", str(output)])
        assert rc == 0
        assert output.is_file()
        payload = json.loads(output.read_text())
        assert "host" in payload
        assert "software" in payload


class TestVerifySubcommand:
    def test_verify_passes_for_equivalent_variants(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "correctness"
        rc = cli_main(
            [
                "verify",
                "--suite",
                "benchmarks/suites/example.yaml",
                "--variants",
                "a,b",
                "--output",
                str(output_dir),
            ]
        )
        assert rc == 0
        report = json.loads((output_dir / "correctness.json").read_text())
        assert report["passed"] is True

    def test_verify_fails_for_incompatible_variants(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "correctness"
        rc = cli_main(
            [
                "verify",
                "--suite",
                "benchmarks/suites/example.yaml",
                "--variants",
                "a",
                "--output",
                str(output_dir),
            ]
        )
        assert rc == 0
        report = json.loads((output_dir / "correctness.json").read_text())
        assert report["passed"] is True  # single variant trivially agrees with itself


class TestRunSubcommand:
    def test_run_warm_writes_samples_jsonl(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "raw"
        rc = cli_main(
            [
                "run",
                "--suite",
                "benchmarks/suites/example.yaml",
                "--variants",
                "a,b",
                "--phase",
                "warm",
                "--min-samples",
                "10",
                "--output",
                str(output_dir),
                "--seed",
                "1",
            ]
        )
        assert rc == 0
        assert (output_dir / "samples.jsonl").is_file()
        assert (output_dir / "manifest.yaml").is_file()

    def test_run_cold_requires_no_oracle(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "raw"
        rc = cli_main(
            [
                "run",
                "--suite",
                "benchmarks/suites/example.yaml",
                "--variants",
                "a",
                "--phase",
                "cold",
                "--min-samples",
                "2",
                "--output",
                str(output_dir),
            ]
        )
        assert rc == 1


class TestAnalyzeSubcommand:
    def test_analyze_produces_summary_artifacts(self, tmp_path: Path) -> None:
        raw_dir = tmp_path / "raw"
        analysis_dir = tmp_path / "analysis"
        rc_run = cli_main(
            [
                "run",
                "--suite",
                "benchmarks/suites/example.yaml",
                "--variants",
                "a,b",
                "--phase",
                "warm",
                "--min-samples",
                "10",
                "--output",
                str(raw_dir),
                "--seed",
                "2",
            ]
        )
        assert rc_run == 0

        rc_analyze = cli_main(
            [
                "analyze",
                "--input",
                str(raw_dir),
                "--output",
                str(analysis_dir),
                "--n-bootstrap",
                "500",
                "--seed",
                "3",
            ]
        )
        assert rc_analyze == 0
        assert (analysis_dir / "summary.json").is_file()
        assert (analysis_dir / "summary.md").is_file()
        assert (analysis_dir / "confidence_intervals.csv").is_file()


class TestCompareSubcommand:
    def _make_summary(self, speedup: float, phase: str = "warm") -> dict[str, object]:
        return {
            "metric": "wall_time_ns",
            "confidence": 0.95,
            "n_bootstrap": 500,
            "seed": 1,
            "phase": phase,
            "suite_geomean_speedup": speedup,
            "workloads": [
                {
                    "workload": "dummy_add",
                    "metric": "wall_time_ns",
                    "baseline_variant": "a",
                    "input_fingerprint": "dummy_add",
                    "geomean_speedup": speedup,
                    "variants": [],
                }
            ],
        }

    def test_compare_reports_no_regression(self, tmp_path: Path) -> None:
        candidate = tmp_path / "candidate.json"
        baseline = tmp_path / "baseline.json"
        candidate.write_text(json.dumps(self._make_summary(2.0)))
        baseline.write_text(json.dumps(self._make_summary(1.0)))

        rc = cli_main(
            [
                "compare",
                "--candidate",
                str(candidate),
                "--baseline",
                str(baseline),
                "--regression-threshold",
                "0.05",
            ]
        )
        assert rc == 0

    def test_compare_fails_on_regression_when_requested(self, tmp_path: Path) -> None:
        candidate = tmp_path / "candidate.json"
        baseline = tmp_path / "baseline.json"
        candidate.write_text(json.dumps(self._make_summary(0.9)))
        baseline.write_text(json.dumps(self._make_summary(1.0)))

        rc = cli_main(
            [
                "compare",
                "--candidate",
                str(candidate),
                "--baseline",
                str(baseline),
                "--regression-threshold",
                "0.05",
                "--fail-on-regression",
            ]
        )
        assert rc == 1

    def test_compare_refuses_mixed_phase(self, tmp_path: Path) -> None:
        candidate = tmp_path / "candidate.json"
        baseline = tmp_path / "baseline.json"
        candidate.write_text(json.dumps(self._make_summary(1.0, phase="warm")))
        baseline.write_text(json.dumps(self._make_summary(1.0, phase="cold")))

        rc = cli_main(
            [
                "compare",
                "--candidate",
                str(candidate),
                "--baseline",
                str(baseline),
            ]
        )
        assert rc == 1

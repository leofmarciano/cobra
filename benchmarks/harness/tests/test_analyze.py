"""Tests for ``cobra-bench analyze`` (plan §33.8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cobra_bench.analyze import main as analyze_main
from cobra_bench.analyze import run_analyze
from cobra_bench.results import SampleRecord, write_jsonl, write_parquet


def _make_records() -> list[SampleRecord]:
    """Two variants with a 2x speedup for ``dummy_add``."""
    records: list[SampleRecord] = []
    for i in range(30):
        records.append(
            SampleRecord(
                run_id="r1",
                workload="dummy_add",
                variant="a",
                phase="warm",
                sample=i,
                correct=True,
                wall_time_ns=100_000,
            )
        )
        records.append(
            SampleRecord(
                run_id="r1",
                workload="dummy_add",
                variant="b",
                phase="warm",
                sample=i,
                correct=True,
                wall_time_ns=50_000,
            )
        )
    return records


class TestAnalyzeArtifacts:
    def test_analyze_from_jsonl_writes_all_artifacts(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "analysis"
        write_jsonl(_make_records(), input_dir / "samples.jsonl")

        summary = run_analyze(
            input_dir,
            output_dir,
            n_bootstrap=500,
            seed=1,
            baseline_variant="a",
        )

        assert (output_dir / "summary.md").is_file()
        assert (output_dir / "summary.json").is_file()
        assert (output_dir / "confidence_intervals.csv").is_file()

        assert summary.suite_geomean_speedup == pytest.approx(2.0, rel=1e-6)

    def test_analyze_from_parquet_writes_all_artifacts(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "analysis"
        write_parquet(_make_records(), input_dir / "samples.parquet")

        summary = run_analyze(
            input_dir,
            output_dir,
            n_bootstrap=500,
            seed=2,
            baseline_variant="a",
        )

        assert (output_dir / "summary.md").is_file()
        assert (output_dir / "summary.json").is_file()
        assert (output_dir / "confidence_intervals.csv").is_file()

        assert summary.suite_geomean_speedup == pytest.approx(2.0, rel=1e-6)

    def test_summary_json_is_machine_readable(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "analysis"
        write_jsonl(_make_records(), input_dir / "samples.jsonl")

        run_analyze(input_dir, output_dir, n_bootstrap=500, seed=3, baseline_variant="a")

        payload = json.loads((output_dir / "summary.json").read_text())
        assert payload["metric"] == "wall_time_ns"
        assert payload["confidence"] == 0.95
        assert len(payload["workloads"]) == 1
        assert payload["suite_geomean_speedup"] == pytest.approx(2.0, rel=1e-6)

        variants = {v["variant"]: v for v in payload["workloads"][0]["variants"]}
        assert variants["b"]["significant"] is True
        assert variants["b"]["speedup"] == pytest.approx(2.0, rel=1e-6)

    def test_summary_markdown_contains_key_sections(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "analysis"
        write_jsonl(_make_records(), input_dir / "samples.jsonl")

        run_analyze(input_dir, output_dir, n_bootstrap=500, seed=4, baseline_variant="a")

        md = (output_dir / "summary.md").read_text()
        assert "Benchmark Analysis Summary" in md
        assert "dummy_add" in md
        assert "2.000" in md
        assert "yes" in md  # significant flag for variant b

    def test_confidence_intervals_csv_has_expected_rows(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "analysis"
        write_jsonl(_make_records(), input_dir / "samples.jsonl")

        run_analyze(input_dir, output_dir, n_bootstrap=500, seed=5, baseline_variant="a")

        lines = (output_dir / "confidence_intervals.csv").read_text().strip().splitlines()
        reader_rows = list(lines[1:])
        variants = [row.split(",")[1] for row in reader_rows]
        assert "a" in variants
        assert "b" in variants


class TestAnalyzeCLI:
    def test_analyze_cli_with_jsonl(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "raw"
        output_dir = tmp_path / "analysis"
        write_jsonl(_make_records(), input_dir / "samples.jsonl")

        rc = analyze_main(
            [
                "--input",
                str(input_dir),
                "--output",
                str(output_dir),
                "--n-bootstrap",
                "500",
                "--seed",
                "6",
                "--baseline-variant",
                "a",
            ]
        )

        assert rc == 0
        assert (output_dir / "summary.json").is_file()

    def test_analyze_cli_missing_input_returns_error(self, tmp_path: Path) -> None:
        rc = analyze_main(
            [
                "--input",
                str(tmp_path / "does-not-exist"),
                "--output",
                str(tmp_path / "analysis"),
            ]
        )
        assert rc == 1

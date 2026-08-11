"""Tests for workload invocation and sample collection (cobra_bench.runner)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from cobra_bench import runner as runner_module
from cobra_bench.manifest import BenchmarkManifest, ProtocolInfo, VariantSpec, WorkloadSpec
from cobra_bench.runner import (
    TimingOptions,
    build_oracle,
    resolve_entrypoint,
    run_and_record,
    run_workload,
    verify_workload,
)


def _example_manifest() -> BenchmarkManifest:
    return BenchmarkManifest(
        run_id="test-run",
        suite="test-suite",
        protocol=ProtocolInfo(minimum_samples=5),
        workloads=[
            WorkloadSpec(
                name="dummy_add",
                variants=[
                    VariantSpec(name="a", entrypoint="cobra_bench.examples.dummy:variant_a"),
                    VariantSpec(name="b", entrypoint="cobra_bench.examples.dummy:variant_b"),
                ],
            )
        ],
    )


class TestResolveEntrypoint:
    def test_resolves_existing_callable(self) -> None:
        fn = resolve_entrypoint("cobra_bench.examples.dummy:variant_a")
        assert fn() == 499500

    def test_rejects_missing_module(self) -> None:
        with pytest.raises(ValueError, match="cannot import module"):
            resolve_entrypoint("no_such_module_12345:no_such")

    def test_rejects_missing_callable(self) -> None:
        with pytest.raises(ValueError, match="has no callable"):
            resolve_entrypoint("cobra_bench.examples.dummy:no_such_callable")

    def test_rejects_non_callable(self) -> None:
        with pytest.raises(ValueError, match="non-callable"):
            resolve_entrypoint("cobra_bench.examples.dummy:__doc__")

    def test_rejects_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="module:callable"):
            resolve_entrypoint("not_a_valid_entrypoint")


class TestVerifyWorkload:
    def test_passes_for_equivalent_dummy_variants(self) -> None:
        workload = _example_manifest().workloads[0]
        report = verify_workload(workload, ["a", "b"], comparator="exact")
        assert report.passed is True
        assert report.errors == []
        assert report.results["a"] == report.results["b"] == 499500

    def test_fails_when_variants_differ(self) -> None:
        workload = WorkloadSpec(
            name="mismatch",
            variants=[
                VariantSpec(name="a", entrypoint="cobra_bench.examples.dummy:variant_a"),
                VariantSpec(name="bad", entrypoint="builtins:bool"),
            ],
        )
        report = verify_workload(workload, ["a", "bad"], comparator="exact")
        assert report.passed is False
        assert any("baseline" in err for err in report.errors)


class TestRunWorkload:
    def test_warm_collects_expected_samples(self) -> None:
        manifest = _example_manifest()
        workload = manifest.workloads[0]
        options = TimingOptions(phase="warm", min_samples=5, seed=42)
        records = run_workload(manifest, workload, ["a", "b"], options)

        a_records = [r for r in records if r.variant == "a"]
        b_records = [r for r in records if r.variant == "b"]
        assert len(a_records) >= 5
        assert len(b_records) >= 5
        assert all(r.phase == "warm" for r in records)
        assert all(r.correct for r in records)
        assert all(r.tags.get("input_fingerprint") == "dummy_add" for r in records)

    def test_run_with_no_oracle_skips_correctness(self) -> None:
        manifest = _example_manifest()
        workload = manifest.workloads[0]
        options = TimingOptions(phase="warm", min_samples=5, no_oracle=True)
        records = run_workload(manifest, workload, ["a", "b"], options)
        assert records
        assert all(not r.correct for r in records)

    def test_cold_without_no_oracle_raises(self) -> None:
        manifest = _example_manifest()
        workload = manifest.workloads[0]
        options = TimingOptions(phase="cold", min_samples=2)
        with pytest.raises(ValueError, match="no-oracle"):
            run_workload(manifest, workload, ["a", "b"], options)


class TestBuildOracle:
    @pytest.fixture()
    def _approx_baseline(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
        expected = {"mean": 1.0, "total": 42}
        monkeypatch.setattr("cobra_bench.runner._load_expected", lambda _variant: expected)
        return expected

    def test_approx_passes_within_float_tolerance(self, _approx_baseline: dict[str, Any]) -> None:
        oracle = build_oracle(
            WorkloadSpec(name="approx", variants=[]),
            VariantSpec(name="baseline", entrypoint="cobra_bench.examples.dummy:variant_a"),
            comparator="approx",
            rtol_by_dtype={"float64": 1e-5},
            atol_by_dtype={"float64": 1e-8},
        )
        assert oracle({"mean": 1.000001, "total": 42}) is True

    def test_approx_fails_outside_float_tolerance(self, _approx_baseline: dict[str, Any]) -> None:
        oracle = build_oracle(
            WorkloadSpec(name="approx", variants=[]),
            VariantSpec(name="baseline", entrypoint="cobra_bench.examples.dummy:variant_a"),
            comparator="approx",
            rtol_by_dtype={"float64": 1e-5},
            atol_by_dtype={"float64": 1e-8},
        )
        assert oracle({"mean": 1.1, "total": 42}) is False

    def test_approx_compares_integer_leaves_exactly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        expected = {"n_rows": 100_000}
        monkeypatch.setattr(runner_module, "_load_expected", lambda _variant: expected)
        oracle = build_oracle(
            WorkloadSpec(name="approx", variants=[]),
            VariantSpec(name="baseline", entrypoint="cobra_bench.examples.dummy:variant_a"),
            comparator="approx",
            rtol_by_dtype={"float": 1e-3},
            atol_by_dtype={"float": 1e-3},
        )

        assert oracle({"n_rows": 100_001}) is False


def test_verify_reuses_loaded_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verification must not execute the baseline again just to build its oracle."""
    expected = {"value": 1}
    load_calls = 0
    resolve_calls = 0

    def load(_variant: VariantSpec) -> dict[str, int]:
        nonlocal load_calls
        load_calls += 1
        return expected

    def resolve(_entrypoint: str):
        nonlocal resolve_calls
        resolve_calls += 1
        return lambda: expected

    monkeypatch.setattr(runner_module, "_load_expected", load)
    monkeypatch.setattr(runner_module, "resolve_entrypoint", resolve)
    workload = WorkloadSpec(
        name="reuse-baseline",
        variants=[
            VariantSpec(name="a", entrypoint="example:a"),
            VariantSpec(name="b", entrypoint="example:b"),
        ],
    )

    report = verify_workload(workload, ["a", "b"], comparator="exact")

    assert report.passed is True
    assert load_calls == 1
    assert resolve_calls == 1


class TestRunAndRecord:
    def test_writes_jsonl_and_manifest_copy(self, tmp_path: Path) -> None:
        manifest = _example_manifest()
        output_dir = tmp_path / "raw"
        options = TimingOptions(phase="warm", min_samples=5, seed=1)
        records = run_and_record(
            manifest,
            {"dummy_add": ["a", "b"]},
            options,
            output_dir,
        )
        assert len(records) >= 10
        assert (output_dir / "samples.jsonl").is_file()

        # Sanity-check JSON-lines content.
        lines = (output_dir / "samples.jsonl").read_text().strip().splitlines()
        assert len(lines) == len(records)
        first = json.loads(lines[0])
        assert first["workload"] == "dummy_add"

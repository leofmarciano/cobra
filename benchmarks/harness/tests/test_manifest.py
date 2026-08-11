"""Tests for the §33.1 benchmark manifest schema and YAML loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from cobra_bench.manifest import (
    BenchmarkManifest,
    ManifestError,
    load_manifest,
    manifest_from_dict,
    manifest_to_dict,
)

EXAMPLE_MANIFEST = Path(__file__).parents[2] / "suites" / "example.yaml"


def test_example_manifest_exists() -> None:
    assert EXAMPLE_MANIFEST.is_file()


def test_example_manifest_loads() -> None:
    manifest = load_manifest(EXAMPLE_MANIFEST)
    assert isinstance(manifest, BenchmarkManifest)
    assert manifest.run_id == "cobra-bench-example"
    assert manifest.suite == "example-v0"
    assert manifest.protocol.minimum_samples == 30
    assert [w.name for w in manifest.workloads] == ["dummy_add"]
    assert [v.name for v in manifest.workloads[0].variants] == ["a", "b"]


def test_example_manifest_round_trips() -> None:
    manifest = load_manifest(EXAMPLE_MANIFEST)
    round_tripped = manifest_from_dict(manifest_to_dict(manifest))
    assert round_tripped == manifest


def test_missing_required_field_reports_field_path() -> None:
    with pytest.raises(ManifestError) as exc_info:
        manifest_from_dict({"suite": "example-v0"})
    assert any("run_id" in error for error in exc_info.value.errors)


def test_wrong_type_reports_field_path() -> None:
    with pytest.raises(ManifestError) as exc_info:
        manifest_from_dict(
            {
                "run_id": "r1",
                "suite": "s1",
                "host": {"numa_nodes": "not-an-int"},
            }
        )
    assert any("host.numa_nodes" in error for error in exc_info.value.errors)


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ManifestError) as exc_info:
        manifest_from_dict({"run_id": "r1", "suite": "s1", "bogus": True})
    assert any("bogus" in error for error in exc_info.value.errors)


def test_multiple_errors_reported_together() -> None:
    with pytest.raises(ManifestError) as exc_info:
        manifest_from_dict({"host": {"numa_nodes": "x"}, "bogus": True})
    # run_id, suite, host.numa_nodes, bogus -> at least 4 distinct problems
    assert len(exc_info.value.errors) >= 4


def test_manual_field_allowed_in_non_strict_mode() -> None:
    manifest = manifest_from_dict(
        {
            "run_id": "r1",
            "suite": "s1",
            "host": {"os": "hand-typed", "manual": True},
        },
        strict=False,
    )
    assert manifest.host.manual is True


def test_manual_field_rejected_in_strict_mode() -> None:
    with pytest.raises(ManifestError) as exc_info:
        manifest_from_dict(
            {
                "run_id": "r1",
                "suite": "s1",
                "host": {"os": "hand-typed", "manual": True},
            },
            strict=True,
        )
    assert any("host.manual" in error for error in exc_info.value.errors)


def test_invalid_variant_entrypoint_format() -> None:
    with pytest.raises(ManifestError) as exc_info:
        manifest_from_dict(
            {
                "run_id": "r1",
                "suite": "s1",
                "workloads": [
                    {
                        "name": "w1",
                        "variants": [{"name": "a", "entrypoint": "not-a-valid-entrypoint"}],
                    }
                ],
            }
        )
    assert any("entrypoint" in error for error in exc_info.value.errors)


def test_default_protocol_values() -> None:
    manifest = manifest_from_dict({"run_id": "r1", "suite": "s1"})
    assert manifest.protocol.warmup_policy == "stability"
    assert manifest.protocol.minimum_samples == 30
    assert manifest.protocol.configuration_order == "randomized"
    assert manifest.protocol.correctness_required is True
    assert manifest.protocol.confidence_interval == "bootstrap-95"


def test_workload_correctness_overrides_global_profile() -> None:
    manifest = manifest_from_dict(
        {
            "run_id": "r1",
            "suite": "s1",
            "correctness": {
                "comparator": "approx",
                "rtol_by_dtype": {"float64": 1e-5},
                "atol_by_dtype": {"float64": 1e-8},
            },
            "workloads": [
                {
                    "name": "vision",
                    "correctness": {
                        "rtol_by_dtype": {"float": 1e-3},
                        "atol_by_dtype": {"float": 1e-3},
                    },
                    "variants": [],
                }
            ],
        }
    )

    correctness = manifest.correctness_for(manifest.workloads[0])
    assert correctness.comparator == "approx"
    assert correctness.rtol_by_dtype == {"float64": 1e-5, "float": 1e-3}
    assert correctness.atol_by_dtype == {"float64": 1e-8, "float": 1e-3}

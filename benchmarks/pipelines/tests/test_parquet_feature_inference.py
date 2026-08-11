"""Tests for the parquet_feature_inference workload."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from cobra_pipelines import parquet_feature_inference


@pytest.fixture(autouse=True)
def _small_dataset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Force a small, temporary dataset for all tests."""
    monkeypatch.setenv("COBRA_PARQUET_ROWS", "1000")
    monkeypatch.setenv("COBRA_DATA_DIR", str(tmp_path))


def test_generation_is_deterministic_and_hash_stable() -> None:
    """Two generations with the same seed must produce identical Parquet bytes."""
    os.environ["COBRA_PARQUET_SEED"] = "12345"
    path1 = parquet_feature_inference.generate_dataset()
    path2 = parquet_feature_inference.generate_dataset()

    assert path1 == path2
    assert Path(path1).is_file()
    hash1 = hashlib.sha256(Path(path1).read_bytes()).hexdigest()
    hash2 = hashlib.sha256(Path(path2).read_bytes()).hexdigest()
    assert hash1 == hash2


def test_b0_runs_and_returns_serializable_result() -> None:
    """The b0 entrypoint must run end-to-end and return a deterministic dict."""
    os.environ["COBRA_PARQUET_SEED"] = "12345"
    result1 = parquet_feature_inference.b0()
    result2 = parquet_feature_inference.b0()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1["n_rows"] == result2["n_rows"]
    assert result1 == result2


def test_b1_runs_and_returns_serializable_result() -> None:
    """The b1 entrypoint must run end-to-end and return a deterministic dict."""
    os.environ["COBRA_PARQUET_SEED"] = "12345"
    result1 = parquet_feature_inference.b1()
    result2 = parquet_feature_inference.b1()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1["n_rows"] == result2["n_rows"]
    assert result1 == result2


def test_b1_produces_same_result_as_b0() -> None:
    """B1 must produce numerically equivalent results to B0 (same pipeline, just compiled)."""
    os.environ["COBRA_PARQUET_SEED"] = "12345"
    b0_result = parquet_feature_inference.b0()
    b1_result = parquet_feature_inference.b1()

    assert b0_result["n_rows"] == b1_result["n_rows"]
    # Float results may differ slightly due to compilation, but must be close
    assert abs(b0_result["mean_score"] - b1_result["mean_score"]) < 1e-4
    assert abs(b0_result["score_sum"] - b1_result["score_sum"]) < 1e-2

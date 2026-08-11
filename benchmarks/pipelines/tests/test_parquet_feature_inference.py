"""Tests for the parquet_feature_inference workload."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import ClassVar

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


@pytest.mark.gpu
def test_b1_runs_and_returns_serializable_result() -> None:
    """The b1 entrypoint must run end-to-end and return a deterministic dict."""
    os.environ["COBRA_PARQUET_SEED"] = "12345"
    result1 = parquet_feature_inference.b1()
    result2 = parquet_feature_inference.b1()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1["n_rows"] == result2["n_rows"]
    assert result1 == result2


@pytest.mark.gpu
def test_b1_produces_same_result_as_b0() -> None:
    """B1 must produce numerically equivalent results to B0 (same pipeline, just compiled)."""
    os.environ["COBRA_PARQUET_SEED"] = "12345"
    b0_result = parquet_feature_inference.b0()
    b1_result = parquet_feature_inference.b1()

    assert b0_result["n_rows"] == b1_result["n_rows"]
    # Float results may differ slightly due to compilation, but must be close
    assert abs(b0_result["mean_score"] - b1_result["mean_score"]) < 1e-4
    assert abs(b0_result["score_sum"] - b1_result["score_sum"]) < 1e-2


def test_b1_isolates_cudf_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cuDF variant reuses one isolated worker across timed samples."""
    monkeypatch.setattr(parquet_feature_inference, "_cudf_pandas_available", lambda: True)
    monkeypatch.delenv(parquet_feature_inference._B1_WORKER_ENV, raising=False)
    monkeypatch.setattr(parquet_feature_inference, "_B1_WORKER", None)

    class FakePipe:
        def __init__(self) -> None:
            self.writes: list[str] = []

        def write(self, value: str) -> None:
            self.writes.append(value)

        def flush(self) -> None:
            return None

        def readline(self) -> str:
            return json.dumps({"n_rows": 1}) + "\n"

    class FakeProcess:
        instances: ClassVar[list[FakeProcess]] = []

        def __init__(self, command, **kwargs) -> None:
            self.command = command
            self.kwargs = kwargs
            self.stdin = FakePipe()
            self.stdout = FakePipe()
            self.stderr = FakePipe()
            self.returncode = None
            self.__class__.instances.append(self)

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.returncode = 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

    monkeypatch.setattr(parquet_feature_inference.subprocess, "Popen", FakeProcess)
    monkeypatch.setenv("COBRA_TEST_SECRET", "must-not-cross-process-boundary")

    assert parquet_feature_inference.b1() == {"n_rows": 1}
    assert parquet_feature_inference.b1() == {"n_rows": 1}
    assert len(FakeProcess.instances) == 1
    process = FakeProcess.instances[0]
    worker_env = process.kwargs["env"]
    assert isinstance(worker_env, dict)
    assert worker_env[parquet_feature_inference._B1_WORKER_ENV] == "1"
    assert "COBRA_TEST_SECRET" not in worker_env
    assert process.kwargs["stderr"] == parquet_feature_inference.subprocess.DEVNULL
    assert process.stdin.writes == ["run\n", "run\n"]

    worker = parquet_feature_inference._B1_WORKER
    assert worker is not None
    worker.close()

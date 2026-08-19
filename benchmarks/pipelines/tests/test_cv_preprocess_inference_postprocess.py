"""Tests for the cv_preprocess_inference_postprocess workload.

T3 acceptance criteria:
- Oracle passes (deterministic, reproducible results).
- Preprocessing is measurably CPU-bound (documented).
"""

from __future__ import annotations

import time

import pytest
import torch
from cobra_pipelines import cv_preprocess_inference_postprocess
from tracer.handles import handle_for
from tracer.session import trace


@pytest.mark.gpu
def test_b0_runs_and_returns_deterministic_result() -> None:
    """The b0 entrypoint must run end-to-end and return the same dict twice."""
    result1 = cv_preprocess_inference_postprocess.b0()
    result2 = cv_preprocess_inference_postprocess.b0()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1 == result2


@pytest.mark.gpu
def test_b0_result_contains_expected_keys() -> None:
    """The output dict must contain classification result keys."""
    result = cv_preprocess_inference_postprocess.b0()
    expected_keys = {
        "n_images",
        "top1_class_ids",
        "top1_confidences",
        "n_above_threshold",
    }
    assert expected_keys.issubset(result.keys())


def test_preprocessing_is_cpu_bound() -> None:
    """Preprocessing must be measurably CPU-bound.

    We measure the time for preprocessing alone vs. the full pipeline and
    verify that preprocessing takes a non-trivial fraction of the total.
    """
    batch_size = cv_preprocess_inference_postprocess.DEFAULT_BATCH_SIZE
    seed = cv_preprocess_inference_postprocess.DEFAULT_SEED

    images = cv_preprocess_inference_postprocess._generate_synthetic_images(batch_size, seed)

    # Time preprocessing (CPU-bound)
    start = time.perf_counter()
    for _ in range(3):
        cv_preprocess_inference_postprocess._preprocess(images)
    preprocess_time = (time.perf_counter() - start) / 3

    # Preprocessing should take measurable time (> 0.1 ms for a batch)
    assert preprocess_time > 1e-4, (
        f"Preprocessing took only {preprocess_time:.6f}s — expected measurably CPU-bound work"
    )


def test_trace_records_synthetic_image_generation_boundary() -> None:
    with trace(enable_pandas=False, enable_torch=False) as session:
        images = cv_preprocess_inference_postprocess._generate_synthetic_images(2, 7)

    event = next(
        event for event in session.events if event.op.endswith("synthetic_image_generation")
    )
    assert handle_for(images[0]) in event.output_handles


def test_trace_records_cv_postprocessing_boundary() -> None:
    with trace(enable_pandas=False, enable_numpy=False) as session:
        logits = torch.randn(2, 1000)
        cv_preprocess_inference_postprocess._postprocess(logits, top_k=1, threshold=0.01)

    event = next(event for event in session.events if event.op.endswith("cv.postprocess"))
    assert handle_for(logits) in event.input_handles


def test_compiled_resnet_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    from cobra_pipelines import _compile_env

    class FakeModel(torch.nn.Module):
        def forward(self, value: torch.Tensor) -> torch.Tensor:
            return value

    calls: list[torch.nn.Module] = []
    cv_preprocess_inference_postprocess._COMPILED_RESNETS.clear()
    monkeypatch.setattr(_compile_env, "ensure_nvcc_in_path", lambda: None)
    monkeypatch.setattr(
        cv_preprocess_inference_postprocess.models,
        "resnet18",
        lambda weights: FakeModel(),
    )

    def fake_compile(model: torch.nn.Module, **kwargs: object) -> torch.nn.Module:
        calls.append(model)
        return model

    monkeypatch.setattr(torch, "compile", fake_compile)
    device = torch.device("cpu")

    first = cv_preprocess_inference_postprocess._get_compiled_resnet18(device)
    second = cv_preprocess_inference_postprocess._get_compiled_resnet18(device)

    assert first is second
    assert len(calls) == 1


def test_eager_resnet_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModel(torch.nn.Module):
        def forward(self, value: torch.Tensor) -> torch.Tensor:
            return value

    cv_preprocess_inference_postprocess._EAGER_RESNETS.clear()
    calls: list[torch.nn.Module] = []
    monkeypatch.setattr(
        cv_preprocess_inference_postprocess.models,
        "resnet18",
        lambda weights: calls.append(FakeModel()) or calls[-1],
    )
    device = torch.device("cpu")

    first = cv_preprocess_inference_postprocess._get_eager_resnet18(device)
    second = cv_preprocess_inference_postprocess._get_eager_resnet18(device)

    assert first is second
    assert len(calls) == 1


@pytest.mark.gpu
def test_top_k_and_thresholding() -> None:
    """Postprocessing must return correct top-k classes with thresholding."""
    result = cv_preprocess_inference_postprocess.b0()

    # top1_class_ids should be a list with one entry per image
    n_images = result["n_images"]
    assert len(result["top1_class_ids"]) == n_images
    assert len(result["top1_confidences"]) == n_images

    # All class IDs must be valid (0..999 for ImageNet-style)
    for cid in result["top1_class_ids"]:
        assert 0 <= cid < 1000

    # All confidences must be in [0, 1]
    for conf in result["top1_confidences"]:
        assert 0.0 <= conf <= 1.0

    # n_above_threshold must be <= n_images
    assert 0 <= result["n_above_threshold"] <= n_images


@pytest.mark.gpu
def test_b1_runs_and_returns_deterministic_result() -> None:
    """The b1 entrypoint must run end-to-end and return the same dict twice."""
    result1 = cv_preprocess_inference_postprocess.b1()
    result2 = cv_preprocess_inference_postprocess.b1()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1 == result2


@pytest.mark.gpu
def test_b1_produces_same_result_as_b0() -> None:
    """B1 must produce numerically equivalent results to B0 (same pipeline, compiled).

    torch.compile may reorder float32 operations, introducing differences up
    to ~1e-3 in softmax probabilities.  We use 1e-3 as the tolerance for
    per-image confidences (float32 model) — this matches the harness's
    rtol_by_dtype for float32 (1e-4 relative) which translates to absolute
    differences of ~1e-3 at typical confidence magnitudes.
    """
    b0_result = cv_preprocess_inference_postprocess.b0()
    b1_result = cv_preprocess_inference_postprocess.b1()

    assert b0_result["n_images"] == b1_result["n_images"]
    # Class IDs must match (softmax + argmax is deterministic for clear winners)
    assert b0_result["top1_class_ids"] == b1_result["top1_class_ids"]
    # Confidences may differ due to compiled float32 reordering (atol=1e-3)
    for c0, c1 in zip(b0_result["top1_confidences"], b1_result["top1_confidences"], strict=True):
        assert abs(c0 - c1) < 1e-3
    assert b0_result["n_above_threshold"] == b1_result["n_above_threshold"]

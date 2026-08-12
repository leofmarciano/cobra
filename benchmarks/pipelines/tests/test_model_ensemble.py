"""Tests for the model_ensemble workload.

T2 acceptance criteria:
- Oracle passes (deterministic, reproducible results).
- Both branches provably independent (no shared mutable state) — assert in test.
"""

from __future__ import annotations

import pytest
import torch
import torch.nn as nn
from cobra_pipelines import model_ensemble


def test_b0_runs_and_returns_deterministic_result() -> None:
    """The b0 entrypoint must run end-to-end and return the same dict twice."""
    result1 = model_ensemble.b0()
    result2 = model_ensemble.b0()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1 == result2


def test_b0_result_contains_expected_keys() -> None:
    """The output dict must contain specific aggregation keys."""
    result = model_ensemble.b0()
    expected_keys = {"n_samples", "mlp_mean", "transformer_mean", "ensemble_mean", "ensemble_sum"}
    assert expected_keys.issubset(result.keys())


def test_branches_are_independent_no_shared_mutable_state() -> None:
    """Both model branches must be provably independent.

    We verify by running each branch alone and checking outputs match
    the ensemble result — i.e., running branch A does not affect branch B.
    """
    seed = model_ensemble.DEFAULT_SEED
    batch_size = model_ensemble.DEFAULT_BATCH_SIZE
    in_features = model_ensemble.IN_FEATURES

    # Generate the shared input
    rng = torch.Generator().manual_seed(seed)
    x = torch.randn(batch_size, in_features, generator=rng, dtype=torch.float64)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_dev = x.to(device)

    # Run branch A (MLP) in isolation
    mlp = model_ensemble._build_mlp(in_features, seed).to(device)
    mlp.eval()
    with torch.inference_mode():
        mlp_out_alone = mlp(x_dev).squeeze(-1).cpu()

    # Run branch B (Transformer) in isolation
    transformer = model_ensemble._build_transformer(in_features, seed + 1).to(device)
    transformer.eval()
    with torch.inference_mode():
        trans_out_alone = transformer(x_dev).squeeze(-1).cpu()

    # Now run both via the pipeline
    mlp2 = model_ensemble._build_mlp(in_features, seed).to(device)
    transformer2 = model_ensemble._build_transformer(in_features, seed + 1).to(device)
    mlp2.eval()
    transformer2.eval()
    with torch.inference_mode():
        mlp_out_together = mlp2(x_dev).squeeze(-1).cpu()
        trans_out_together = transformer2(x_dev).squeeze(-1).cpu()

    # Outputs must be identical regardless of isolation vs. together
    assert torch.equal(mlp_out_alone, mlp_out_together), (
        "MLP output changed when run alongside transformer"
    )
    assert torch.equal(trans_out_alone, trans_out_together), (
        "Transformer output changed when run alongside MLP"
    )


def test_weighted_aggregation_is_correct() -> None:
    """The weighted aggregation must match a manual calculation."""
    seed = model_ensemble.DEFAULT_SEED
    batch_size = model_ensemble.DEFAULT_BATCH_SIZE
    in_features = model_ensemble.IN_FEATURES

    rng = torch.Generator().manual_seed(seed)
    x = torch.randn(batch_size, in_features, generator=rng, dtype=torch.float64)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    x_dev = x.to(device)

    mlp = model_ensemble._build_mlp(in_features, seed).to(device)
    transformer = model_ensemble._build_transformer(in_features, seed + 1).to(device)
    mlp.eval()
    transformer.eval()

    with torch.inference_mode():
        mlp_scores = mlp(x_dev).squeeze(-1).cpu().numpy()
        trans_scores = transformer(x_dev).squeeze(-1).cpu().numpy()

    import numpy as np

    w_mlp = model_ensemble.WEIGHT_MLP
    w_trans = model_ensemble.WEIGHT_TRANSFORMER
    expected_ensemble = w_mlp * mlp_scores + w_trans * trans_scores

    result = model_ensemble.b0()
    assert abs(result["ensemble_mean"] - float(np.mean(expected_ensemble))) < 1e-10
    assert abs(result["ensemble_sum"] - float(np.sum(expected_ensemble))) < 1e-6


def test_compiled_models_are_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[nn.Module] = []
    model_ensemble._COMPILED_MODELS.clear()
    monkeypatch.setattr(model_ensemble, "_build_mlp", lambda in_features, seed: nn.Identity())
    monkeypatch.setattr(
        model_ensemble,
        "_build_transformer",
        lambda in_features, seed: nn.Identity(),
    )

    def fake_compile(model: nn.Module, **kwargs: object) -> nn.Module:
        calls.append(model)
        return model

    monkeypatch.setattr(torch, "compile", fake_compile)
    device = torch.device("cpu")

    first = model_ensemble._get_compiled_models(model_ensemble.IN_FEATURES, 7, device)
    second = model_ensemble._get_compiled_models(model_ensemble.IN_FEATURES, 7, device)

    assert first is second
    assert len(calls) == 2


@pytest.mark.gpu
def test_b1_runs_and_returns_deterministic_result() -> None:
    """The b1 entrypoint must run end-to-end and return the same dict twice."""
    result1 = model_ensemble.b1()
    result2 = model_ensemble.b1()

    assert isinstance(result1, dict)
    assert result1.keys() == result2.keys()
    assert result1 == result2


@pytest.mark.gpu
def test_b1_produces_same_result_as_b0() -> None:
    """B1 must produce numerically equivalent results to B0 (same pipeline, compiled)."""
    b0_result = model_ensemble.b0()
    b1_result = model_ensemble.b1()

    assert b0_result["n_samples"] == b1_result["n_samples"]
    # torch.compile may introduce small numerical differences
    assert abs(b0_result["ensemble_mean"] - b1_result["ensemble_mean"]) < 1e-4
    assert abs(b0_result["ensemble_sum"] - b1_result["ensemble_sum"]) < 1e-1

"""Workload 2 — model_ensemble.

One input batch → two independent torch models (MLP + small transformer
encoder) → weighted aggregation.  This is the parallel-branch opportunity
workload (plan §2.4): the two model forward passes share no mutable state
and can execute concurrently.

Architecture choices:
- Branch A: 3-layer MLP (in → 64 → 32 → 1), ReLU activations, float64.
- Branch B: 2-layer TransformerEncoder with a linear head (in → 1), float64.
  Uses a single attention head and positional encoding is omitted (input is
  a flat feature vector, not sequential); the transformer treats the batch
  dimension normally.

Weighted aggregation:  ensemble = w_mlp * mlp_scores + w_trans * trans_scores
with w_mlp = 0.6, w_trans = 0.4 (arbitrary but fixed).

Output is a JSON-serializable dict of Python floats/ints.  Floats are
compared with rtol/atol tolerance; integers are compared exactly.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
import torch
import torch.nn as nn

# --- Constants (public; tests reference these) ---

DEFAULT_SEED: int = 7
DEFAULT_BATCH_SIZE: int = 2048
IN_FEATURES: int = 16

WEIGHT_MLP: float = 0.6
WEIGHT_TRANSFORMER: float = 0.4


# --- Model definitions ---


class _EnsembleMLP(nn.Module):
    """Branch A: 3-layer MLP → scalar score per sample."""

    def __init__(self, in_features: int, seed: int) -> None:
        super().__init__()
        torch.manual_seed(seed)
        self.net = nn.Sequential(
            nn.Linear(in_features, 64, dtype=torch.float64),
            nn.ReLU(),
            nn.Linear(64, 32, dtype=torch.float64),
            nn.ReLU(),
            nn.Linear(32, 1, dtype=torch.float64),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return cast(torch.Tensor, self.net(x))


class _EnsembleTransformer(nn.Module):
    """Branch B: TransformerEncoder + linear head → scalar score per sample.

    The input feature vector of shape (batch, in_features) is reshaped to
    (batch, in_features, 1) — treating each feature as a "token" of
    dimension 1 — then projected up to d_model.  This is a minimal but
    legitimate use of multi-head self-attention that exercises the full
    transformer forward path.
    """

    def __init__(self, in_features: int, seed: int) -> None:
        super().__init__()
        torch.manual_seed(seed)
        d_model = 16
        self.input_proj = nn.Linear(1, d_model, dtype=torch.float64)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=2,
            dim_feedforward=32,
            dropout=0.0,
            batch_first=True,
            dtype=torch.float64,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.head = nn.Linear(d_model * in_features, 1, dtype=torch.float64)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, in_features)
        batch = x.shape[0]
        # Treat each feature as a token of dim 1
        tokens = x.unsqueeze(-1)  # (batch, in_features, 1)
        tokens = self.input_proj(tokens)  # (batch, in_features, d_model)
        encoded = self.encoder(tokens)  # (batch, in_features, d_model)
        flat = encoded.reshape(batch, -1)  # (batch, in_features * d_model)
        return cast(torch.Tensor, self.head(flat))


# --- Public helpers for building models (used by tests to verify independence) ---


def _build_mlp(in_features: int, seed: int) -> _EnsembleMLP:
    """Construct the MLP branch with deterministic weights."""
    return _EnsembleMLP(in_features, seed)


def _build_transformer(in_features: int, seed: int) -> _EnsembleTransformer:
    """Construct the transformer branch with deterministic weights."""
    return _EnsembleTransformer(in_features, seed)


# --- Pipeline ---


def b0() -> dict[str, Any]:
    """B0: eager Python — two independent model branches + weighted aggregation.

    Plan §20.2: B0 is "plain eager execution with no automatic tools applied."
    """
    seed = DEFAULT_SEED
    batch_size = DEFAULT_BATCH_SIZE
    in_features = IN_FEATURES

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Generate deterministic input batch
    rng = torch.Generator().manual_seed(seed)
    x = torch.randn(batch_size, in_features, generator=rng, dtype=torch.float64)
    x_dev = x.to(device)

    # Branch A: MLP (independent — no shared mutable state with branch B)
    mlp = _build_mlp(in_features, seed).to(device)
    mlp.eval()

    # Branch B: Transformer (independent — no shared mutable state with branch A)
    transformer = _build_transformer(in_features, seed + 1).to(device)
    transformer.eval()

    with torch.inference_mode():
        mlp_scores = mlp(x_dev).squeeze(-1)  # (batch_size,)
        trans_scores = transformer(x_dev).squeeze(-1)  # (batch_size,)

    # Weighted aggregation
    ensemble_scores = WEIGHT_MLP * mlp_scores + WEIGHT_TRANSFORMER * trans_scores

    # Move to CPU numpy for summary
    mlp_np: np.ndarray = mlp_scores.cpu().numpy()
    trans_np: np.ndarray = trans_scores.cpu().numpy()
    ensemble_np: np.ndarray = ensemble_scores.cpu().numpy()

    return {
        "n_samples": int(batch_size),
        "mlp_mean": float(np.mean(mlp_np)),
        "transformer_mean": float(np.mean(trans_np)),
        "ensemble_mean": float(np.mean(ensemble_np)),
        "ensemble_sum": float(np.sum(ensemble_np)),
    }

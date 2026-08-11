"""Workload 1 — parquet_feature_inference.

A synthetic Parquet -> pandas feature engineering -> torch MLP baseline (B0).

Pipeline:
    1. Generate or reuse a seeded Parquet file with mixed dtypes, nulls,
       categoricals, and bools.
    2. read_parquet into a pandas DataFrame.
    3. Filter rows and fill nulls.
    4. Engineer features (interaction term + one-hot categoricals).
    5. Convert to a torch tensor.
    6. Run a small, seeded MLP.
    7. Project the per-row scores into summary statistics.

The output is a JSON-serializable dict of integers and Python floats.  Floats
are compared with ``rtol_by_dtype`` / ``atol_by_dtype`` tolerance; integers are
compared exactly (plan §33.4).
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import torch
import torch.nn as nn

DATA_DIR_ENV = "COBRA_DATA_DIR"
N_ROWS_ENV = "COBRA_PARQUET_ROWS"
SEED_ENV = "COBRA_PARQUET_SEED"

DEFAULT_N_ROWS = 100_000
DEFAULT_SEED = 42


def _default_data_dir() -> Path:
    return Path(tempfile.gettempdir()) / "cobra" / "parquet_feature_inference"


def _n_rows() -> int:
    return int(os.environ.get(N_ROWS_ENV, DEFAULT_N_ROWS))


def _seed() -> int:
    return int(os.environ.get(SEED_ENV, DEFAULT_SEED))


def _parquet_path(
    data_dir: Path | None = None,
    n_rows: int | None = None,
    seed: int | None = None,
) -> Path:
    if data_dir is None:
        data_dir = Path(os.environ.get(DATA_DIR_ENV, _default_data_dir()))
    n_rows = _n_rows() if n_rows is None else n_rows
    seed = _seed() if seed is None else seed
    data_dir = data_dir / f"rows_{n_rows}_seed_{seed}"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "data.parquet"


def _synthetic_table(n_rows: int, seed: int) -> pa.Table:
    """Build a deterministic PyArrow Table with mixed dtypes and nulls."""
    rng = np.random.default_rng(seed)

    categories = ["A", "B", "C", "D"]
    labels = ["x", "y", "z"]

    score = rng.normal(5.0, 2.0, size=n_rows)
    null_mask = rng.random(size=n_rows) < 0.10
    score[null_mask] = np.nan

    return pa.table(
        {
            "id": pa.array(np.arange(n_rows, dtype=np.int64)),
            "category": pa.array(rng.choice(categories, size=n_rows)),
            "flag": pa.array(rng.choice([True, False], size=n_rows)),
            "feature_a": pa.array(rng.normal(0.0, 1.0, size=n_rows), type=pa.float64()),
            "feature_b": pa.array(rng.normal(0.0, 1.0, size=n_rows), type=pa.float64()),
            "group": pa.array(rng.integers(0, 5, size=n_rows, dtype=np.int64)),
            "label": pa.array(rng.choice(labels, size=n_rows)),
            "score": pa.array(score, type=pa.float64()),
        }
    )


def generate_dataset(
    n_rows: int | None = None,
    seed: int | None = None,
    data_dir: Path | None = None,
) -> str:
    """Generate the synthetic Parquet dataset and return its file path.

    The file is written with deterministic settings (no compression, no
    dictionary encoding) so the bytes are hash-stable across runs on the same
    version of PyArrow.
    """
    n_rows = _n_rows() if n_rows is None else n_rows
    seed = _seed() if seed is None else seed
    path = _parquet_path(data_dir, n_rows=n_rows, seed=seed)

    table = _synthetic_table(n_rows, seed)
    pq.write_table(
        table,
        path,
        compression="none",
        use_dictionary=False,
        write_statistics=False,
    )
    return str(path)


def _read_and_filter(parquet_path: str) -> pd.DataFrame:
    """read_parquet + deterministic filter."""
    df = pd.read_parquet(parquet_path)
    # Keep rows where feature_a is above a threshold, flag is true, and score
    # is present.  This exercises a mixed boolean/numeric/null filter.
    return df[(df["feature_a"] > -1.0) & df["flag"] & df["score"].notna()].reset_index(drop=True)


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Pandas feature engineering: fill nulls, interaction term, one-hots."""
    df = df.copy()
    df["feature_c"] = df["feature_a"] * df["feature_b"] + df["group"].astype(np.float64)
    df["score_filled"] = df["score"].fillna(5.0)

    one_hot = pd.get_dummies(df["category"], prefix="cat", dtype=np.float64)
    df = pd.concat([df, one_hot], axis=1)

    # Select a stable, ordered set of numeric columns.
    numeric_cols = [
        "feature_a",
        "feature_b",
        "feature_c",
        "group",
        "score_filled",
        "cat_A",
        "cat_B",
        "cat_C",
        "cat_D",
    ]
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0

    # Normalize each column to zero mean and unit variance using the data
    # statistics themselves (a realistic preprocessing step).
    numeric = df[numeric_cols].astype(np.float64)
    mean = numeric.mean()
    std = numeric.std(ddof=0).replace(0.0, 1.0)
    return (numeric - mean) / std


class _SmallMLP(nn.Module):
    """A tiny fully-connected network with deterministic, seeded weights."""

    def __init__(self, in_features: int, seed: int) -> None:
        super().__init__()
        torch.manual_seed(seed)
        self.fc1 = nn.Linear(in_features, 32, dtype=torch.float64)
        self.fc2 = nn.Linear(32, 1, dtype=torch.float64)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return cast(torch.Tensor, self.fc2(torch.relu(self.fc1(x))))


def _mlp_scores(features: pd.DataFrame, seed: int) -> np.ndarray:
    """Convert features to a torch tensor and run the seeded MLP."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    x = torch.from_numpy(features.to_numpy(dtype=np.float64)).to(device, dtype=torch.float64)
    model = _SmallMLP(x.shape[1], seed).to(device)
    model.eval()
    with torch.inference_mode():
        return cast(np.ndarray, model(x).squeeze(-1).to("cpu", dtype=torch.float64).numpy())


def _project(scores: np.ndarray, n_rows: int) -> dict[str, Any]:
    """Project per-row scores into a JSON-serializable summary."""
    if len(scores) == 0:
        return {
            "n_rows": n_rows,
            "mean_score": 0.0,
            "p95_score": 0.0,
            "p99_score": 0.0,
            "score_sum": 0.0,
        }

    mean = float(np.mean(scores))
    p95 = float(np.percentile(scores, 95))
    p99 = float(np.percentile(scores, 99))
    total = float(np.sum(scores))

    return {
        "n_rows": int(n_rows),
        "mean_score": mean,
        "p95_score": p95,
        "p99_score": p99,
        "score_sum": total,
    }


def b0() -> dict[str, Any]:
    """B0: ordinary eager Python with pandas and torch (plan §20.2)."""
    seed = _seed()
    n_rows = _n_rows()
    data_dir = Path(os.environ.get(DATA_DIR_ENV, _default_data_dir()))

    # Ensure the dataset exists; generate if missing.  The file path is stable
    # for a given (n_rows, seed) pair.
    expected_path = _parquet_path(data_dir, n_rows=n_rows, seed=seed)
    if not expected_path.is_file():
        generate_dataset(n_rows, seed, data_dir)

    df = _read_and_filter(str(expected_path))
    features = _engineer_features(df)
    scores = _mlp_scores(features, seed)
    return _project(scores, len(df))


class _SmallMLPCompiled(nn.Module):
    """Same architecture as _SmallMLP, for use with torch.compile."""

    def __init__(self, in_features: int, seed: int) -> None:
        super().__init__()
        torch.manual_seed(seed)
        self.fc1 = nn.Linear(in_features, 32, dtype=torch.float64)
        self.fc2 = nn.Linear(32, 1, dtype=torch.float64)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return cast(torch.Tensor, self.fc2(torch.relu(self.fc1(x))))


def _mlp_scores_compiled(features: pd.DataFrame, seed: int) -> np.ndarray:
    """Convert features to a torch tensor and run a torch.compiled MLP."""
    from cobra_pipelines._compile_env import ensure_nvcc_in_path

    ensure_nvcc_in_path()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    x = torch.from_numpy(features.to_numpy(dtype=np.float64)).to(device, dtype=torch.float64)
    model = _SmallMLPCompiled(x.shape[1], seed).to(device)
    model.eval()
    compiled_model = torch.compile(model, mode="default", fullgraph=False)
    with torch.inference_mode():
        out = compiled_model(x).squeeze(-1).to("cpu", dtype=torch.float64)
        return cast(np.ndarray, out.numpy())


def _cudf_pandas_available() -> bool:
    """Check whether cudf.pandas is importable."""
    try:
        import cudf.pandas  # noqa: F401

        return True
    except (ImportError, ModuleNotFoundError):
        return False


def b1() -> dict[str, Any]:
    """B1: torch.compile on MLP + cudf.pandas acceleration (plan §20.2).

    Strongest automatic composition without manual restructuring:
    - torch.compile(mode="default", fullgraph=False) on the MLP.
    - cudf.pandas monkey-patches pandas for GPU-accelerated dataframe ops
      (if cudf is available; gracefully falls back to CPU pandas otherwise).

    Flags/modes:
    - torch.compile: mode="default", fullgraph=False
    - cudf.pandas: install() called before pandas operations (transparent
      acceleration — no code changes to the pipeline logic).
    """
    # Activate cudf.pandas if available (transparent acceleration)
    if _cudf_pandas_available():
        import cudf.pandas

        cudf.pandas.install()

    seed = _seed()
    n_rows = _n_rows()
    data_dir = Path(os.environ.get(DATA_DIR_ENV, _default_data_dir()))

    # Ensure the dataset exists
    expected_path = _parquet_path(data_dir, n_rows=n_rows, seed=seed)
    if not expected_path.is_file():
        generate_dataset(n_rows, seed, data_dir)

    # Pipeline is identical to b0 in structure — only the model is compiled
    # and pandas is transparently accelerated by cudf.pandas.
    df = _read_and_filter(str(expected_path))
    features = _engineer_features(df)
    scores = _mlp_scores_compiled(features, seed)
    return _project(scores, len(df))


def dataset_fingerprint() -> str:
    """Return a sha256 hash of the current dataset file for the manifest."""
    path = _parquet_path()
    if not path.is_file():
        generate_dataset(_n_rows(), _seed())
    return hashlib.sha256(path.read_bytes()).hexdigest()[:32]

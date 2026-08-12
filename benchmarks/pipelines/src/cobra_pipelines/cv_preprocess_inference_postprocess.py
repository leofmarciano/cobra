"""Workload 3 — cv_preprocess_inference_postprocess.

Synthetic image batch → CPU preprocessing (resize/normalize) →
torchvision model (resnet18, pinned weights) → postprocessing (top-k +
thresholding).  This is the mixed CPU/GPU transition workload (plan §2.4):
preprocessing is measurably CPU-bound while inference runs on GPU.

Pipeline:
    1. Generate synthetic random images (batch of uint8 HWC tensors).
    2. CPU preprocessing: resize to 224x224, convert to float, normalize
       with ImageNet mean/std.  This step is intentionally CPU-bound
       (uses numpy/torch CPU ops, no GPU).
    3. Run resnet18 (torchvision, deterministic weights) on GPU.
    4. Postprocessing: softmax → top-k per image → threshold filtering.

Output is a JSON-serializable dict.  Lists of ints/floats are compared
element-wise with tolerances per the harness comparator.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

# --- Constants ---

DEFAULT_SEED: int = 99
DEFAULT_BATCH_SIZE: int = 32
IMAGE_H: int = 256
IMAGE_W: int = 256
TARGET_SIZE: int = 224
TOP_K: int = 1
CONFIDENCE_THRESHOLD: float = 0.01

# ImageNet normalization constants
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
_T = TypeVar("_T")


def _run_traced_boundary(
    op_name: str,
    func: Callable[..., _T],
    *args: Any,
    **kwargs: Any,
) -> _T:
    """Record a boundary when the disposable tracer is installed and active."""
    try:
        from tracer.session import run_boundary
    except ImportError:
        return func(*args, **kwargs)
    return run_boundary(op_name, func, *args, **kwargs)


# --- Synthetic data generation ---


def _generate_synthetic_images_impl(batch_size: int, seed: int) -> list[np.ndarray]:
    """Generate a batch of synthetic uint8 HWC images with deterministic RNG."""
    rng = np.random.default_rng(seed)
    images: list[np.ndarray] = []
    for _ in range(batch_size):
        img = rng.integers(0, 256, size=(IMAGE_H, IMAGE_W, 3), dtype=np.uint8)
        images.append(img)
    return images


def _generate_synthetic_images(batch_size: int, seed: int) -> list[np.ndarray]:
    return _run_traced_boundary(
        "cv.synthetic_image_generation",
        _generate_synthetic_images_impl,
        batch_size,
        seed,
    )


# --- CPU preprocessing (intentionally CPU-bound) ---


def _preprocess(images: list[np.ndarray]) -> torch.Tensor:
    """Resize, convert to float, normalize — all on CPU.

    This function is intentionally CPU-bound: it performs bilinear
    interpolation via torch CPU ops and per-channel normalization.
    No GPU operations occur here.

    Args:
        images: list of (H, W, 3) uint8 numpy arrays.

    Returns:
        Tensor of shape (batch, 3, 224, 224), float32, on CPU.
    """
    batch: list[torch.Tensor] = []
    mean = torch.tensor(IMAGENET_MEAN, dtype=torch.float32).view(3, 1, 1)
    std = torch.tensor(IMAGENET_STD, dtype=torch.float32).view(3, 1, 1)

    for img in images:
        # HWC uint8 numpy → CHW float32 tensor [0, 1]
        t = torch.from_numpy(img).permute(2, 0, 1).to(torch.float32) / 255.0
        # Bilinear resize to TARGET_SIZE x TARGET_SIZE (CPU)
        t = t.unsqueeze(0)
        t = F.interpolate(t, size=(TARGET_SIZE, TARGET_SIZE), mode="bilinear", align_corners=False)
        t = t.squeeze(0)
        # Normalize with ImageNet stats
        t = (t - mean) / std
        batch.append(t)

    return torch.stack(batch)  # (batch, 3, 224, 224) on CPU


# --- Inference ---


def _run_resnet18(preprocessed: torch.Tensor, device: torch.device) -> torch.Tensor:
    """Run resnet18 with deterministic (default) weights on the given device.

    Returns raw logits of shape (batch, 1000).
    """
    # Use default pretrained weights — pinned via torchvision version pin.
    # set_default_weights is pinned by torchvision==0.28.0.
    torch.manual_seed(0)  # ensure determinism in any stochastic path
    weights = models.ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights).to(device)
    model.eval()

    x = preprocessed.to(device)
    with torch.inference_mode():
        logits: torch.Tensor = model(x)
    return logits


# --- Postprocessing ---


def _postprocess_impl(logits: torch.Tensor, top_k: int, threshold: float) -> dict[str, Any]:
    """Softmax → top-k → threshold filtering.

    Returns a dict with per-image top-1 class IDs, confidences, and
    the count of images above the confidence threshold.
    """
    probs = F.softmax(logits, dim=-1)  # (batch, 1000)
    topk_vals, topk_ids = probs.topk(top_k, dim=-1)  # (batch, top_k)

    # Move to CPU for serialization
    topk_vals_np = topk_vals.cpu().numpy()
    topk_ids_np = topk_ids.cpu().numpy()

    top1_class_ids = [int(topk_ids_np[i, 0]) for i in range(len(topk_ids_np))]
    top1_confidences = [float(topk_vals_np[i, 0]) for i in range(len(topk_vals_np))]

    n_above_threshold = sum(1 for c in top1_confidences if c >= threshold)

    return {
        "top1_class_ids": top1_class_ids,
        "top1_confidences": top1_confidences,
        "n_above_threshold": n_above_threshold,
    }


def _postprocess(logits: torch.Tensor, top_k: int, threshold: float) -> dict[str, Any]:
    return _run_traced_boundary(
        "cv.postprocess",
        _postprocess_impl,
        logits,
        top_k,
        threshold,
    )


# --- Pipeline entrypoint ---


def b0() -> dict[str, Any]:
    """B0: eager Python — CPU preprocessing + GPU inference + postprocessing.

    Plan §20.2: B0 is "plain eager execution with no automatic tools applied."
    """
    seed = DEFAULT_SEED
    batch_size = DEFAULT_BATCH_SIZE
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Step 1: Generate synthetic images
    images = _generate_synthetic_images(batch_size, seed)

    # Step 2: CPU preprocessing (measurably CPU-bound)
    preprocessed = _preprocess(images)

    # Step 3: GPU inference
    logits = _run_resnet18(preprocessed, device)

    # Step 4: Postprocessing (top-k + thresholding)
    post_result = _postprocess(logits, TOP_K, CONFIDENCE_THRESHOLD)

    return {
        "n_images": batch_size,
        "top1_class_ids": post_result["top1_class_ids"],
        "top1_confidences": post_result["top1_confidences"],
        "n_above_threshold": post_result["n_above_threshold"],
    }


_COMPILED_RESNETS: dict[str, nn.Module] = {}


def _get_compiled_resnet18(device: torch.device) -> nn.Module:
    """Run torch.compiled resnet18 with deterministic (default) weights.

    Returns raw logits of shape (batch, 1000).
    """
    from cobra_pipelines._compile_env import ensure_nvcc_in_path

    ensure_nvcc_in_path()

    cache_key = str(device)
    compiled_model = _COMPILED_RESNETS.get(cache_key)
    if compiled_model is not None:
        return compiled_model

    torch.manual_seed(0)
    weights = models.ResNet18_Weights.DEFAULT
    model = models.resnet18(weights=weights).to(device)
    model.eval()
    compiled_model = cast(nn.Module, torch.compile(model, mode="default", fullgraph=False))
    _COMPILED_RESNETS[cache_key] = compiled_model
    return compiled_model


def _run_resnet18_compiled(preprocessed: torch.Tensor, device: torch.device) -> torch.Tensor:
    compiled_model = _get_compiled_resnet18(device)

    x = preprocessed.to(device)
    with torch.inference_mode():
        logits: torch.Tensor = compiled_model(x)
    return logits


def b1() -> dict[str, Any]:
    """B1: torch.compile on resnet18 — strongest automatic composition.

    Plan §20.2: B1 is "strongest reasonable composition of existing automatic
    tools, such as torch.compile [...] without hand-written application
    restructuring."

    Flags/modes:
    - torch.compile(mode="default", fullgraph=False) on resnet18.
    - Preprocessing remains CPU-bound (no manual restructuring).
    - No cudf.pandas (this workload does not use pandas).
    """
    seed = DEFAULT_SEED
    batch_size = DEFAULT_BATCH_SIZE
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Step 1: Generate synthetic images (identical to b0)
    images = _generate_synthetic_images(batch_size, seed)

    # Step 2: CPU preprocessing (identical to b0 — no restructuring)
    preprocessed = _preprocess(images)

    # Step 3: GPU inference with torch.compile
    logits = _run_resnet18_compiled(preprocessed, device)

    # Step 4: Postprocessing (identical to b0)
    post_result = _postprocess(logits, TOP_K, CONFIDENCE_THRESHOLD)

    return {
        "n_images": batch_size,
        "top1_class_ids": post_result["top1_class_ids"],
        "top1_confidences": post_result["top1_confidences"],
        "n_above_threshold": post_result["n_above_threshold"],
    }

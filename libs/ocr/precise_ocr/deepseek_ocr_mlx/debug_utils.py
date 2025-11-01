"""Diagnostics and parity helpers for the MLX DeepSeek-OCR port.

This module bundles the recurring analysis steps we have been carrying out
manually while aligning the MLX implementation with the Hugging Face / PyTorch
reference.  The goal is to make it easy to:

* Inspect intermediary tensors (vision features, fused embeddings, decoder
  layers, logits) and compute cosine-difference summaries in a repeatable way.
* Reorder local vision tokens between the Hugging Face tiling layout and the
  MLX row-major layout produced by :func:`_format_local`.
* Highlight the most mismatched elements so the next debugging iteration can
  focus on a narrow slice of the sequence.

Downstream scripts can import these utilities instead of rewriting bespoke
NumPy snippets each time we need to compare checkpoints or sanity-check
pre/post fixes.  The helpers only depend on NumPy so they can be used from both
the MLX environment and the PyTorch reference environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np


DEFAULT_LOCAL_SPATIAL = 10


@dataclass
class CosineSummary:
    """Basic statistics describing a set of cosine similarities."""

    mean: float
    min: float
    max: float
    median: float
    pct_10: float
    pct_90: float


@dataclass
class ArrayComparison:
    """Container for reporting pairwise array diagnostics."""

    shape_a: Tuple[int, ...]
    shape_b: Tuple[int, ...]
    overall_cosine: float
    l2_norm: float
    cosine_per_row: Optional[np.ndarray] = None
    top_mismatched: Optional[np.ndarray] = None


def _safe_array(x: np.ndarray | Sequence[float]) -> np.ndarray:
    if isinstance(x, np.ndarray):
        return x
    return np.asarray(x, dtype=np.float32)


def cosine_similarity(
    a: np.ndarray, b: np.ndarray, axis: Optional[int] = None
) -> np.ndarray:
    """Compute cosine similarity along given axis."""

    a = _safe_array(a)
    b = _safe_array(b)
    if axis is None:
        return float(
            np.dot(a.ravel(), b.ravel()) / (np.linalg.norm(a) * np.linalg.norm(b))
        )

    a_norm = np.linalg.norm(a, axis=axis, keepdims=True)
    b_norm = np.linalg.norm(b, axis=axis, keepdims=True)
    denom = np.clip(a_norm * b_norm, a_min=1e-12, a_max=None)
    return np.sum(a * b, axis=axis) / denom.squeeze(axis)


def summarize_cosines(values: Iterable[float]) -> CosineSummary:
    vals = np.asarray(list(values), dtype=np.float32)
    return CosineSummary(
        mean=float(vals.mean()),
        min=float(vals.min()),
        max=float(vals.max()),
        median=float(np.median(vals)),
        pct_10=float(np.percentile(vals, 10)),
        pct_90=float(np.percentile(vals, 90)),
    )


def compare_arrays(
    a: np.ndarray,
    b: np.ndarray,
    *,
    per_row: bool = True,
    top_k: int = 10,
    axis: int = 0,
) -> ArrayComparison:
    """Compare two arrays and return cosine + L2 diagnostics."""

    a = _safe_array(a)
    b = _safe_array(b)
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")

    overall = cosine_similarity(a, b)
    l2 = float(np.linalg.norm(a - b))

    row_cos = None
    top_indices = None
    if per_row:
        row_cos = cosine_similarity(a, b, axis=axis)
        if row_cos.ndim > 1:
            row_cos = row_cos.reshape(-1)
        order = np.argsort(row_cos)
        top_indices = order[:top_k]

    return ArrayComparison(
        shape_a=a.shape,
        shape_b=b.shape,
        overall_cosine=float(overall),
        l2_norm=l2,
        cosine_per_row=row_cos,
        top_mismatched=top_indices,
    )


def hf_local_index_to_mlx(
    index: int,
    *,
    width_tiles: int,
    height_tiles: int,
    spatial: int = DEFAULT_LOCAL_SPATIAL,
) -> int:
    """Map a Hugging Face local-token index to the MLX row-major order."""

    tile_size = spatial * spatial
    num_tiles = width_tiles * height_tiles
    if index >= tile_size * num_tiles:
        raise ValueError("Local index exceeds available tile capacity")

    tile_idx = index // tile_size
    inner = index % tile_size

    local_row = inner // spatial
    local_col = inner % spatial
    tile_row = tile_idx // width_tiles
    tile_col = tile_idx % width_tiles

    total_width = width_tiles * spatial
    return (
        (tile_row * spatial + local_row) * total_width + tile_col * spatial + local_col
    )


def mlx_local_index_to_hf(
    index: int,
    *,
    width_tiles: int,
    height_tiles: int,
    spatial: int = DEFAULT_LOCAL_SPATIAL,
) -> int:
    """Inverse mapping of :func:`hf_local_index_to_mlx`."""

    total_tokens = width_tiles * height_tiles * spatial * spatial
    if index >= total_tokens:
        raise ValueError("Local index exceeds available tile capacity")

    total_width = width_tiles * spatial
    row = index // total_width
    col = index % total_width

    tile_row = row // spatial
    tile_col = col // spatial
    local_row = row % spatial
    local_col = col % spatial

    tile_idx = tile_row * width_tiles + tile_col
    tile_size = spatial * spatial
    return tile_idx * tile_size + local_row * spatial + local_col


def reorder_locals(
    tokens: np.ndarray,
    *,
    width_tiles: int,
    height_tiles: int,
    spatial: int = DEFAULT_LOCAL_SPATIAL,
    direction: str = "hf_to_mlx",
) -> np.ndarray:
    """Reorder local vision tokens between HF and MLX layouts."""

    tokens = _safe_array(tokens)
    tile_total = width_tiles * height_tiles * spatial * spatial
    if tokens.shape[0] != tile_total:
        raise ValueError(
            "Token count does not match expected local capacity; provide local-only slice"
        )

    if direction not in {"hf_to_mlx", "mlx_to_hf"}:
        raise ValueError("direction must be 'hf_to_mlx' or 'mlx_to_hf'")

    mapper = (
        hf_local_index_to_mlx if direction == "hf_to_mlx" else mlx_local_index_to_hf
    )
    reordered = np.empty_like(tokens)
    for idx in range(tile_total):
        target = mapper(
            idx, width_tiles=width_tiles, height_tiles=height_tiles, spatial=spatial
        )
        reordered[target] = tokens[idx]
    return reordered


def load_npy(path: str) -> np.ndarray:
    """Thin wrapper around :func:`np.load` with float32 casting."""

    arr = np.load(path)
    return _safe_array(arr)


def print_comparison(title: str, comparison: ArrayComparison) -> None:
    """Pretty-print comparison results for quick CLI use."""

    print(f"=== {title} ===")
    print(f"shape A: {comparison.shape_a}")
    print(f"shape B: {comparison.shape_b}")
    print(f"overall cosine: {comparison.overall_cosine:.6f}")
    print(f"L2 norm diff: {comparison.l2_norm:.6f}")
    if comparison.cosine_per_row is not None:
        summary = summarize_cosines(comparison.cosine_per_row)
        print(
            "per-row cosine: "
            f"mean={summary.mean:.6f}, min={summary.min:.6f}, max={summary.max:.6f}, "
            f"median={summary.median:.6f}, p10={summary.pct_10:.6f}, p90={summary.pct_90:.6f}"
        )
    if comparison.top_mismatched is not None:
        print(f"worst indices: {comparison.top_mismatched.tolist()}")


__all__ = [
    "ArrayComparison",
    "CosineSummary",
    "DEFAULT_LOCAL_SPATIAL",
    "compare_arrays",
    "cosine_similarity",
    "hf_local_index_to_mlx",
    "load_npy",
    "mlx_local_index_to_hf",
    "print_comparison",
    "reorder_locals",
    "summarize_cosines",
]

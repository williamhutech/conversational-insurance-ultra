"""Utility helpers to instantiate and load the DeepSeek-OCR MLX model."""

from __future__ import annotations

import json
from pathlib import Path
import mlx.core as mx

from .config import DeepSeekOCRConfig
from .model import DeepSeekOCRForCausalLM


def load_config(model_path: Path) -> DeepSeekOCRConfig:
    """Load a Hugging Face `config.json` into :class:`DeepSeekOCRConfig`."""

    config_path = model_path / "config.json"
    with config_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return DeepSeekOCRConfig.from_dict(raw)


def _gather_weights(model_path: Path) -> dict[str, mx.array]:
    """Read all `.safetensors` shards under ``model_path``."""

    weights: dict[str, mx.array] = {}
    for shard in sorted(model_path.glob("*.safetensors")):
        loaded = mx.load(str(shard))
        if not isinstance(loaded, dict):
            raise ValueError(f"Unexpected payload type for {shard}: {type(loaded)!r}")
        weights.update(loaded)
    if not weights:
        raise FileNotFoundError(f"No safetensors found in {model_path}")
    return weights


def load_model(model_path: Path, *, lazy: bool = False) -> DeepSeekOCRForCausalLM:
    """Instantiate ``DeepSeekOCRForCausalLM`` and load MLX weights."""

    config = load_config(model_path)
    model = DeepSeekOCRForCausalLM(config)

    weights = _gather_weights(model_path)
    weights = model.model.sanitize(weights)

    casted: dict[str, mx.array] = {}
    for name, tensor in weights.items():
        if tensor.dtype == mx.float32:
            casted[name] = tensor.astype(mx.float16)
        else:
            casted[name] = tensor

    weights = casted

    model.load_weights(list(weights.items()))

    if not lazy:
        mx.eval(model.parameters())

    model.eval()
    return model


def load(model_path: Path | str, *, lazy: bool = False) -> DeepSeekOCRForCausalLM:
    """Convenience wrapper accepting either a :class:`Path` or string."""

    resolved = Path(model_path)
    return load_model(resolved, lazy=lazy)

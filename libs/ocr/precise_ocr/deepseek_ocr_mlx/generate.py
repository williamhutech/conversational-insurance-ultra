"""Text generation helpers for the DeepSeek-OCR MLX port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, Sequence

import numpy as np
import mlx.core as mx

from .processor import ProcessorOutput
from mlx_vlm.models.cache import make_prompt_cache


class TokenizerProtocol(Protocol):
    def decode(
        self, token_ids: Sequence[int], *, skip_special_tokens: bool = ...
    ) -> str: ...


@dataclass
class GenerationConfig:
    """Configuration controlling the decoding loop."""

    max_new_tokens: int = 512
    temperature: float = 0.0
    eos_token_id: Optional[int] = None
    stop_token_ids: Optional[Sequence[int]] = None
    skip_special_tokens: bool = True


@dataclass
class GenerationResult:
    """Container with the generated text and token ids."""

    text: str
    generated_ids: List[int]
    full_ids: List[int]


def _sample_token(logits: np.ndarray, temperature: float) -> int:
    if temperature <= 0.0 or np.isclose(temperature, 0.0):
        return int(logits.argmax())

    scaled = logits / temperature
    scaled -= scaled.max()  # numerical stability
    probs = np.exp(scaled)
    probs /= probs.sum()
    return int(np.random.choice(len(probs), p=probs))


def generate(
    model,
    tokenizer: TokenizerProtocol,
    batch: ProcessorOutput,
    config: Optional[GenerationConfig] = None,
) -> GenerationResult:
    """Run a simple greedy/temperature sampling loop for the given batch.

    The ``batch`` should be produced by :class:`DeepSeekOCRPreprocessor` and
    contain exactly one prompt/image pair. Image tokens in ``batch`` are
    preserved across steps; only text tokens are appended during decoding.
    """

    if batch.input_ids.shape[0] != 1:
        raise ValueError("Generation helper currently supports batch size 1.")

    if config is None:
        config = GenerationConfig()
    if config.eos_token_id is None:
        eos_id = getattr(getattr(model, "config", None), "eos_token_id", None)
        config.eos_token_id = eos_id

    input_row = np.array(batch.input_ids[0])
    image_mask_row = np.array(batch.images_seq_mask[0])

    input_ids: List[int] = [int(token) for token in input_row.tolist()]
    image_mask: List[bool] = [bool(flag) for flag in image_mask_row.tolist()]
    pixel_values = batch.pixel_values
    images_spatial_crop = batch.images_spatial_crop

    generated: List[int] = []

    base_model = getattr(model, "model", model)
    language_model = getattr(base_model, "language_model", None)
    if language_model is None:
        raise ValueError(
            "Model must expose a language_model attribute for KV cache construction."
        )
    prompt_cache = make_prompt_cache(language_model)

    input_array = mx.array([input_ids], dtype=mx.int32)
    image_mask_array = mx.array([image_mask])

    logits = model(
        input_array,
        pixel_values=pixel_values,
        cache=prompt_cache,
        images_seq_mask=image_mask_array,
        images_seq_types=batch.images_seq_types,
        images_spatial_crop=images_spatial_crop,
    )

    next_logits = logits[:, -1, :].astype(mx.float32)
    mx.eval(next_logits)
    next_logits_np = np.array(next_logits)[0]

    for _ in range(config.max_new_tokens):
        next_token = _sample_token(next_logits_np, config.temperature)

        input_ids.append(next_token)
        image_mask.append(False)
        generated.append(next_token)

        if config.stop_token_ids and next_token in config.stop_token_ids:
            break
        if config.eos_token_id is not None and next_token == config.eos_token_id:
            break

        logits = model(
            mx.array([[next_token]], dtype=mx.int32),
            cache=prompt_cache,
        )
        next_logits = logits[:, -1, :].astype(mx.float32)
        mx.eval(next_logits)
        next_logits_np = np.array(next_logits)[0]

    text = tokenizer.decode(
        generated,
        skip_special_tokens=config.skip_special_tokens,
    )
    return GenerationResult(text=text, generated_ids=generated, full_ids=input_ids)

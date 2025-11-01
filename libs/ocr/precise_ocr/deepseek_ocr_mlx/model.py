"""Local MLX implementation scaffolding for DeepSeek-OCR."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten

from PIL import Image

from mlx_vlm.models.base import interpolate, scaled_dot_product_attention
from mlx_vlm.models.deepseek_vl_v2.config import TextConfig as DeepseekTextConfig
from mlx_vlm.models.deepseek_vl_v2.language import DeepseekV2Model, MoEGate
from mlx_vlm.models.multi_modality import sam as sam_module
from .sam_custom import ImageEncoderViT_MLX

# --- Debug toggles to make decoder debugging tractable ---
# If True, routed experts are effectively disabled: gate returns zero scores so
# the routed mixture contributes nothing and only shared experts (if any) run.
DEBUG_DISABLE_ROUTED_EXPERTS: bool = False

# Optional forced gating (inds, scores). When set, the patched MoE gate will
# return these tensors (sliced to current [B, T]) instead of recomputing.
# Shape contract: inds: (B, T, top_k) int32, scores: (B, T, top_k) float32
DEBUG_FORCED_GATE: Optional[tuple[mx.array, mx.array]] = None
DEBUG_FORCED_GATE_MAP: Optional[Dict[int, tuple[mx.array, mx.array]]] = None
DEBUG_ROPE_SCALE_OVERRIDE: Optional[float] = None
DEBUG_EXTERNAL_ROPE: Optional[Dict[int, tuple[mx.array, mx.array]]] = None
DEBUG_ROPE_VARIANT: Optional[str] = (
    None  # None|"invert-sin"|"swap-even-odd"|"swap+invert"
)
# Optional override to force post-RoPE queries/keys from HF dumps for isolation
DEBUG_FORCE_QK_ROPE: Optional[Dict[int, tuple[mx.array, mx.array]]] = None


def set_debug_disable_routed_experts(value: bool) -> None:
    global DEBUG_DISABLE_ROUTED_EXPERTS
    DEBUG_DISABLE_ROUTED_EXPERTS = bool(value)


def set_debug_forced_gate(inds: mx.array, scores: mx.array) -> None:
    """Install forced gate selections for debugging.

    Args:
        inds: int indices (B, T, top_k)
        scores: float weights (B, T, top_k)
    """
    global DEBUG_FORCED_GATE
    DEBUG_FORCED_GATE = (inds, scores)


def set_debug_forced_gate_map(mapping: Dict[int, tuple[mx.array, mx.array]]) -> None:
    """Install per-layer forced gate selections for debugging.

    Args:
        mapping: dict layer_idx -> (inds, scores) with shapes (B,T,top_k)
    """
    global DEBUG_FORCED_GATE_MAP
    DEBUG_FORCED_GATE_MAP = mapping


def set_debug_rope_scale_override(value: Optional[float]) -> None:
    """Override the RoPE scale used by Llama-style attention (debug only)."""
    global DEBUG_ROPE_SCALE_OVERRIDE
    DEBUG_ROPE_SCALE_OVERRIDE = value


def set_debug_external_rope_map(mapping: Dict[int, tuple[mx.array, mx.array]]) -> None:
    """Install per-layer external RoPE (cos, sin) caches to force rotary application.

    Args:
        mapping: dict layer_idx -> (cos, sin) with shapes broadcastable to (1,1,L,half)
    """
    global DEBUG_EXTERNAL_ROPE
    DEBUG_EXTERNAL_ROPE = mapping


def set_debug_rope_variant(variant: Optional[str]) -> None:
    """Set external RoPE variant: invert sin and/or swap even/odd pairing."""
    global DEBUG_ROPE_VARIANT
    DEBUG_ROPE_VARIANT = variant


def set_debug_force_qk_rope_map(mapping: Dict[int, tuple[mx.array, mx.array]]) -> None:
    """Force attention to use provided post-RoPE q/k tensors per layer.

    Args:
        mapping: dict layer_idx -> (q_rope, k_rope) with shapes (B,H,L,D)
    """
    global DEBUG_FORCE_QK_ROPE
    DEBUG_FORCE_QK_ROPE = mapping


# Optional attention internals capture for early-layer analysis
ATTENTION_CAPTURE_LAYERS: set[int] = set()
ATTENTION_CAPTURE: Dict[tuple[int, str], mx.array] = {}


def set_attention_capture_layers(layers: Sequence[int]) -> None:
    global ATTENTION_CAPTURE_LAYERS, ATTENTION_CAPTURE
    ATTENTION_CAPTURE_LAYERS = set(int(i) for i in layers)
    ATTENTION_CAPTURE = {}


def get_attention_capture() -> Dict[tuple[int, str], mx.array]:
    """Return the current attention capture dictionary.

    Note: this returns a live reference; callers should copy if they plan to mutate.
    """
    return ATTENTION_CAPTURE


# Override SAM's internal resize to a no-op to match DeepSeek-OCR reference
# behavior (no fixed 96x96 resize; rely on conv strides to reach 16x16 and 10x10).
def _identity_resize_image(image_np, new_size=(96, 96), order=1):
    # Pass through unchanged; preserves (B, C, H, W) and dtype
    return image_np


sam_module.resize_image = _identity_resize_image


def _patched_moe_gate_call(self, x: mx.array):
    """Match Hugging Face MoE routing for noaux_tc selection."""
    # Forced debug gate path
    global DEBUG_FORCED_GATE, DEBUG_FORCED_GATE_MAP, DEBUG_DISABLE_ROUTED_EXPERTS
    bsz, seq_len = x.shape[:2]
    # Layer-specific forced gate takes precedence
    layer_idx = getattr(self, "_layer_index", None)
    if DEBUG_FORCED_GATE_MAP is not None and layer_idx is not None:
        forced = DEBUG_FORCED_GATE_MAP.get(int(layer_idx))
        if forced is not None:
            f_inds, f_scores = forced
            inds = f_inds[:bsz, :seq_len]
            scores_selected = f_scores[:bsz, :seq_len]
            return inds.astype(mx.int32), scores_selected.astype(mx.float32)
    if DEBUG_FORCED_GATE is not None:
        f_inds, f_scores = DEBUG_FORCED_GATE
        # Best-effort slice to current sequence
        inds = f_inds[:bsz, :seq_len]
        scores_selected = f_scores[:bsz, :seq_len]
        return inds.astype(mx.int32), scores_selected.astype(mx.float32)

    # Disable routed experts (shared experts only)
    if DEBUG_DISABLE_ROUTED_EXPERTS:
        inds = mx.zeros((bsz, seq_len, self.top_k), dtype=mx.int32)
        scores_selected = mx.zeros((bsz, seq_len, self.top_k), dtype=mx.float32)
        return inds, scores_selected

    gates = x @ self.weight.T

    if self.scoring_func == "softmax":
        scores = mx.softmax(gates, axis=-1, precise=True)  # type: ignore[call-arg]
    elif self.scoring_func == "sigmoid":
        scores = mx.sigmoid(gates)
    else:
        raise ValueError(f"Unknown scoring function: {self.scoring_func}")

    if self.topk_method == "greedy":
        flat_scores = scores
        k = self.top_k
        inds = mx.argpartition(flat_scores, kth=-k, axis=-1)[..., -k:]
        scores_selected = mx.take_along_axis(flat_scores, inds, axis=-1)

    elif self.topk_method == "noaux_tc":
        experts_per_group = self.n_routed_experts // self.n_group
        topk_group = self.topk_group if self.topk_group else self.n_group

        scores_bt = scores.reshape(bsz, seq_len, self.n_routed_experts)
        bias = self.e_score_correction_bias.astype(mx.float32)
        bias = mx.reshape(bias, (1, 1, self.n_routed_experts))
        corrected = scores_bt + bias
        corrected_groups = corrected.reshape(
            bsz, seq_len, self.n_group, experts_per_group
        )

        sorted_groups = mx.sort(corrected_groups, axis=-1)
        if experts_per_group >= 2:
            top_values = sorted_groups[..., -2:]
        else:
            top_values = sorted_groups
        group_scores = mx.sum(top_values, axis=-1)

        if topk_group < self.n_group:
            kth_group = self.n_group - topk_group
            group_idx = mx.argpartition(group_scores, kth=kth_group, axis=-1)[
                ..., -topk_group:
            ]
            group_axis = mx.reshape(
                mx.arange(self.n_group, dtype=mx.int32), (1, 1, self.n_group)
            )
            mask = mx.zeros(group_scores.shape, dtype=mx.bool_)
            for slot in range(topk_group):
                idx = mx.expand_dims(group_idx[..., slot], axis=-1)
                mask = mx.logical_or(mask, mx.equal(idx, group_axis))
        else:
            mask = mx.ones(group_scores.shape, dtype=mx.bool_)

        mask_expanded = mx.expand_dims(mask, axis=-1)
        corrected_masked = mx.where(
            mask_expanded,
            corrected_groups,
            mx.zeros_like(corrected_groups),
        )

        corrected_flat = corrected_masked.reshape(bsz, seq_len, -1)
        raw_flat = scores_bt

        total_experts = corrected_flat.shape[-1]
        kth_value = max(total_experts - self.top_k, 0)
        inds = mx.argpartition(corrected_flat, kth=kth_value, axis=-1)[
            ..., -self.top_k :
        ].astype(mx.int32)
        scores_selected = mx.take_along_axis(raw_flat, inds, axis=-1)

    else:
        raise ValueError(f"Unknown topk method: {self.topk_method}")

    scores_selected = scores_selected * self.routed_scaling_factor
    return inds, scores_selected


if not hasattr(MoEGate, "_deepseekocr_patch"):
    MoEGate.__call__ = _patched_moe_gate_call  # type: ignore[assignment]
    setattr(MoEGate, "_deepseekocr_patch", True)


from .config import DeepSeekOCRConfig


class ClipVisionAttention(nn.Module):
    """Multi-head self-attention used by the CLIP vision backbone."""

    def __init__(self, hidden_size: int, num_heads: int):
        super().__init__()
        if hidden_size % num_heads != 0:
            raise ValueError(
                "hidden_size must be divisible by num_heads for CLIP attention"
            )

        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads

        self.qkv_proj = nn.Linear(hidden_size, hidden_size * 3, bias=True)
        self.out_proj = nn.Linear(hidden_size, hidden_size, bias=True)

    def __call__(self, x: mx.array) -> mx.array:
        batch, seq_len, _ = x.shape

        qkv = self.qkv_proj(x)
        # Match HF packing: (B, S, 3, H, D) then transpose to (B, H, S, 3, D)
        qkv = qkv.reshape(batch, seq_len, 3, self.num_heads, self.head_dim)
        qkv = qkv.transpose(0, 3, 1, 2, 4)

        queries = qkv[:, :, :, 0, :]
        keys = qkv[:, :, :, 1, :]
        values = qkv[:, :, :, 2, :]

        scale = 1.0 / math.sqrt(self.head_dim)
        attn = scaled_dot_product_attention(
            queries, keys, values, cache=None, scale=scale, mask=None
        )
        attn = attn.transpose(0, 2, 1, 3).reshape(batch, seq_len, -1)
        return self.out_proj(attn)


class ClipVisionMLP(nn.Module):
    """Feed-forward network block for the CLIP vision backbone."""

    def __init__(self, hidden_size: int, mlp_ratio: float):
        super().__init__()
        intermediate = int(hidden_size * mlp_ratio)
        self.fc1 = nn.Linear(hidden_size, intermediate, bias=True)

        # Use QuickGELU to match HF implementation: x * sigmoid(1.702 * x)
        class QuickGELU(nn.Module):
            def __call__(self, x: mx.array) -> mx.array:
                return x * mx.sigmoid(1.702 * x)

        self.act = QuickGELU()
        self.fc2 = nn.Linear(intermediate, hidden_size, bias=True)

    def __call__(self, x: mx.array) -> mx.array:
        return self.fc2(self.act(self.fc1(x)))


class ClipVisionBlock(nn.Module):
    """Transformer block used in the CLIP vision backbone."""

    def __init__(self, hidden_size: int, num_heads: int, mlp_ratio: float):
        super().__init__()
        self.layer_norm1 = nn.LayerNorm(hidden_size, eps=1e-5)
        self.self_attn = ClipVisionAttention(hidden_size, num_heads)
        self.layer_norm2 = nn.LayerNorm(hidden_size, eps=1e-5)
        self.mlp = ClipVisionMLP(hidden_size, mlp_ratio)

    def __call__(self, x: mx.array) -> mx.array:
        x = x + self.self_attn(self.layer_norm1(x))
        x = x + self.mlp(self.layer_norm2(x))
        return x


class ClipVisionTransformer(nn.Module):
    """Stack of transformer blocks matching the HF CLIP layout."""

    def __init__(
        self, hidden_size: int, num_layers: int, num_heads: int, mlp_ratio: float
    ):
        super().__init__()
        self.layers = [
            ClipVisionBlock(hidden_size, num_heads, mlp_ratio)
            for _ in range(num_layers)
        ]

    def __call__(self, x: mx.array) -> mx.array:
        for block in self.layers:
            x = block(x)
        return x


class ClipVisionEmbeddings(nn.Module):
    """Embedding layer that merges SAM features with CLIP positional embeds."""

    def __init__(self, width: int, image_size: int, patch_size: int):
        super().__init__()
        self.embed_dim = width
        self.image_size = image_size
        self.patch_size = patch_size

        self.patch_embedding = nn.Conv2d(
            in_channels=3,
            out_channels=width,
            kernel_size=patch_size,
            stride=patch_size,
            bias=False,
        )

        base_patches = (image_size // patch_size) ** 2
        self.num_positions = base_patches + 1
        # These will be loaded from model weights, not random
        self.class_embedding = mx.zeros((width,))
        self.position_embedding = mx.zeros((self.num_positions, width))

    def _interpolated_position(self, target_patches: int) -> mx.array:
        pos_embed = self.position_embedding
        cls_token = pos_embed[:1]
        spatial = pos_embed[1:]

        grid = int(math.sqrt(spatial.shape[0]))
        target = int(math.sqrt(target_patches))

        if grid == target:
            return pos_embed

        # Reshape to (C, H, W)
        spatial = spatial.reshape(grid, grid, self.embed_dim)
        spatial = spatial.transpose(2, 0, 1)

        # Use bicubic interpolation to better match HF behavior
        spatial_np = np.array(spatial.astype(mx.float32))  # (C, H, W)
        out = []
        for c in range(spatial_np.shape[0]):
            ch = spatial_np[c]
            # PIL expects (W, H) with float32 supported in mode 'F'
            im = Image.fromarray(ch, mode="F")
            # Prefer Resampling.BICUBIC; fallback to numeric 3 if constant missing
            resample = getattr(getattr(Image, "Resampling", Image), "BICUBIC", 3)
            imr = im.resize((target, target), resample=resample)
            out.append(np.array(imr, dtype=np.float32))
        spatial_np = np.stack(out, axis=0)  # (C, target, target)
        spatial = mx.array(spatial_np)

        spatial = spatial.transpose(1, 2, 0)
        spatial = spatial.reshape(target * target, self.embed_dim)
        return mx.concatenate([cls_token, spatial], axis=0)

    def __call__(
        self,
        pixel_values: mx.array,
        patch_embeds: Optional[mx.array] = None,
    ) -> mx.array:
        # If no external patches provided, compute with conv and obtain NCHW
        if patch_embeds is None:
            # pixel_values expected as NCHW for conv
            patches_nchw = self.patch_embedding(pixel_values)
        else:
            # Expect external patches as NCHW: (B, C, H, W)
            patches_nchw = patch_embeds

        batch = patches_nchw.shape[0]
        # Flatten spatial and move channels to the last dim -> (B, HW, C)
        b, c, h, w = patches_nchw.shape
        patches = patches_nchw.reshape(b, c, h * w).transpose(0, 2, 1)

        # Class token
        cls_token = mx.expand_dims(self.class_embedding, axis=0)
        cls_token = mx.repeat(cls_token, repeats=batch, axis=0)
        cls_token = mx.expand_dims(cls_token, axis=1)

        embeddings = mx.concatenate([cls_token, patches], axis=1)
        pos_embed = self._interpolated_position(patches.shape[1])
        embeddings = embeddings + mx.expand_dims(pos_embed, axis=0)
        return embeddings


class ClipVisionModel(nn.Module):
    """Minimal CLIP vision transformer that consumes SAM features."""

    def __init__(self, config_clip):
        super().__init__()
        self.hidden_size = config_clip.width
        self.embeddings = ClipVisionEmbeddings(
            width=config_clip.width,
            image_size=config_clip.image_size,
            patch_size=config_clip.patch_size,
        )
        self.pre_layrnorm = nn.LayerNorm(config_clip.width, eps=1e-5)
        self.transformer = ClipVisionTransformer(
            hidden_size=config_clip.width,
            num_layers=config_clip.layers,
            num_heads=config_clip.heads,
            mlp_ratio=config_clip.mlp_ratio,
        )

    def __call__(
        self,
        pixel_values: mx.array,
        patch_embeds: Optional[mx.array] = None,
    ) -> mx.array:
        hidden_states = self.embeddings(pixel_values, patch_embeds)
        hidden_states = self.pre_layrnorm(hidden_states)
        hidden_states = self.transformer(hidden_states)
        return hidden_states


class DeepEncoder(nn.Module):
    """Implements the DeepSeek-OCR vision pipeline (SAM + CLIP + projector)."""

    def __init__(self, config: DeepSeekOCRConfig):
        super().__init__()
        self.config = config
        # Precompute target token grid sizes per side for global/local views
        self._global_queries = int(
            math.ceil(
                (
                    config.vision_config.sam.image_size
                    // config.vision_config.sam.patch_size
                )
                / config.projector_config.downsample_ratio
            )
        )
        self._local_queries = int(
            math.ceil(
                (
                    config.projector_config.downsample_ratio
                    and (
                        config.projector_config.downsample_ratio
                        * config.vision_config.sam.patch_size
                    )
                    and (
                        config.vision_config.sam.patch_size
                        * (config.projector_config.downsample_ratio)
                    )
                )
            )
        )

        sam_cfg = config.vision_config.sam
        self.sam_model = ImageEncoderViT_MLX(
            img_size=sam_cfg.image_size,
            patch_size=sam_cfg.patch_size,
            embed_dim=sam_cfg.width,
            depth=sam_cfg.layers,
            num_heads=sam_cfg.heads,
            mlp_ratio=sam_cfg.mlp_ratio,
            global_attn_indexes=tuple(sam_cfg.global_attn_indexes),
        )

        clip_cfg = config.vision_config.clip
        self.vision_model = ClipVisionModel(clip_cfg)

        proj_in = config.projector_config.input_dim
        proj_out = config.projector_config.n_embed
        self.projector = nn.Linear(proj_in, proj_out, bias=True)
        self.hidden_size = proj_out

        embed_std = 1 / mx.sqrt(mx.array(proj_out, dtype=mx.float32))
        self.image_newline = mx.random.normal((proj_out,)) * embed_std
        self.view_seperator = mx.random.normal((proj_out,)) * embed_std

    def _flatten_sam(self, sam_features: mx.array) -> mx.array:
        batch, height, width, channels = sam_features.shape
        return sam_features.reshape(batch, height * width, channels)

    def _resize_nchw(self, x: mx.array, target: int) -> mx.array:
        """Resize an NCHW tensor to (B, C, target, target) using PIL bicubic per-channel.

        This avoids layout assumptions in generic upsamplers and preserves channels.
        """
        arr = np.array(x.astype(mx.float32))  # (B, C, H, W)
        B, C, H, W = arr.shape
        out = np.empty((B, C, target, target), dtype=np.float32)
        # Determine resample
        try:
            resample = Image.Resampling.BICUBIC
        except Exception:
            resample = 3
        for b in range(B):
            for c in range(C):
                im = Image.fromarray(arr[b, c], mode="F")
                imr = im.resize((target, target), resample=resample)
                out[b, c] = np.array(imr, dtype=np.float32)
        return mx.array(out)

    def _encode_tiles(
        self, tiles: Sequence[mx.array], target_side: Optional[int] = None
    ) -> mx.array:
        if not tiles:
            return mx.zeros((0, 0, self.hidden_size), dtype=mx.float32)
        stacked = mx.stack(list(tiles), axis=0)
        # SAM expects NHWC, returns NHWC
        nhwc = stacked.transpose(0, 2, 3, 1).astype(mx.float32)
        sam_nhwc = self.sam_model(nhwc)
        # Convert SAM features to NCHW for CLIP
        sam_nchw = sam_nhwc.transpose(0, 3, 1, 2)
        # Optionally resize SAM features spatially (locals -> 10x10 tokens per side)
        if target_side is not None:
            b, c, h, w = sam_nchw.shape
            if int(h) != target_side or int(w) != target_side:
                sam_nchw = self._resize_nchw(sam_nchw, target_side)

        # Feed CLIP with external patch embeddings (NCHW). pixel_values not used here.
        dummy_pixels = mx.zeros(
            (
                sam_nchw.shape[0],
                3,
                self.vision_model.embeddings.image_size,
                self.vision_model.embeddings.image_size,
            ),
            dtype=mx.float32,
        )
        vision_hidden = self.vision_model(dummy_pixels, sam_nchw)

        vision_tokens = vision_hidden[:, 1:, :]
        # Flatten SAM tokens from the (possibly resized) NCHW map
        sam_nhwc_resized = sam_nchw.transpose(0, 2, 3, 1)
        sam_tokens = self._flatten_sam(sam_nhwc_resized)
        combined = mx.concatenate([vision_tokens, sam_tokens], axis=-1)
        return self.projector(combined)

    # removed: token-grid downsample after projection; we now resize SAM features before CLIP

    def _encode_view(
        self,
        global_tile: mx.array,
        local_tiles: Optional[Sequence[mx.array]],
        width_tiles: int,
        height_tiles: int,
    ) -> mx.array:
        global_encoded = self._encode_tiles([global_tile], target_side=None)[0]

        seq_global = int(global_encoded.shape[0])
        spatial_global = int(math.sqrt(seq_global))
        global_tokens = global_encoded.reshape(
            spatial_global, spatial_global, self.hidden_size
        )
        global_tokens = global_tokens.reshape(-1, self.hidden_size)

        local_tokens: mx.array
        if local_tiles is not None and len(local_tiles) > 0:
            local_encoded = self._encode_tiles(local_tiles, target_side=None)
            seq_local = int(local_encoded.shape[1])
            spatial_local = int(math.sqrt(seq_local))
            tokens = local_encoded.reshape(
                int(len(local_tiles)), spatial_local, spatial_local, self.hidden_size
            )
            tokens = tokens.reshape(
                height_tiles,
                width_tiles,
                spatial_local,
                spatial_local,
                self.hidden_size,
            )
            tokens = tokens.transpose(0, 2, 1, 3, 4)
            tokens = tokens.reshape(
                height_tiles * spatial_local,
                width_tiles * spatial_local,
                self.hidden_size,
            )
            local_tokens = tokens.reshape(-1, self.hidden_size)
        else:
            local_tokens = mx.zeros((0, self.hidden_size), dtype=global_tokens.dtype)

        if local_tokens.shape[0] > 0:
            return mx.concatenate([local_tokens, global_tokens], axis=0)
        else:
            return global_tokens

    def __call__(
        self,
        pixel_values: Optional[List[List[mx.array]]],
        images_spatial_crop: Optional[mx.array],
    ) -> List[mx.array]:
        if pixel_values is None or images_spatial_crop is None:
            return []

        batch_size = len(pixel_values)
        results: List[mx.array] = []

        for batch_idx in range(batch_size):
            sample_tiles = pixel_values[batch_idx]
            crop_info = np.array(
                images_spatial_crop[batch_idx].tolist(), dtype=np.int32
            )

            sample_features: List[mx.array] = []
            cursor = 0

            for view_idx in range(crop_info.shape[0]):
                width_tiles = int(crop_info[view_idx, 0])
                height_tiles = int(crop_info[view_idx, 1])
                if width_tiles == 0 or height_tiles == 0:
                    break

                num_local_tiles = (
                    width_tiles * height_tiles
                    if (width_tiles > 1 or height_tiles > 1)
                    else 0
                )
                if cursor >= len(sample_tiles):
                    raise ValueError(
                        "Insufficient image tiles for the specified crop layout"
                    )

                global_tile = sample_tiles[cursor]
                cursor += 1

                if num_local_tiles > 0:
                    if cursor + num_local_tiles > len(sample_tiles):
                        raise ValueError(
                            "Insufficient local tiles for the specified crop layout"
                        )
                    local_tile_list = sample_tiles[cursor : cursor + num_local_tiles]
                    cursor += num_local_tiles
                else:
                    local_tile_list = []

                sample_features.append(
                    self._encode_view(
                        global_tile,
                        local_tile_list,
                        width_tiles,
                        height_tiles,
                    )
                )

            if sample_features:
                results.append(mx.concatenate(sample_features, axis=0))
            else:
                results.append(mx.zeros((0, self.hidden_size), dtype=mx.float32))

        return results


class DeepSeekOCRModel(nn.Module):
    """Structure that mirrors the Hugging Face `DeepseekOCRModel` layout."""

    def __init__(self, config: DeepSeekOCRConfig):
        super().__init__()
        self.config = config

        # Vision stack (DeepEncoder / DeepEncoder + projector)
        self.sam_model = None  # exposed for weight alignment, wired via encoder
        self.vision_model = None

        self.encoder = DeepEncoder(config)
        self.sam_model = self.encoder.sam_model
        self.vision_model = self.encoder.vision_model
        self.projector = self.encoder.projector
        self.image_newline = self.encoder.image_newline
        self.view_seperator = self.encoder.view_seperator

        # Language model (DeepseekV2 backbone)
        text_cfg = DeepseekTextConfig.from_dict(config.text_config.__dict__)
        self.language_model = DeepseekV2Model(text_cfg)
        self.embed_tokens = self.language_model.embed_tokens
        self.layers = self.language_model.layers
        self.norm = self.language_model.norm

        # Patch decoder attention to a numerically stable, HF-style LlamaAttention.
        # This forces float32 math inside SDPA and uses RoPE parameters from config.
        self._patch_decoder_attention()

    # --- Decoder attention replacement aligned with DeepseekV2Attention semantics ---
    class _OCRDeepseekV2Attention(nn.Module):
        """Mirror DeepseekV2Attention head partitioning while enforcing float32 math.

        This matches the specialized DeepSeek-V2 layout with separate NOPE/ROPE
        sub-dimensions for q/k and a reduced v_head_dim, while routing SDPA via
        the shared wrapper to keep mask/quantization semantics identical to
        upstream MLX-VLM.
        """

        def __init__(self, config: DeepseekTextConfig):
            super().__init__()
            self.config = config
            self.hidden_size = config.hidden_size
            self.num_heads = config.num_attention_heads
            self.max_position_embeddings = config.max_position_embeddings
            self.rope_theta = config.rope_theta
            self.q_lora_rank = config.q_lora_rank
            self.qk_rope_head_dim = config.qk_rope_head_dim
            self.kv_lora_rank = config.kv_lora_rank
            self.v_head_dim = config.v_head_dim
            self.qk_nope_head_dim = config.qk_nope_head_dim
            self.q_head_dim = self.qk_nope_head_dim + self.qk_rope_head_dim

            self.scale = self.q_head_dim**-0.5

            if self.q_lora_rank is None:
                self.q_proj = nn.Linear(
                    self.hidden_size, self.num_heads * self.q_head_dim, bias=False
                )
            else:
                self.q_a_proj = nn.Linear(
                    self.hidden_size, self.q_lora_rank, bias=config.attention_bias
                )
                self.q_a_layernorm = nn.RMSNorm(self.q_lora_rank)
                self.q_b_proj = nn.Linear(
                    self.q_lora_rank, self.num_heads * self.q_head_dim, bias=False
                )

            self.kv_a_proj_with_mqa = nn.Linear(
                self.hidden_size,
                self.kv_lora_rank + self.qk_rope_head_dim,
                bias=config.attention_bias,
            )
            self.kv_a_layernorm = nn.RMSNorm(self.kv_lora_rank)
            self.kv_b_proj = nn.Linear(
                self.kv_lora_rank,
                self.num_heads
                * (self.q_head_dim - self.qk_rope_head_dim + self.v_head_dim),
                bias=False,
            )

            self.o_proj = nn.Linear(
                self.num_heads * self.v_head_dim,
                self.hidden_size,
                bias=config.attention_bias,
            )

            # RoPE matches MLX-VLM variants (YARN if configured)
            if config.rope_scaling is None:
                self.rope = nn.RoPE(
                    self.qk_rope_head_dim,
                    traditional=config.rope_traditional,
                    base=self.rope_theta,
                )
            else:
                # Minimal YARN subset: delegate to MLX when available
                mscale_all_dim = config.rope_scaling.get("mscale_all_dim", 0)
                scaling_factor = config.rope_scaling.get("factor", 1)
                if mscale_all_dim:
                    mscale = (
                        0.1 * mscale_all_dim * math.log(max(scaling_factor, 1)) + 1.0
                    )
                    self.scale = self.scale * mscale * mscale
                self.rope = nn.RoPE(
                    self.qk_rope_head_dim,
                    traditional=True,
                    base=self.rope_theta,
                )

        def __call__(
            self,
            x: mx.array,
            mask: Optional[mx.array] = None,
            cache=None,
        ) -> mx.array:
            B, L, D = x.shape
            x32 = x.astype(mx.float32)

            if self.q_lora_rank is None:
                q = self.q_proj(x32)
            else:
                q = self.q_b_proj(self.q_a_layernorm(self.q_a_proj(x32)))

            q = q.reshape(B, L, self.num_heads, self.q_head_dim).transpose(0, 2, 1, 3)
            q_nope, q_pe = mx.split(q, [self.qk_nope_head_dim], axis=-1)

            compressed_kv = self.kv_a_proj_with_mqa(x32)
            compressed_kv, k_pe = mx.split(compressed_kv, [self.kv_lora_rank], axis=-1)
            k_pe = k_pe.reshape(B, L, 1, self.qk_rope_head_dim).transpose(0, 2, 1, 3)
            kv = self.kv_b_proj(self.kv_a_layernorm(compressed_kv))
            kv = kv.reshape(B, L, self.num_heads, -1).transpose(0, 2, 1, 3)
            k_nope, values = mx.split(kv, [self.qk_nope_head_dim], axis=-1)

            if cache is not None:
                q_pe = self.rope(q_pe, cache.offset)
                k_pe = self.rope(k_pe, cache.offset)
                k_pe = mx.repeat(k_pe, self.num_heads, axis=1)
                keys, values = cache.update_and_fetch(
                    mx.concatenate([k_nope, k_pe], axis=-1), values
                )
            else:
                q_pe = self.rope(q_pe)
                k_pe = self.rope(k_pe)
                k_pe = mx.repeat(k_pe, self.num_heads, axis=1)
                keys = mx.concatenate([k_nope, k_pe], axis=-1)

            queries = mx.concatenate([q_nope, q_pe], axis=-1)

            # Optional capture of post-RoPE queries/keys
            layer_idx = getattr(self, "_layer_index", None)
            if layer_idx is not None and int(layer_idx) in ATTENTION_CAPTURE_LAYERS:
                k_full = mx.concatenate([k_nope, k_pe], axis=-1)
                q_store = queries.astype(mx.float32)
                k_store = k_full.astype(mx.float32)
                ATTENTION_CAPTURE[(int(layer_idx), "q_rope")] = q_store
                ATTENTION_CAPTURE[(int(layer_idx), "k_rope")] = k_store
                # Also stash on self for wrappers that may want to fetch
                setattr(self, "_last_queries", q_store)
                setattr(self, "_last_keys", k_store)

            out = scaled_dot_product_attention(
                queries, keys, values, cache, scale=self.scale, mask=mask
            )
            out = out.transpose(0, 2, 1, 3).reshape(B, L, -1)
            return self.o_proj(out)

    # --- Fallback Llama-style attention (used by this OCR model per HF config) ---
    class _OCRLlamaAttention(nn.Module):
        def __init__(self, text_cfg: DeepseekTextConfig):
            super().__init__()
            dim = text_cfg.hidden_size
            self.n_heads = text_cfg.num_attention_heads
            self.n_kv_heads = text_cfg.num_key_value_heads
            self.head_dim = dim // self.n_heads
            self.scale = self.head_dim**-0.5

            attn_bias = bool(getattr(text_cfg, "attention_bias", False))
            self.q_proj = nn.Linear(dim, self.n_heads * self.head_dim, bias=attn_bias)
            self.k_proj = nn.Linear(
                dim, self.n_kv_heads * self.head_dim, bias=attn_bias
            )
            self.v_proj = nn.Linear(
                dim, self.n_kv_heads * self.head_dim, bias=attn_bias
            )
            self.o_proj = nn.Linear(self.n_heads * self.head_dim, dim, bias=attn_bias)

            rope_scale = (
                1 / text_cfg.rope_scaling["factor"]
                if getattr(text_cfg, "rope_scaling", None) is not None
                and text_cfg.rope_scaling.get("type") == "linear"
                else 1
            )
            if DEBUG_ROPE_SCALE_OVERRIDE is not None:
                rope_scale = float(DEBUG_ROPE_SCALE_OVERRIDE)
            # Keep an MLX RoPE instance for potential future use, but we'll apply
            # HF-style rotary explicitly to match Transformers semantics.
            self.rope = nn.RoPE(
                self.head_dim,
                traditional=getattr(text_cfg, "rope_traditional", True),
                base=getattr(text_cfg, "rope_theta", 10000.0),
                scale=rope_scale,
            )
            # Cache base/scale for our explicit HF-style rotary
            self._rope_base = getattr(text_cfg, "rope_theta", 10000.0)
            self._rope_scale = rope_scale

        def __call__(
            self,
            x: mx.array,
            mask: Optional[mx.array] = None,
            cache=None,
        ) -> mx.array:
            B, L, _ = x.shape
            x_fp32 = x.astype(mx.float32)
            q = self.q_proj(x_fp32)
            k = self.k_proj(x_fp32)
            v = self.v_proj(x_fp32)

            q = q.reshape(B, L, self.n_heads, self.head_dim).transpose(0, 2, 1, 3)
            k = k.reshape(B, L, self.n_kv_heads, self.head_dim).transpose(0, 2, 1, 3)
            v = v.reshape(B, L, self.n_kv_heads, self.head_dim).transpose(0, 2, 1, 3)

            # Optional capture of pre-RoPE queries/keys
            layer_idx = getattr(self, "_layer_index", None)
            if layer_idx is not None and int(layer_idx) in ATTENTION_CAPTURE_LAYERS:
                ATTENTION_CAPTURE[(int(layer_idx), "q_pre")] = q.astype(mx.float32)
                ATTENTION_CAPTURE[(int(layer_idx), "k_pre")] = k.astype(mx.float32)

            def _rotate_half(xh: mx.array) -> mx.array:
                half = int(xh.shape[-1] // 2)
                first = xh[..., :half]
                second = xh[..., half : half * 2]
                rotated = mx.concatenate([mx.negative(second), first], axis=-1)
                if int(xh.shape[-1]) % 2 == 1:
                    rotated = mx.concatenate([rotated, xh[..., half * 2 :]], axis=-1)
                return rotated

            def _swap_even_odd(xh: mx.array) -> mx.array:
                swapped = mx.zeros_like(xh)
                swapped[..., 0::2] = xh[..., 1::2]
                swapped[..., 1::2] = xh[..., 0::2]
                if int(xh.shape[-1]) % 2 == 1:
                    swapped[..., -1] = xh[..., -1]
                return swapped

            def _broadcast_cos_sin(
                xh: mx.array, cos: mx.array, sin: mx.array
            ) -> tuple[mx.array, mx.array]:
                cos_local = cos
                sin_local = sin
                # Support caches stored with half-dim last axis
                if int(cos_local.shape[-1]) == int(xh.shape[-1] // 2):
                    cos_local = mx.concatenate([cos_local, cos_local], axis=-1)
                    sin_local = mx.concatenate([sin_local, sin_local], axis=-1)
                while cos_local.ndim < xh.ndim:
                    cos_local = mx.expand_dims(cos_local, axis=1)
                    sin_local = mx.expand_dims(sin_local, axis=1)
                target_shape = tuple(int(d) for d in xh.shape)
                cos_local = mx.broadcast_to(cos_local, target_shape).astype(xh.dtype)
                sin_local = mx.broadcast_to(sin_local, target_shape).astype(xh.dtype)
                return cos_local, sin_local

            def _apply_rotary(xh: mx.array, cos: mx.array, sin: mx.array) -> mx.array:
                cos_local, sin_local = _broadcast_cos_sin(xh, cos, sin)
                variant = DEBUG_ROPE_VARIANT
                base = xh
                swapped = False
                if variant is not None and ("swap" in variant):
                    base = _swap_even_odd(base)
                    swapped = True
                if variant is not None and ("invert" in variant):
                    sin_local = -sin_local
                rotated = _rotate_half(base)
                out = base * cos_local + rotated * sin_local
                if swapped:
                    out = _swap_even_odd(out)
                return out

            def _apply_rope_external(
                xh: mx.array, cos: mx.array, sin: mx.array
            ) -> mx.array:
                return _apply_rotary(xh, cos, sin)

            # Apply RoPE: either external cos/sin (debug), or explicit HF-style
            ext_map = DEBUG_EXTERNAL_ROPE or {}
            layer_idx = getattr(self, "_layer_index", None)

            # Helper: LLaMA-style rotary using even/odd formulation
            def _apply_rope_llama(
                qh: mx.array, kh: mx.array, offset: int = 0
            ) -> tuple[mx.array, mx.array]:
                D = int(qh.shape[-1])
                seq_len = int(qh.shape[-2])
                positions = mx.arange(offset, offset + seq_len, dtype=mx.float32)
                positions = positions * self._rope_scale
                inv_freq = 1.0 / (
                    self._rope_base ** (mx.arange(0, D, 2, dtype=mx.float32) / D)
                )
                freqs = positions[:, None] * inv_freq[None, :]
                emb = mx.concatenate([freqs, freqs], axis=-1)
                cos_full = mx.cos(emb)[None, None, :, :]
                sin_full = mx.sin(emb)[None, None, :, :]
                return _apply_rotary(qh, cos_full, sin_full), _apply_rotary(
                    kh, cos_full, sin_full
                )

            if cache is not None:
                if layer_idx is not None and int(layer_idx) in ext_map:
                    cos, sin = ext_map[int(layer_idx)]
                    q = _apply_rope_external(q, cos, sin)
                    k = _apply_rope_external(k, cos, sin)
                else:
                    q, k = _apply_rope_llama(q, k, offset=cache.offset)
                k, v = cache.update_and_fetch(k, v)
            else:
                if layer_idx is not None and int(layer_idx) in ext_map:
                    cos, sin = ext_map[int(layer_idx)]
                    q = _apply_rope_external(q, cos, sin)
                    k = _apply_rope_external(k, cos, sin)
                else:
                    q, k = _apply_rope_llama(q, k, offset=0)

            # Optional: force post-RoPE q/k from external source (HF dumps)
            force_map = DEBUG_FORCE_QK_ROPE or {}
            if layer_idx is not None and int(layer_idx) in force_map:
                fq, fk = force_map[int(layer_idx)]
                # Best-effort shape alignment and dtype cast
                try:
                    q = fq.astype(q.dtype)
                    k = fk.astype(k.dtype)
                except Exception:
                    pass

            # Optional capture of post-RoPE queries/keys
            layer_idx = getattr(self, "_layer_index", None)
            if layer_idx is not None and int(layer_idx) in ATTENTION_CAPTURE_LAYERS:
                q_store = q.astype(mx.float32)
                k_store = k.astype(mx.float32)
                ATTENTION_CAPTURE[(int(layer_idx), "q_rope")] = q_store
                ATTENTION_CAPTURE[(int(layer_idx), "k_rope")] = k_store
                setattr(self, "_last_queries", q_store)
                setattr(self, "_last_keys", k_store)

            out = scaled_dot_product_attention(
                q, k, v, cache, scale=self.scale, mask=mask
            )
            out = out.transpose(0, 2, 1, 3).reshape(B, L, -1)
            return self.o_proj(out)

    def _patch_decoder_attention(self) -> None:
        """Replace each decoder layer's attention with the custom HF-style module.

        Copies weights from the existing attention to preserve loaded params.
        """
        text_cfg = DeepseekTextConfig.from_dict(self.config.text_config.__dict__)
        use_deepseek_split = (
            int(getattr(text_cfg, "qk_nope_head_dim", 0))
            + int(getattr(text_cfg, "qk_rope_head_dim", 0))
        ) > 0
        for idx, layer in enumerate(self.language_model.layers):
            if not hasattr(layer, "self_attn"):
                continue
            # Build replacement aligned with model config: DeepseekV2 split if configured,
            # otherwise fall back to Llama-style attention (as in HF OCR config).
            if use_deepseek_split:
                new_attn = DeepSeekOCRModel._OCRDeepseekV2Attention(text_cfg)
                # Map weights for DeepseekV2-style attention
                weight_pairs = [
                    ("q_proj", "q_proj"),
                    ("q_a_proj", "q_a_proj"),
                    ("q_a_layernorm", "q_a_layernorm"),
                    ("q_b_proj", "q_b_proj"),
                    ("kv_a_proj_with_mqa", "kv_a_proj_with_mqa"),
                    ("kv_a_layernorm", "kv_a_layernorm"),
                    ("kv_b_proj", "kv_b_proj"),
                    ("o_proj", "o_proj"),
                ]
            else:
                new_attn = DeepSeekOCRModel._OCRLlamaAttention(text_cfg)
                # Map weights for Llama-style attention
                weight_pairs = [
                    ("q_proj", "q_proj"),
                    ("k_proj", "k_proj"),
                    ("v_proj", "v_proj"),
                    ("o_proj", "o_proj"),
                ]
            old_attn = layer.self_attn
            # Annotate layer index for optional captures
            setattr(new_attn, "_layer_index", idx)
            # Also annotate MoE gate with layer index for per-layer forced gating
            try:
                if hasattr(layer, "mlp") and hasattr(layer.mlp, "gate"):
                    setattr(layer.mlp.gate, "_layer_index", idx)
            except Exception:
                pass

            # Best-effort weight transfer if shapes match
            for old_name, new_name in weight_pairs:
                if hasattr(old_attn, old_name) and hasattr(new_attn, new_name):
                    try:
                        old_mod = getattr(old_attn, old_name)
                        new_mod = getattr(new_attn, new_name)
                        if hasattr(old_mod, "weight") and hasattr(new_mod, "weight"):
                            new_mod.weight = old_mod.weight
                        if hasattr(old_mod, "bias") and hasattr(new_mod, "bias"):
                            new_mod.bias = getattr(old_mod, "bias")
                    except Exception:
                        pass

            # Bypass static type narrowing from upstream module types
            from typing import cast, Any

            layer.self_attn = cast(Any, new_attn)

    def get_input_embeddings(
        self,
        input_ids: mx.array,
        pixel_values: Optional[List[List[mx.array]]] = None,
        images_seq_mask: Optional[mx.array] = None,
        images_spatial_crop: Optional[mx.array] = None,
        images_seq_types: Optional[mx.array] = None,
    ) -> mx.array:
        token_embeddings = self.language_model.embed_tokens(input_ids)

        # Early exit for pure text if no types and no images
        if pixel_values is None and images_seq_types is None:
            return token_embeddings

        if pixel_values is not None:
            if images_seq_mask is None or images_spatial_crop is None:
                raise ValueError(
                    "Image masks and crop metadata are required for vision inputs"
                )
            image_features = self.encoder(pixel_values, images_spatial_crop)
        else:
            image_features = []

        mx.eval(token_embeddings)
        token_embeddings_fp32 = token_embeddings.astype(mx.float32)
        token_embeddings_np = np.array(token_embeddings_fp32)

        # Precompute special embeddings once in float32 for stable broadcasting
        newline_np = None
        separator_np = None
        if images_seq_types is not None:
            mx.eval(self.image_newline, self.view_seperator)
            newline_np = np.array(self.image_newline.astype(mx.float32))
            separator_np = np.array(self.view_seperator.astype(mx.float32))

        for batch_idx in range(token_embeddings_np.shape[0]):
            # Fill vision features according to mask order (matches HF scatter)
            if image_features:
                features = image_features[batch_idx]
                if features.shape[0] > 0:
                    if images_seq_types is not None:
                        types_row = np.array(
                            images_seq_types[batch_idx].tolist(), dtype=np.int8
                        )
                        positions = np.nonzero(types_row == 1)[0]
                    elif images_seq_mask is not None:
                        mask_row = images_seq_mask[batch_idx]
                        positions = np.nonzero(np.array(mask_row.tolist(), dtype=bool))[
                            0
                        ]
                    else:
                        raise ValueError(
                            "Either images_seq_types or images_seq_mask required"
                        )

                    if features.shape[0] != len(positions):
                        fill = min(features.shape[0], len(positions))
                        if fill == 0:
                            continue
                        positions = positions[:fill]
                        features = features[:fill]

                    mx.eval(features)
                    features_np = np.array(features.astype(mx.float32))
                    token_embeddings_np[batch_idx, positions, :] = features_np

            if images_seq_types is not None:
                types_row = np.array(
                    images_seq_types[batch_idx].tolist(), dtype=np.int8
                )
                if newline_np is not None:
                    newline_positions = np.nonzero(types_row == 2)[0]
                    if len(newline_positions) > 0:
                        broadcast_newline = np.broadcast_to(
                            newline_np, (len(newline_positions), newline_np.shape[0])
                        )
                        token_embeddings_np[batch_idx, newline_positions, :] = (
                            broadcast_newline
                        )
                if separator_np is not None:
                    separator_positions = np.nonzero(types_row == 3)[0]
                    if len(separator_positions) > 0:
                        broadcast_sep = np.broadcast_to(
                            separator_np,
                            (len(separator_positions), separator_np.shape[0]),
                        )
                        token_embeddings_np[batch_idx, separator_positions, :] = (
                            broadcast_sep
                        )

        updated = mx.array(token_embeddings_np, dtype=mx.float32)
        return updated.astype(token_embeddings.dtype)

    def __call__(
        self,
        input_ids: mx.array,
        pixel_values: Optional[List[List[mx.array]]] = None,
        mask: Optional[mx.array] = None,
        cache=None,
        **kwargs,
    ) -> mx.array:
        images_seq_mask = kwargs.get("images_seq_mask")
        images_spatial_crop = kwargs.get("images_spatial_crop")

        inputs_embeds = self.get_input_embeddings(
            input_ids,
            pixel_values=pixel_values,
            images_seq_mask=images_seq_mask,
            images_spatial_crop=images_spatial_crop,
            images_seq_types=kwargs.get("images_seq_types"),
        )

        kwargs.pop("images_seq_mask", None)
        kwargs.pop("images_spatial_crop", None)
        kwargs.pop("images_seq_types", None)

        # When inputs_embeds is provided, we pass a dummy input_ids array
        # but the language model will use inputs_embeds instead
        return self.language_model(
            input_ids,
            cache=cache,
            inputs_embeds=inputs_embeds,
            mask=mask,
            **kwargs,
        )

    def sanitize(self, weights: Dict[str, mx.array]) -> Dict[str, mx.array]:
        """Normalize DeepSeek MoE weights to match MLX layout.

        The HF checkpoints store routed expert weights under
        ``model.layers.{i}.mlp.experts.{e}.``. The MLX `SwitchGLU` expects them
        stacked under ``switch_mlp`` instead. This utility mirrors the
        sanitization step performed in ``mlx_vlm``'s DeepSeekV2 model.
        """

        def convert_conv_weight(name: str, tensor: mx.array) -> mx.array:
            if tensor.ndim != 4:
                return tensor

            conv_markers = (
                "patch_embed.proj.weight",
                "patch_embedding.weight",
                "neck.",
                "downsamples.",
                "projector.weight",  # linear, skip below
            )

            if "projector.weight" in name:
                return tensor

            if any(marker in name for marker in conv_markers):
                # Transpose to (out, kh, kw, in) expected by MLX Conv2d NHWC
                return mx.transpose(tensor, (0, 2, 3, 1))
            return tensor

        renamed: Dict[str, mx.array] = {}

        for key, value in weights.items():
            new_key = key
            if key.startswith("model."):
                suffix = key[len("model.") :]
                if suffix.startswith("sam_model."):
                    sam_suffix = suffix[len("sam_model.") :]
                    new_key = f"model.encoder.sam_model.{sam_suffix}"
                    new_key = new_key.replace(".net_2.", ".downsamples.0.")
                    new_key = new_key.replace(".net_3.", ".downsamples.1.")
                elif suffix.startswith("vision_model."):
                    vis_suffix = suffix[len("vision_model.") :]
                    new_key = f"model.encoder.vision_model.{vis_suffix}"
                    # Handle position_embedding: HF stores as .weight, MLX uses direct array
                    new_key = new_key.replace(
                        ".position_embedding.weight",
                        ".position_embedding",
                    )
                    # Handle class_embedding: same in both but needs to be aliased
                    # (it's already correctly named, no replacement needed)
                elif suffix.startswith("projector."):
                    proj_suffix = suffix[len("projector.") :]
                    if proj_suffix.startswith("layers."):
                        proj_suffix = proj_suffix[len("layers.") :]
                    new_key = f"model.encoder.projector.{proj_suffix}"
                elif suffix == "image_newline":
                    renamed["model.encoder.image_newline"] = value
                    renamed["model.image_newline"] = value
                    continue
                elif suffix == "view_seperator":
                    renamed["model.encoder.view_seperator"] = value
                    renamed["model.view_seperator"] = value
                    continue
                elif suffix.startswith("embed_tokens"):
                    new_key = f"model.language_model.{suffix}"
                elif suffix.startswith("layers"):
                    new_key = f"model.language_model.{suffix}"
                elif suffix.startswith("norm"):
                    new_key = f"model.language_model.{suffix}"
                else:
                    new_key = f"model.{suffix}"

            tensor = convert_conv_weight(new_key, value)
            if ".rel_pos_" in new_key:
                tensor = tensor.astype(mx.float32)
            renamed[new_key] = tensor

        weights = renamed

        text_layers = self.config.text_config.num_hidden_layers
        num_experts = self.config.text_config.n_routed_experts

        for layer_idx in range(text_layers):
            prefix = f"model.language_model.layers.{layer_idx}"
            experts_prefix = f"{prefix}.mlp.experts"
            # Skip dense layers (before MoE kicks in).
            if any(
                f"{experts_prefix}.0.gate_proj.weight" not in weights for _ in range(1)
            ):
                continue

            for name in ["gate_proj", "up_proj", "down_proj"]:
                collector = []
                key_template = f"{experts_prefix}.{{expert}}.{name}.weight"
                for expert_id in range(num_experts):
                    key = key_template.format(expert=expert_id)
                    if key not in weights:
                        collector = []
                        break
                    collector.append(weights.pop(key))

                if collector:
                    stacked = mx.stack(collector, axis=0)
                    weights[f"{prefix}.mlp.switch_mlp.{name}.weight"] = stacked

            # Biases / quantization statistics are optional; pass-through if present.
            for stat_name in ["scales", "biases"]:
                template = f"{experts_prefix}.{{expert}}.gate_proj.{stat_name}"
                if template.format(expert=0) in weights:
                    stacked = mx.stack(
                        [
                            weights.pop(template.format(expert=i))
                            for i in range(num_experts)
                        ],
                        axis=0,
                    )
                    weights[f"{prefix}.mlp.switch_mlp.gate_proj.{stat_name}"] = stacked

        aliases: Dict[str, mx.array] = {}
        for key, value in weights.items():
            if key.startswith("model.language_model.layers."):
                aliases[key.replace("model.language_model.", "model.")] = value
            elif key.startswith("model.language_model.embed_tokens"):
                aliases[key.replace("model.language_model.", "model.")] = value
            elif key.startswith("model.language_model.norm"):
                aliases[key.replace("model.language_model.", "model.")] = value
            elif key.startswith("model.encoder.sam_model."):
                aliases[key.replace("model.encoder.", "model.")] = value
            elif key.startswith("model.encoder.vision_model."):
                aliases[key.replace("model.encoder.", "model.")] = value
            elif key.startswith("model.encoder.projector."):
                aliases[key.replace("model.encoder.", "model.")] = value

        weights.update(aliases)

        # Fill in SAM-HD auxiliary parameters with their initialized values if absent.
        param_entries = tree_flatten(self.parameters())
        iterator = (
            param_entries.items() if isinstance(param_entries, dict) else param_entries
        )
        for key, value in iterator:
            if (
                "sam_model.neck_hd" not in key
                and "sam_model.hd_alpha_downsamples" not in key
            ):
                continue

            target_key = key if key.startswith("model.") else f"model.{key}"
            if target_key not in weights:
                weights[target_key] = value

            if target_key.startswith("model.encoder.sam_model."):
                alias_key = target_key.replace("model.encoder.", "model.")
                if alias_key not in weights:
                    weights[alias_key] = value

        return weights


class DeepSeekOCRForCausalLM(nn.Module):
    """Top-level wrapper that adds the language modeling head."""

    def __init__(self, config: DeepSeekOCRConfig):
        super().__init__()
        self.config = config
        self.model = DeepSeekOCRModel(config)
        # Keep an lm_head module for compatibility, but prefer tied embedding logits
        self.lm_head = nn.Linear(
            config.text_config.hidden_size, config.text_config.vocab_size, bias=False
        )

    def __call__(
        self,
        input_ids: mx.array,
        pixel_values: Optional[List[List[mx.array]]] = None,
        mask: Optional[mx.array] = None,
        cache=None,
        **kwargs,
    ) -> mx.array:
        hidden_states = self.model(
            input_ids,
            pixel_values=pixel_values,
            mask=mask,
            cache=cache,
            **kwargs,
        )
        # Use the trained lm_head (matches HF behavior)
        return self.lm_head(hidden_states)

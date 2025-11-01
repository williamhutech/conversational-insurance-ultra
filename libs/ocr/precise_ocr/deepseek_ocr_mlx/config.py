"""Configuration objects for the local DeepSeek-OCR MLX port."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Dict, Mapping, Optional, Sequence, Tuple, Type, TypeVar


_ConfigT = TypeVar("_ConfigT", bound="_ConfigMixin")


@dataclass
class _ConfigMixin:
    """Convenience mixin to build dataclasses from plain dictionaries."""

    @classmethod
    def from_dict(cls: Type[_ConfigT], data: Mapping[str, object]) -> _ConfigT:
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)  # type: ignore[arg-type]


@dataclass
class LanguageConfig(_ConfigMixin):
    model_type: str = "deepseek_v2"
    vocab_size: int = 129_280
    hidden_size: int = 1_280
    intermediate_size: int = 6_848
    moe_intermediate_size: int = 896
    num_hidden_layers: int = 12
    num_attention_heads: int = 10
    num_key_value_heads: int = 10
    n_shared_experts: int = 2
    n_routed_experts: int = 64
    num_experts_per_tok: int = 6
    first_k_dense_replace: int = 1
    max_position_embeddings: int = 8_192
    bos_token_id: int = 0
    eos_token_id: int = 1
    rope_theta: float = 10_000.0
    rms_norm_eps: float = 1e-6
    topk_method: str = "greedy"
    topk_group: int = 1
    n_group: int = 1
    use_mla: bool = False
    attn_dropout: float = 0.0
    hidden_dropout: float = 0.0
    routed_scaling_factor: float = 1.0
    kv_lora_rank: Optional[int] = None
    q_lora_rank: Optional[int] = None
    qk_nope_head_dim: int = 0
    qk_rope_head_dim: int = 0
    v_head_dim: int = 0
    rope_scaling: Optional[Dict[str, float]] = None
    rope_traditional: bool = True
    attention_bias: bool = False
    scoring_func: str = "softmax"


@dataclass
class SAMBackboneConfig(_ConfigMixin):
    width: int = 768
    layers: int = 12
    heads: int = 12
    patch_size: int = 16
    image_size: int = 1_024
    mlp_ratio: float = 4.0
    global_attn_indexes: Tuple[int, ...] = (2, 5, 8, 11)
    downsample_channels: Tuple[int, ...] = (512, 1024)


@dataclass
class CLIPBackboneConfig(_ConfigMixin):
    width: int = 1_024
    layers: int = 24
    heads: int = 16
    image_size: int = 224
    patch_size: int = 14
    mlp_ratio: float = 4.0


@dataclass
class VisionConfig(_ConfigMixin):
    model_type: str = "vision"
    image_size: int = 1_024
    mlp_ratio: float = 3.7362
    sam: SAMBackboneConfig = field(default_factory=SAMBackboneConfig)
    clip: CLIPBackboneConfig = field(default_factory=CLIPBackboneConfig)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "VisionConfig":
        params = dict(data)
        width_section = params.pop("width", None)
        if isinstance(width_section, Mapping):
            sam_raw = width_section.get("sam_vit_b", {})
            clip_raw = width_section.get("clip-l-14-224", {})
        else:
            sam_raw = {}
            clip_raw = {}

        sam_cfg = SAMBackboneConfig.from_dict(sam_raw)
        clip_cfg = CLIPBackboneConfig.from_dict(clip_raw)
        params["sam"] = sam_cfg
        params["clip"] = clip_cfg

        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in params.items() if k in allowed}
        return cls(**filtered)  # type: ignore[arg-type]


@dataclass
class ProjectorConfig(_ConfigMixin):
    projector_type: str = "linear"
    input_dim: int = 2_048
    n_embed: int = 1_280
    depth: int = 1
    mlp_ratio: int = 1
    downsample_ratio: int = 4
    token_pooling: bool = False


@dataclass
class DeepSeekOCRConfig(_ConfigMixin):
    model_type: str = "deepseek_ocr_mlx"
    text_config: LanguageConfig = field(default_factory=LanguageConfig)
    vision_config: VisionConfig = field(default_factory=VisionConfig)
    projector_config: ProjectorConfig = field(default_factory=ProjectorConfig)
    tile_tag: str = "2D"
    global_view_pos: str = "head"
    candidate_resolutions: Sequence[Sequence[int]] = field(
        default_factory=lambda: [[1_024, 1_024]]
    )
    eos_token_id: Optional[int] = 1
    bos_token_id: Optional[int] = 0
    quantization: Optional[Dict[str, object]] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "DeepSeekOCRConfig":
        params = dict(data)

        language_raw = params.pop("language_config", None)
        text_raw = params.pop("text_config", None)
        if language_raw is not None and text_raw is None:
            text_raw = language_raw

        if isinstance(text_raw, Mapping):
            text_cfg = LanguageConfig.from_dict(text_raw)
        else:
            text_cfg = LanguageConfig()

        vision_raw = params.pop("vision_config", None)
        if isinstance(vision_raw, Mapping):
            vision_cfg = VisionConfig.from_dict(vision_raw)
        else:
            vision_cfg = VisionConfig()

        projector_raw = params.pop("projector_config", None)
        if isinstance(projector_raw, Mapping):
            projector_cfg = ProjectorConfig.from_dict(projector_raw)
        else:
            projector_cfg = ProjectorConfig()

        params["text_config"] = text_cfg
        params["vision_config"] = vision_cfg
        params["projector_config"] = projector_cfg

        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in params.items() if k in allowed}
        return cls(**filtered)  # type: ignore[arg-type]

    def to_dict(self) -> Dict[str, object]:
        return {
            "model_type": self.model_type,
            "tile_tag": self.tile_tag,
            "global_view_pos": self.global_view_pos,
            "candidate_resolutions": [list(r) for r in self.candidate_resolutions],
            "text_config": self.text_config.__dict__,
            "vision_config": {
                "model_type": self.vision_config.model_type,
                "image_size": self.vision_config.image_size,
                "mlp_ratio": self.vision_config.mlp_ratio,
                "sam": self.vision_config.sam.__dict__,
                "clip": self.vision_config.clip.__dict__,
            },
            "projector_config": self.projector_config.__dict__,
            "bos_token_id": self.bos_token_id,
            "eos_token_id": self.eos_token_id,
        }

"""Input preparation utilities for the local DeepSeek-OCR MLX port."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageOps

import mlx.core as mx

from .config import DeepSeekOCRConfig

try:  # transformers is only required at runtime when building token ids
    from transformers import PreTrainedTokenizerBase
except (
    Exception
):  # pragma: no cover - transformers might not be present during docs builds
    PreTrainedTokenizerBase = object  # type: ignore[misc]


@dataclass
class ProcessorOutput:
    """Container with the tensors required by :class:`DeepSeekOCRForCausalLM`."""

    input_ids: mx.array
    attention_mask: mx.array
    images_seq_mask: (
        mx.array
    )  # True for <image> token positions to replace with vision features
    images_seq_types: Optional[
        mx.array
    ]  # Type codes: 0=text, 1=vision, 2=newline, 3=separator
    pixel_values: Optional[List[List[mx.array]]]
    images_spatial_crop: Optional[mx.array]


class DeepSeekOCRPreprocessor:
    """Prepare multimodal batches for the MLX DeepSeek-OCR implementation.

    The helper mirrors the Hugging Face ``DeepseekVLV2Processor`` behaviour,
    including the dynamic local crop pipeline used to tile high-resolution
    documents for SAM+CLIP processing.
    """

    def __init__(
        self,
        tokenizer: PreTrainedTokenizerBase,
        config: DeepSeekOCRConfig,
        *,
        image_token: str = "<image>",
        normalize: bool = True,
        mean: Tuple[float, float, float] = (0.5, 0.5, 0.5),
        std: Tuple[float, float, float] = (0.5, 0.5, 0.5),
        add_bos: bool = True,
        dynamic_crops: bool = True,
        crop_size: int = 640,
        min_dynamic_crops: int = 2,
        max_dynamic_crops: int = 9,
    ) -> None:
        self.tokenizer = tokenizer
        self.config = config
        self.image_token = image_token
        self.normalize = normalize
        self.mean = np.array(mean, dtype=np.float32)[:, None, None]
        self.std = np.array(std, dtype=np.float32)[:, None, None]
        self.add_bos = add_bos
        self.dynamic_crops = dynamic_crops
        self.crop_size = crop_size
        self.min_dynamic_crops = min_dynamic_crops
        self.max_dynamic_crops = max_dynamic_crops

        self.base_size = config.candidate_resolutions[0][0]
        self.patch_size = config.vision_config.sam.patch_size
        self.downsample_ratio = config.projector_config.downsample_ratio

        # Token grid per side equals image_size / patch_size / total_downsample.
        # Global view uses the model base size (e.g., 1024 -> 16),
        # local tiles use crop_size (e.g., 640 -> 10).
        self._global_queries = int(
            math.ceil((self.base_size // self.patch_size) / self.downsample_ratio)
        )
        self._local_queries = int(
            math.ceil((self.crop_size // self.patch_size) / self.downsample_ratio)
        )

        image_token_id = tokenizer.convert_tokens_to_ids(image_token)
        if image_token_id is None:
            raise ValueError(
                f"Tokenizer does not define an id for the image token '{image_token}'."
            )
        self.image_token_id = int(image_token_id)

        self.pad_token_id = (
            tokenizer.pad_token_id
            if tokenizer.pad_token_id is not None
            else tokenizer.eos_token_id
        )
        if self.pad_token_id is None:
            raise ValueError(
                "Tokenizer must define either a pad_token_id or eos_token_id."
            )

        self.bos_token_id = tokenizer.bos_token_id

        # ``resize_image`` inside the SAM encoder upsamples the feature map to 96×96
        # before two stride-2 convolutions reduce it back down. This yields
        # 96 / (2 ** len(downsample_channels)) = 24 spatial tokens per side.
        self._pad_color = tuple(int(channel * 255) for channel in mean)
        self._candidate_ratios = self._build_candidate_ratios()

    def _encode_text(self, text: str) -> List[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def _image_token_sequence(
        self, width_tiles: int, height_tiles: int
    ) -> Tuple[List[int], List[int]]:
        """Return token ids and type codes for a view.

        Types: 1=vision feature, 2=image_newline, 3=view_separator.
        Layout: locals (stitched grid with per-row newlines), view separator,
        then global 16×16 with per-row newlines. This matches HF order.
        Only type==1 positions are filled by encoder features.
        """
        token_ids: List[int] = []
        types: List[int] = []

        # Locals stitched first (HF order)
        if width_tiles > 1 or height_tiles > 1:
            stitched_cols = self._local_queries * width_tiles
            stitched_rows = self._local_queries * height_tiles
            for _ in range(stitched_rows):
                token_ids.extend([self.image_token_id] * stitched_cols)
                types.extend([1] * stitched_cols)
                token_ids.append(self.image_token_id)
                types.append(2)  # newline

        # View separator between locals and global
        token_ids.append(self.image_token_id)
        types.append(3)

        # Global grid with per-row newlines
        for _ in range(self._global_queries):
            token_ids.extend([self.image_token_id] * self._global_queries)
            types.extend([1] * self._global_queries)  # Type 1 = vision features
            token_ids.append(self.image_token_id)
            types.append(2)  # newline

        return token_ids, types

    def _to_chw(self, array: np.ndarray) -> np.ndarray:
        tensor = array.astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))
        if self.normalize:
            tensor = (tensor - self.mean) / self.std
        return tensor

    def _prepare_global_tile(self, image: Image.Image) -> np.ndarray:
        padded = ImageOps.pad(
            image,
            (self.base_size, self.base_size),
            color=self._pad_color,
            method=Image.Resampling.BICUBIC,
        )
        return self._to_chw(np.array(padded, dtype=np.float32))

    def _build_candidate_ratios(self) -> List[Tuple[int, int]]:
        ratios = {(1, 1)}
        for total in range(self.min_dynamic_crops, self.max_dynamic_crops + 1):
            for width in range(1, total + 1):
                for height in range(1, total + 1):
                    blocks = width * height
                    if self.min_dynamic_crops <= blocks <= self.max_dynamic_crops:
                        ratios.add((width, height))
        return sorted(ratios, key=lambda item: item[0] * item[1])

    def _select_ratio(self, width: int, height: int) -> Tuple[int, int]:
        aspect_ratio = width / height if height else 1.0
        best_ratio = (1, 1)
        best_diff = float("inf")
        reference_area = self.crop_size * self.crop_size

        for candidate in self._candidate_ratios:
            cand_width, cand_height = candidate
            cand_ratio = cand_width / cand_height
            diff = abs(aspect_ratio - cand_ratio)
            if diff < best_diff:
                best_diff = diff
                best_ratio = candidate
                continue

            if diff == best_diff:
                if width * height > 0.5 * reference_area * cand_width * cand_height:
                    best_ratio = candidate

        return best_ratio

    def _dynamic_preprocess(
        self, image: Image.Image
    ) -> Tuple[List[np.ndarray], Tuple[int, int]]:
        width, height = image.size
        width_tiles, height_tiles = self._select_ratio(width, height)
        if width_tiles <= 1 and height_tiles <= 1:
            return [], (1, 1)

        target_width = self.crop_size * width_tiles
        target_height = self.crop_size * height_tiles

        resized = image.resize(
            (target_width, target_height), resample=Image.Resampling.BICUBIC
        )

        local_tiles: List[np.ndarray] = []
        for row in range(height_tiles):
            for col in range(width_tiles):
                left = col * self.crop_size
                top = row * self.crop_size
                crop = resized.crop(
                    (left, top, left + self.crop_size, top + self.crop_size)
                )
                # Keep locals at crop_size (e.g., 640x640); custom SAM will handle abs-pos interp
                local_tiles.append(self._to_chw(np.array(crop, dtype=np.float32)))

        return local_tiles, (width_tiles, height_tiles)

    def _prepare_tiles(
        self, image: Image.Image
    ) -> Tuple[List[np.ndarray], List[Tuple[int, int]]]:
        # Match HF preprocessing: correct orientation using EXIF before any resizing/cropping
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            # If EXIF is missing or corrupt, proceed without transpose
            pass
        image = image.convert("RGB")
        global_tile = self._prepare_global_tile(image)
        tiles: List[np.ndarray] = [global_tile]
        specs: List[Tuple[int, int]]

        width_tiles = 1
        height_tiles = 1

        if self.dynamic_crops and (
            image.width > self.crop_size or image.height > self.crop_size
        ):
            local_tiles, ratio = self._dynamic_preprocess(image)
            width_tiles, height_tiles = ratio
            if local_tiles and (width_tiles > 1 or height_tiles > 1):
                tiles.extend(local_tiles)
            else:
                width_tiles = height_tiles = 1

        specs = [(width_tiles, height_tiles)]
        return tiles, specs

    def _prepare_single(
        self, prompt: str, images: Sequence[Image.Image]
    ) -> Tuple[
        List[int], List[bool], List[np.ndarray], List[Tuple[int, int]], List[int]
    ]:
        segments = prompt.split(self.image_token)
        if len(images) != len(segments) - 1:
            raise ValueError(
                "Number of image placeholders does not match number of images provided."
            )

        token_ids: List[int] = []
        image_mask: List[bool] = []
        tiles: List[np.ndarray] = []
        crop_specs: List[Tuple[int, int]] = []
        type_codes: List[int] = []

        if self.add_bos and self.bos_token_id is not None:
            token_ids.append(int(self.bos_token_id))
            image_mask.append(False)
            type_codes.append(0)  # BOS is a text token, type 0

        for idx, segment in enumerate(segments[:-1]):
            text_ids = self._encode_text(segment)
            token_ids.extend(text_ids)
            image_mask.extend([False] * len(text_ids))
            type_codes.extend([0] * len(text_ids))  # Text tokens are type 0

            img_tiles, specs = self._prepare_tiles(images[idx])
            tiles.extend(img_tiles)
            crop_specs.extend(specs)

            for spec in specs:
                ids_view, types_view = self._image_token_sequence(*spec)
                token_ids.extend(ids_view)
                # Mark ALL vision-related positions (types 1,2,3) as True in mask
                # to match HF convention: mask=True means "<image> token to replace"
                # These include: vision features (1), newlines (2), separators (3)
                image_mask.extend([t != 0 for t in types_view])
                type_codes.extend(types_view)

        # Final text segment after the last <image>
        final_text_ids = self._encode_text(segments[-1])
        token_ids.extend(final_text_ids)
        image_mask.extend([False] * len(final_text_ids))
        type_codes.extend([0] * len(final_text_ids))  # Text tokens are type 0

        return token_ids, image_mask, tiles, crop_specs, type_codes

    def _collate(
        self,
        token_ids: List[List[int]],
        image_masks: List[List[bool]],
        tiles: List[List[np.ndarray]],
        crop_specs: List[List[Tuple[int, int]]],
        type_codes: List[List[int]],
    ) -> ProcessorOutput:
        batch_size = len(token_ids)
        max_seq_len = max(len(ids) for ids in token_ids)
        max_views = max((len(spec) for spec in crop_specs), default=0)

        input_ids_arr = np.full(
            (batch_size, max_seq_len), self.pad_token_id, dtype=np.int32
        )
        attention_mask_arr = np.zeros((batch_size, max_seq_len), dtype=np.int32)
        image_mask_arr = np.zeros((batch_size, max_seq_len), dtype=bool)

        images_types_arr = np.zeros((batch_size, max_seq_len), dtype=np.int8)

        for idx, ids in enumerate(token_ids):
            length = len(ids)
            input_ids_arr[idx, :length] = ids
            attention_mask_arr[idx, :length] = 1
            image_mask_arr[idx, :length] = image_masks[idx]
            if type_codes:
                types_row = np.array(type_codes[idx], dtype=np.int8)
                images_types_arr[idx, : len(types_row)] = types_row

        pixel_values_list: List[List[mx.array]] = []
        any_tiles = False
        for sample_tiles in tiles:
            converted_tiles = [
                mx.array(tile).astype(mx.bfloat16) for tile in sample_tiles
            ]
            if converted_tiles:
                any_tiles = True
            pixel_values_list.append(converted_tiles)

        pixel_values: Optional[List[List[mx.array]]]
        if any_tiles:
            pixel_values = pixel_values_list
        else:
            pixel_values = None

        if max_views > 0:
            crop_array = np.zeros((batch_size, max_views, 2), dtype=np.int32)
            for idx, sample_specs in enumerate(crop_specs):
                for view_idx, spec in enumerate(sample_specs):
                    crop_array[idx, view_idx] = spec
            images_spatial_crop = mx.array(crop_array)
        else:
            images_spatial_crop = None

        return ProcessorOutput(
            input_ids=mx.array(input_ids_arr),
            attention_mask=mx.array(attention_mask_arr),
            images_seq_mask=mx.array(image_mask_arr),
            images_seq_types=mx.array(images_types_arr) if type_codes else None,
            pixel_values=pixel_values,
            images_spatial_crop=images_spatial_crop,
        )

    def prepare_batch(
        self,
        prompts: Sequence[str],
        images: Sequence[Sequence[Image.Image]] | Sequence[Iterable[Image.Image]],
    ) -> ProcessorOutput:
        if len(prompts) != len(images):
            raise ValueError("Each prompt must have a matching list of images.")

        token_ids: List[List[int]] = []
        image_masks: List[List[bool]] = []
        tiles: List[List[np.ndarray]] = []
        crop_specs: List[List[Tuple[int, int]]] = []
        type_codes: List[List[int]] = []

        for prompt, image_group in zip(prompts, images):
            ids, mask, sample_tiles, specs, types = self._prepare_single(
                prompt, list(image_group)
            )
            token_ids.append(ids)
            image_masks.append(mask)
            tiles.append(sample_tiles)
            crop_specs.append(specs)
            type_codes.append(types)

        return self._collate(token_ids, image_masks, tiles, crop_specs, type_codes)

    def prepare_single(
        self, prompt: str, images: Sequence[Image.Image]
    ) -> ProcessorOutput:
        return self.prepare_batch([prompt], [images])

"""Local MLX implementation scaffolding for DeepSeek-OCR."""

from .config import DeepSeekOCRConfig
from .generate import GenerationConfig, GenerationResult, generate
from .processor import DeepSeekOCRPreprocessor, ProcessorOutput
from .postprocess import (
    Detection,
    annotate_image,
    parse_detections,
    render_markdown,
    save_image_crops,
    save_ocr_outputs,
    scale_box,
)
from .debug_utils import (
    ArrayComparison,
    CosineSummary,
    DEFAULT_LOCAL_SPATIAL,
    compare_arrays,
    cosine_similarity,
    hf_local_index_to_mlx,
    load_npy,
    mlx_local_index_to_hf,
    print_comparison,
    reorder_locals,
    summarize_cosines,
)

__all__ = [
    "DeepSeekOCRConfig",
    "DeepSeekOCRPreprocessor",
    "ProcessorOutput",
    "GenerationConfig",
    "GenerationResult",
    "generate",
    "Detection",
    "annotate_image",
    "parse_detections",
    "render_markdown",
    "save_image_crops",
    "save_ocr_outputs",
    "scale_box",
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

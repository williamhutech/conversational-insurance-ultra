"""
Configuration dataclasses for fast_ocr module.

Defines OCR and extraction settings with sensible defaults.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class OCRConfig:
    """
    RapidOCR configuration.

    Attributes:
        lang: Language code ('en', 'ch', 'fr', etc.). Supports 80+ languages.
        det: Enable text detection
        rec: Enable text recognition
        use_angle_cls: Enable angle classification for rotated text
        use_gpu: Use GPU acceleration (requires CUDA) - Note: ONNX Runtime default
        show_log: Show OCR logging output (corresponds to log_level in RapidOCR)
        det_db_thresh: Detection DB threshold (0-1, higher = stricter)
        det_db_box_thresh: Detection box threshold (0-1)
        rec_batch_num: Recognition batch size
        engine_type: Inference engine ('onnxruntime', 'openvino', 'paddle', 'torch')
        ocr_version: OCR model version ('PP-OCRv4' or 'PP-OCRv5')
        model_type: Model size ('mobile' or 'server')
        text_score: Text recognition confidence threshold (0-1)
    """

    lang: str = 'en'
    det: bool = True
    rec: bool = True
    use_angle_cls: bool = True
    use_gpu: bool = False
    show_log: bool = False
    det_db_thresh: float = 0.3
    det_db_box_thresh: float = 0.5
    rec_batch_num: int = 6

    # RapidOCR specific parameters
    engine_type: str = 'onnxruntime'  # onnxruntime, openvino, paddle, torch
    ocr_version: str = 'PP-OCRv4'     # PP-OCRv4, PP-OCRv5 (Note: PP-OCRv5 has limited model availability)
    model_type: str = 'mobile'         # mobile, server
    text_score: float = 0.5            # Global text score threshold


@dataclass
class ExtractionConfig:
    """
    Text extraction configuration.

    Attributes:
        ocr_config: OCR-specific configuration
        max_file_size_mb: Maximum file size to process (MB)
        supported_languages: List of supported language codes
        pdf_dpi: DPI for PDF to image conversion
        enable_text_cleanup: Enable post-processing text cleanup
        image_max_dimension: Max dimension for image resizing (0 = no resize)
        archive_max_depth: Maximum recursion depth for archive extraction
        timeout_seconds: Processing timeout per file
    """

    ocr_config: OCRConfig = field(default_factory=OCRConfig)
    max_file_size_mb: int = 100
    supported_languages: List[str] = field(default_factory=lambda: [
        'en', 'ch', 'fr', 'german', 'japan', 'korean', 'it', 'es', 'pt', 'ru',
        'ar', 'hi', 'ug', 'fa', 'ur', 'bg', 'uk', 'be', 'te', 'ta', 'af', 'az',
        'bs', 'cs', 'cy', 'da', 'et', 'ga', 'hr', 'hu', 'id', 'is', 'ku', 'lt',
        'lv', 'mi', 'ms', 'mt', 'nl', 'no', 'pl', 'ro', 'sk', 'sl', 'sq', 'sv',
        'sw', 'tl', 'tr', 'uz', 'vi', 'mn', 'abq', 'ava', 'dar', 'inh', 'che',
        'lbe', 'lez', 'tab', 'bh', 'mai', 'ang', 'bho', 'mah', 'sck', 'new',
        'gom', 'sa', 'ady', 'chinese_cht', 'rs_latin', 'rs_cyrillic', 'oc', 'mr',
        'ne'
    ])
    pdf_dpi: int = 300
    enable_text_cleanup: bool = True
    image_max_dimension: int = 0  # 0 = no resize
    archive_max_depth: int = 3
    timeout_seconds: int = 300

"""
Main text extraction function for fast_ocr module.
"""

from typing import Union, Dict, Any
from pathlib import Path

from .core.extractor import TextExtractor
from .config import OCRConfig, ExtractionConfig


def fast_text_extract(
    file: Union[str, Path, bytes],
    lang: str = 'auto',
    detect_orientation: bool = True,
    use_angle_cls: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Extract text from file using appropriate handler.

    Args:
        file: File path, Path object, or bytes
        lang: Language code ('en', 'ch', 'fr', etc.) or 'auto' for auto-detection
        detect_orientation: Enable orientation detection for images
        use_angle_cls: Use angle classification for rotated text
        **kwargs: Additional configuration options

    Returns:
        Dictionary with:
            - text: str - Extracted text content
            - file_type: str - Detected file type
            - language: str - Detected or specified language
            - page_count: int - Number of pages (for multi-page documents)
            - confidence: float - OCR confidence score (if applicable)
            - metadata: dict - Additional file-specific metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file type is unsupported
        ImportError: If required dependencies are missing

    Example:
        >>> result = fast_text_extract('document.pdf', lang='en')
        >>> print(result['text'])
        >>> print(f"Confidence: {result['confidence']:.2%}")
    """
    # Build configuration
    ocr_config = OCRConfig(
        lang=lang if lang != 'auto' else 'en',
        use_angle_cls=use_angle_cls,
        **{k: v for k, v in kwargs.items() if k in OCRConfig.__annotations__}
    )

    extraction_config = ExtractionConfig(
        ocr_config=ocr_config,
        **{k: v for k, v in kwargs.items() if k in ExtractionConfig.__annotations__}
    )

    # Extract text
    extractor = TextExtractor(extraction_config)
    result = extractor.extract(file, lang=lang)

    # Raise exception if there's an error instead of silently returning empty text
    if not result['text'] and result.get('metadata', {}).get('error'):
        error_msg = result['metadata']['error']
        raise RuntimeError(f"Text extraction failed: {error_msg}")

    return result

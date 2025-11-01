"""Utility functions for fast_ocr."""

from .file_utils import (
    detect_file_type,
    validate_file,
    get_file_size_mb,
    detect_encoding
)
from .text_utils import (
    clean_ocr_text,
    merge_text_blocks,
    normalize_whitespace
)

__all__ = [
    'detect_file_type',
    'validate_file',
    'get_file_size_mb',
    'detect_encoding',
    'clean_ocr_text',
    'merge_text_blocks',
    'normalize_whitespace'
]

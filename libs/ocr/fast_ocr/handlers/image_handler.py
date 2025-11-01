"""
Image handler for OCR-based text extraction from image files.

Handles various image formats with EXIF orientation correction.
"""

from pathlib import Path
from typing import Dict, Any, List
from PIL import Image, ImageOps
import numpy as np

from .base import BaseFileHandler
from ..config import ExtractionConfig
from ..core.ocr_engine import OCREngine
from ..utils.text_utils import clean_ocr_text


class ImageHandler(BaseFileHandler):
    """
    Handler for image files using PaddleOCR.

    Supported formats:
    - JPEG: .jpg, .jpeg
    - PNG: .png
    - BMP: .bmp
    - TIFF: .tif, .tiff
    - WebP: .webp
    - HEIC: .heic, .heif (if pillow-heif installed)
    - GIF: .gif
    - Other: .pbm, .pgm, .ppm
    """

    def __init__(self, ocr_engine: OCREngine):
        """
        Initialize image handler.

        Args:
            ocr_engine: OCR engine instance
        """
        self.ocr_engine = ocr_engine

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported image extensions."""
        return [
            '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff',
            '.webp', '.heic', '.heif', '.gif', '.pbm', '.pgm', '.ppm',
            '.jfif', '.jpe', '.jp2', '.j2k', '.jpf', '.jpx', '.jpm'
        ]

    @property
    def requires_ocr(self) -> bool:
        """Images require OCR."""
        return True

    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from image using OCR.

        Args:
            file_path: Path to image file
            config: Extraction configuration

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Load and preprocess image
            image = self._load_image(file_path, config)

            # Run OCR
            ocr_result = self.ocr_engine.extract_from_image(image)

            # Extract text and metadata
            text = ocr_result['text']
            confidence = ocr_result['average_confidence']

            # Optional cleanup
            if config.enable_text_cleanup:
                text = clean_ocr_text(text)

            # Get image metadata
            img_width, img_height = image.size

            # Create result
            return self._create_result(
                text=text,
                page_count=1,
                confidence=confidence,
                metadata={
                    'image_width': img_width,
                    'image_height': img_height,
                    'extension': file_path.suffix,
                    'text_regions': len(ocr_result['texts']),
                    'language': self.ocr_engine.config.lang,
                    'confidences': ocr_result['confidences'],
                    'bounding_boxes': ocr_result['boxes']
                }
            )

        except Exception as e:
            return self._create_result(
                text="",
                page_count=1,
                confidence=0.0,
                metadata={
                    'error': str(e),
                    'extension': file_path.suffix
                }
            )

    def _load_image(self, file_path: Path, config: ExtractionConfig) -> Image.Image:
        """
        Load image with EXIF orientation correction and optional resizing.

        Args:
            file_path: Path to image file
            config: Extraction configuration

        Returns:
            PIL Image in RGB format
        """
        # Load image
        image = Image.open(file_path)

        # Apply EXIF orientation correction
        image = ImageOps.exif_transpose(image)

        # Convert to RGB (handle RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Optional resizing for very large images
        if config.image_max_dimension > 0:
            max_dim = config.image_max_dimension
            width, height = image.size

            if width > max_dim or height > max_dim:
                # Calculate scaling factor
                scale = max_dim / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)

                # Resize with high-quality resampling
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image

    def extract_from_multiple_images(
        self,
        image_paths: List[Path],
        config: ExtractionConfig
    ) -> List[Dict[str, Any]]:
        """
        Extract text from multiple images (batch processing).

        Args:
            image_paths: List of image file paths
            config: Extraction configuration

        Returns:
            List of extraction results
        """
        return [self.extract_text(path, config) for path in image_paths]

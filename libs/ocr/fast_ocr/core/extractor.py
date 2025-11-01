"""
Main text extraction orchestrator.

Coordinates file handlers and OCR engine to extract text from any supported format.
"""

from pathlib import Path
from typing import Dict, Any, List, Union, Optional

from ..config import ExtractionConfig
from .ocr_engine import OCREngine
from ..handlers.base import FileHandler
from ..handlers.text_handler import TextHandler
from ..handlers.image_handler import ImageHandler
from ..handlers.pdf_handler import PDFHandler
from ..handlers.document_handler import DocumentHandler
from ..handlers.spreadsheet_handler import SpreadsheetHandler
from ..handlers.archive_handler import ArchiveHandler
from ..utils.file_utils import validate_file, detect_file_type, get_file_size_mb


class TextExtractor:
    """
    Main extraction orchestrator.

    Manages file handlers and coordinates the extraction process.
    """

    def __init__(self, config: ExtractionConfig):
        """
        Initialize text extractor.

        Args:
            config: Extraction configuration
        """
        self.config = config
        self.ocr_engine = OCREngine(config.ocr_config)
        self.handlers: List[FileHandler] = self._initialize_handlers()

    def _initialize_handlers(self) -> List[FileHandler]:
        """
        Register all file handlers.

        Returns:
            List of file handlers in priority order
        """
        # Order matters: more specific handlers first
        return [
            PDFHandler(self.ocr_engine),
            ImageHandler(self.ocr_engine),
            DocumentHandler(),
            SpreadsheetHandler(),
            TextHandler(),
            ArchiveHandler(self),  # Pass self for recursive processing
        ]

    def extract(
        self,
        file: Union[str, Path, bytes],
        lang: str = 'auto',
        config: Optional[ExtractionConfig] = None
    ) -> Dict[str, Any]:
        """
        Main extraction entry point.

        Args:
            file: File path, Path object, or bytes
            lang: Language code or 'auto' for auto-detection
            config: Optional extraction configuration override

        Returns:
            Dictionary with:
                - text: str - Extracted text
                - file_type: str - Detected file type
                - language: str - Detected/specified language
                - page_count: int - Number of pages
                - confidence: float - OCR confidence (0-1)
                - metadata: dict - Additional metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is unsupported or too large
        """
        # Use provided config or default
        extraction_config = config or self.config

        # 1. Validate file
        file_path = validate_file(file, max_size_mb=extraction_config.max_file_size_mb)

        # 2. Detect file type
        file_type = detect_file_type(file_path)

        # 3. Update language config if specified
        if lang != 'auto':
            if lang in extraction_config.supported_languages:
                self.ocr_engine.set_language(lang)
            else:
                raise ValueError(
                    f"Unsupported language: {lang}. "
                    f"Supported: {', '.join(extraction_config.supported_languages[:10])}..."
                )

        # 4. Select handler
        handler = self._select_handler(file_path)

        if handler is None:
            return {
                'text': '',
                'file_type': file_type,
                'language': 'unknown',
                'page_count': 0,
                'confidence': 0.0,
                'metadata': {
                    'error': f'No handler found for file type: {file_type}',
                    'extension': file_path.suffix
                }
            }

        # 5. Auto-detect language if needed and handler requires OCR
        if lang == 'auto' and handler.requires_ocr:
            # Try to detect language from first page/image
            try:
                detected_lang = self.ocr_engine.detect_language(str(file_path))
                self.ocr_engine.set_language(detected_lang)
            except Exception:
                # Fallback to English if detection fails
                self.ocr_engine.set_language('en')

        # 6. Extract text
        result = handler.extract_text(file_path, extraction_config)

        # 7. Add file-level metadata
        result['file_type'] = file_type
        result['language'] = self.ocr_engine.config.lang
        result['file_size_mb'] = get_file_size_mb(file_path)
        result['file_name'] = file_path.name

        return result

    def _select_handler(self, file_path: Path) -> Optional[FileHandler]:
        """
        Select appropriate handler for file.

        Args:
            file_path: Path to file

        Returns:
            FileHandler instance or None if no handler found
        """
        for handler in self.handlers:
            if handler.can_handle(file_path):
                return handler

        return None

    def get_supported_extensions(self) -> Dict[str, List[str]]:
        """
        Get all supported file extensions grouped by handler.

        Returns:
            Dictionary mapping handler names to supported extensions
        """
        supported = {}

        for handler in self.handlers:
            handler_name = handler.__class__.__name__.replace('Handler', '')
            supported[handler_name] = handler.supported_extensions

        return supported

    def is_supported(self, file: Union[str, Path]) -> bool:
        """
        Check if file type is supported.

        Args:
            file: File path

        Returns:
            True if file type is supported
        """
        file_path = Path(file) if isinstance(file, str) else file
        return self._select_handler(file_path) is not None

    def extract_batch(
        self,
        files: List[Union[str, Path]],
        lang: str = 'auto',
        skip_errors: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract text from multiple files.

        Args:
            files: List of file paths
            lang: Language code
            skip_errors: If True, skip files that fail; if False, raise exception

        Returns:
            List of extraction results
        """
        results = []

        for file in files:
            try:
                result = self.extract(file, lang=lang)
                results.append(result)
            except Exception as e:
                if skip_errors:
                    # Add error result
                    results.append({
                        'text': '',
                        'file_type': 'unknown',
                        'language': 'unknown',
                        'page_count': 0,
                        'confidence': 0.0,
                        'metadata': {
                            'error': str(e),
                            'file_name': str(file)
                        }
                    })
                else:
                    raise

        return results

    def get_handler_for_file(self, file: Union[str, Path]) -> Optional[str]:
        """
        Get handler name for file.

        Args:
            file: File path

        Returns:
            Handler class name or None
        """
        file_path = Path(file) if isinstance(file, str) else file
        handler = self._select_handler(file_path)

        if handler:
            return handler.__class__.__name__

        return None

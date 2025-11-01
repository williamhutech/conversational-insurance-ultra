"""
PDF handler with intelligent fallback logic.

Attempts direct text extraction first, falls back to OCR for scanned PDFs.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image
import io

from .base import BaseFileHandler
from ..config import ExtractionConfig
from ..core.ocr_engine import OCREngine
from ..utils.text_utils import clean_ocr_text, merge_text_blocks


class PDFHandler(BaseFileHandler):
    """
    Handler for PDF files with smart text extraction.

    Strategy:
    1. Try direct text extraction (PyMuPDF/pdfplumber)
    2. If minimal text found: OCR each page
    3. Combine results with page metadata
    """

    def __init__(self, ocr_engine: OCREngine):
        """
        Initialize PDF handler.

        Args:
            ocr_engine: OCR engine instance
        """
        self.ocr_engine = ocr_engine

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported PDF extensions."""
        return ['.pdf']

    @property
    def requires_ocr(self) -> bool:
        """PDFs may require OCR."""
        return True

    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from PDF using best available method.

        Args:
            file_path: Path to PDF file
            config: Extraction configuration

        Returns:
            Dictionary with extracted text and metadata
        """
        try:
            # Try direct text extraction first
            direct_result = self._extract_text_direct(file_path, config)

            # Check if we got meaningful text (more than 100 chars)
            if len(direct_result['text']) > 100:
                return direct_result

            # Fallback to OCR
            print(f"Minimal text extracted ({len(direct_result['text'])} chars), using OCR...")
            return self._extract_text_ocr(file_path, config)

        except Exception as e:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': str(e), 'extension': '.pdf'}
            )

    def _extract_text_direct(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text directly from PDF (embedded text layer).

        Args:
            file_path: Path to PDF file
            config: Extraction configuration

        Returns:
            Dictionary with extracted text
        """
        try:
            import pymupdf as fitz
        except ImportError:
            try:
                import fitz
            except ImportError:
                raise ImportError(
                    "PyMuPDF not installed. Install with: pip install pymupdf"
                )

        # Open PDF
        doc = fitz.open(str(file_path))
        page_texts = []
        total_chars = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()

            if page_text.strip():
                page_texts.append(f"--- Page {page_num + 1} ---\n\n{page_text}")
                total_chars += len(page_text)

        doc.close()

        # Merge pages
        text = merge_text_blocks(page_texts, separator='\n\n')

        # Optional cleanup
        if config.enable_text_cleanup:
            text = clean_ocr_text(text)

        return self._create_result(
            text=text,
            page_count=len(page_texts),
            confidence=1.0,  # Direct extraction = 100% confidence
            metadata={
                'method': 'direct_text_extraction',
                'total_chars': total_chars,
                'pages_with_text': len(page_texts)
            }
        )

    def _extract_text_ocr(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from PDF using OCR (for scanned PDFs).

        Args:
            file_path: Path to PDF file
            config: Extraction configuration

        Returns:
            Dictionary with OCR-extracted text
        """
        try:
            import pymupdf as fitz
        except ImportError:
            try:
                import fitz
            except ImportError:
                raise ImportError(
                    "PyMuPDF not installed. Install with: pip install pymupdf"
                )

        # Open PDF
        doc = fitz.open(str(file_path))
        page_texts = []
        confidences = []
        total_regions = 0

        # Convert each page to image and OCR
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Render page to image at specified DPI
            zoom = config.pdf_dpi / 72  # 72 DPI is default
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            # Run OCR
            ocr_result = self.ocr_engine.extract_from_image(image)

            if ocr_result['text'].strip():
                page_text = f"--- Page {page_num + 1} ---\n\n{ocr_result['text']}"
                page_texts.append(page_text)
                confidences.append(ocr_result['average_confidence'])
                total_regions += len(ocr_result['texts'])

        doc.close()

        # Merge pages
        text = merge_text_blocks(page_texts, separator='\n\n')

        # Optional cleanup
        if config.enable_text_cleanup:
            text = clean_ocr_text(text)

        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return self._create_result(
            text=text,
            page_count=len(page_texts),
            confidence=avg_confidence,
            metadata={
                'method': 'ocr',
                'dpi': config.pdf_dpi,
                'pages_ocr': len(page_texts),
                'total_text_regions': total_regions,
                'page_confidences': confidences,
                'language': self.ocr_engine.config.lang
            }
        )

    def extract_page_images(
        self,
        file_path: Path,
        config: ExtractionConfig
    ) -> List[Image.Image]:
        """
        Extract PDF pages as images.

        Args:
            file_path: Path to PDF file
            config: Extraction configuration

        Returns:
            List of PIL Images (one per page)
        """
        try:
            import pymupdf as fitz
        except ImportError:
            try:
                import fitz
            except ImportError:
                raise ImportError("PyMuPDF not installed")

        doc = fitz.open(str(file_path))
        images = []

        zoom = config.pdf_dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        for page in doc:
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            images.append(image)

        doc.close()

        return images

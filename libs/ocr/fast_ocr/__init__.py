"""
Fast OCR - Multi-format text extraction with PaddleOCR

Supports 80+ languages and comprehensive file format coverage:
- Plain text & markup files (direct read)
- Images (OCR)
- PDFs (text extraction + OCR fallback)
- Documents (DOCX, ODT, RTF, EPUB)
- Spreadsheets (XLSX, XLS, ODS, CSV)
- Archives (ZIP, TAR, GZ, 7Z - recursive extraction)
"""

from .fast_text_extract import fast_text_extract

__version__ = "0.1.0"
__all__ = ["fast_text_extract"]



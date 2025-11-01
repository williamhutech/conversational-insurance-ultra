"""
Base file handler protocol and abstract class.

Defines the interface that all file handlers must implement.
"""

from typing import Protocol, Dict, Any, List
from pathlib import Path
from abc import ABC, abstractmethod

from ..config import ExtractionConfig


class FileHandler(Protocol):
    """
    Protocol for file type handlers.

    All handlers must implement these methods to be compatible with the extraction system.
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions (with leading dot)."""
        ...

    @property
    def requires_ocr(self) -> bool:
        """Return True if this handler requires OCR engine."""
        ...

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if handler can process this file.

        Args:
            file_path: Path to file

        Returns:
            True if handler can process this file type
        """
        ...

    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from file and return structured result.

        Args:
            file_path: Path to file
            config: Extraction configuration

        Returns:
            Dictionary with:
                - text: str - Extracted text
                - page_count: int - Number of pages (1 for single-page)
                - confidence: float - OCR confidence (1.0 if not OCR-based)
                - metadata: dict - Handler-specific metadata
        """
        ...


class BaseFileHandler(ABC):
    """
    Abstract base class for file handlers with common functionality.

    Provides default implementations and helper methods.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        pass

    @property
    def requires_ocr(self) -> bool:
        """Return True if handler requires OCR. Default: False."""
        return False

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if handler can process this file based on extension.

        Args:
            file_path: Path to file

        Returns:
            True if file extension is in supported_extensions
        """
        return file_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """Extract text from file. Must be implemented by subclasses."""
        pass

    def _create_result(
        self,
        text: str,
        page_count: int = 1,
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create standardized result dictionary.

        Args:
            text: Extracted text
            page_count: Number of pages
            confidence: OCR confidence score (0-1)
            metadata: Additional metadata

        Returns:
            Standardized result dictionary
        """
        return {
            'text': text,
            'page_count': page_count,
            'confidence': confidence,
            'metadata': metadata or {}
        }

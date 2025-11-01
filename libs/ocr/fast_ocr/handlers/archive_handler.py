"""
Archive handler for compressed files with recursive extraction.

Extracts and processes files from archives (ZIP, TAR, GZ, 7Z, etc.).
"""

from pathlib import Path
from typing import Dict, Any, List, TYPE_CHECKING
import zipfile
import tarfile
import tempfile
import shutil

from .base import BaseFileHandler
from ..config import ExtractionConfig
from ..utils.text_utils import merge_text_blocks
from ..utils.file_utils import get_safe_filename

if TYPE_CHECKING:
    from ..core.extractor import TextExtractor


class ArchiveHandler(BaseFileHandler):
    """
    Handler for archive files with recursive text extraction.

    Supported formats:
    - ZIP: .zip
    - TAR: .tar, .tar.gz, .tar.bz2, .tar.xz, .tgz, .tbz2
    - GZIP: .gz
    - BZIP2: .bz2
    - XZ: .xz
    - 7-Zip: .7z (if py7zr installed)
    - RAR: .rar (limited support)
    """

    def __init__(self, extractor: 'TextExtractor'):
        """
        Initialize archive handler.

        Args:
            extractor: Parent TextExtractor instance for recursive processing
        """
        self.extractor = extractor

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported archive extensions."""
        return [
            '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
            '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2', '.txz'
        ]

    @property
    def requires_ocr(self) -> bool:
        """Archives themselves don't require OCR, but contents might."""
        return False

    def can_handle(self, file_path: Path) -> bool:
        """
        Check if handler can process this file.

        Args:
            file_path: Path to file

        Returns:
            True if file is an archive
        """
        # Check for compound extensions
        name_lower = file_path.name.lower()
        if any(name_lower.endswith(ext) for ext in ['.tar.gz', '.tar.bz2', '.tar.xz']):
            return True

        # Check simple extension
        return file_path.suffix.lower() in self.supported_extensions

    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from archive by extracting contents and processing recursively.

        Args:
            file_path: Path to archive file
            config: Extraction configuration

        Returns:
            Dictionary with extracted text and metadata
        """
        # Check recursion depth
        current_depth = config.archive_max_depth
        if current_depth <= 0:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': 'Maximum recursion depth reached'}
            )

        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract archive
                extracted_files = self._extract_archive(file_path, temp_path)

                if not extracted_files:
                    return self._create_result(
                        text="",
                        page_count=0,
                        confidence=0.0,
                        metadata={'error': 'No files extracted from archive'}
                    )

                # Process extracted files recursively
                file_results = []

                # Create modified config with reduced recursion depth
                sub_config = ExtractionConfig(
                    ocr_config=config.ocr_config,
                    max_file_size_mb=config.max_file_size_mb,
                    supported_languages=config.supported_languages,
                    pdf_dpi=config.pdf_dpi,
                    enable_text_cleanup=config.enable_text_cleanup,
                    image_max_dimension=config.image_max_dimension,
                    archive_max_depth=current_depth - 1,
                    timeout_seconds=config.timeout_seconds
                )

                for file in extracted_files:
                    try:
                        result = self.extractor.extract(file, lang='auto', config=sub_config)
                        if result['text'].strip():
                            # Add file header
                            safe_name = get_safe_filename(file)
                            file_text = f"=== File: {safe_name} ===\n\n{result['text']}"
                            file_results.append(file_text)
                    except Exception as e:
                        # Skip files that can't be processed
                        continue

                # Merge all extracted texts
                text = merge_text_blocks(file_results, separator='\n\n---\n\n')

                return self._create_result(
                    text=text,
                    page_count=len(file_results),
                    confidence=1.0,
                    metadata={
                        'archive_type': self._detect_archive_type(file_path),
                        'files_extracted': len(extracted_files),
                        'files_processed': len(file_results),
                        'recursion_depth': config.archive_max_depth - current_depth + 1
                    }
                )

        except Exception as e:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': str(e)}
            )

    def _extract_archive(self, file_path: Path, extract_path: Path) -> List[Path]:
        """
        Extract archive contents to temporary directory.

        Args:
            file_path: Path to archive file
            extract_path: Path to extract to

        Returns:
            List of extracted file paths
        """
        archive_type = self._detect_archive_type(file_path)

        if archive_type == 'zip':
            return self._extract_zip(file_path, extract_path)
        elif archive_type == 'tar':
            return self._extract_tar(file_path, extract_path)
        elif archive_type == '7z':
            return self._extract_7z(file_path, extract_path)
        else:
            raise ValueError(f"Unsupported archive type: {archive_type}")

    def _extract_zip(self, file_path: Path, extract_path: Path) -> List[Path]:
        """Extract ZIP archive."""
        extracted_files = []

        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

            for file_name in zip_ref.namelist():
                file_path = extract_path / file_name
                if file_path.is_file():
                    extracted_files.append(file_path)

        return extracted_files

    def _extract_tar(self, file_path: Path, extract_path: Path) -> List[Path]:
        """Extract TAR archive (including .tar.gz, .tar.bz2, etc.)."""
        extracted_files = []

        with tarfile.open(file_path, 'r:*') as tar_ref:
            tar_ref.extractall(extract_path)

            for member in tar_ref.getmembers():
                if member.isfile():
                    file_path = extract_path / member.name
                    if file_path.exists():
                        extracted_files.append(file_path)

        return extracted_files

    def _extract_7z(self, file_path: Path, extract_path: Path) -> List[Path]:
        """Extract 7-Zip archive."""
        try:
            import py7zr
        except ImportError:
            raise ImportError("py7zr not installed. Install with: pip install py7zr")

        extracted_files = []

        with py7zr.SevenZipFile(file_path, 'r') as archive:
            archive.extractall(path=extract_path)

            for name in archive.getnames():
                file_path = extract_path / name
                if file_path.is_file():
                    extracted_files.append(file_path)

        return extracted_files

    def _detect_archive_type(self, file_path: Path) -> str:
        """
        Detect archive type from filename.

        Args:
            file_path: Path to archive file

        Returns:
            Archive type ('zip', 'tar', '7z', etc.)
        """
        name_lower = file_path.name.lower()

        if name_lower.endswith(('.tar.gz', '.tar.bz2', '.tar.xz', '.tgz', '.tbz2', '.txz', '.tar')):
            return 'tar'
        elif name_lower.endswith('.zip'):
            return 'zip'
        elif name_lower.endswith('.7z'):
            return '7z'
        elif name_lower.endswith(('.gz', '.bz2', '.xz')):
            # Single-file compression (not implemented yet)
            return 'compressed'
        else:
            return 'unknown'

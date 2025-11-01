"""
Text handler for plain text and markup files.

Handles direct text file reading with encoding detection.
"""

from pathlib import Path
from typing import Dict, Any, List

from .base import BaseFileHandler
from ..config import ExtractionConfig
from ..utils.file_utils import detect_encoding
from ..utils.text_utils import clean_ocr_text, get_text_stats


class TextHandler(BaseFileHandler):
    """
    Handler for plain text and markup files that can be read directly.

    Supported formats:
    - Plain text: .txt, .log, .md, .rst, .nfo
    - Markup: .html, .xml, .json, .jsonl, .yaml, .yml, .ini, .cfg, .toml, .conf, .properties
    - Documentation: .tex, .ltx, .srt, .vtt, .po, .pot, .org, .wiki, .bbcode, .texinfo
    - Code: .py, .js, .java, .cpp, .c, .h, .go, .rs, .sh, .sql, .php, .rb, .swift, etc.
    - Data: .csv, .tsv, .jsonl
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported text file extensions."""
        return [
            # Plain text
            '.txt', '.log', '.md', '.rst', '.nfo', '.readme',

            # Markup & structured text
            '.html', '.htm', '.xml', '.json', '.jsonl', '.yaml', '.yml',
            '.ini', '.cfg', '.toml', '.conf', '.properties',

            # Documentation
            '.tex', '.ltx', '.srt', '.vtt', '.po', '.pot', '.org',
            '.wiki', '.bbcode', '.texinfo',

            # Code & scripts
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp',
            '.go', '.rs', '.sh', '.bash', '.zsh', '.ps1', '.bat',
            '.sql', '.php', '.rb', '.swift', '.kt', '.scala',
            '.r', '.m', '.pl', '.lua', '.vim', '.el',

            # Data serialization
            '.csv', '.tsv', '.arff', '.geojson', '.gpx', '.rdf',
            '.ttl', '.n3', '.nt', '.nq',

            # Notebooks
            '.ipynb',

            # Email & contacts
            '.eml', '.ics', '.vcf', '.vcard',

            # Web & archives
            '.rss', '.atom', '.har', '.mhtml', '.mht'
        ]

    @property
    def requires_ocr(self) -> bool:
        """Text files don't require OCR."""
        return False

    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from text file.

        Args:
            file_path: Path to text file
            config: Extraction configuration

        Returns:
            Dictionary with extracted text and metadata
        """
        # Detect encoding
        encoding = detect_encoding(file_path)

        try:
            # Read file
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                text = f.read()

            # Optional cleanup
            if config.enable_text_cleanup:
                text = clean_ocr_text(text)

            # Get text statistics
            stats = get_text_stats(text)

            # Create result
            return self._create_result(
                text=text,
                page_count=1,
                confidence=1.0,
                metadata={
                    'encoding': encoding,
                    'extension': file_path.suffix,
                    **stats
                }
            )

        except Exception as e:
            # Return error in metadata but don't fail completely
            return self._create_result(
                text="",
                page_count=1,
                confidence=0.0,
                metadata={
                    'error': str(e),
                    'encoding_attempted': encoding,
                    'extension': file_path.suffix
                }
            )

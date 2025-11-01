"""
File utility functions for file type detection, validation, and metadata.
"""

import mimetypes
from pathlib import Path
from typing import Union, Optional

# Optional dependency - chardet for encoding detection
try:
    import chardet
    HAS_CHARDET = True
except ImportError:
    HAS_CHARDET = False


# File type categories mapped to extensions
FILE_TYPE_MAP = {
    # Plain text & markup
    'text': {'.txt', '.log', '.md', '.rst', '.nfo'},
    'markup': {'.html', '.xml', '.json', '.jsonl', '.yaml', '.yml', '.ini', '.cfg', '.toml', '.conf', '.properties'},
    'documentation': {'.tex', '.ltx', '.srt', '.vtt', '.po', '.pot', '.org', '.wiki', '.bbcode', '.texinfo'},

    # Images
    'image': {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp', '.heic', '.heif', '.pbm', '.pgm', '.ppm', '.gif', '.raw', '.cr2', '.nef', '.arw', '.dng'},
    'vector': {'.svg'},

    # Documents
    'word': {'.docx', '.dotx', '.doc', '.odt', '.rtf', '.pages'},
    'pdf': {'.pdf'},
    'ebook': {'.epub', '.mobi', '.azw', '.azw3'},

    # Spreadsheets
    'spreadsheet': {'.xls', '.xlsx', '.xlsm', '.ods', '.csv', '.tsv', '.numbers'},

    # Archives
    'archive': {'.zip', '.tar', '.gz', '.bz2', '.7z', '.xz', '.rar', '.tar.gz', '.tar.bz2', '.tar.xz', '.tgz'},

    # Code & scripts
    'code': {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.sh', '.ps1', '.sql', '.php', '.rb', '.swift', '.ipynb'},

    # Email & contacts
    'email': {'.msg', '.eml', '.ics', '.vcf', '.vcard'},

    # Web archives
    'web_archive': {'.mhtml', '.mht', '.har'},
}


def detect_file_type(file_path: Path) -> str:
    """
    Detect file type from extension.

    Args:
        file_path: Path to file

    Returns:
        File type category (e.g., 'text', 'image', 'pdf', 'word', etc.)
        Returns 'unknown' if type cannot be determined
    """
    extension = file_path.suffix.lower()

    # Special handling for compound extensions
    if file_path.name.endswith(('.tar.gz', '.tar.bz2', '.tar.xz')):
        return 'archive'

    # Search in category map
    for file_type, extensions in FILE_TYPE_MAP.items():
        if extension in extensions:
            return file_type

    # Fallback to mimetypes
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        if mime_type.startswith('text/'):
            return 'text'
        elif mime_type.startswith('image/'):
            return 'image'
        elif mime_type == 'application/pdf':
            return 'pdf'

    return 'unknown'


def validate_file(file: Union[str, Path, bytes], max_size_mb: Optional[int] = None) -> Path:
    """
    Validate file exists, is readable, and within size limits.

    Args:
        file: File path, Path object, or bytes
        max_size_mb: Maximum file size in MB (None = no limit)

    Returns:
        Validated Path object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is too large or not a file
    """
    # Handle bytes input (save to temp file if needed in future)
    if isinstance(file, bytes):
        raise NotImplementedError("Bytes input not yet supported. Please provide file path.")

    # Convert to Path
    file_path = Path(file) if isinstance(file, str) else file

    # Check existence
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check if it's a file (not directory)
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Check size
    if max_size_mb is not None:
        size_mb = get_file_size_mb(file_path)
        if size_mb > max_size_mb:
            raise ValueError(
                f"File too large: {size_mb:.2f}MB exceeds limit of {max_size_mb}MB"
            )

    return file_path


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def detect_encoding(file_path: Path, num_bytes: int = 10000) -> str:
    """
    Detect text file encoding using chardet (if available).

    Args:
        file_path: Path to text file
        num_bytes: Number of bytes to read for detection

    Returns:
        Detected encoding (e.g., 'utf-8', 'iso-8859-1', 'ascii')
        Falls back to 'utf-8' if detection fails or chardet not available
    """
    if not HAS_CHARDET:
        # Fallback: try common encodings
        encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']

        with open(file_path, 'rb') as f:
            raw_data = f.read(num_bytes)

        for encoding in encodings_to_try:
            try:
                raw_data.decode(encoding)
                return encoding
            except (UnicodeDecodeError, AttributeError):
                continue

        return 'utf-8'  # Ultimate fallback

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(num_bytes)

        result = chardet.detect(raw_data)
        encoding = result.get('encoding')

        if encoding and result.get('confidence', 0) > 0.7:
            return encoding

        # Fallback to utf-8
        return 'utf-8'

    except Exception:
        # If anything fails, default to utf-8
        return 'utf-8'


def is_binary_file(file_path: Path) -> bool:
    """
    Check if file is binary (non-text).

    Args:
        file_path: Path to file

    Returns:
        True if file appears to be binary
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)

        # Check for null bytes
        if b'\x00' in chunk:
            return True

        # Try to decode as text
        try:
            chunk.decode('utf-8')
            return False
        except UnicodeDecodeError:
            return True

    except Exception:
        return True


def get_safe_filename(file_path: Path) -> str:
    """
    Get safe filename without path separators.

    Args:
        file_path: Path to file

    Returns:
        Safe filename string
    """
    return file_path.name.replace('/', '_').replace('\\', '_')

"""
Text utility functions for cleaning, normalizing, and formatting extracted text.
"""

import re
import unicodedata
from typing import List


def clean_ocr_text(text: str) -> str:
    """
    Clean OCR artifacts and normalize text.

    Args:
        text: Raw OCR text

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove excessive whitespace
    text = normalize_whitespace(text)

    # Remove common OCR artifacts
    text = re.sub(r'[|┃│║]', ' ', text)  # Vertical bars often OCR errors
    text = re.sub(r'[─━═]', '-', text)  # Horizontal lines
    text = re.sub(r'[\u2022\u2023\u2043]', '•', text)  # Bullets
    text = re.sub(r'…', '...', text)  # Ellipsis

    # Fix common OCR character confusions
    text = re.sub(r'\b0(?=[A-Z])', 'O', text)  # 0 → O before capital letters
    text = re.sub(r'\bl(?=\d)', '1', text)  # l → 1 before digits

    # Remove control characters except newlines and tabs
    def is_control_char(c):
        """Check if character is a control character."""
        if c in '\n\t':
            return False
        category = unicodedata.category(c)
        return category.startswith('C')  # 'Cc', 'Cf', 'Cn', 'Co', 'Cs'

    text = ''.join(char for char in text if not is_control_char(char))

    # Normalize line breaks
    text = re.sub(r'\r\n', '\n', text)  # Windows → Unix
    text = re.sub(r'\r', '\n', text)  # Old Mac → Unix

    # Remove trailing whitespace from lines
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace characters.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""

    # Replace multiple spaces with single space
    text = re.sub(r'  +', ' ', text)

    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r'\n\n+', '\n\n', text)

    # Remove spaces at start/end of lines
    lines = [line.strip() for line in text.split('\n')]

    return '\n'.join(lines)


def merge_text_blocks(blocks: List[str], separator: str = '\n\n') -> str:
    """
    Merge text blocks with smart spacing.

    Args:
        blocks: List of text blocks
        separator: Separator between blocks

    Returns:
        Merged text
    """
    if not blocks:
        return ""

    # Filter out empty blocks
    non_empty = [block.strip() for block in blocks if block.strip()]

    if not non_empty:
        return ""

    # Join blocks
    merged = separator.join(non_empty)

    # Normalize the result
    return normalize_whitespace(merged)


def extract_lines(text: str, min_length: int = 1) -> List[str]:
    """
    Extract non-empty lines from text.

    Args:
        text: Input text
        min_length: Minimum line length to include

    Returns:
        List of non-empty lines
    """
    if not text:
        return []

    lines = text.split('\n')
    return [line.strip() for line in lines if len(line.strip()) >= min_length]


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Input text
        max_length: Maximum length (including suffix)
        suffix: Truncation indicator

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    truncate_at = max_length - len(suffix)
    return text[:truncate_at] + suffix


def remove_duplicates(text: str) -> str:
    """
    Remove duplicate consecutive lines.

    Args:
        text: Input text

    Returns:
        Text with duplicates removed
    """
    if not text:
        return ""

    lines = text.split('\n')
    deduplicated = []
    prev_line = None

    for line in lines:
        if line != prev_line:
            deduplicated.append(line)
            prev_line = line

    return '\n'.join(deduplicated)


def fix_hyphenation(text: str) -> str:
    """
    Fix word hyphenation at line breaks (common in PDFs).

    Args:
        text: Input text

    Returns:
        Text with hyphenation fixed
    """
    # Pattern: word- followed by newline and word continuation
    # Example: "exam-\nple" → "example"
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

    return text


def count_words(text: str) -> int:
    """
    Count words in text.

    Args:
        text: Input text

    Returns:
        Word count
    """
    if not text:
        return 0

    # Split on whitespace and count non-empty tokens
    words = text.split()
    return len([w for w in words if w])


def get_text_stats(text: str) -> dict:
    """
    Get statistics about text.

    Args:
        text: Input text

    Returns:
        Dictionary with text statistics
    """
    if not text:
        return {
            'char_count': 0,
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0
        }

    lines = text.split('\n')
    paragraphs = text.split('\n\n')

    return {
        'char_count': len(text),
        'word_count': count_words(text),
        'line_count': len([l for l in lines if l.strip()]),
        'paragraph_count': len([p for p in paragraphs if p.strip()])
    }

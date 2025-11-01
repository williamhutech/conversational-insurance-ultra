"""
File Utilities
Helper functions for file I/O operations (JSON, pickle, text).
"""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Union


def load_json(file_path: Union[str, Path], encoding: str = 'utf-8') -> Any:
    """
    Load JSON data from a file.

    Args:
        file_path: Path to JSON file
        encoding: File encoding (default: utf-8)

    Returns:
        Parsed JSON data
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding=encoding) as f:
        return json.load(f)


def save_json(
    data: Any,
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    indent: int = 2,
    ensure_ascii: bool = False
):
    """
    Save data to a JSON file.

    Args:
        data: Data to save
        file_path: Output file path
        encoding: File encoding (default: utf-8)
        indent: JSON indentation (default: 2)
        ensure_ascii: Whether to escape non-ASCII characters (default: False)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding=encoding) as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

    print(f"Saved JSON to: {file_path}")


def load_json_directory(
    directory: Union[str, Path],
    pattern: str = "*.json",
    encoding: str = 'utf-8'
) -> List[Any]:
    """
    Load all JSON files from a directory matching a pattern.

    Args:
        directory: Directory path
        pattern: Glob pattern for matching files (default: *.json)
        encoding: File encoding (default: utf-8)

    Returns:
        List of loaded JSON data from all files
    """
    directory = Path(directory)
    all_data = []

    for json_file in directory.glob(pattern):
        with open(json_file, 'r', encoding=encoding) as f:
            data = json.load(f)
            # Handle both single items and lists
            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)

    print(f"Loaded {len(all_data)} items from {directory}")
    return all_data


def load_pickle(file_path: Union[str, Path]) -> Any:
    """
    Load data from a pickle file.

    Args:
        file_path: Path to pickle file

    Returns:
        Unpickled data
    """
    file_path = Path(file_path)
    with open(file_path, 'rb') as f:
        return pickle.load(f)


def save_pickle(data: Any, file_path: Union[str, Path]):
    """
    Save data to a pickle file.

    Args:
        data: Data to pickle
        file_path: Output file path
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

    print(f"Saved pickle to: {file_path}")


def load_text_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Load text from a file.

    Args:
        file_path: Path to text file
        encoding: File encoding (default: utf-8)

    Returns:
        File contents as string
    """
    file_path = Path(file_path)
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()


def save_text_file(
    text: str,
    file_path: Union[str, Path],
    encoding: str = 'utf-8'
):
    """
    Save text to a file.

    Args:
        text: Text to save
        file_path: Output file path
        encoding: File encoding (default: utf-8)
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding=encoding) as f:
        f.write(text)

    print(f"Saved text to: {file_path}")


def ensure_directory(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Directory path

    Returns:
        Path object for the directory
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def list_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = False
) -> List[Path]:
    """
    List files in a directory matching a pattern.

    Args:
        directory: Directory path
        pattern: Glob pattern (default: *)
        recursive: Whether to search recursively (default: False)

    Returns:
        List of Path objects
    """
    directory = Path(directory)

    if recursive:
        files = list(directory.rglob(pattern))
    else:
        files = list(directory.glob(pattern))

    return sorted([f for f in files if f.is_file()])


def get_file_size_mb(file_path: Union[str, Path]) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    file_path = Path(file_path)
    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def merge_json_files(
    input_files: List[Union[str, Path]],
    output_file: Union[str, Path],
    encoding: str = 'utf-8'
):
    """
    Merge multiple JSON files into a single file.

    Args:
        input_files: List of input JSON file paths
        output_file: Output file path
        encoding: File encoding (default: utf-8)
    """
    merged_data = []

    for file_path in input_files:
        data = load_json(file_path, encoding=encoding)
        if isinstance(data, list):
            merged_data.extend(data)
        else:
            merged_data.append(data)

    save_json(merged_data, output_file, encoding=encoding)
    print(f"Merged {len(input_files)} files into {output_file}")
    print(f"Total items: {len(merged_data)}")

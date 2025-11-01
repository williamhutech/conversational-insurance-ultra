"""
Comprehensive test file for fast_ocr module.

Tests both OCR-free formats (text files) and OCR-dependent formats (images/PDFs).
"""

import os
import tempfile
from pathlib import Path
from libs.ocr.fast_ocr.fast_text_extract import fast_text_extract


def print_separator(title):
    """Print a nice separator."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_text_file():
    """Test 1: Plain text file (NO OCR needed - works without RapidOCR)."""
    print_separator("TEST 1: Plain Text File (No OCR Required)")

    # Create a temporary text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        test_content = """Hello, World!
This is a test text file.
Fast OCR can extract text from this file without needing RapidOCR!

Features:
- Multi-line support
- Unicode characters: 你好, مرحبا, Привет
- Special characters: @#$%^&*()
"""
        f.write(test_content)
        temp_path = f.name

    try:
        print(f"Test file: {temp_path}")

        result = fast_text_extract(temp_path, lang='en')

        print(f"\n✓ Extraction successful!")
        print(f"  - Text length: {len(result['text'])} characters")
        print(f"  - File type: {result['file_type']}")
        print(f"  - Language: {result['language']}")
        print(f"  - Confidence: {result['confidence']:.1%}")
        print(f"  - Encoding: {result['metadata'].get('encoding', 'N/A')}")
        print(f"\n  Text preview (first 100 chars):")
        print(f"  \"{result['text'][:100]}...\"")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_markdown_file():
    """Test 2: Markdown file (NO OCR needed)."""
    print_separator("TEST 2: Markdown File (No OCR Required)")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        test_content = """# Fast OCR Test Document

## Introduction

This is a **markdown** file with *formatting*.

### Features List

- Item 1
- Item 2
- Item 3

### Code Block

```python
def hello():
    print("Hello, World!")
```
"""
        f.write(test_content)
        temp_path = f.name

    try:
        print(f"Test file: {temp_path}")

        result = fast_text_extract(temp_path, lang='en')

        print(f"\n✓ Extraction successful!")
        print(f"  - Text length: {len(result['text'])} characters")
        print(f"  - File type: {result['file_type']}")
        print(f"  - Confidence: {result['confidence']:.1%}")
        print(f"  - Word count: {result['metadata'].get('word_count', 0)}")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_json_file():
    """Test 3: JSON file (NO OCR needed)."""
    print_separator("TEST 3: JSON File (No OCR Required)")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        test_content = """{
    "name": "Fast OCR Test",
    "version": "1.0.0",
    "features": ["text extraction", "OCR", "multi-format"],
    "languages": ["English", "Chinese", "Arabic"],
    "status": "working"
}"""
        f.write(test_content)
        temp_path = f.name

    try:
        print(f"Test file: {temp_path}")

        result = fast_text_extract(temp_path, lang='en')

        print(f"\n✓ Extraction successful!")
        print(f"  - Text length: {len(result['text'])} characters")
        print(f"  - File type: {result['file_type']}")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_image_file_if_available():
    """Test 4: Image file (REQUIRES RapidOCR - optional)."""
    print_separator("TEST 4: Image File (Requires RapidOCR)")

    # Check if test image exists
    image_path = Path(__file__).parent / "test_files" / "image.png"

    if not image_path.exists():
        print(f"⚠ Test image not found: {image_path}")
        print("  Skipping image test (this is OK)")
        return None

    try:
        print(f"Test file: {image_path}")
        print("Attempting OCR extraction (this requires RapidOCR)...")

        result = fast_text_extract(str(image_path), lang='en')

        print(f"\n✓ OCR extraction successful!")
        print(f"  - Text length: {len(result['text'])} characters")
        print(f"  - File type: {result['file_type']}")
        print(f"  - Language: {result['language']}")
        print(f"  - Confidence: {result['confidence']:.1%}")
        print(f"  - Image size: {result['metadata'].get('image_width')}x{result['metadata'].get('image_height')}")
        print(f"\n  Extracted text preview:")
        print(f"  \"{result['text'][:200]}...\"")

        return True

    except RuntimeError as e:
        if "RapidOCR" in str(e):
            print(f"\n⚠ RapidOCR not installed (this is OK for text-only testing)")
            print(f"  To enable OCR: pip install RapidOCR")
            return None
        else:
            print(f"\n✗ Test failed: {e}")
            return False
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return False


def check_dependencies():
    """Check what dependencies are available."""
    print_separator("Dependency Check")

    dependencies = {
        'RapidOCR': 'OCR engine',
        'PIL': 'Image processing',
        'pymupdf': 'PDF processing',
        'docx': 'DOCX files',
        'openpyxl': 'Excel files',
        'chardet': 'Encoding detection',
    }

    available = []
    missing = []

    for dep, description in dependencies.items():
        try:
            __import__(dep)
            available.append(f"✓ {dep:15} - {description}")
        except ImportError:
            missing.append(f"✗ {dep:15} - {description}")

    print("\nInstalled:")
    for item in available:
        print(f"  {item}")

    print("\nNot installed (optional):")
    for item in missing:
        print(f"  {item}")

    if missing:
        print("\n💡 Tip: Install missing dependencies for full functionality:")
        print("   pip install RapidOCR python-docx openpyxl chardet")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  FAST_OCR MODULE TEST SUITE")
    print("=" * 80)

    # Run tests
    results = []

    results.append(("Text File (TXT)", test_text_file()))
    results.append(("Markdown File (MD)", test_markdown_file()))
    results.append(("JSON File", test_json_file()))
    results.append(("Image File (PNG)", test_image_file_if_available()))

    # Dependency check
    check_dependencies()

    # Summary
    print_separator("TEST SUMMARY")

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results:
        if result is True:
            print(f"  ✓ PASS: {name}")
            passed += 1
        elif result is False:
            print(f"  ✗ FAIL: {name}")
            failed += 1
        else:  # None = skipped
            print(f"  ⊘ SKIP: {name}")
            skipped += 1

    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0 and passed > 0:
        print("\n🎉 All enabled tests passed!")
        if skipped > 0:
            print(f"   ({skipped} test(s) skipped due to missing dependencies)")
    elif failed > 0:
        print(f"\n❌ {failed} test(s) failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
"""
OCR Service
Wrapper for libs/ocr/precise_ocr to convert PDFs to markdown files.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Find repo root by searching for marker files
def find_repo_root(start_path: Path) -> Path:
    """Find repository root by searching for pyproject.toml or .git"""
    current = start_path
    while current.parent != current:
        if (current / "pyproject.toml").exists() or (current / ".git").exists():
            return current
        current = current.parent
    # Fallback to hardcoded depth if markers not found
    return start_path.parents[4]

REPO_ROOT = find_repo_root(Path(__file__).resolve())
OCR_PATH = REPO_ROOT / "libs" / "ocr" / "precise_ocr"
if str(OCR_PATH) not in sys.path:
    sys.path.insert(0, str(OCR_PATH))

try:
    from utils.process_pdf import _discover_pdfs, _process_single_pdf
    HAS_OCR = True
except ImportError as e:
    HAS_OCR = False
    print(f"Warning: Could not import OCR module: {e}")
    print(f"Attempted path: {OCR_PATH}")



class OCRService:
    """
    Service for converting PDFs to markdown using DeepSeek-OCR.

    This service wraps the libs/ocr/precise_ocr functionality for use
    in the Neo4j generation pipeline.
    """

    def __init__(
        self,
        model: str = "deepseek-ai/DeepSeek-OCR",
        workers: int = 3,
        zoom: float = 2.0,
        max_new_tokens: int = 1024,
        temperature: float = 0.2,
        prompt: str = "<image>\n<|grounding|>Convert the document to markdown."
    ):
        """
        Initialize OCR service.

        Args:
            model: Hugging Face model ID
            workers: Number of parallel workers for page processing
            zoom: PDF rendering zoom (1-3, default 2.0 = ~144 DPI)
            max_new_tokens: Max tokens for OCR generation
            temperature: Sampling temperature
            prompt: OCR prompt template
        """
        if not HAS_OCR:
            raise ImportError(
                "OCR module not available. Ensure libs/ocr/precise_ocr/ is properly installed."
            )

        self.model = model
        self.workers = workers
        self.zoom = zoom
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.prompt = prompt
        self.stop_on_eos = True

    def convert_pdf_to_markdown(
        self,
        pdf_path: Path,
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Convert a single PDF to markdown.

        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory for markdown and artifacts

        Returns:
            Dictionary with conversion results:
            {
                "success": bool,
                "pdf_path": str,
                "markdown_file": str,
                "combined_markdown_file": str,
                "skipped": bool (if file already exists),
                "error": str (if failed)
            }
        """
        try:
            pdf_path = Path(pdf_path).resolve()
            output_dir = Path(output_dir).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            # Check if markdown already exists
            pdf_stem = pdf_path.stem
            markdown_file = output_dir / f"{pdf_stem}.md"

            if markdown_file.exists():
                print(f"[INFO] Skipping {pdf_path.name} - markdown already exists")
                combined_file = output_dir / pdf_stem / "combined.md"
                return {
                    "success": True,
                    "pdf_path": str(pdf_path),
                    "markdown_file": str(markdown_file),
                    "combined_markdown_file": str(combined_file) if combined_file.exists() else None,
                    "skipped": True
                }

            # Process PDF
            _process_single_pdf(
                pdf_path=pdf_path,
                out_root=output_dir,
                workers=self.workers,
                model=self.model,
                prompt=self.prompt,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                stop_on_eos=self.stop_on_eos,
                zoom=self.zoom
            )

            # Check output files
            combined_file = output_dir / pdf_stem / "combined.md"

            if not markdown_file.exists():
                return {
                    "success": False,
                    "pdf_path": str(pdf_path),
                    "error": "Markdown file was not created"
                }

            return {
                "success": True,
                "pdf_path": str(pdf_path),
                "markdown_file": str(markdown_file),
                "combined_markdown_file": str(combined_file) if combined_file.exists() else None,
                "skipped": False
            }

        except Exception as e:
            return {
                "success": False,
                "pdf_path": str(pdf_path),
                "error": str(e)
            }

    def convert_directory(
        self,
        input_dir: Path,
        output_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        Convert all PDFs in a directory to markdown.

        Args:
            input_dir: Directory containing PDFs
            output_dir: Output directory for all conversions

        Returns:
            List of conversion result dictionaries
        """
        input_dir = Path(input_dir).resolve()
        pdfs = _discover_pdfs(input_dir)

        if not pdfs:
            print(f"No PDFs found in {input_dir}")
            return []

        print(f"Found {len(pdfs)} PDF(s) to process")

        results = []
        for pdf_path in pdfs:
            print(f"\nProcessing: {pdf_path.name}")
            result = self.convert_pdf_to_markdown(pdf_path, output_dir)
            results.append(result)

        return results

    def extract_text_to_json(
        self,
        markdown_file: Path,
        output_json: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Extract text from page-by-page markdown files and save as JSON.

        This method reads individual page-XXX/result.md files from the PDF output
        directory and creates a JSON array where each element is the full content
        of one page.

        Args:
            markdown_file: Path to root markdown file (used to locate page folders)
            output_json: Output JSON file path (optional)

        Returns:
            Dictionary with:
            {
                "success": bool,
                "markdown_file": str,
                "json_file": str,
                "text_chunks": int (number of pages),
                "error": str (if failed)
            }
        """
        try:
            markdown_file = Path(markdown_file)

            if not markdown_file.exists():
                return {
                    "success": False,
                    "markdown_file": str(markdown_file),
                    "error": "Markdown file not found"
                }

            # Find the PDF output directory (where page-XXX folders are)
            pdf_stem = markdown_file.stem
            pdf_output_dir = markdown_file.parent / pdf_stem

            if not pdf_output_dir.exists() or not pdf_output_dir.is_dir():
                return {
                    "success": False,
                    "markdown_file": str(markdown_file),
                    "error": f"PDF output directory not found: {pdf_output_dir}"
                }

            # Find all page-XXX folders and sort them
            page_folders = sorted([
                p for p in pdf_output_dir.iterdir()
                if p.is_dir() and p.name.startswith('page-')
            ])

            if not page_folders:
                return {
                    "success": False,
                    "markdown_file": str(markdown_file),
                    "error": f"No page folders found in {pdf_output_dir}"
                }

            # Read result.md from each page folder
            page_texts = []
            for page_folder in page_folders:
                result_md = page_folder / "result.md"
                if result_md.exists():
                    page_content = result_md.read_text(encoding='utf-8')
                    page_texts.append(page_content)
                else:
                    # If result.md is missing, add empty string but warn
                    print(f"[WARN] Missing result.md in {page_folder.name}")
                    page_texts.append("")

            # Determine output JSON path
            if output_json is None:
                output_json = markdown_file.with_suffix('.json')
            else:
                output_json = Path(output_json)

            output_json.parent.mkdir(parents=True, exist_ok=True)

            # Save as JSON array (one element per page)
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(page_texts, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "markdown_file": str(markdown_file),
                "json_file": str(output_json),
                "text_chunks": len(page_texts)
            }

        except Exception as e:
            return {
                "success": False,
                "markdown_file": str(markdown_file),
                "error": str(e)
            }

    def process_pipeline_pdfs(
        self,
        pdf_dir: Path,
        markdown_output_dir: Path,
        json_output_dir: Path
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Convert PDFs to markdown, then extract to JSON.

        This is the main entry point for Stage 0 of the Neo4j pipeline.

        Args:
            pdf_dir: Directory containing source PDFs
            markdown_output_dir: Output directory for markdown files
            json_output_dir: Output directory for JSON files

        Returns:
            Dictionary with pipeline results
        """
        print("=" * 60)
        print("OCR PIPELINE: PDF → Markdown → JSON")
        print("=" * 60)

        # Step 1: Convert PDFs to markdown
        print("\n[Step 1] Converting PDFs to markdown...")
        conversion_results = self.convert_directory(pdf_dir, markdown_output_dir)

        successful_conversions = [r for r in conversion_results if r.get("success")]
        failed_conversions = [r for r in conversion_results if not r.get("success")]

        print(f"\nConversion complete: {len(successful_conversions)} succeeded, {len(failed_conversions)} failed")

        # Step 2: Extract text to JSON
        # Process ALL folders in markdown_output_dir, not just successful conversions
        print("\n[Step 2] Extracting text to JSON...")
        extraction_results = []

        # Find all PDF folders in the markdown output directory
        markdown_output_dir = Path(markdown_output_dir)

        # Look for all .md files in the output directory (these are the root markdown files)
        markdown_files = sorted(markdown_output_dir.glob("*.md"))

        if not markdown_files:
            print("No markdown files found to process")
        else:
            print(f"Found {len(markdown_files)} markdown file(s) to process")

            for markdown_file in markdown_files:
                pdf_stem = markdown_file.stem
                json_file = json_output_dir / f"{pdf_stem}.json"

                # Check if corresponding folder exists
                pdf_folder = markdown_output_dir / pdf_stem
                if not pdf_folder.exists() or not pdf_folder.is_dir():
                    print(f"[SKIP] No folder found for {pdf_stem}")
                    continue

                print(f"Processing: {pdf_stem}")
                extraction_result = self.extract_text_to_json(markdown_file, json_file)
                extraction_results.append(extraction_result)

        successful_extractions = [r for r in extraction_results if r.get("success")]
        failed_extractions = [r for r in extraction_results if not r.get("success")]

        print(f"\nExtraction complete: {len(successful_extractions)} succeeded, {len(failed_extractions)} failed")

        # Summary
        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        print(f"PDFs processed: {len(conversion_results)}")
        print(f"Markdown files created: {len(successful_conversions)}")
        print(f"JSON files created: {len(successful_extractions)}")
        print("=" * 60)

        # Return with both top-level keys (for pipeline.py) and nested summary (for backward compatibility)
        return {
            "conversion_results": conversion_results,
            "extraction_results": extraction_results,
            "pdfs_processed": len(conversion_results),
            "markdown_files_generated": len(successful_conversions),
            "json_files_generated": len(successful_extractions),
            "total_pages": sum(r.get("text_chunks", 0) for r in successful_extractions),
            "summary": {
                "pdfs_processed": len(conversion_results),
                "markdown_created": len(successful_conversions),
                "json_created": len(successful_extractions),
                "total_chunks": sum(r.get("text_chunks", 0) for r in successful_extractions)
            }
        }

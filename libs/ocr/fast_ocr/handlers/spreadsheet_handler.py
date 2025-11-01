"""
Spreadsheet handler for Excel, OpenDocument, and CSV files.

Extracts text from spreadsheet cells with sheet structure preservation.
"""

from pathlib import Path
from typing import Dict, Any, List
import io

from .base import BaseFileHandler
from ..config import ExtractionConfig
from ..utils.text_utils import merge_text_blocks


class SpreadsheetHandler(BaseFileHandler):
    """
    Handler for spreadsheet files.

    Supported formats:
    - Excel: .xlsx, .xlsm, .xls
    - OpenDocument: .ods
    - CSV: .csv, .tsv
    - Apple Numbers: .numbers (limited support)
    """

    @property
    def supported_extensions(self) -> List[str]:
        """Return list of supported spreadsheet extensions."""
        return ['.xlsx', '.xlsm', '.xls', '.ods', '.csv', '.tsv', '.numbers']

    @property
    def requires_ocr(self) -> bool:
        """Spreadsheets don't require OCR."""
        return False

    def extract_text(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """
        Extract text from spreadsheet file.

        Args:
            file_path: Path to spreadsheet file
            config: Extraction configuration

        Returns:
            Dictionary with extracted text and metadata
        """
        extension = file_path.suffix.lower()

        try:
            if extension in ['.csv', '.tsv']:
                return self._extract_csv(file_path, config)
            elif extension in ['.xlsx', '.xlsm', '.xls']:
                return self._extract_excel(file_path, config)
            elif extension == '.ods':
                return self._extract_ods(file_path, config)
            elif extension == '.numbers':
                return self._extract_numbers(file_path, config)
            else:
                raise ValueError(f"Unsupported spreadsheet format: {extension}")

        except Exception as e:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': str(e), 'extension': extension}
            )

    def _extract_csv(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """Extract text from CSV/TSV file."""
        import csv
        from ..utils.file_utils import detect_encoding

        encoding = detect_encoding(file_path)
        delimiter = '\t' if file_path.suffix.lower() == '.tsv' else ','

        try:
            with open(file_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)

            if not rows:
                return self._create_result(text="", page_count=1, confidence=1.0)

            # Convert to text: tab-separated cells, newline-separated rows
            text_rows = []
            for row in rows:
                row_text = '\t'.join(str(cell) for cell in row)
                text_rows.append(row_text)

            text = '\n'.join(text_rows)

            return self._create_result(
                text=text,
                page_count=1,
                confidence=1.0,
                metadata={
                    'encoding': encoding,
                    'row_count': len(rows),
                    'col_count': max(len(row) for row in rows) if rows else 0,
                    'delimiter': delimiter
                }
            )

        except Exception as e:
            return self._create_result(
                text="",
                page_count=1,
                confidence=0.0,
                metadata={'error': str(e)}
            )

    def _extract_excel(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """Extract text from Excel file (.xlsx, .xls)."""
        try:
            import openpyxl
            import pandas as pd
        except ImportError:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': 'openpyxl or pandas not installed'}
            )

        try:
            # Load workbook
            wb = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
            sheet_texts = []
            total_rows = 0
            total_cols = 0

            for sheet in wb.worksheets:
                sheet_name = sheet.title
                rows = []

                for row in sheet.iter_rows(values_only=True):
                    # Filter out completely empty rows
                    if any(cell is not None for cell in row):
                        row_text = '\t'.join(str(cell) if cell is not None else '' for cell in row)
                        rows.append(row_text)
                        total_cols = max(total_cols, len(row))

                if rows:
                    sheet_text = f"## Sheet: {sheet_name}\n\n" + '\n'.join(rows)
                    sheet_texts.append(sheet_text)
                    total_rows += len(rows)

            wb.close()

            text = merge_text_blocks(sheet_texts, separator='\n\n\n')

            return self._create_result(
                text=text,
                page_count=len(sheet_texts),
                confidence=1.0,
                metadata={
                    'sheet_count': len(sheet_texts),
                    'total_rows': total_rows,
                    'total_cols': total_cols
                }
            )

        except Exception as e:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': str(e)}
            )

    def _extract_ods(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """Extract text from OpenDocument Spreadsheet (.ods)."""
        try:
            from odf import text, teletype
            from odf.opendocument import load
            from odf.table import Table, TableRow, TableCell
        except ImportError:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': 'odfpy not installed'}
            )

        try:
            doc = load(str(file_path))
            tables = doc.spreadsheet.getElementsByType(Table)
            sheet_texts = []

            for table in tables:
                table_name = table.getAttribute('name')
                rows = []

                for row in table.getElementsByType(TableRow):
                    cells = row.getElementsByType(TableCell)
                    row_values = []

                    for cell in cells:
                        # Get cell text content
                        cell_text = teletype.extractText(cell)
                        row_values.append(cell_text if cell_text else '')

                    if any(val for val in row_values):  # Skip empty rows
                        row_text = '\t'.join(row_values)
                        rows.append(row_text)

                if rows:
                    sheet_text = f"## Sheet: {table_name}\n\n" + '\n'.join(rows)
                    sheet_texts.append(sheet_text)

            text = merge_text_blocks(sheet_texts, separator='\n\n\n')

            return self._create_result(
                text=text,
                page_count=len(sheet_texts),
                confidence=1.0,
                metadata={'sheet_count': len(sheet_texts)}
            )

        except Exception as e:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': str(e)}
            )

    def _extract_numbers(self, file_path: Path, config: ExtractionConfig) -> Dict[str, Any]:
        """Extract text from Apple Numbers file (limited support)."""
        # Numbers files are actually ZIP archives containing XML
        try:
            import zipfile
            import xml.etree.ElementTree as ET
        except ImportError:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': 'zipfile or xml not available'}
            )

        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # Numbers files contain Index.xml with content
                if 'Index.xml' in z.namelist():
                    with z.open('Index.xml') as xml_file:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()

                        # Extract all text nodes (simplified)
                        text_elements = root.findall('.//*[@text]')
                        texts = [elem.get('text') for elem in text_elements]

                        text = '\n'.join(filter(None, texts))

                        return self._create_result(
                            text=text,
                            page_count=1,
                            confidence=0.8,  # Lower confidence for Numbers
                            metadata={'format': 'numbers', 'note': 'limited support'}
                        )

            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': 'Index.xml not found in Numbers file'}
            )

        except Exception as e:
            return self._create_result(
                text="",
                page_count=0,
                confidence=0.0,
                metadata={'error': str(e)}
            )

"""
Product Extractor Agent (Stage 1)
Extracts insurance product names from OCR-extracted text files.
"""

from pathlib import Path
from typing import Dict, List
from ..utils.api_client import APIClient
from ..utils.file_utils import load_json, save_json, list_files


class ProductExtractorPrompt:
    """Prompt template for product name extraction."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for product extraction."""
        return "You are an insurance product identification specialist. Extract the exact insurance product name from the given text samples."

    @staticmethod
    def get_user_prompt(sample_texts: List[str]) -> str:
        """
        Get user prompt for product extraction.

        Args:
            sample_texts: List of sampled text passages

        Returns:
            Formatted prompt string
        """
        sample_text = "\n---\n".join(sample_texts)

        return f"""Based on these text samples from an insurance document, identify the EXACT insurance product name:

{sample_text}

Return ONLY the exact product name with the brand name (e.g., "SingTel Elite Insurance Plan", "AXA SmartHealth Insurance").

The Product Name should not contain any special characters like '_', '-'. The Product Name should be capitalized appropriately.

Product name:"""


class ProductExtractor:
    """
    Extract insurance product names from JSON text files.

    Samples representative texts (first, middle, last) from each file,
    uses LLM to identify the product name, and returns a mapping of
    product names to their full text lists.
    """

    def __init__(
        self,
        api_client: APIClient,
        sample_size: int = 3
    ):
        """
        Initialize product extractor.

        Args:
            api_client: Configured API client
            sample_size: Number of text samples to use (default: 3)
        """
        self.api_client = api_client
        self.sample_size = sample_size
        self.prompt = ProductExtractorPrompt()

    def _sample_texts(self, text_list: List[str]) -> List[str]:
        """
        Sample representative texts from list.

        Args:
            text_list: Full list of texts

        Returns:
            Sampled texts (first, middle, last)
        """
        if not text_list:
            return []

        if len(text_list) >= 3:
            return [
                text_list[0],  # First
                text_list[len(text_list) // 2],  # Middle
                text_list[-1]  # Last
            ]
        else:
            return text_list[:min(self.sample_size, len(text_list))]

    def extract_product_from_file(
        self,
        json_file: Path
    ) -> Dict[str, any]:
        """
        Extract product name from a single JSON file.

        Args:
            json_file: Path to JSON file containing text list

        Returns:
            Dictionary with:
            {
                "success": bool,
                "file_name": str,
                "product_name": str,
                "text_list": List[str],
                "error": str (if failed)
            }
        """
        try:
            # Load text list
            text_list = load_json(json_file)

            if not text_list or len(text_list) == 0:
                return {
                    "success": False,
                    "file_name": json_file.name,
                    "error": "Empty file"
                }

            # Sample texts
            sample_texts = self._sample_texts(text_list)

            # Create prompt
            messages = [
                {
                    "role": "system",
                    "content": self.prompt.get_system_prompt()
                },
                {
                    "role": "user",
                    "content": self.prompt.get_user_prompt(sample_texts)
                }
            ]

            # Call API
            result = self.api_client.call_api(messages, timeout=30)

            if result["status"] == "success":
                product_name = result["content"].strip().strip('"').strip("'")

                if product_name:
                    print(f"✓ Extracted: {product_name} from {json_file.name}")
                    return {
                        "success": True,
                        "file_name": json_file.name,
                        "product_name": product_name,
                        "text_list": text_list
                    }
                else:
                    return {
                        "success": False,
                        "file_name": json_file.name,
                        "error": "Empty product name"
                    }
            else:
                return {
                    "success": False,
                    "file_name": json_file.name,
                    "error": result.get("error", "API call failed")
                }

        except Exception as e:
            return {
                "success": False,
                "file_name": json_file.name,
                "error": str(e)
            }

    def extract_products_from_directory(
        self,
        raw_text_dir: Path,
        output_file: Path = None
    ) -> Dict[str, List[str]]:
        """
        Extract product names from all JSON files in directory.

        Args:
            raw_text_dir: Directory containing JSON files
            output_file: Optional output file path for results

        Returns:
            Dictionary mapping product names to their full text lists
        """
        raw_text_dir = Path(raw_text_dir)
        json_files = list(raw_text_dir.glob("*.json"))

        print(f"Found {len(json_files)} JSON files to process")

        product_dict = {}
        failed_files = []

        for json_file in json_files:
            result = self.extract_product_from_file(json_file)

            if result["success"]:
                product_name = result["product_name"]
                text_list = result["text_list"]
                product_dict[product_name] = text_list
            else:
                failed_files.append({
                    "file": result["file_name"],
                    "error": result.get("error")
                })
                print(f"✗ Failed: {result['file_name']} - {result.get('error')}")

        print(f"\nExtraction complete:")
        print(f"  Products extracted: {len(product_dict)}")
        print(f"  Failed files: {len(failed_files)}")

        # Save results if output file specified
        if output_file:
            save_json(product_dict, output_file)

        return product_dict

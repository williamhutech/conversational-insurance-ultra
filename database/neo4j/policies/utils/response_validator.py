"""
Response Validator Utility
Validates and repairs JSON responses from LLM APIs.
"""

import json
import re
from typing import Dict, List

# Try to import json_repair library
try:
    from json_repair import repair_json
    HAS_JSONREPAIR = True
except ImportError:
    HAS_JSONREPAIR = False
    print("Warning: json_repair library not available. Install with: pip install json-repair")


class ResponseValidator:
    """
    Validates and repairs JSON responses from API calls.

    Features:
    - Removes markdown code blocks (```json ... ```)
    - Handles quoted wrappers
    - Extracts JSON from mixed text
    - Automatic JSON repair using json_repair library
    - Validates presence of expected keys
    """

    @staticmethod
    def validate_json_response(response_text: str, expected_keys: List[str]) -> Dict:
        """
        Validates and parses JSON response with automatic repair.

        Args:
            response_text: Raw response text from API
            expected_keys: List of required keys in the JSON object

        Returns:
            Dictionary with validation results:
            {
                "is_valid_json": bool,
                "parsed_json": dict or None,
                "error_type": str or None,
                "raw_response": str,
                "repair_attempts": list of repair steps attempted
            }
        """
        # Handle empty responses
        if not response_text or not response_text.strip():
            return {
                "is_valid_json": False,
                "parsed_json": None,
                "error_type": "empty_response",
                "raw_response": response_text
            }

        repair_attempts = []

        try:
            # Pre-processing and cleaning
            text = response_text.strip()

            # Step 1: Handle markdown code blocks ```json...``` or ```...```
            code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if code_block_match:
                text = code_block_match.group(1).strip()
                repair_attempts.append("removed_markdown_code_block")

            # Step 2: Handle quoted wrappers '...' or "..."
            if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
                text = text[1:-1]
                repair_attempts.append("removed_quotes")

            # Step 3: Remove leading/trailing backticks
            text = text.strip('`').strip()

            # Step 4: Extract JSON - from first { to last }
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                text = json_match.group(1)
                repair_attempts.append("extracted_json_object")

            # Attempt 1: Direct parsing
            try:
                parsed = json.loads(text)
                repair_attempts.append("direct_parse_success")
            except json.JSONDecodeError as e:
                repair_attempts.append(f"direct_parse_failed: {str(e)}")

                # Attempt 2: Repair with json_repair library
                if HAS_JSONREPAIR:
                    try:
                        repaired_text = repair_json(text)
                        parsed = json.loads(repaired_text)
                        repair_attempts.append("jsonrepair_success")
                    except Exception as e:
                        repair_attempts.append(f"jsonrepair_failed: {str(e)}")
                        raise
                else:
                    repair_attempts.append("jsonrepair_not_available")
                    raise

            # Validate structure - check if expected keys are present
            if isinstance(parsed, dict) and all(key in parsed for key in expected_keys):
                return {
                    "is_valid_json": True,
                    "parsed_json": parsed,
                    "error_type": None,
                    "raw_response": response_text,
                    "repair_attempts": repair_attempts
                }
            else:
                # Report missing keys
                missing_keys = (
                    [key for key in expected_keys if key not in parsed]
                    if isinstance(parsed, dict)
                    else expected_keys
                )
                return {
                    "is_valid_json": False,
                    "parsed_json": parsed,
                    "error_type": f"missing_keys: expected {expected_keys}, missing {missing_keys}",
                    "raw_response": response_text,
                    "repair_attempts": repair_attempts
                }

        except json.JSONDecodeError as e:
            return {
                "is_valid_json": False,
                "parsed_json": None,
                "error_type": f"json_decode_error: {str(e)}",
                "raw_response": response_text,
                "repair_attempts": repair_attempts
            }
        except Exception as e:
            return {
                "is_valid_json": False,
                "parsed_json": None,
                "error_type": f"unexpected_error: {str(e)}",
                "raw_response": response_text,
                "repair_attempts": repair_attempts
            }

    @staticmethod
    def extract_json_array(response_text: str) -> Dict:
        """
        Extract and parse JSON array from response text.

        Args:
            response_text: Raw response text containing a JSON array

        Returns:
            Dictionary with parsing results
        """
        if not response_text or not response_text.strip():
            return {
                "is_valid_json": False,
                "parsed_json": None,
                "error_type": "empty_response"
            }

        try:
            text = response_text.strip()

            # Remove markdown code blocks
            code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if code_block_match:
                text = code_block_match.group(1).strip()

            # Extract JSON array - from first [ to last ]
            json_match = re.search(r'(\[.*\])', text, re.DOTALL)
            if json_match:
                text = json_match.group(1)

            # Parse JSON
            parsed = json.loads(text)

            if isinstance(parsed, list):
                return {
                    "is_valid_json": True,
                    "parsed_json": parsed,
                    "error_type": None
                }
            else:
                return {
                    "is_valid_json": False,
                    "parsed_json": parsed,
                    "error_type": "not_an_array"
                }

        except json.JSONDecodeError as e:
            return {
                "is_valid_json": False,
                "parsed_json": None,
                "error_type": f"json_decode_error: {str(e)}"
            }
        except Exception as e:
            return {
                "is_valid_json": False,
                "parsed_json": None,
                "error_type": f"unexpected_error: {str(e)}"
            }

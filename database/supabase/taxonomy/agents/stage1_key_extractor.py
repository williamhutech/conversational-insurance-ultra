"""
Stage 1: Key Extraction Agent
Extracts unique keys from the taxonomy schema without using LLMs.

Extracts:
1. Layer 1: Unique condition names
2. Layer 2: Unique benefit identifiers
3. Layer 3: Unique (benefit_name, condition) pairs
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from entities.data_models import KeyExtractionResult


class KeyExtractor:
    """Extracts unique keys from taxonomy schema."""

    def __init__(self, schema_path: Path):
        """
        Initialize key extractor.

        Args:
            schema_path: Path to Taxonomy_Hackathon.json
        """
        self.schema_path = Path(schema_path).resolve()
        self.schema_data: Dict[str, Any] = {}

    def load_schema(self) -> bool:
        """
        Load taxonomy schema from JSON file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self.schema_data = json.load(f)
            print(f"✓ Loaded schema from: {self.schema_path}")
            print(f"  Taxonomy: {self.schema_data.get('taxonomy_name', 'Unknown')}")
            print(f"  Products: {len(self.schema_data.get('products', []))}")
            return True
        except Exception as e:
            print(f"✗ Error loading schema: {e}")
            return False

    def extract_condition_names(self) -> KeyExtractionResult:
        """
        Extract unique condition names from Layer 1: General Conditions.

        Returns:
            KeyExtractionResult with list of unique condition names
        """
        try:
            layer_1 = self.schema_data.get('layers', {}).get('layer_1_general_conditions', [])

            # Extract all condition names
            condition_names: Set[str] = set()
            for item in layer_1:
                condition = item.get('condition')
                if condition:
                    condition_names.add(condition)

            # Convert to sorted list for consistency
            unique_conditions = sorted(list(condition_names))

            print(f"\n{'=' * 80}")
            print(f"Layer 1: General Conditions")
            print(f"{'=' * 80}")
            print(f"Total unique conditions: {len(unique_conditions)}")
            print(f"Sample conditions: {unique_conditions[:5]}")

            return KeyExtractionResult(
                status="success",
                layer_name="layer_1_general_conditions",
                unique_keys=unique_conditions,
                count=len(unique_conditions)
            )

        except Exception as e:
            print(f"✗ Error extracting condition names: {e}")
            return KeyExtractionResult(
                status="error",
                layer_name="layer_1_general_conditions",
                error=str(e)
            )

    def extract_benefit_names(self) -> KeyExtractionResult:
        """
        Extract unique benefit identifiers from Layer 2: Benefits.

        Returns:
            KeyExtractionResult with list of unique benefit names
        """
        try:
            layer_2 = self.schema_data.get('layers', {}).get('layer_2_benefits', [])

            # Extract all benefit names
            benefit_names: Set[str] = set()
            for item in layer_2:
                benefit_name = item.get('benefit_name')
                if benefit_name:
                    benefit_names.add(benefit_name)

            # Convert to sorted list for consistency
            unique_benefits = sorted(list(benefit_names))

            print(f"\n{'=' * 80}")
            print(f"Layer 2: Benefits")
            print(f"{'=' * 80}")
            print(f"Total unique benefits: {len(unique_benefits)}")
            print(f"Sample benefits: {unique_benefits[:5]}")

            return KeyExtractionResult(
                status="success",
                layer_name="layer_2_benefits",
                unique_keys=unique_benefits,
                count=len(unique_benefits)
            )

        except Exception as e:
            print(f"✗ Error extracting benefit names: {e}")
            return KeyExtractionResult(
                status="error",
                layer_name="layer_2_benefits",
                error=str(e)
            )

    def extract_benefit_condition_pairs(self) -> KeyExtractionResult:
        """
        Extract unique (benefit_name, condition) pairs from Layer 3.

        Returns:
            KeyExtractionResult with list of unique (benefit_name, condition) tuples
        """
        try:
            layer_3 = self.schema_data.get('layers', {}).get('layer_3_benefit_specific_conditions', [])

            # Extract all (benefit_name, condition) pairs
            pairs: Set[Tuple[str, str]] = set()
            for item in layer_3:
                benefit_name = item.get('benefit_name')
                condition = item.get('condition')
                if benefit_name and condition:
                    pairs.add((benefit_name, condition))

            # Convert to sorted list for consistency
            unique_pairs = sorted(list(pairs))

            print(f"\n{'=' * 80}")
            print(f"Layer 3: Benefit-Specific Conditions")
            print(f"{'=' * 80}")
            print(f"Total unique (benefit, condition) pairs: {len(unique_pairs)}")
            print(f"Sample pairs: {unique_pairs[:3]}")

            return KeyExtractionResult(
                status="success",
                layer_name="layer_3_benefit_specific_conditions",
                unique_keys=unique_pairs,
                count=len(unique_pairs)
            )

        except Exception as e:
            print(f"✗ Error extracting benefit-condition pairs: {e}")
            return KeyExtractionResult(
                status="error",
                layer_name="layer_3_benefit_specific_conditions",
                error=str(e)
            )

    def extract_all(self) -> Dict[str, KeyExtractionResult]:
        """
        Extract all unique keys from all layers.

        Returns:
            Dictionary mapping layer name to KeyExtractionResult
        """
        if not self.schema_data:
            if not self.load_schema():
                return {}

        results = {
            "condition_names": self.extract_condition_names(),
            "benefit_names": self.extract_benefit_names(),
            "benefit_condition_pairs": self.extract_benefit_condition_pairs()
        }

        # Print summary
        print(f"\n{'=' * 80}")
        print(f"EXTRACTION SUMMARY")
        print(f"{'=' * 80}")
        for key, result in results.items():
            if result.status == "success":
                print(f"✓ {key}: {result.count} unique items")
            else:
                print(f"✗ {key}: ERROR - {result.error}")

        return results

    def save_results(self, results: Dict[str, KeyExtractionResult], output_dir: Path):
        """
        Save extraction results to JSON files.

        Args:
            results: Dictionary of extraction results
            output_dir: Output directory path
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 80}")
        print(f"SAVING RESULTS")
        print(f"{'=' * 80}")

        # Save condition names
        if "condition_names" in results and results["condition_names"].status == "success":
            output_file = output_dir / "condition_names.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results["condition_names"].unique_keys, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved: {output_file}")

        # Save benefit names
        if "benefit_names" in results and results["benefit_names"].status == "success":
            output_file = output_dir / "benefit_names.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results["benefit_names"].unique_keys, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved: {output_file}")

        # Save benefit-condition pairs
        if "benefit_condition_pairs" in results and results["benefit_condition_pairs"].status == "success":
            output_file = output_dir / "benefit_condition.json"
            # Convert tuples to lists for JSON serialization
            pairs_as_lists = [list(pair) for pair in results["benefit_condition_pairs"].unique_keys]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(pairs_as_lists, f, indent=2, ensure_ascii=False)
            print(f"✓ Saved: {output_file}")


def main():
    """Main function for testing."""
    # Set up paths
    base_dir = Path(__file__).resolve().parent.parent
    schema_path = base_dir / "data_schema" / "Taxonomy_Hackathon.json"
    output_dir = base_dir / "output"

    print(f"\n{'=' * 80}")
    print(f"STAGE 1: KEY EXTRACTION")
    print(f"{'=' * 80}")
    print(f"Schema: {schema_path}")
    print(f"Output: {output_dir}")

    # Extract keys
    extractor = KeyExtractor(schema_path)
    results = extractor.extract_all()

    # Save results
    extractor.save_results(results, output_dir)

    print(f"\n{'=' * 80}")
    print(f"STAGE 1 COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()

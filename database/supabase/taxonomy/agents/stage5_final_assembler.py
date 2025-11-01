"""
Stage 5: Final Taxonomy Assembler
Merges all three standardized layers into final taxonomy format (no LLM).

Produces the final taxonomy JSON matching the Taxonomy_Hackathon.json structure.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))

from entities.data_models import FinalTaxonomy


class FinalAssembler:
    """Assembles final taxonomy from standardized layers."""

    @staticmethod
    def assemble_final_taxonomy(
        condition_standardized: List[Dict[str, Any]],
        benefit_standardized: List[Dict[str, Any]],
        benefit_condition_standardized: List[Dict[str, Any]],
        taxonomy_name: str = "Travel Insurance Product Taxonomy"
    ) -> FinalTaxonomy:
        """
        Assemble final taxonomy from three standardized layers.

        Args:
            condition_standardized: Standardized general conditions
            benefit_standardized: Standardized benefits
            benefit_condition_standardized: Standardized benefit-specific conditions
            taxonomy_name: Name of the taxonomy

        Returns:
            FinalTaxonomy object
        """
        print(f"\n{'=' * 80}")
        print(f"Assembling Final Taxonomy")
        print(f"{'=' * 80}")

        # Extract product names from first layer (they should be consistent across all layers)
        all_products = set()
        for item in condition_standardized:
            all_products.update(item.get("products", {}).keys())
        for item in benefit_standardized:
            all_products.update(item.get("products", {}).keys())
        for item in benefit_condition_standardized:
            all_products.update(item.get("products", {}).keys())

        products = sorted(list(all_products))

        print(f"Products: {len(products)}")
        print(f"  - {', '.join(products)}")

        # Assemble layers
        layers = {
            "layer_1_general_conditions": condition_standardized,
            "layer_2_benefits": benefit_standardized,
            "layer_3_benefit_specific_conditions": benefit_condition_standardized
        }

        print(f"Layer 1 (General Conditions): {len(condition_standardized)} items")
        print(f"Layer 2 (Benefits): {len(benefit_standardized)} items")
        print(f"Layer 3 (Benefit-Specific Conditions): {len(benefit_condition_standardized)} items")

        # Create metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "pipeline": "Taxonomy Extraction Pipeline",
            "version": "1.0",
            "layers": {
                "layer_1_count": len(condition_standardized),
                "layer_2_count": len(benefit_standardized),
                "layer_3_count": len(benefit_condition_standardized)
            }
        }

        # Create FinalTaxonomy object
        final_taxonomy = FinalTaxonomy(
            taxonomy_name=taxonomy_name,
            products=products,
            layers=layers,
            metadata=metadata
        )

        return final_taxonomy

    @staticmethod
    def save_final_taxonomy(final_taxonomy: FinalTaxonomy, output_dir: Path):
        """
        Save final taxonomy to JSON file.

        Args:
            final_taxonomy: FinalTaxonomy object
            output_dir: Output directory
        """
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "final_value.json"

        print(f"\n{'=' * 80}")
        print(f"Saving Final Taxonomy")
        print(f"{'=' * 80}")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_taxonomy.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"✓ Saved: {output_file}")
        print(f"\nTaxonomy Statistics:")
        stats = final_taxonomy.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        return output_file


def main():
    """Main function for testing."""
    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / "output"

    print(f"\n{'=' * 80}")
    print(f"STAGE 5: FINAL TAXONOMY ASSEMBLY")
    print(f"{'=' * 80}")

    # Load Stage 4 outputs (standardized data)
    with open(output_dir / "condition_value_aggregated_standardized.json", 'r') as f:
        condition_standardized = json.load(f)

    with open(output_dir / "benefit_value_aggregated_standardized.json", 'r') as f:
        benefit_standardized = json.load(f)

    with open(output_dir / "benefit_value_pair_aggregated_standardized.json", 'r') as f:
        benefit_condition_standardized = json.load(f)

    # Assemble
    assembler = FinalAssembler()
    final_taxonomy = assembler.assemble_final_taxonomy(
        condition_standardized,
        benefit_standardized,
        benefit_condition_standardized
    )

    # Save
    assembler.save_final_taxonomy(final_taxonomy, output_dir)

    print(f"\n{'=' * 80}")
    print(f"STAGE 5 COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()

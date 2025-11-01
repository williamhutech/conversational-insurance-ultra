"""
Stage 3: Product Aggregator
Aggregates same condition/benefit across different products (no LLM).

Takes separate product extractions and merges them into unified structures
where each condition/benefit shows all products.
"""

import json
import sys
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.append(str(Path(__file__).resolve().parent.parent))


def load_stage1_outputs(output_dir: Path) -> Tuple[List[str], List[str], List[Tuple[str, str]]]:
    """
    Load Stage 1 outputs containing all unique keys.

    Returns:
        - condition_names: List of unique condition names (50 expected)
        - benefit_names: List of unique benefit names (61 expected)
        - benefit_conditions: List of (benefit_name, condition) tuples (139 expected)
    """
    output_dir = Path(output_dir).resolve()

    print(f"\n{'=' * 80}")
    print(f"Loading Stage 1 Outputs (Unique Keys)")
    print(f"{'=' * 80}")

    # Load condition names
    with open(output_dir / "condition_names.json", 'r') as f:
        condition_names = json.load(f)
    print(f"✓ Loaded {len(condition_names)} unique condition names")

    # Load benefit names
    with open(output_dir / "benefit_names.json", 'r') as f:
        benefit_names = json.load(f)
    print(f"✓ Loaded {len(benefit_names)} unique benefit names")

    # Load benefit-condition pairs
    with open(output_dir / "benefit_condition.json", 'r') as f:
        benefit_condition_list = json.load(f)
        # Convert to list of tuples
        benefit_conditions = [tuple(pair) for pair in benefit_condition_list]
    print(f"✓ Loaded {len(benefit_conditions)} unique benefit-condition pairs")

    return condition_names, benefit_names, benefit_conditions


def load_product_names(raw_text_dir: Path) -> List[str]:
    """
    Load product names from product_dict.pkl.

    Returns:
        List of product names (3 expected)
    """
    raw_text_dir = Path(raw_text_dir).resolve()
    product_dict_path = raw_text_dir / "product_dict.pkl"

    print(f"\n{'=' * 80}")
    print(f"Loading Product Names")
    print(f"{'=' * 80}")

    with open(product_dict_path, 'rb') as f:
        product_dict = pickle.load(f)

    product_names = list(product_dict.keys())
    print(f"✓ Loaded {len(product_names)} product names:")
    for name in product_names:
        print(f"  - {name}")

    return product_names


class ProductAggregator:
    """Aggregates extracted values across products."""

    @staticmethod
    def aggregate_conditions(
        condition_values: List[Dict[str, Any]],
        all_condition_names: List[str],
        product_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate general conditions across products.

        Input:
            - condition_values: List of condition dictionaries from Stage 2
            - all_condition_names: Complete list of condition names from Stage 1
            - product_names: List of all product names
        Output: List of aggregated conditions with all products (one entry per condition)
        """
        print(f"\n{'=' * 80}")
        print(f"Aggregating General Conditions")
        print(f"{'=' * 80}")
        print(f"Input Stage 2 values: {len(condition_values)}")
        print(f"Expected unique conditions from Stage 1: {len(all_condition_names)}")
        print(f"Products: {len(product_names)}")

        # Default empty product structure
        def default_product():
            return {
                "condition_exist": False,
                "original_text": "",
                "parameters": {}
            }

        # Initialize ALL conditions from Stage 1 with ALL products
        condition_groups = {}
        for condition_name in all_condition_names:
            condition_groups[condition_name] = {
                "condition": condition_name,
                "condition_type": None,  # Will be set when found in Stage 2 data
                "products": {product: default_product() for product in product_names}
            }

        # Now merge Stage 2 data into the initialized structure
        for item in condition_values:
            condition_name = item.get("condition")
            condition_type = item.get("condition_type")

            if not condition_name:
                continue

            # Update condition_type if found
            if condition_name in condition_groups and condition_type:
                condition_groups[condition_name]["condition_type"] = condition_type

            # Merge products from Stage 2
            products = item.get("products", {})
            for product_name, product_data in products.items():
                if condition_name in condition_groups and product_name in condition_groups[condition_name]["products"]:
                    condition_groups[condition_name]["products"][product_name] = product_data

        aggregated = list(condition_groups.values())
        print(f"Output aggregated conditions: {len(aggregated)} (should match {len(all_condition_names)})")

        return aggregated

    @staticmethod
    def aggregate_benefits(
        benefit_values: List[Dict[str, Any]],
        all_benefit_names: List[str],
        product_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate benefits across products.

        Input:
            - benefit_values: List of benefit dictionaries from Stage 2
            - all_benefit_names: Complete list of benefit names from Stage 1
            - product_names: List of all product names
        Output: List of aggregated benefits with all products (one entry per benefit)
        """
        print(f"\n{'=' * 80}")
        print(f"Aggregating Benefits")
        print(f"{'=' * 80}")
        print(f"Input Stage 2 values: {len(benefit_values)}")
        print(f"Expected unique benefits from Stage 1: {len(all_benefit_names)}")
        print(f"Products: {len(product_names)}")

        # Default empty product structure
        def default_product():
            return {
                "benefit_exist": False,
                "original_text": "",
                "parameters": {}
            }

        # Initialize ALL benefits from Stage 1 with ALL products
        benefit_groups = {}
        for benefit_name in all_benefit_names:
            benefit_groups[benefit_name] = {
                "benefit_name": benefit_name,
                "parameters": [],  # Will be set when found in Stage 2 data
                "products": {product: default_product() for product in product_names}
            }

        # Now merge Stage 2 data into the initialized structure
        for item in benefit_values:
            benefit_name = item.get("benefit_name")

            if not benefit_name:
                continue

            # Update parameters if found
            if benefit_name in benefit_groups:
                parameters = item.get("parameters", [])
                if parameters:
                    benefit_groups[benefit_name]["parameters"] = parameters

            # Merge products from Stage 2
            products = item.get("products", {})
            for product_name, product_data in products.items():
                if benefit_name in benefit_groups and product_name in benefit_groups[benefit_name]["products"]:
                    benefit_groups[benefit_name]["products"][product_name] = product_data

        aggregated = list(benefit_groups.values())
        print(f"Output aggregated benefits: {len(aggregated)} (should match {len(all_benefit_names)})")

        return aggregated

    @staticmethod
    def aggregate_benefit_conditions(
        benefit_condition_values: List[Dict[str, Any]],
        all_benefit_conditions: List[Tuple[str, str]],
        product_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate benefit-specific conditions across products.

        Input:
            - benefit_condition_values: List of benefit-condition dictionaries from Stage 2
            - all_benefit_conditions: Complete list of (benefit_name, condition) tuples from Stage 1
            - product_names: List of all product names
        Output: List of aggregated benefit-conditions with all products (one entry per pair)
        """
        print(f"\n{'=' * 80}")
        print(f"Aggregating Benefit-Specific Conditions")
        print(f"{'=' * 80}")
        print(f"Input Stage 2 values: {len(benefit_condition_values)}")
        print(f"Expected unique benefit-condition pairs from Stage 1: {len(all_benefit_conditions)}")
        print(f"Products: {len(product_names)}")

        # Default empty product structure
        def default_product():
            return {
                "condition_exist": False,
                "original_text": "",
                "parameters": {}
            }

        # Initialize ALL benefit-condition pairs from Stage 1 with ALL products
        bc_groups = {}
        for benefit_name, condition in all_benefit_conditions:
            key = (benefit_name, condition)
            bc_groups[key] = {
                "benefit_name": benefit_name,
                "condition": condition,
                "condition_type": None,  # Will be set when found in Stage 2 data
                "parameters": [],  # Will be set when found in Stage 2 data
                "products": {product: default_product() for product in product_names}
            }

        # Now merge Stage 2 data into the initialized structure
        for item in benefit_condition_values:
            benefit_name = item.get("benefit_name")
            condition = item.get("condition")
            condition_type = item.get("condition_type")

            if not benefit_name or not condition:
                continue

            # Create composite key
            key = (benefit_name, condition)

            # Update metadata if found
            if key in bc_groups:
                if condition_type:
                    bc_groups[key]["condition_type"] = condition_type
                parameters = item.get("parameters", [])
                if parameters:
                    bc_groups[key]["parameters"] = parameters

            # Merge products from Stage 2
            products = item.get("products", {})
            for product_name, product_data in products.items():
                if key in bc_groups and product_name in bc_groups[key]["products"]:
                    bc_groups[key]["products"][product_name] = product_data

        aggregated = list(bc_groups.values())
        print(f"Output aggregated benefit-conditions: {len(aggregated)} (should match {len(all_benefit_conditions)})")

        return aggregated

    @staticmethod
    def save_aggregated(
        aggregated_conditions: List[Dict[str, Any]],
        aggregated_benefits: List[Dict[str, Any]],
        aggregated_benefit_conditions: List[Dict[str, Any]],
        output_dir: Path
    ):
        """Save aggregated results to JSON files."""
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 80}")
        print(f"Saving Aggregated Results")
        print(f"{'=' * 80}")

        # Save conditions
        conditions_file = output_dir / "condition_value_aggregated.json"
        with open(conditions_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated_conditions, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved: {conditions_file}")

        # Save benefits
        benefits_file = output_dir / "benefit_value_aggregated.json"
        with open(benefits_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated_benefits, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved: {benefits_file}")

        # Save benefit-conditions
        bc_file = output_dir / "benefit_value_pair_aggregated.json"
        with open(bc_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated_benefit_conditions, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved: {bc_file}")


def main():
    """Main function for testing."""
    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / "output"
    raw_text_dir = base_dir / "raw_text"

    print(f"\n{'=' * 80}")
    print(f"STAGE 3: PRODUCT AGGREGATION")
    print(f"{'=' * 80}")

    # Load Stage 1 outputs (unique keys from schema)
    condition_names, benefit_names, benefit_conditions = load_stage1_outputs(output_dir)

    # Load product names
    product_names = load_product_names(raw_text_dir)

    # Load Stage 2 outputs (extracted values)
    print(f"\n{'=' * 80}")
    print(f"Loading Stage 2 Outputs (Extracted Values)")
    print(f"{'=' * 80}")

    with open(output_dir / "condition_values.json", 'r') as f:
        condition_values = json.load(f)
    print(f"✓ Loaded {len(condition_values)} condition value entries")

    with open(output_dir / "benefit_values.json", 'r') as f:
        benefit_values = json.load(f)
    print(f"✓ Loaded {len(benefit_values)} benefit value entries")

    with open(output_dir / "benefit_condition_values.json", 'r') as f:
        benefit_condition_values = json.load(f)
    print(f"✓ Loaded {len(benefit_condition_values)} benefit-condition value entries")

    # Aggregate with complete keys from Stage 1
    aggregator = ProductAggregator()

    aggregated_conditions = aggregator.aggregate_conditions(
        condition_values,
        condition_names,
        product_names
    )
    aggregated_benefits = aggregator.aggregate_benefits(
        benefit_values,
        benefit_names,
        product_names
    )
    aggregated_bc = aggregator.aggregate_benefit_conditions(
        benefit_condition_values,
        benefit_conditions,
        product_names
    )

    # Save
    aggregator.save_aggregated(
        aggregated_conditions,
        aggregated_benefits,
        aggregated_bc,
        output_dir
    )

    print(f"\n{'=' * 80}")
    print(f"STAGE 3 COMPLETE")
    print(f"{'=' * 80}")
    print(f"\nFinal Statistics:")
    print(f"  • Conditions: {len(aggregated_conditions)}/{len(condition_names)} (expected {len(condition_names)})")
    print(f"  • Benefits: {len(aggregated_benefits)}/{len(benefit_names)} (expected {len(benefit_names)})")
    print(f"  • Benefit-Conditions: {len(aggregated_bc)}/{len(benefit_conditions)} (expected {len(benefit_conditions)})")
    print(f"  • Products per entry: {len(product_names)}")
    print()


if __name__ == "__main__":
    main()

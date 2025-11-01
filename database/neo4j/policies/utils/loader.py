"""
ETL Pipeline for Loading Travel Insurance Taxonomy into Supabase.
Reads final_value.json, generates dual embeddings, and loads into PostgreSQL.
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from supabase import create_client, Client
from datetime import datetime

from .config import TaxonomyLoaderConfig, load_config
from .models import (
    TravelInsuranceTaxonomy,
    ProductDB,
    GeneralConditionDB,
    BenefitDB,
    BenefitConditionDB,
)
from .embedding_service import EmbeddingService


class TaxonomyLoader:
    """Main ETL pipeline for loading taxonomy data with dual embeddings"""

    def __init__(self, config: TaxonomyLoaderConfig):
        self.config = config
        self.supabase: Client = create_client(
            config.supabase_url,
            config.supabase_service_key
        )
        self.embedding_service = EmbeddingService(config)
        self.product_id_map: Dict[str, int] = {}

    async def load_taxonomy(self) -> Dict[str, int]:
        """
        Main entry point: Load entire taxonomy into Supabase.

        Returns:
            Statistics dict with counts of loaded records
        """
        print("=" * 80)
        print("🚀 TRAVEL INSURANCE TAXONOMY LOADER")
        print("=" * 80)

        # Load and validate JSON
        print("\n📖 Step 1: Loading JSON data...")
        taxonomy = self._load_json()
        print(f"✓ Loaded taxonomy: {taxonomy.taxonomy_name}")
        print(f"  - Products: {len(taxonomy.products)}")
        print(f"  - Layer 1 (General Conditions): {len(taxonomy.layers['layer_1_general_conditions'])}")
        print(f"  - Layer 2 (Benefits): {len(taxonomy.layers['layer_2_benefits'])}")
        print(f"  - Layer 3 (Benefit Conditions): {len(taxonomy.layers['layer_3_benefit_specific_conditions'])}")

        stats = {
            "products": 0,
            "general_conditions": 0,
            "benefits": 0,
            "benefit_conditions": 0,
            "embeddings_generated": 0,
        }

        try:
            # Step 2: Load products
            print("\n📦 Step 2: Loading products...")
            await self._load_products(taxonomy.products)
            stats["products"] = len(self.product_id_map)
            print(f"✓ Loaded {stats['products']} products")

            # Step 3: Load Layer 1 (General Conditions)
            print("\n🔒 Step 3: Loading Layer 1 (General Conditions)...")
            layer1_count = await self._load_general_conditions(
                taxonomy.layers["layer_1_general_conditions"]
            )
            stats["general_conditions"] = layer1_count
            print(f"✓ Loaded {layer1_count} general condition records")

            # Step 4: Load Layer 2 (Benefits)
            print("\n💰 Step 4: Loading Layer 2 (Benefits)...")
            layer2_count = await self._load_benefits(
                taxonomy.layers["layer_2_benefits"]
            )
            stats["benefits"] = layer2_count
            print(f"✓ Loaded {layer2_count} benefit records")

            # Step 5: Load Layer 3 (Benefit-Specific Conditions)
            print("\n📋 Step 5: Loading Layer 3 (Benefit Conditions)...")
            layer3_count = await self._load_benefit_conditions(
                taxonomy.layers["layer_3_benefit_specific_conditions"]
            )
            stats["benefit_conditions"] = layer3_count
            print(f"✓ Loaded {layer3_count} benefit condition records")

            # Calculate embedding stats
            stats["embeddings_generated"] = (
                stats["general_conditions"] * 2 +
                stats["benefits"] * 2 +
                stats["benefit_conditions"] * 2
            )

            print("\n" + "=" * 80)
            print("✅ LOADING COMPLETE!")
            print("=" * 80)
            print(f"📊 Final Statistics:")
            print(f"  - Products: {stats['products']}")
            print(f"  - General Conditions: {stats['general_conditions']}")
            print(f"  - Benefits: {stats['benefits']}")
            print(f"  - Benefit Conditions: {stats['benefit_conditions']}")
            print(f"  - Total Records: {sum([stats['general_conditions'], stats['benefits'], stats['benefit_conditions']])}")
            print(f"  - Embeddings Generated: {stats['embeddings_generated']}")
            print("=" * 80)

            return stats

        finally:
            await self.embedding_service.close()

    def _load_json(self) -> TravelInsuranceTaxonomy:
        """Load and validate JSON file"""
        json_path = Path(self.config.json_file_path)

        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate with Pydantic
        taxonomy = TravelInsuranceTaxonomy(**data)
        return taxonomy

    async def _load_products(self, products: List[str]):
        """Load products and build ID mapping"""
        for product_name in products:
            # Try to insert, or get existing
            result = self.supabase.table("products").upsert(
                {"product_name": product_name},
                on_conflict="product_name"
            ).execute()

            if result.data:
                product_id = result.data[0]["id"]
                self.product_id_map[product_name] = product_id

    async def _load_general_conditions(self, conditions: List[Any]) -> int:
        """Load Layer 1: General Conditions with dual embeddings"""
        total_records = 0

        for condition in conditions:
            condition_name = condition.condition
            condition_type = condition.condition_type

            # Process each product variant
            for product_name, product_data in condition.products.items():
                if not product_data.condition_exist:
                    continue  # Skip non-existent conditions

                product_id = self.product_id_map.get(product_name)
                if not product_id:
                    print(f"⚠️  Product not found: {product_name}")
                    continue

                # Generate dual embeddings
                normalized_emb, original_emb = None, None
                if self.config.generate_embeddings:
                    normalized_emb, original_emb = await self.embedding_service.generate_dual_embeddings_for_condition(
                        condition_name=condition_name,
                        condition_type=condition_type,
                        parameters=product_data.parameters,
                        original_text=product_data.original_text
                    )

                # Prepare record
                record = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "condition_name": condition_name,
                    "condition_type": condition_type,
                    "condition_exist": product_data.condition_exist,
                    "original_text": product_data.original_text,
                    "parameters": product_data.parameters,
                    "normalized_embedding": normalized_emb,
                    "original_embedding": original_emb,
                }

                # Insert into database
                self.supabase.table("general_conditions").upsert(
                    record,
                    on_conflict="product_name,condition_name"
                ).execute()

                total_records += 1

                if self.config.verbose and total_records % 10 == 0:
                    print(f"  ... {total_records} records processed")

        return total_records

    async def _load_benefits(self, benefits: List[Any]) -> int:
        """Load Layer 2: Benefits with dual embeddings"""
        total_records = 0

        for benefit in benefits:
            benefit_name = benefit.benefit_name

            # Process each product variant
            for product_name, product_data in benefit.products.items():
                if not product_data.benefit_exist:
                    continue  # Skip non-existent benefits

                product_id = self.product_id_map.get(product_name)
                if not product_id:
                    print(f"⚠️  Product not found: {product_name}")
                    continue

                # FIXED: Extract coverage_limit and sub_limits from nested parameters dict
                # In the JSON, these fields are nested inside product_data.parameters,
                # not at the top level of product_data
                raw_coverage_limit = product_data.parameters.get("coverage_limit")
                sub_limits = product_data.parameters.get("sub_limits", {})

                # FIXED: original_text might not exist in the JSON for benefits
                # Use getattr with None default to handle missing field
                original_text = getattr(product_data, "original_text", None)

                # Generate dual embeddings
                # IMPORTANT: Pass RAW coverage_limit to embedding service (not normalized)
                # The embedding service's format_coverage_limit expects raw values
                normalized_emb, original_emb = None, None
                if self.config.generate_embeddings:
                    normalized_emb, original_emb = await self.embedding_service.generate_dual_embeddings_for_benefit(
                        benefit_name=benefit_name,
                        coverage_limit=raw_coverage_limit,  # Pass raw value, not normalized
                        sub_limits=sub_limits,
                        parameters=product_data.parameters,
                        original_text=original_text
                    )

                # Convert coverage_limit to JSONB-compatible format for database storage
                coverage_limit_normalized = self._normalize_coverage_limit(raw_coverage_limit)

                # Prepare record
                record = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "benefit_name": benefit_name,
                    "benefit_exist": product_data.benefit_exist,
                    "coverage_limit": coverage_limit_normalized,
                    "sub_limits": sub_limits,
                    "parameters": product_data.parameters,
                    "original_text": original_text,
                    "normalized_embedding": normalized_emb,
                    "original_embedding": original_emb,
                }

                # Insert into database
                self.supabase.table("benefits").upsert(
                    record,
                    on_conflict="product_name,benefit_name"
                ).execute()

                total_records += 1

                if self.config.verbose and total_records % 10 == 0:
                    print(f"  ... {total_records} records processed")

        return total_records

    async def _load_benefit_conditions(self, benefit_conditions: List[Any]) -> int:
        """Load Layer 3: Benefit-Specific Conditions with dual embeddings"""
        total_records = 0

        for benefit_condition in benefit_conditions:
            benefit_name = benefit_condition.benefit_name
            condition_name = benefit_condition.condition
            condition_type = benefit_condition.condition_type

            # Process each product variant
            for product_name, product_data in benefit_condition.products.items():
                if not product_data.condition_exist:
                    continue  # Skip non-existent conditions

                product_id = self.product_id_map.get(product_name)
                if not product_id:
                    print(f"⚠️  Product not found: {product_name}")
                    continue

                # Generate dual embeddings
                normalized_emb, original_emb = None, None
                if self.config.generate_embeddings:
                    normalized_emb, original_emb = await self.embedding_service.generate_dual_embeddings_for_benefit_condition(
                        benefit_name=benefit_name,
                        condition_name=condition_name,
                        condition_type=condition_type,
                        parameters=product_data.parameters,
                        original_text=product_data.original_text
                    )

                # Prepare record
                record = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "benefit_name": benefit_name,
                    "condition_name": condition_name,
                    "condition_type": condition_type,
                    "condition_exist": product_data.condition_exist,
                    "original_text": product_data.original_text,
                    "parameters": product_data.parameters,
                    "normalized_embedding": normalized_emb,
                    "original_embedding": original_emb,
                }

                # Insert into database
                self.supabase.table("benefit_conditions").upsert(
                    record,
                    on_conflict="product_name,benefit_name,condition_name"
                ).execute()

                total_records += 1

                if self.config.verbose and total_records % 10 == 0:
                    print(f"  ... {total_records} records processed")

        return total_records

    def _normalize_coverage_limit(self, coverage_limit: Any) -> Optional[Dict[str, Any]]:
        """Normalize coverage_limit to JSONB-compatible format"""
        if coverage_limit is None:
            return None

        if isinstance(coverage_limit, (int, float)):
            return {"value": coverage_limit, "type": "numeric"}

        if isinstance(coverage_limit, dict):
            return {"value": coverage_limit, "type": "plan_tiered"}

        if isinstance(coverage_limit, bool):
            return {"value": coverage_limit, "type": "boolean"}

        return {"value": str(coverage_limit), "type": "other"}


# ============================================================================
# CLI INTERFACE
# ============================================================================

async def main():
    """Main entry point for CLI execution"""
    try:
        # Load configuration
        config = load_config()

        # Create loader
        loader = TaxonomyLoader(config)

        # Run ETL pipeline
        stats = await loader.load_taxonomy()

        print(f"\n✨ Success! Data loaded into Supabase at {config.supabase_url}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())

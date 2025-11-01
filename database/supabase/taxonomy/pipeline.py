"""
Taxonomy Extraction Pipeline
Main orchestrator for the 5-stage taxonomy extraction and aggregation workflow.

Stages:
1. Key Extraction - Extract unique keys from schema (no LLM)
2. Value Extraction - Extract and validate values with LLMs
3. Product Aggregation - Merge same condition/benefit across products (no LLM)
4. Parameter Standardization - Normalize parameters with LLMs
5. Final Assembly - Merge all layers into final taxonomy (no LLM)
"""

import yaml
import pickle
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add current directory to path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from utils.api_client import APIClient
from utils.file_utils import load_json, save_json, load_pickle, save_pickle
from entities.data_models import PipelineMetadata, StageMetadata

# Import agents
from agents.stage1_key_extractor import KeyExtractor
from agents.stage3_aggregator import ProductAggregator
from agents.stage5_final_assembler import FinalAssembler


# ============================================================================
# Pipeline Configuration
# ============================================================================

class PipelineConfig:
    """Centralized configuration management."""

    def __init__(self, base_dir: Path):
        """
        Initialize pipeline configuration.

        Args:
            base_dir: Base directory of the taxonomy pipeline
        """
        self.base_dir = Path(base_dir).resolve()
        self.config_dir = self.base_dir / "config"

        # Load all configs
        self.models_config = self._load_yaml(self.config_dir / "models.yaml")
        self.pipeline_config = self._load_yaml(self.config_dir / "pipeline.yaml")
        self.generation_config = self._load_yaml(self.config_dir / "generation.yaml")

    def _load_yaml(self, filepath: Path) -> Dict:
        """Load YAML configuration file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_api_client(self, model_key: str) -> APIClient:
        """
        Get configured API client for a specific model.

        Args:
            model_key: Model key from models.yaml (e.g., 'condition_extractor')

        Returns:
            Configured APIClient
        """
        api_config = self.models_config["api"]
        model_config = self.models_config["models"][model_key]

        return APIClient(
            api_url=api_config["url"],
            api_key=api_config["key"],
            model_name=model_config["name"],
            use_responses_api=model_config.get("use_responses_api", False),
            retry_total=self.generation_config["api"]["retry"]["total"],
            backoff_factor=self.generation_config["api"]["retry"]["backoff_factor"]
        )

    def is_stage_enabled(self, stage_name: str) -> bool:
        """Check if a stage is enabled."""
        return self.pipeline_config["pipeline"]["stages"][stage_name]["enabled"]

    def get_stage_config(self, stage_name: str) -> Dict:
        """Get configuration for a specific stage."""
        return self.pipeline_config["pipeline"]["stages"][stage_name]


# ============================================================================
# Main Pipeline Orchestrator
# ============================================================================

class TaxonomyExtractionPipeline:
    """Main pipeline orchestrator."""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize pipeline.

        Args:
            base_dir: Base directory (defaults to script location)
        """
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent

        self.base_dir = Path(base_dir).resolve()
        self.config = PipelineConfig(self.base_dir)

        # Set up paths
        self.data_schema_dir = self.base_dir / "data_schema"
        self.raw_text_dir = self.base_dir / "raw_text"
        self.output_dir = self.base_dir / self.config.pipeline_config["pipeline"]["paths"]["output_dir"]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Pipeline metadata
        self.metadata = PipelineMetadata()
        self.stage_results = {}  # In-memory fallback for stage outputs

        print(f"\n{'=' * 80}")
        print(f"TAXONOMY EXTRACTION PIPELINE")
        print(f"{'=' * 80}")
        print(f"Base directory: {self.base_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"{'=' * 80}\n")

    # ========================================================================
    # Stage 1: Key Extraction
    # ========================================================================

    def run_stage_1_key_extraction(self):
        """Stage 1: Extract unique keys from taxonomy schema."""
        if not self.config.is_stage_enabled("stage_1_key_extraction"):
            print("Stage 1 disabled, skipping...")
            return

        stage_start = datetime.now()
        stage_metadata = StageMetadata(
            stage_name="Key Extraction",
            stage_number=1,
            started_at=stage_start.isoformat()
        )

        print(f"\n{'=' * 80}")
        print(f"STAGE 1: KEY EXTRACTION")
        print(f"{'=' * 80}")

        try:
            # Load schema
            stage_config = self.config.get_stage_config("stage_1_key_extraction")
            schema_path = self.base_dir / stage_config["input_files"]["schema"]

            # Extract keys
            extractor = KeyExtractor(schema_path)
            results = extractor.extract_all()

            # Save results
            extractor.save_results(results, self.output_dir)

            # Update metadata
            stage_metadata.completed_at = datetime.now().isoformat()
            stage_metadata.duration_seconds = (datetime.now() - stage_start).total_seconds()
            stage_metadata.status = "completed"
            stage_metadata.statistics = {
                "conditions": results["condition_names"].count,
                "benefits": results["benefit_names"].count,
                "benefit_condition_pairs": results["benefit_condition_pairs"].count
            }

            # Store in memory
            self.stage_results["stage_1"] = results

            print(f"\n✓ Stage 1 complete ({stage_metadata.duration_seconds:.2f}s)")

        except Exception as e:
            stage_metadata.status = "failed"
            stage_metadata.errors.append(str(e))
            print(f"\n✗ Stage 1 failed: {e}")
            raise

        finally:
            self.metadata.stages.append(stage_metadata)

    # ========================================================================
    # Stage 2: Value Extraction (Simplified - requires full agent implementations)
    # ========================================================================

    def run_stage_2_value_extraction(self):
        """Stage 2: Extract and validate values with LLMs."""
        if not self.config.is_stage_enabled("stage_2_value_extraction"):
            print("Stage 2 disabled, skipping...")
            return

        stage_start = datetime.now()
        stage_metadata = StageMetadata(
            stage_name="Value Extraction & Validation",
            stage_number=2,
            started_at=stage_start.isoformat()
        )

        print(f"\n{'=' * 80}")
        print(f"STAGE 2: VALUE EXTRACTION & VALIDATION")
        print(f"{'=' * 80}")

        try:
            # Import Stage 2 agents
            from agents.stage2_condition_extractor import ConditionExtractor, BatchConditionExtractor
            from agents.stage2_condition_judger import ConditionJudger, BatchConditionJudger
            from agents.stage2_benefit_extractor import BenefitExtractor, BatchBenefitExtractor
            from agents.stage2_benefit_judger import BenefitJudger, BatchBenefitJudger
            from agents.stage2_benefit_condition_extractor import BenefitConditionExtractor, BatchBenefitConditionExtractor
            from agents.stage2_benefit_condition_judger import BenefitConditionJudger, BatchBenefitConditionJudger

            # Load Stage 1 outputs
            stage_config = self.config.get_stage_config("stage_2_value_extraction")
            condition_names = load_json(self.output_dir / stage_config["input_files"]["condition_names"])
            benefit_names = load_json(self.output_dir / stage_config["input_files"]["benefit_names"])
            benefit_condition_data = load_json(self.output_dir / stage_config["input_files"]["benefit_condition_pairs"])

            # Convert benefit_condition_pairs to list of tuples (data is [[benefit, condition], ...])
            benefit_condition_pairs = [tuple(item) for item in benefit_condition_data]

            # Load product dictionary
            product_dict_path = self.raw_text_dir / "product_dict.pkl"
            product_dict = load_pickle(product_dict_path)

            # Get concurrency settings
            max_workers = self.config.generation_config["concurrency"]["max_workers"]
            batch_size = self.config.generation_config["batch_sizes"]["condition_extraction"]

            # Initialize statistics
            stage_stats = {}

            # Process each layer
            layers = stage_config["layers"]

            for layer_config in layers:
                layer_name = layer_config["name"]
                print(f"\n{'=' * 80}")
                print(f"Processing Layer: {layer_name}")
                print(f"{'=' * 80}")

                # Get API clients
                extractor_model = layer_config["extractor"]
                judger_model = layer_config["judger"]
                api_client_extractor = self.config.get_api_client(extractor_model)
                api_client_judger = self.config.get_api_client(judger_model)

                # Initialize agents based on layer
                if layer_name == "general_conditions":
                    extractor = ConditionExtractor(api_client_extractor, condition_names)
                    batch_extractor = BatchConditionExtractor(extractor, self.output_dir)
                    judger = ConditionJudger(api_client_judger, condition_names)
                    batch_judger = BatchConditionJudger(judger, self.output_dir)

                elif layer_name == "benefits":
                    extractor = BenefitExtractor(api_client_extractor, benefit_names)
                    batch_extractor = BatchBenefitExtractor(extractor, self.output_dir)
                    judger = BenefitJudger(api_client_judger, benefit_names)
                    batch_judger = BatchBenefitJudger(judger, self.output_dir)

                elif layer_name == "benefit_specific_conditions":
                    extractor = BenefitConditionExtractor(api_client_extractor, benefit_condition_pairs)
                    batch_extractor = BatchBenefitConditionExtractor(extractor, self.output_dir)
                    judger = BenefitConditionJudger(api_client_judger, benefit_condition_pairs)
                    batch_judger = BatchBenefitConditionJudger(judger, self.output_dir)

                # Run extraction (returns Dict[str, ExtractionResult])
                print(f"\n--- Extraction Phase ---")
                extraction_results = batch_extractor.extract_from_product_dict(
                    product_dict,
                    max_workers=max_workers,
                    batch_size=batch_size
                )

                # Run judgment (returns Dict[str, JudgmentResult])
                print(f"\n--- Judgment Phase ---")
                judgment_results = batch_judger.judge_extractions(
                    extraction_results,
                    max_workers=max_workers,
                    batch_size=batch_size
                )

                # Save results
                output_filename = stage_config["output_files"][
                    "condition_values" if layer_name == "general_conditions"
                    else "benefit_values" if layer_name == "benefits"
                    else "benefit_condition_values"
                ]
                output_path = self.output_dir / output_filename

                # Convert results to JSON-serializable format (as a list)
                # Extract actual condition/benefit objects from judgment validations
                results_to_save = []
                extraction_errors = []  # Track errors for debugging

                for result_id, judgment in judgment_results.items():
                    if judgment.status == "success" and judgment.final_value:
                        # Extract actual items from validations
                        validations = judgment.final_value.get("validations", [])
                        for validation in validations:
                            if validation.get("approve") and validation.get("final_value"):
                                # Add the approved condition/benefit object
                                results_to_save.append(validation["final_value"])
                    else:
                        # Track error for debugging
                        error_record = {
                            "result_id": result_id,
                            "status": judgment.status,
                            "product_name": judgment.product_name,
                            "text_index": judgment.text_index,
                            "error_details": judgment.error_details or "Unknown error",
                            "processing_time": judgment.processing_time
                        }
                        extraction_errors.append(error_record)

                save_json(results_to_save, output_path)

                # Also save errors to a separate file for debugging
                if extraction_errors:
                    error_filename = output_filename.replace(".json", "_errors.json")
                    error_path = self.output_dir / error_filename
                    save_json(extraction_errors, error_path)
                    print(f"  - Errors saved to: {error_path}")

                # Update statistics
                successful = sum(1 for j in judgment_results.values() if j.status == "success")
                approved = sum(1 for j in judgment_results.values() if j.approve)
                stage_stats[layer_name] = {
                    "total_text_chunks": len(judgment_results),
                    "successful_extractions": successful,
                    "approved_chunks": approved,
                    "total_items_extracted": len(results_to_save),
                    "extraction_errors": len(extraction_errors),
                    "output_file": str(output_path)
                }

                print(f"\n✓ Layer complete: {layer_name}")
                print(f"  - Text chunks processed: {len(judgment_results)}")
                print(f"  - Successful extractions: {successful}")
                print(f"  - Approved chunks: {approved}")
                print(f"  - Total items extracted: {len(results_to_save)}")
                print(f"  - Extraction errors: {len(extraction_errors)}")
                print(f"  - Output: {output_path}")

            # Update metadata
            stage_metadata.completed_at = datetime.now().isoformat()
            stage_metadata.duration_seconds = (datetime.now() - stage_start).total_seconds()
            stage_metadata.status = "completed"
            stage_metadata.statistics = stage_stats

            print(f"\n✓ Stage 2 complete ({stage_metadata.duration_seconds:.2f}s)")

        except Exception as e:
            stage_metadata.status = "failed"
            stage_metadata.errors.append(str(e))
            print(f"\n✗ Stage 2 failed: {e}")
            raise

        finally:
            self.metadata.stages.append(stage_metadata)

    # ========================================================================
    # Stage 3: Product Aggregation
    # ========================================================================

    def run_stage_3_product_aggregation(self):
        """Stage 3: Aggregate same condition/benefit across products."""
        if not self.config.is_stage_enabled("stage_3_product_aggregation"):
            print("Stage 3 disabled, skipping...")
            return

        stage_start = datetime.now()
        stage_metadata = StageMetadata(
            stage_name="Product Aggregation",
            stage_number=3,
            started_at=stage_start.isoformat()
        )

        print(f"\n{'=' * 80}")
        print(f"STAGE 3: PRODUCT AGGREGATION")
        print(f"{'=' * 80}")

        try:
            # Load Stage 1 outputs (unique keys from schema)
            from agents.stage3_aggregator import load_stage1_outputs, load_product_names

            condition_names, benefit_names, benefit_conditions = load_stage1_outputs(self.output_dir)
            product_names = load_product_names(self.raw_text_dir)

            # Load Stage 2 outputs (extracted values)
            stage_config = self.config.get_stage_config("stage_3_product_aggregation")

            condition_values = load_json(self.output_dir / stage_config["input_files"]["condition_values"])
            benefit_values = load_json(self.output_dir / stage_config["input_files"]["benefit_values"])
            benefit_condition_values = load_json(self.output_dir / stage_config["input_files"]["benefit_condition_values"])

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
                self.output_dir
            )

            # Update metadata
            stage_metadata.completed_at = datetime.now().isoformat()
            stage_metadata.duration_seconds = (datetime.now() - stage_start).total_seconds()
            stage_metadata.status = "completed"
            stage_metadata.statistics = {
                "expected_conditions": len(condition_names),
                "conditions_aggregated": len(aggregated_conditions),
                "expected_benefits": len(benefit_names),
                "benefits_aggregated": len(aggregated_benefits),
                "expected_benefit_conditions": len(benefit_conditions),
                "benefit_conditions_aggregated": len(aggregated_bc),
                "products_per_entry": len(product_names)
            }

            print(f"\n✓ Stage 3 complete ({stage_metadata.duration_seconds:.2f}s)")
            print(f"\nAggregation Coverage:")
            print(f"  • Conditions: {len(aggregated_conditions)}/{len(condition_names)}")
            print(f"  • Benefits: {len(aggregated_benefits)}/{len(benefit_names)}")
            print(f"  • Benefit-Conditions: {len(aggregated_bc)}/{len(benefit_conditions)}")

        except Exception as e:
            stage_metadata.status = "failed"
            stage_metadata.errors.append(str(e))
            print(f"\n✗ Stage 3 failed: {e}")
            raise

        finally:
            self.metadata.stages.append(stage_metadata)

    # ========================================================================
    # Stage 4: Parameter Standardization
    # ========================================================================

    def run_stage_4_standardization(self):
        """Stage 4: Standardize parameters across products with LLMs."""
        if not self.config.is_stage_enabled("stage_4_standardization"):
            print("Stage 4 disabled, skipping...")
            return

        stage_start = datetime.now()
        stage_metadata = StageMetadata(
            stage_name="Parameter Standardization",
            stage_number=4,
            started_at=stage_start.isoformat()
        )

        print(f"\n{'=' * 80}")
        print(f"STAGE 4: PARAMETER STANDARDIZATION")
        print(f"{'=' * 80}")

        try:
            # Import Stage 4 standardizer agents
            from agents.stage4_condition_standardizer import ConditionStandardizer, BatchConditionStandardizer
            from agents.stage4_benefit_standardizer import BenefitStandardizer, BatchBenefitStandardizer
            from agents.stage4_benefit_condition_standardizer import BenefitConditionStandardizer, BatchBenefitConditionStandardizer

            # Load Stage 3 aggregated outputs
            stage_config = self.config.get_stage_config("stage_4_standardization")

            condition_aggregated = load_json(self.output_dir / stage_config["input_files"]["condition_aggregated"])
            benefit_aggregated = load_json(self.output_dir / stage_config["input_files"]["benefit_aggregated"])
            benefit_condition_aggregated = load_json(self.output_dir / stage_config["input_files"]["benefit_condition_aggregated"])

            # Get concurrency settings
            max_workers = self.config.generation_config["concurrency"]["max_workers"]
            batch_size = self.config.generation_config["batch_sizes"]["condition_extraction"]

            # Initialize statistics
            stage_stats = {}

            # Process each layer
            layers = stage_config["layers"]

            for layer_config in layers:
                layer_name = layer_config["name"]
                print(f"\n{'=' * 80}")
                print(f"Processing Layer: {layer_name}")
                print(f"{'=' * 80}")

                # Get API client for standardizer
                standardizer_model = layer_config["standardizer"]
                api_client = self.config.get_api_client(standardizer_model)

                # Initialize agents based on layer
                if layer_name == "general_conditions":
                    standardizer = ConditionStandardizer(api_client)
                    batch_standardizer = BatchConditionStandardizer(standardizer, self.output_dir)
                    aggregated_data = condition_aggregated
                    output_filename = stage_config["output_files"]["condition_standardized"]

                elif layer_name == "benefits":
                    standardizer = BenefitStandardizer(api_client)
                    batch_standardizer = BatchBenefitStandardizer(standardizer, self.output_dir)
                    aggregated_data = benefit_aggregated
                    output_filename = stage_config["output_files"]["benefit_standardized"]

                elif layer_name == "benefit_specific_conditions":
                    standardizer = BenefitConditionStandardizer(api_client)
                    batch_standardizer = BatchBenefitConditionStandardizer(standardizer, self.output_dir)
                    aggregated_data = benefit_condition_aggregated
                    output_filename = stage_config["output_files"]["benefit_condition_standardized"]

                # Run standardization
                print(f"\n--- Standardization Phase ---")
                if layer_name == "general_conditions":
                    standardized_results = batch_standardizer.standardize_all_conditions(
                        aggregated_data,
                        max_workers=max_workers,
                        batch_size=batch_size
                    )
                elif layer_name == "benefits":
                    standardized_results = batch_standardizer.standardize_all_benefits(
                        aggregated_data,
                        max_workers=max_workers,
                        batch_size=batch_size
                    )
                elif layer_name == "benefit_specific_conditions":
                    standardized_results = batch_standardizer.standardize_all_benefit_conditions(
                        aggregated_data,
                        max_workers=max_workers,
                        batch_size=batch_size
                    )

                # Save standardized results
                output_path = self.output_dir / output_filename
                save_json(standardized_results, output_path)

                # Update statistics
                stage_stats[layer_name] = {
                    "total_items": len(aggregated_data),
                    "standardized_items": len(standardized_results),
                    "output_file": str(output_path)
                }

                print(f"\n✓ Layer complete: {layer_name}")
                print(f"  - Items processed: {len(aggregated_data)}")
                print(f"  - Items standardized: {len(standardized_results)}")
                print(f"  - Output: {output_path}")

            # Update metadata
            stage_metadata.completed_at = datetime.now().isoformat()
            stage_metadata.duration_seconds = (datetime.now() - stage_start).total_seconds()
            stage_metadata.status = "completed"
            stage_metadata.statistics = stage_stats

            print(f"\n✓ Stage 4 complete ({stage_metadata.duration_seconds:.2f}s)")

        except Exception as e:
            stage_metadata.status = "failed"
            stage_metadata.errors.append(str(e))
            print(f"\n✗ Stage 4 failed: {e}")
            raise

        finally:
            self.metadata.stages.append(stage_metadata)

    # ========================================================================
    # Stage 5: Final Assembly
    # ========================================================================

    def run_stage_5_final_assembly(self):
        """Stage 5: Merge all layers into final taxonomy."""
        if not self.config.is_stage_enabled("stage_5_final_assembly"):
            print("Stage 5 disabled, skipping...")
            return

        stage_start = datetime.now()
        stage_metadata = StageMetadata(
            stage_name="Final Assembly",
            stage_number=5,
            started_at=stage_start.isoformat()
        )

        print(f"\n{'=' * 80}")
        print(f"STAGE 5: FINAL TAXONOMY ASSEMBLY")
        print(f"{'=' * 80}")

        try:
            # Load Stage 4 outputs (standardized data)
            stage_config = self.config.get_stage_config("stage_5_final_assembly")

            condition_standardized = load_json(
                self.output_dir / stage_config["input_files"]["condition_standardized"]
            )
            benefit_standardized = load_json(
                self.output_dir / stage_config["input_files"]["benefit_standardized"]
            )
            benefit_condition_standardized = load_json(
                self.output_dir / stage_config["input_files"]["benefit_condition_standardized"]
            )

            # Assemble
            assembler = FinalAssembler()
            final_taxonomy = assembler.assemble_final_taxonomy(
                condition_standardized,
                benefit_standardized,
                benefit_condition_standardized
            )

            # Save
            assembler.save_final_taxonomy(final_taxonomy, self.output_dir)

            # Update metadata
            stage_metadata.completed_at = datetime.now().isoformat()
            stage_metadata.duration_seconds = (datetime.now() - stage_start).total_seconds()
            stage_metadata.status = "completed"
            stage_metadata.statistics = final_taxonomy.get_stats()

            print(f"\n✓ Stage 5 complete ({stage_metadata.duration_seconds:.2f}s)")

        except Exception as e:
            stage_metadata.status = "failed"
            stage_metadata.errors.append(str(e))
            print(f"\n✗ Stage 5 failed: {e}")
            raise

        finally:
            self.metadata.stages.append(stage_metadata)

    # ========================================================================
    # Pipeline Execution
    # ========================================================================

    def run_pipeline(self):
        """Run the complete pipeline."""
        pipeline_start = datetime.now()

        print(f"\n{'=' * 80}")
        print(f"STARTING TAXONOMY EXTRACTION PIPELINE")
        print(f"{'=' * 80}")
        print(f"Started at: {pipeline_start.isoformat()}\n")

        try:
            # Run all stages
            self.run_stage_1_key_extraction()
            self.run_stage_2_value_extraction()
            self.run_stage_3_product_aggregation()
            self.run_stage_4_standardization()
            self.run_stage_5_final_assembly()

            # Update pipeline metadata
            self.metadata.completed_at = datetime.now().isoformat()
            self.metadata.total_duration_seconds = (datetime.now() - pipeline_start).total_seconds()
            self.metadata.status = "completed"

            print(f"\n{'=' * 80}")
            print(f"PIPELINE COMPLETED SUCCESSFULLY")
            print(f"{'=' * 80}")
            print(f"Total duration: {self.metadata.total_duration_seconds:.2f}s")
            print(f"Stages completed: {len([s for s in self.metadata.stages if s.status == 'completed'])}/{len(self.metadata.stages)}")

        except Exception as e:
            self.metadata.status = "failed"
            print(f"\n{'=' * 80}")
            print(f"PIPELINE FAILED")
            print(f"{'=' * 80}")
            print(f"Error: {e}")
            raise

        finally:
            # Save metadata
            metadata_file = self.output_dir / "pipeline_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"\nMetadata saved: {metadata_file}\n")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    # Initialize and run pipeline
    pipeline = TaxonomyExtractionPipeline()
    pipeline.run_pipeline()


if __name__ == "__main__":
    main()

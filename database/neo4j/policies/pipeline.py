"""
Main Pipeline Orchestrator
Coordinates all 9 stages of the Neo4j knowledge graph construction pipeline.
"""

import sys
from pathlib import Path

# Add the repo root to sys.path to enable imports
REPO_ROOT = Path(__file__).resolve().parents[3]  # Go up to repo root
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml
from datetime import datetime
from typing import Dict

# Import all agents (using full package path)
from database.neo4j.policies.agents.product_extractor import ProductExtractor
from database.neo4j.policies.agents.concept_extractor import ConceptExtractor
from database.neo4j.policies.agents.fact_extractor import FactExtractor
from database.neo4j.policies.agents.concept_expander import run_multiple_iterations
from database.neo4j.policies.agents.personality_generator import PersonalityGenerator
from database.neo4j.policies.agents.fact_integrator import FactGraphIntegrator
from database.neo4j.policies.agents.concept_distiller import ConceptDistiller, BatchConceptDistiller
from database.neo4j.policies.agents.pair_validator import ConceptPairValidator, BatchConceptPairValidator
from database.neo4j.policies.agents.qa_converter import QACollectionConverter

# Import services
from database.neo4j.policies.services.ocr_service import OCRService
from database.neo4j.policies.services.neo4j_service import Neo4jService

# Import utilities
from database.neo4j.policies.utils.api_client import APIClient
from database.neo4j.policies.utils.embedding_utils import load_embedding_model, generate_embeddings_batch
from database.neo4j.policies.utils.file_utils import save_json, save_pickle, load_pickle, load_json

# Import entities
from database.neo4j.policies.entities.concept_graph import ConceptGraph
from database.neo4j.policies.entities.data_models import GraphNode, GraphEdge, KnowledgeGraph, QAPair


class PipelineConfig:
    """Configuration manager for the pipeline."""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager.

        Args:
            config_dir: Directory containing YAML configuration files (relative to policies/)
        """
        self.base_dir = Path(__file__).resolve().parent
        self.config_dir = self.base_dir / config_dir

        self.models_config = self._load_yaml("models.yaml")
        self.pipeline_config = self._load_yaml("pipeline.yaml")
        self.neo4j_config = self._load_yaml("neo4j.yaml")
        self.generation_config = self._load_yaml("generation.yaml")

    def _load_yaml(self, filename: str) -> Dict:
        """Load a YAML configuration file."""
        filepath = self.config_dir / filename
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)

    def get_api_client(self, model_key: str) -> APIClient:
        """Create an API client for a specific model."""
        api_config = self.models_config['api']
        model_config = self.models_config['models'][model_key]

        return APIClient(
            api_url=api_config['url'],
            api_key=api_config['key'],
            model_name=model_config['name'],
            use_responses_api=model_config.get('use_responses_api', False)
        )

    def is_stage_enabled(self, stage_name: str) -> bool:
        """Check if a pipeline stage is enabled."""
        return self.pipeline_config['pipeline']['stages'].get(stage_name, {}).get('enabled', False)


class KnowledgeGraphPipeline:
    """
    Main pipeline orchestrator for Neo4j knowledge graph construction.

    Coordinates all 9 stages from PDF processing to Neo4j import.
    """

    def __init__(self, config_dir: str = "config", output_base_dir: str = "output"):
        """
        Initialize the pipeline.

        Args:
            config_dir: Directory containing configuration files (relative to policies/)
            output_base_dir: Base directory for all output files (relative to policies/)
        """
        self.base_dir = Path(__file__).resolve().parent
        self.config = PipelineConfig(config_dir)
        self.output_base_dir = self.base_dir / output_base_dir
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

        # Create output directories (anchor to base_dir)
        self.pdf_convert_dir = self.base_dir / self.config.pipeline_config['pipeline']['paths']['pdf_convert_dir']
        self.raw_text_dir = self.base_dir / self.config.pipeline_config['pipeline']['paths']['raw_text_dir']
        self.pdf_convert_dir.mkdir(parents=True, exist_ok=True)
        self.raw_text_dir.mkdir(parents=True, exist_ok=True)

        # Pipeline state
        self.stage_results = {}

        print("=" * 80)
        print("INSURANCE KNOWLEDGE GRAPH PIPELINE")
        print("=" * 80)
        print(f"Configuration loaded from: {config_dir}")
        print(f"Output directory: {output_base_dir}")
        print()

    def run_full_pipeline(self) -> Dict:
        """
        Run the complete 9-stage pipeline.

        Returns:
            Dictionary with results from all stages
        """
        print("\n" + "=" * 80)
        print("STARTING FULL PIPELINE EXECUTION")
        print("=" * 80)

        start_time = datetime.now()

        # Stage 0: OCR
        if self.config.is_stage_enabled('stage_0_ocr'):
            self.run_stage_0_ocr()

        # Stage 1: Product Extraction
        if self.config.is_stage_enabled('stage_1_product_extraction'):
            self.run_stage_1_product_extraction()

        # Stage 2: Concept Extraction
        if self.config.is_stage_enabled('stage_2_concept_extraction'):
            self.run_stage_2_concept_extraction()

        # Stage 3: Fact Extraction
        if self.config.is_stage_enabled('stage_3_fact_extraction'):
            self.run_stage_3_fact_extraction()

        # Stage 4: Concept Expansion
        if self.config.is_stage_enabled('stage_4_concept_expansion'):
            self.run_stage_4_concept_expansion()

        # Stage 5: Personality Generation
        if self.config.is_stage_enabled('stage_5_personality_generation'):
            self.run_stage_5_personality_generation()

        # Stage 6: Fact Integration
        if self.config.is_stage_enabled('stage_6_fact_integration'):
            self.run_stage_6_fact_integration()

        # Stage 7a: Concept Distillation
        if self.config.is_stage_enabled('stage_7a_concept_distillation'):
            self.run_stage_7a_concept_distillation()

        # Stage 7b: Pair Validation
        if self.config.is_stage_enabled('stage_7b_pair_validation'):
            self.run_stage_7b_pair_validation()

        # Stage 7c: QA Conversion
        if self.config.is_stage_enabled('stage_7c_qa_conversion'):
            self.run_stage_7c_qa_conversion()

        # Stage 8: MemOS Assembly
        if self.config.is_stage_enabled('stage_8_memos_assembly'):
            self.run_stage_8_memos_assembly()

        # Stage 9: Neo4j Import
        if self.config.is_stage_enabled('stage_9_neo4j_import'):
            self.run_stage_9_neo4j_import()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION COMPLETE")
        print("=" * 80)
        print(f"Total time: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"Results saved to: {self.output_base_dir}")
        print()

        return self.stage_results

    def run_stage_0_ocr(self):
        """Stage 0: Convert PDFs to markdown and JSON."""
        print("\n" + "=" * 80)
        print("STAGE 0: OCR - PDF TO JSON CONVERSION")
        print("=" * 80)

        # Anchor pdf_input_dir to base_dir
        pdf_input_dir = self.base_dir / self.config.pipeline_config['pipeline']['paths']['pdf_input_dir']

        ocr_service = OCRService()
        # Pass Path objects directly (OCR service handles conversion)
        result = ocr_service.process_pipeline_pdfs(
            pdf_dir=pdf_input_dir,
            markdown_output_dir=self.pdf_convert_dir,
            json_output_dir=self.raw_text_dir
        )

        self.stage_results['stage_0'] = result
        # Handle both old and new dictionary structures for robustness
        pdfs_processed = result.get('pdfs_processed', result.get('summary', {}).get('pdfs_processed', 0))
        json_generated = result.get('json_files_generated', result.get('summary', {}).get('json_created', 0))
        print(f"Processed {pdfs_processed} PDFs")
        print(f"Generated {json_generated} JSON files")

    def run_stage_1_product_extraction(self):
        """Stage 1: Extract product names from raw text."""
        print("\n" + "=" * 80)
        print("STAGE 1: PRODUCT EXTRACTION")
        print("=" * 80)

        # Get config
        stage_1_config = self.config.pipeline_config['pipeline']['stages']['stage_1_product_extraction']

        # Get input directory from config (relative to output_base_dir)
        input_dir = self.output_base_dir / stage_1_config.get('input_dir', '../raw_text')
        print(f"Loading raw text from: {input_dir}")

        api_client = self.config.get_api_client('insurance_name_extractor')
        extractor = ProductExtractor(api_client, sample_size=3)

        product_dict = extractor.extract_products_from_directory(input_dir)

        # Save results using configured output file
        output_filename = stage_1_config.get('output_file', 'stage_1_product_dict.pkl')
        output_file = self.output_base_dir / output_filename
        save_pickle(product_dict, output_file)

        self.stage_results['stage_1'] = {
            'product_dict': product_dict,
            'output_file': str(output_file),
            'num_products': len(product_dict)
        }

        print(f"Extracted {len(product_dict)} products")
        print(f"Saved to: {output_file}")
        for product, texts in product_dict.items():
            print(f"  - {product}: {len(texts)} texts")

    def run_stage_2_concept_extraction(self):
        """Stage 2: Generate seed concepts from all texts."""
        print("\n" + "=" * 80)
        print("STAGE 2: SEED CONCEPT EXTRACTION")
        print("=" * 80)

        # Get config
        stage_2_config = self.config.pipeline_config['pipeline']['stages']['stage_2_concept_extraction']

        # Load product dict from file or fallback to memory
        input_files = stage_2_config.get('input_files', {})
        product_dict_file = self.output_base_dir / input_files.get('product_dict', 'stage_1_product_dict.pkl')

        if product_dict_file.exists():
            print(f"Loading product dict from: {product_dict_file}")
            product_dict = load_pickle(product_dict_file)
        else:
            print(f"Product dict file not found: {product_dict_file}")
            print("Falling back to stage 1 results in memory")
            product_dict = self.stage_results.get('stage_1', {}).get('product_dict', {})

        # Collect all texts
        all_texts = []
        for texts in product_dict.values():
            all_texts.extend(texts)

        api_client = self.config.get_api_client('concept_extractor')
        max_workers = self.config.generation_config['concurrency']['stage_2_concept_extraction']

        extractor = ConceptExtractor(api_client, max_workers=max_workers)
        seed_concepts = extractor.generate_seed_concepts(all_texts)

        # Save results using configured output file
        output_filename = stage_2_config.get('output_file', 'stage_2_seed_concepts.json')
        output_file = self.output_base_dir / output_filename
        save_json(seed_concepts, output_file)

        self.stage_results['stage_2'] = {
            'seed_concepts': seed_concepts,
            'output_file': str(output_file),
            'num_concepts': len(seed_concepts)
        }

        print(f"Saved to: {output_file}")

        print(f"Generated {len(seed_concepts)} unique seed concepts")

    def run_stage_3_fact_extraction(self):
        """Stage 3: Extract facts from product texts."""
        print("\n" + "=" * 80)
        print("STAGE 3: FACT EXTRACTION")
        print("=" * 80)

        # Get config
        stage_3_config = self.config.pipeline_config['pipeline']['stages']['stage_3_fact_extraction']

        # Load product dict from file or fallback to memory
        input_files = stage_3_config.get('input_files', {})
        product_dict_file = self.output_base_dir / input_files.get('product_dict', 'stage_1_product_dict.pkl')

        if product_dict_file.exists():
            print(f"Loading product dict from: {product_dict_file}")
            product_dict = load_pickle(product_dict_file)
        else:
            print(f"Product dict file not found: {product_dict_file}")
            print("Falling back to stage 1 results in memory")
            product_dict = self.stage_results.get('stage_1', {}).get('product_dict', {})

        api_client = self.config.get_api_client('fact_extractor')
        max_workers = self.config.generation_config['concurrency']['stage_3_fact_extraction']

        extractor = FactExtractor(api_client, max_workers=max_workers)
        product_facts = extractor.extract_facts(product_dict)
        all_facts = extractor.get_all_facts(product_facts)

        # Save results using configured output files
        output_files_config = stage_3_config.get('output_files', {})
        output_file_facts = self.output_base_dir / output_files_config.get('product_facts', 'stage_3_product_facts.json')
        output_file_all = self.output_base_dir / output_files_config.get('all_facts', 'stage_3_all_facts.json')
        save_json(product_facts, output_file_facts)
        save_json(all_facts, output_file_all)

        self.stage_results['stage_3'] = {
            'product_facts': product_facts,
            'all_facts': all_facts,
            'output_files': [str(output_file_facts), str(output_file_all)],
            'total_facts': len(all_facts)
        }

        print(f"Extracted {len(all_facts)} total facts across {len(product_facts)} products")
        print(f"Saved to: {output_file_facts} and {output_file_all}")

    def run_stage_4_concept_expansion(self):
        """Stage 4: Expand concept graph through iterations."""
        print("\n" + "=" * 80)
        print("STAGE 4: CONCEPT GRAPH EXPANSION")
        print("=" * 80)

        # Load configuration
        stage_4_config = self.config.pipeline_config['pipeline']['stages']['stage_4_concept_expansion']
        input_files = stage_4_config.get('input_files', {})

        # Load seed concepts from file or memory
        seed_concepts_file = self.output_base_dir / input_files.get('seed_concepts', 'stage_2_seed_concepts.json')

        if seed_concepts_file.exists():
            print(f"Loading seed concepts from: {seed_concepts_file}")
            seed_concepts = load_json(seed_concepts_file)
        else:
            print(f"Seed concepts file not found: {seed_concepts_file}")
            print("Falling back to stage 2 results in memory")
            seed_concepts = self.stage_results.get('stage_2', {}).get('seed_concepts', [])

        # Load embedding model
        embedding_config = self.config.models_config['models']['embedding']
        embedding_model = load_embedding_model(
            embedding_config['name'],
            embedding_config.get('device', 'cpu')
        )

        # Initialize concept graph
        concept_graph = ConceptGraph(
            seed_concepts=seed_concepts,
            model=embedding_model,
            similarity_threshold=0.8
        )

        # Run iterations
        api_client = self.config.get_api_client('concept_expander')
        max_workers = self.config.generation_config['concurrency']['stage_4_concept_expansion']
        convergence_config = self.config.pipeline_config['pipeline']['convergence']

        iteration_results, iteration_snapshots = run_multiple_iterations(
            api_client=api_client,
            concept_graph=concept_graph,
            max_iterations=convergence_config['max_iterations'],
            max_workers=max_workers,
            concept_add_threshold=convergence_config['concept_add_threshold'],
            connectivity_threshold=convergence_config['connectivity_threshold']
        )

        # Save iteration snapshots according to configuration
        save_iterations = stage_4_config.get('save_iterations', list(iteration_snapshots.keys()))
        pattern = stage_4_config.get('output_files', {}).get('pattern', 'concept_graph_iter_{iter}.pkl')

        saved_files = {}
        for iter_num in save_iterations:
            if iter_num in iteration_snapshots:
                # Replace {iter} placeholder with iteration number
                filename = pattern.replace('{iter}', str(iter_num))
                output_file = self.output_base_dir / filename
                output_file.parent.mkdir(parents=True, exist_ok=True)
                save_pickle(iteration_snapshots[iter_num], output_file)
                saved_files[iter_num] = str(output_file)
                print(f"Saved iteration {iter_num} graph to: {output_file}")

        # Keep final graph for backward compatibility
        final_graph = concept_graph.get_current_adjacency()

        self.stage_results['stage_4'] = {
            'concept_graph': final_graph,
            'iteration_snapshots': iteration_snapshots,
            'saved_files': saved_files,
            'num_iterations': len(iteration_results),
            'final_stats': concept_graph.get_graph_stats()
        }

        print(f"Completed {len(iteration_results)} iterations")
        print(f"Saved {len(saved_files)} iteration snapshots")
        print(f"Final graph: {self.stage_results['stage_4']['final_stats']}")

    def run_stage_5_personality_generation(self):
        """Stage 5: Generate customer personalities."""
        print("\n" + "=" * 80)
        print("STAGE 5: PERSONALITY GENERATION")
        print("=" * 80)

        api_client = self.config.get_api_client('personality_generator')
        personality_config = self.config.generation_config['personality']

        generator = PersonalityGenerator(api_client)
        personalities = generator.generate_personalities(
            personality_number=personality_config['total_count'],
            batch_size=self.config.generation_config['batch_sizes']['personality_generation'],
            max_workers=self.config.generation_config['concurrency']['stage_5_personality_generation']
        )

        # Save results
        output_file = self.output_base_dir / "stage_5_personalities.json"
        generator.save_personalities(personalities, output_file)

        self.stage_results['stage_5'] = {
            'personalities': personalities,
            'output_file': str(output_file),
            'num_personalities': len(personalities)
        }

        print(f"Generated {len(personalities)} personalities")

    def run_stage_6_fact_integration(self):
        """Stage 6: Integrate facts into concept graphs."""
        print("\n" + "=" * 80)
        print("STAGE 6: FACT-GRAPH INTEGRATION")
        print("=" * 80)

        # Load configuration
        stage_6_config = self.config.pipeline_config['pipeline']['stages']['stage_6_fact_integration']
        input_files = stage_6_config.get('input_files', {})

        # Load main and sub graphs from files or memory
        if input_files.get('main_graph'):
            main_graph_path = self.output_base_dir / input_files['main_graph']
            if main_graph_path.exists():
                print(f"Loading main graph from: {main_graph_path}")
                concept_dict = load_pickle(main_graph_path)
            else:
                print(f"Main graph file not found: {main_graph_path}")
                print("Falling back to stage 4 results in memory")
                concept_dict = self.stage_results.get('stage_4', {}).get('concept_graph', {}).copy()
        else:
            print("No main_graph path configured, using stage 4 results from memory")
            concept_dict = self.stage_results.get('stage_4', {}).get('concept_graph', {}).copy()

        if input_files.get('sub_graph'):
            sub_graph_path = self.output_base_dir / input_files['sub_graph']
            if sub_graph_path.exists():
                print(f"Loading sub graph from: {sub_graph_path}")
                sub_concept_dict = load_pickle(sub_graph_path)
            else:
                print(f"Sub graph file not found: {sub_graph_path}")
                print("Falling back to stage 4 results in memory")
                sub_concept_dict = self.stage_results.get('stage_4', {}).get('concept_graph', {}).copy()
        else:
            print("No sub_graph path configured, using stage 4 results from memory")
            sub_concept_dict = self.stage_results.get('stage_4', {}).get('concept_graph', {}).copy()

        # Load all_facts from file or memory
        all_facts_file = self.output_base_dir / input_files.get('all_facts', 'stage_3_all_facts.json')
        if all_facts_file.exists():
            print(f"Loading all facts from: {all_facts_file}")
            all_facts = load_json(all_facts_file)
        else:
            print(f"All facts file not found: {all_facts_file}")
            print("Falling back to stage 3 results in memory")
            all_facts = self.stage_results.get('stage_3', {}).get('all_facts', [])

        # Load product_dict from file or memory
        product_dict_file = self.output_base_dir / input_files.get('product_dict', 'stage_1_product_dict.pkl')
        if product_dict_file.exists():
            print(f"Loading product dict from: {product_dict_file}")
            product_dict = load_pickle(product_dict_file)
            product_names = list(product_dict.keys())
        else:
            print(f"Product dict file not found: {product_dict_file}")
            print("Falling back to stage 1 results in memory")
            product_names = list(self.stage_results.get('stage_1', {}).get('product_dict', {}).keys())

        # Load embedding model
        embedding_config = self.config.models_config['models']['embedding']

        integrator = FactGraphIntegrator(
            embedding_model_name=embedding_config['name'],
            device=embedding_config.get('device', 'cpu')
        )

        # Add products and integrate facts
        concept_dict, sub_concept_dict = integrator.add_products_to_graphs(
            concept_dict=concept_dict,
            sub_concept_dict=sub_concept_dict,
            insurance_product_names=product_names
        )

        concept_dict, sub_concept_dict = integrator.integrate_facts_with_graphs(
            seed_facts=all_facts,
            concept_dict=concept_dict,
            sub_concept_dict=sub_concept_dict,
            top_k=5
        )

        # Save results using configured paths
        output_files = stage_6_config.get('output_files', {})
        main_output_filename = output_files.get('main_graph_with_facts', 'concept_dict_with_facts.pkl')
        sub_output_filename = output_files.get('sub_graph_with_facts', 'sub_concept_dict_with_facts.pkl')

        output_file_concept = self.output_base_dir / main_output_filename
        output_file_sub = self.output_base_dir / sub_output_filename
        output_file_concept.parent.mkdir(parents=True, exist_ok=True)
        output_file_sub.parent.mkdir(parents=True, exist_ok=True)

        integrator.save_graphs(concept_dict, sub_concept_dict, output_file_concept, output_file_sub)

        self.stage_results['stage_6'] = {
            'concept_dict': concept_dict,
            'sub_concept_dict': sub_concept_dict,
            'output_files': [str(output_file_concept), str(output_file_sub)]
        }

        print(f"Integrated facts into graphs")
        print(f"Saved main graph to: {output_file_concept}")
        print(f"Saved sub graph to: {output_file_sub}")

    def run_stage_7a_concept_distillation(self):
        """Stage 7a: Generate QA pairs for single concepts."""
        print("\n" + "=" * 80)
        print("STAGE 7a: CONCEPT DISTILLATION (SINGLE-CONCEPT QA)")
        print("=" * 80)

        # Load configuration
        stage_7a_config = self.config.pipeline_config['pipeline']['stages']['stage_7a_concept_distillation']
        input_files = stage_7a_config.get('input_files', {})

        # Load concept_graph from file or memory
        concept_graph_file = self.output_base_dir / input_files.get('concept_graph', 'concept_graph_4omini_3_iter.pkl')
        if concept_graph_file.exists():
            print(f"Loading concept graph from: {concept_graph_file}")
            concept_graph = load_pickle(concept_graph_file)
        else:
            print(f"Concept graph file not found: {concept_graph_file}")
            print("Falling back to stage 4 results in memory")
            concept_graph = self.stage_results.get('stage_4', {}).get('concept_graph', {})

        # Load personalities from file or memory
        personalities_file = self.output_base_dir / input_files.get('personalities', 'stage_5_personalities.json')
        if personalities_file.exists():
            print(f"Loading personalities from: {personalities_file}")
            personalities = load_json(personalities_file)
        else:
            print(f"Personalities file not found: {personalities_file}")
            print("Falling back to stage 5 results in memory")
            personalities = self.stage_results.get('stage_5', {}).get('personalities', [])

        api_client = self.config.get_api_client('qa_synthesizer')
        distiller = ConceptDistiller(api_client, personalities)
        batch_distiller = BatchConceptDistiller(
            distiller,
            output_dir=str(self.output_base_dir / "concept_distillation")
        )

        results = batch_distiller.distill_concept_graph(
            concept_graph_dict=concept_graph,
            max_workers=self.config.generation_config['concurrency']['stage_7a_concept_distillation'],
            batch_size=self.config.generation_config['batch_sizes']['concept_distillation']
        )

        self.stage_results['stage_7a'] = {
            'distillation_results': results,
            'output_dir': str(self.output_base_dir / "concept_distillation"),
            'num_concepts': len(results)
        }

        print(f"Generated QA pairs for {len(results)} concepts")

    def run_stage_7b_pair_validation(self):
        """Stage 7b: Validate concept pairs and generate QA."""
        print("\n" + "=" * 80)
        print("STAGE 7b: CONCEPT PAIR VALIDATION")
        print("=" * 80)

        # Load configuration
        stage_7b_config = self.config.pipeline_config['pipeline']['stages']['stage_7b_pair_validation']
        input_files = stage_7b_config.get('input_files', {})

        # Load concept_graph from file or memory
        concept_graph_file = self.output_base_dir / input_files.get('concept_graph', 'concept_graph_4omini_3_iter.pkl')
        if concept_graph_file.exists():
            print(f"Loading concept graph from: {concept_graph_file}")
            concept_graph = load_pickle(concept_graph_file)
        else:
            print(f"Concept graph file not found: {concept_graph_file}")
            print("Falling back to stage 4 results in memory")
            concept_graph = self.stage_results.get('stage_4', {}).get('concept_graph', {})

        # Load personalities from file or memory
        personalities_file = self.output_base_dir / input_files.get('personalities', 'stage_5_personalities.json')
        if personalities_file.exists():
            print(f"Loading personalities from: {personalities_file}")
            personalities = load_json(personalities_file)
        else:
            print(f"Personalities file not found: {personalities_file}")
            print("Falling back to stage 5 results in memory")
            personalities = self.stage_results.get('stage_5', {}).get('personalities', [])

        api_client = self.config.get_api_client('qa_synthesizer')
        validator = ConceptPairValidator(api_client, personalities)
        batch_validator = BatchConceptPairValidator(
            validator,
            output_dir=str(self.output_base_dir / "pair_validation")
        )

        results = batch_validator.validate_concept_pair_graph(
            concept_graph_dict=concept_graph,
            max_workers=self.config.generation_config['concurrency']['stage_7b_pair_validation'],
            batch_size=self.config.generation_config['batch_sizes']['pair_validation']
        )

        self.stage_results['stage_7b'] = {
            'validation_results': results,
            'output_dir': str(self.output_base_dir / "pair_validation"),
            'num_pairs': len(results)
        }

        print(f"Validated {len(results)} concept pairs")

    def run_stage_7c_qa_conversion(self):
        """Stage 7c: Convert and merge QA collections."""
        print("\n" + "=" * 80)
        print("STAGE 7c: QA COLLECTION CONVERSION")
        print("=" * 80)

        # Load configuration
        stage_7c_config = self.config.pipeline_config['pipeline']['stages']['stage_7c_qa_conversion']
        input_files = stage_7c_config.get('input_files', {})

        # Check if we should load from directories or use memory results
        concept_distillation_dir = self.output_base_dir / input_files.get('concept_distillation', 'concept_distillation')
        pair_validation_dir = self.output_base_dir / input_files.get('pair_validation', 'pair_validation')

        # Load from directories if they exist (preferred method)
        if concept_distillation_dir.exists() and pair_validation_dir.exists():
            print(f"\nLoading from batch pickle files...")
            print(f"Concept distillation directory: {concept_distillation_dir}")
            print(f"Pair validation directory: {pair_validation_dir}")

            # Import the load_pickle_directory function
            from database.neo4j.policies.utils.file_utils import load_pickle_directory

            # Load and aggregate all batch pickle files
            distillation_results = load_pickle_directory(concept_distillation_dir)
            validation_results = load_pickle_directory(pair_validation_dir)

            print(f"\nAggregation complete:")
            print(f"  Loaded {len(distillation_results)} concept distillation results")
            print(f"  Loaded {len(validation_results)} pair validation results")
        else:
            # Fall back to memory results (only if directories don't exist)
            print(f"\nDirectories not found, falling back to stage 7a/7b in-memory results")
            print(f"  Concept distillation dir exists: {concept_distillation_dir.exists()}")
            print(f"  Pair validation dir exists: {pair_validation_dir.exists()}")

            distillation_results = self.stage_results.get('stage_7a', {}).get('distillation_results', {})
            validation_results = self.stage_results.get('stage_7b', {}).get('validation_results', {})

            print(f"  Loaded {len(distillation_results)} distillation results from memory")
            print(f"  Loaded {len(validation_results)} validation results from memory")

        converter = QACollectionConverter(verbose=True)

        # Convert both collections
        single_qa = converter.convert_distillation_results(distillation_results)
        pair_qa = converter.convert_distillation_results(validation_results)

        # Merge
        merged_qa = converter.merge_qa_collections(single_qa, pair_qa)

        # Validate
        validation_results = converter.validate_qa_collection(merged_qa)

        # Save
        output_file = self.output_base_dir / "stage_7c_qa_collection.json"
        converter.save_qa_collection(merged_qa, str(output_file))

        self.stage_results['stage_7c'] = {
            'qa_collection': merged_qa,
            'output_file': str(output_file),
            'validation_results': validation_results
        }

        print(f"Generated {len(merged_qa)} total QA items")

    def run_stage_8_memos_assembly(self):
        """Stage 8: Assemble MemOS knowledge graph with embeddings."""
        print("\n" + "=" * 80)
        print("STAGE 8: MEMOS ASSEMBLY (GRAPH GENERATION)")
        print("=" * 80)

        # Load configuration
        stage_8_config = self.config.pipeline_config['pipeline']['stages']['stage_8_memos_assembly']
        input_files = stage_8_config.get('input_files', {})

        # Load qa_collection from file or memory
        qa_collection_file = self.output_base_dir / input_files.get('qa_collection', 'stage_7c_qa_collection.json')
        if qa_collection_file.exists():
            print(f"Loading QA collection from: {qa_collection_file}")
            qa_data = load_json(qa_collection_file)
            # Extract qa_collection list from the JSON structure
            if isinstance(qa_data, dict) and 'qa_collection' in qa_data:
                qa_collection = qa_data['qa_collection']
                print(f"  Loaded {len(qa_collection)} QA items from collection")
            else:
                qa_collection = qa_data  # Fallback for different structure
        else:
            print(f"QA collection file not found: {qa_collection_file}")
            print("Falling back to stage 7c results in memory")
            qa_collection = self.stage_results.get('stage_7c', {}).get('qa_collection', [])

        # ========================================================================
        # Step 1: Extract unique concepts and validate data
        # ========================================================================
        print("\n" + "-" * 80)
        print("STEP 1: EXTRACTING UNIQUE CONCEPTS")
        print("-" * 80)

        unique_concepts = set()
        invalid_data = []
        valid_concept_qa = 0
        valid_relation_qa = 0

        for i, qa_data in enumerate(qa_collection):
            if isinstance(qa_data['concept'], str):
                # Concept QA - single concept
                unique_concepts.add(qa_data['concept'])
                valid_concept_qa += 1
            elif isinstance(qa_data['concept'], list):
                # Relation QA - should be a pair of 2 concepts
                if len(qa_data['concept']) == 2:
                    unique_concepts.update(qa_data['concept'])
                    valid_relation_qa += 1
                else:
                    # Data anomaly: not a pair of 2 concepts
                    invalid_data.append({
                        'index': i,
                        'concept': qa_data['concept'],
                        'length': len(qa_data['concept'])
                    })
            else:
                # Data anomaly: concept is neither str nor list
                invalid_data.append({
                    'index': i,
                    'concept': qa_data['concept'],
                    'type': type(qa_data['concept']).__name__
                })

        print(f"Data Validation Results:")
        print(f"  - Valid Concept QA: {valid_concept_qa}")
        print(f"  - Valid Relation QA: {valid_relation_qa}")
        print(f"  - Anomalous Data: {len(invalid_data)}")
        print(f"  - Extracted unique concepts: {len(unique_concepts)}")

        unique_concepts_list = list(unique_concepts)

        # ========================================================================
        # Step 2: Load embedding model
        # ========================================================================
        print("\n" + "-" * 80)
        print("STEP 2: LOADING EMBEDDING MODEL")
        print("-" * 80)

        embedding_config = self.config.models_config['models']['embedding']
        embedding_model = load_embedding_model(
            embedding_config['name'],
            embedding_config.get('device', 'mps')
        )
        print(f"Loaded embedding model: {embedding_config['name']}")

        # ========================================================================
        # Step 3: Create concept nodes with embeddings
        # ========================================================================
        print("\n" + "-" * 80)
        print("STEP 3: CREATING CONCEPT NODES")
        print("-" * 80)

        print(f"Generating embeddings for {len(unique_concepts_list)} concepts...")
        concept_embeddings = generate_embeddings_batch(
            unique_concepts_list,
            embedding_model,
            batch_size=100
        )

        concept_nodes = {}  # Map concept name -> node info
        for concept, embedding in zip(unique_concepts_list, concept_embeddings):
            node = GraphNode.create_concept_node(concept, embedding)
            concept_nodes[concept] = {
                "id": node.id,
                "node": node
            }

        print(f"Created {len(concept_nodes)} concept nodes")

        # ========================================================================
        # Step 4: Create QA nodes with embeddings
        # ========================================================================
        print("\n" + "-" * 80)
        print("STEP 4: CREATING QA NODES")
        print("-" * 80)

        # Collect all questions for batch embedding
        all_questions = []
        all_metadata = []
        skipped_count = 0

        for qa_data in qa_collection:
            question = qa_data['question']

            # Determine QA type and prepare metadata
            if isinstance(qa_data['concept'], str):
                # Concept QA
                concept_name = qa_data['concept']
                if concept_name not in concept_nodes:
                    print(f"  Warning: Concept '{concept_name}' does not exist, skipping this QA")
                    skipped_count += 1
                    continue

                qa_type = "concept_qa"
                related_concept_ids = [concept_nodes[concept_name]["id"]]

            elif isinstance(qa_data['concept'], list) and len(qa_data['concept']) == 2:
                # Relation QA
                concept_names = qa_data['concept']

                # Check if all concepts exist
                missing_concepts = [name for name in concept_names if name not in concept_nodes]
                if missing_concepts:
                    print(f"  Warning: Concepts {missing_concepts} do not exist, skipping this QA")
                    skipped_count += 1
                    continue

                qa_type = "relation_qa"
                related_concept_ids = [concept_nodes[name]["id"] for name in concept_names]

            else:
                # Skip anomalous data
                skipped_count += 1
                continue

            all_questions.append(question)
            all_metadata.append({
                'qa_data': qa_data,
                'qa_type': qa_type,
                'related_concept_ids': related_concept_ids
            })

        print(f"Collected {len(all_questions)} valid questions (skipped {skipped_count})")
        print(f"Generating embeddings for questions...")

        # Batch generate embeddings for all questions
        question_embeddings = generate_embeddings_batch(
            all_questions,
            embedding_model,
            batch_size=100
        )

        # Create QA nodes
        qa_nodes = []
        concept_qa_count = 0
        relation_qa_count = 0

        for metadata, embedding in zip(all_metadata, question_embeddings):
            node = GraphNode.create_qa_node(
                qa_data=metadata['qa_data'],
                embedding=embedding,
                qa_type=metadata['qa_type'],
                related_concept_ids=metadata['related_concept_ids']
            )
            qa_nodes.append(node)

            if metadata['qa_type'] == "concept_qa":
                concept_qa_count += 1
            else:
                relation_qa_count += 1

        print(f"Created {len(qa_nodes)} QA nodes")
        print(f"  - Concept QA: {concept_qa_count}")
        print(f"  - Relation QA: {relation_qa_count}")

        # ========================================================================
        # Step 5: Create relationship edges
        # ========================================================================
        print("\n" + "-" * 80)
        print("STEP 5: CREATING RELATIONSHIP EDGES")
        print("-" * 80)

        edges = []
        edge_set = set()  # For deduplicating edges

        # 5.1: Concept↔Concept RELATE_TO relationships (derived from Relation QA)
        print("Creating inter-concept RELATE_TO relationships...")
        concept_relations = set()
        for qa_data in qa_collection:
            if isinstance(qa_data['concept'], list) and len(qa_data['concept']) == 2:
                concept_A, concept_B = qa_data['concept']
                if concept_A in concept_nodes and concept_B in concept_nodes:
                    relation_key = tuple(sorted([concept_A, concept_B]))
                    concept_relations.add(relation_key)

        relate_count = 0
        for concept_A, concept_B in concept_relations:
            concept_A_id = concept_nodes[concept_A]["id"]
            concept_B_id = concept_nodes[concept_B]["id"]

            edge_key = tuple(sorted([concept_A_id, concept_B_id]))
            if edge_key not in edge_set:
                edge = GraphEdge.create_relate_to_edge(concept_A_id, concept_B_id)
                edges.append(edge)
                edge_set.add(edge_key)
                relate_count += 1

        print(f"  Created {relate_count} inter-concept RELATE_TO relationships")

        # 5.2: Concept→QA PARENT relationships (Concept QA)
        print("Creating Concept→QA PARENT relationships...")
        parent_count = 0
        for qa_node in qa_nodes:
            if qa_node.metadata['qa_type'] == "concept_qa":
                concept_id = qa_node.metadata['related_concept_ids'][0]
                edge = GraphEdge.create_parent_edge(concept_id, qa_node.id)
                edges.append(edge)
                parent_count += 1

        print(f"  Created {parent_count} Concept→QA PARENT relationships")

        # 5.3: Concept→QA PARENT relationships (Relation QA - bridging questions)
        print("Creating Concept→Bridging QA PARENT relationships...")
        relation_parent_count = 0
        for qa_node in qa_nodes:
            if qa_node.metadata['qa_type'] == "relation_qa":
                for concept_id in qa_node.metadata['related_concept_ids']:
                    edge = GraphEdge.create_parent_edge(concept_id, qa_node.id)
                    edges.append(edge)
                    relation_parent_count += 1

        print(f"  Created {relation_parent_count} Concept→Bridging QA PARENT relationships")
        print(f"Total relationships: {len(edges)}")

        # Step 6: Assemble final knowledge graph
        print("\n" + "-" * 80)
        print("STEP 6: ASSEMBLING KNOWLEDGE GRAPH")
        print("-" * 80)

        # Collect all nodes
        all_nodes = []

        # Add concept nodes
        for concept_data in concept_nodes.values():
            all_nodes.append(concept_data["node"])

        # Add QA nodes (clean up temporary fields in metadata) - MODIFIED
        for qa_node in qa_nodes:
            # Create a clean copy without temporary fields
            clean_metadata = qa_node.metadata.copy()
            if "qa_type" in clean_metadata:
                del clean_metadata["qa_type"]
            if "related_concept_ids" in clean_metadata:
                del clean_metadata["related_concept_ids"]

            # MODIFIED: Create clean node with sources field
            clean_node = GraphNode(
                id=qa_node.id,
                memory=qa_node.memory,
                sources=qa_node.sources,  # ADDED
                metadata=clean_metadata
            )
            all_nodes.append(clean_node)

        # Create knowledge graph
        knowledge_graph = KnowledgeGraph(nodes=all_nodes, edges=edges)

        # Save to JSON
        output_file = self.output_base_dir / "stage_8_knowledge_graph.json"
        graph_dict = knowledge_graph.to_dict()
        save_json(graph_dict, output_file)

        stats = knowledge_graph.get_stats()

        self.stage_results['stage_8'] = {
            'knowledge_graph': graph_dict,
            'output_file': str(output_file),
            'stats': stats
        }

        print("\n" + "=" * 80)
        print("STAGE 8 COMPLETE")
        print("=" * 80)
        print(f"Final Knowledge Graph Statistics:")
        for key, value in stats.items():
            print(f"  - {key}: {value}")
        print(f"\nSaved to: {output_file}")

    def run_stage_9_neo4j_import(self):
        """Stage 9: Import knowledge graph into Neo4j."""
        print("\n" + "=" * 80)
        print("STAGE 9: NEO4J IMPORT")
        print("=" * 80)

        # Load configuration
        stage_9_config = self.config.pipeline_config['pipeline']['stages']['stage_9_neo4j_import']
        input_files = stage_9_config.get('input_files', {})

        graph_file = self.output_base_dir / input_files.get('concept_graph', 'stage_8_knowledge_graph.json')

        neo4j_config = self.config.neo4j_config['connection']
        service = Neo4jService(
            uri=neo4j_config['uri'],
            username=neo4j_config['username'],
            password=neo4j_config['password'],
            database=neo4j_config.get('database', 'neo4j')
        )

        # Test connection
        if not service.test_connection():
            print("ERROR: Cannot connect to Neo4j")
            return

        # Full import pipeline
        import_results = service.full_import_pipeline(graph_file)

        self.stage_results['stage_9'] = import_results

        print(f"Import complete: {import_results}")


def main():
    """Main entry point for the pipeline."""
    pipeline = KnowledgeGraphPipeline(
        config_dir="config",
        output_base_dir="output"
    )

    try:
        results = pipeline.run_full_pipeline()
        print("\n" + "=" * 80)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        return results

    except Exception as e:
        print("\n" + "=" * 80)
        print("PIPELINE FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()

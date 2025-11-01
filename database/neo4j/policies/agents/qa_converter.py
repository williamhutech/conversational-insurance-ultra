"""
QA Collection Converter Agent (Stage 7c)
Converts raw distillation results to standardized QA collection format.
Handles both single-concept and concept-pair QAs.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Union


@dataclass
class QAItem:
    """Standardized QA item format."""
    concept: Union[str, List[str]]
    question: str
    reasoning_guidance: str
    knowledge_facts: List[str]
    final_answer: str
    best_to_know: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert QA item to dictionary."""
        return {
            'concept': self.concept,
            'question': self.question,
            'reasoning_guidance': self.reasoning_guidance,
            'knowledge_facts': self.knowledge_facts,
            'final_answer': self.final_answer,
            'best_to_know': self.best_to_know
        }


class QACollectionConverter:
    """
    Convert raw distillation results to standardized QA collection format.

    Processes output from ConceptDistiller and ConceptPairValidator
    and transforms them into unified QA_COLLECTION format for
    downstream processing.
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the converter.

        Args:
            verbose: If True, print conversion progress information
        """
        self.verbose = verbose
        self.qa_collection: List[QAItem] = []
        self.conversion_stats = {
            'total_concepts_processed': 0,
            'total_qa_items_generated': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'skipped_items': 0,
            'single_concept_items': 0,
            'concept_pair_items': 0
        }

    def convert_distillation_results(
        self,
        results_dict: Dict[str, Any],
        concept_graph: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Convert raw distillation results to QA collection format.

        Handles both single-concept QAs from ConceptDistiller and
        concept-pair QAs from ConceptPairValidator.

        Args:
            results_dict: Dictionary of distillation results
                         Format: {concept_id: ConceptDistillationResult or PairValidationResult}
            concept_graph: Optional concept graph dict for relationships

        Returns:
            List of QA items in standardized format
        """
        if self.verbose:
            print("\n" + "=" * 80)
            print("QA COLLECTION CONVERSION PROCESS")
            print("=" * 80)
            print(f"Starting conversion of {len(results_dict)} concept/pair results...")

        self.qa_collection = []
        self.conversion_stats = {
            'total_concepts_processed': 0,
            'total_qa_items_generated': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'skipped_items': 0,
            'single_concept_items': 0,
            'concept_pair_items': 0
        }

        for concept_id, result in results_dict.items():
            self.conversion_stats['total_concepts_processed'] += 1

            # Convert dataclass to dict if needed
            if hasattr(result, '__dataclass_fields__'):
                result = asdict(result)

            # Skip if not successful
            if result.get('status') != 'success':
                self.conversion_stats['failed_conversions'] += 1
                if self.verbose:
                    print(f"  ✗ Skipping {concept_id}: status={result.get('status')}")
                continue

            # Determine if this is a concept pair or single concept
            is_concept_pair = 'concept_pair' in result

            # Extract concept name (single concept or pair)
            if is_concept_pair:
                concept_name = result.get('concept_pair')  # Will be a tuple/list
            else:
                concept_name = result.get('concept_name')  # Will be a string

            if not concept_name:
                self.conversion_stats['skipped_items'] += 1
                if self.verbose:
                    print(f"  ⊘ Missing concept_name for {concept_id}")
                continue

            # Extract questions from either generated_questions (single) or qa_data (pair)
            if is_concept_pair:
                qa_data = result.get('qa_data')
                # qa_data is a dict with single question, convert to list
                generated_questions = [qa_data] if qa_data else []
                self.conversion_stats['concept_pair_items'] += 1
            else:
                generated_questions = result.get('generated_questions', [])
                self.conversion_stats['single_concept_items'] += len(generated_questions)

            if not generated_questions:
                self.conversion_stats['skipped_items'] += 1
                if self.verbose:
                    print(f"  ⊘ No questions generated for {concept_id}")
                continue

            # Convert each question to QA item
            for question_data in generated_questions:
                try:
                    qa_item = self._convert_single_question(
                        concept_name=concept_name,
                        question_data=question_data,
                        concept_graph=concept_graph,
                        is_concept_pair=is_concept_pair
                    )
                    self.qa_collection.append(qa_item)
                    self.conversion_stats['total_qa_items_generated'] += 1
                except Exception as e:
                    self.conversion_stats['failed_conversions'] += 1
                    if self.verbose:
                        print(f"  ✗ Error converting question in {concept_id}: {str(e)}")

            self.conversion_stats['successful_conversions'] += 1
            if self.conversion_stats['total_concepts_processed'] % 10 == 0:
                print(f"  Processed {self.conversion_stats['total_concepts_processed']} concepts, "
                      f"Generated {self.conversion_stats['total_qa_items_generated']} QA items")

        self._print_conversion_summary()
        return [item.to_dict() for item in self.qa_collection]

    def _convert_single_question(
        self,
        concept_name: Union[str, List[str]],
        question_data: Dict[str, Any],
        concept_graph: Optional[Dict] = None,
        is_concept_pair: bool = False
    ) -> QAItem:
        """
        Convert a single question from distillation output to QA item format.

        Args:
            concept_name: Name of the concept or list for concept pairs
            question_data: Single question data from generated_questions
            concept_graph: Optional concept graph for relationships
            is_concept_pair: Whether this is a concept pair QA

        Returns:
            Formatted QA item
        """
        # Extract fields from question_data
        if isinstance(question_data, dict):
            question = question_data.get('question', '')
            reasoning_guidance = question_data.get('reasoning_guidance', '')
            knowledge_facts = question_data.get('knowledge_facts', [])
            final_answer = question_data.get('final_answer', '')
            best_to_know = question_data.get('best_to_know', '')
        else:
            raise ValueError("question_data must be a dictionary")

        # Validate required fields
        if not question or not final_answer:
            raise ValueError("Missing required fields: 'question' or 'final_answer'")

        # Handle concept_pair (tuple/list) directly or single concept
        if is_concept_pair and isinstance(concept_name, (tuple, list)):
            concept = list(concept_name)
        else:
            concept = self._determine_concept_format(concept_name, concept_graph)

        # Create QA item
        qa_item = QAItem(
            concept=concept,
            question=question,
            reasoning_guidance=reasoning_guidance,
            knowledge_facts=knowledge_facts,
            final_answer=final_answer,
            best_to_know=best_to_know
        )

        return qa_item

    def _determine_concept_format(
        self,
        concept_name: Union[str, List[str]],
        concept_graph: Optional[Dict] = None
    ) -> Union[str, List[str]]:
        """
        Determine if concept should be single string or concept pair.

        Args:
            concept_name: Name of the concept or list for pairs
            concept_graph: Optional concept graph for checking relationships

        Returns:
            Single concept string or list of related concepts
        """
        # Handle both string and list inputs
        if isinstance(concept_name, (list, tuple)):
            return list(concept_name)

        # If concept graph provided, check for related concepts
        if concept_graph and concept_name in concept_graph:
            related_concepts = concept_graph[concept_name]
            # If concept has strong relationships, could create concept pair
            if related_concepts and len(related_concepts) > 0:
                # For now, use single concept; extend this for multi-concept relationships
                return concept_name

        return concept_name

    def convert_from_batch_files(
        self,
        batch_files_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert from a list of batch result dictionaries.

        Supports both single-concept batch files (from ConceptDistiller)
        and concept-pair batch files (from ConceptPairValidator).

        Args:
            batch_files_list: List of batch result dicts with 'metadata' and 'results'

        Returns:
            QA collection in standardized format
        """
        if self.verbose:
            print(f"\nLoading QA data from {len(batch_files_list)} batch files...")

        combined_results = {}
        for batch_data in batch_files_list:
            results = batch_data.get('results', {})
            combined_results.update(results)

        return self.convert_distillation_results(combined_results)

    def _print_conversion_summary(self):
        """Print summary statistics of the conversion process."""
        if not self.verbose:
            return

        print("\n" + "=" * 80)
        print("CONVERSION SUMMARY")
        print("=" * 80)
        print(f"Total concepts/pairs processed:  {self.conversion_stats['total_concepts_processed']}")
        print(f"Successful conversions:          {self.conversion_stats['successful_conversions']}")
        print(f"Failed conversions:              {self.conversion_stats['failed_conversions']}")
        print(f"Skipped items:                   {self.conversion_stats['skipped_items']}")
        print(f"Total QA items generated:        {self.conversion_stats['total_qa_items_generated']}")
        print(f"Single-concept QA items:         {self.conversion_stats['single_concept_items']}")
        print(f"Concept-pair QA items:           {self.conversion_stats['concept_pair_items']}")

        if self.conversion_stats['successful_conversions'] > 0:
            avg_qa_per_concept = (
                self.conversion_stats['total_qa_items_generated'] /
                self.conversion_stats['successful_conversions']
            )
            print(f"Avg QA items per concept/pair:   {avg_qa_per_concept:.2f}")

        print("=" * 80 + "\n")

    def save_qa_collection(
        self,
        qa_collection: List[Dict[str, Any]],
        output_path: str
    ) -> str:
        """
        Save QA collection to JSON file.

        Args:
            qa_collection: List of QA items
            output_path: Path to save the JSON file

        Returns:
            Path to saved file
        """
        output_data = {
            'metadata': {
                'conversion_timestamp': datetime.now().isoformat(),
                'total_qa_items': len(qa_collection),
                'conversion_stats': self.conversion_stats
            },
            'qa_collection': qa_collection
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        if self.verbose:
            print(f"QA collection saved to: {output_path}")
            print(f"Total QA items: {len(qa_collection)}")

        return output_path

    def get_qa_collection(self) -> List[Dict[str, Any]]:
        """
        Get the current QA collection as list of dicts.

        Returns:
            QA items in standardized format
        """
        return [item.to_dict() for item in self.qa_collection]

    def validate_qa_item(self, qa_item: Dict[str, Any]) -> bool:
        """
        Validate that a QA item has all required fields.

        Args:
            qa_item: QA item to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'concept', 'question', 'reasoning_guidance',
            'knowledge_facts', 'final_answer', 'best_to_know'
        ]

        for field in required_fields:
            if field not in qa_item:
                if self.verbose:
                    print(f"  Missing field: {field}")
                return False

        # Validate field types
        if not isinstance(qa_item['concept'], (str, list)):
            if self.verbose:
                print(f"  Invalid concept type: {type(qa_item['concept'])}")
            return False

        if not isinstance(qa_item['knowledge_facts'], list):
            if self.verbose:
                print(f"  Invalid knowledge_facts type: {type(qa_item['knowledge_facts'])}")
            return False

        if not isinstance(qa_item['best_to_know'], str):
            if self.verbose:
                print(f"  Invalid best_to_know type: {type(qa_item['best_to_know'])}")
            return False

        return True

    def validate_qa_collection(
        self,
        qa_collection: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate entire QA collection.

        Args:
            qa_collection: QA collection to validate

        Returns:
            Validation results with statistics
        """
        if self.verbose:
            print("\nValidating QA collection...")

        validation_results = {
            'total_items': len(qa_collection),
            'valid_items': 0,
            'invalid_items': 0,
            'invalid_items_details': [],
            'items_with_best_to_know': 0
        }

        for idx, item in enumerate(qa_collection):
            if self.validate_qa_item(item):
                validation_results['valid_items'] += 1
                # Track items with best_to_know content
                if item.get('best_to_know', '').strip():
                    validation_results['items_with_best_to_know'] += 1
            else:
                validation_results['invalid_items'] += 1
                validation_results['invalid_items_details'].append({
                    'index': idx,
                    'concept': item.get('concept', 'N/A')
                })

        if self.verbose:
            print(f"  Valid items:              {validation_results['valid_items']}/{validation_results['total_items']}")
            print(f"  Invalid items:            {validation_results['invalid_items']}/{validation_results['total_items']}")
            print(f"  Items with best_to_know:  {validation_results['items_with_best_to_know']}/{validation_results['valid_items']}")

        return validation_results

    def filter_qa_collection_by_best_to_know(
        self,
        qa_collection: List[Dict[str, Any]],
        require_best_to_know: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Filter QA collection based on best_to_know presence.

        Args:
            qa_collection: QA collection to filter
            require_best_to_know: If True, only return items with non-empty best_to_know

        Returns:
            Filtered QA collection
        """
        if not require_best_to_know:
            return qa_collection

        filtered = [
            item for item in qa_collection
            if item.get('best_to_know', '').strip()
        ]

        if self.verbose:
            print(f"\nFiltered QA collection: {len(filtered)}/{len(qa_collection)} items with best_to_know")

        return filtered

    def merge_qa_collections(
        self,
        *qa_collections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge multiple QA collections into a single collection.

        Args:
            *qa_collections: Variable number of QA collection lists

        Returns:
            Merged QA collection
        """
        merged = []
        for qa_collection in qa_collections:
            merged.extend(qa_collection)

        if self.verbose:
            print(f"\nMerged {len(qa_collections)} QA collections into {len(merged)} total items")

        return merged


def convert_single_concept_qa(
    distillation_results: Dict[str, Any],
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Convenience function to convert single-concept distillation results.

    Args:
        distillation_results: Results from ConceptDistiller
        output_path: Optional path to save the collection
        verbose: Whether to print progress

    Returns:
        QA collection in standardized format
    """
    converter = QACollectionConverter(verbose=verbose)
    qa_collection = converter.convert_distillation_results(distillation_results)

    if output_path:
        converter.save_qa_collection(qa_collection, output_path)

    return qa_collection


def convert_pair_validation_qa(
    validation_results: Dict[str, Any],
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Convenience function to convert concept-pair validation results.

    Args:
        validation_results: Results from ConceptPairValidator
        output_path: Optional path to save the collection
        verbose: Whether to print progress

    Returns:
        QA collection in standardized format
    """
    converter = QACollectionConverter(verbose=verbose)
    qa_collection = converter.convert_distillation_results(validation_results)

    if output_path:
        converter.save_qa_collection(qa_collection, output_path)

    return qa_collection


def merge_and_save_qa_collections(
    single_concept_results: Dict[str, Any],
    pair_validation_results: Dict[str, Any],
    output_path: str,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Merge single-concept and pair QA collections and save to file.

    Args:
        single_concept_results: Results from ConceptDistiller
        pair_validation_results: Results from ConceptPairValidator
        output_path: Path to save the merged collection
        verbose: Whether to print progress

    Returns:
        Merged QA collection
    """
    converter = QACollectionConverter(verbose=verbose)

    # Convert both collections
    single_qa = converter.convert_distillation_results(single_concept_results)
    pair_qa = converter.convert_distillation_results(pair_validation_results)

    # Merge collections
    merged_qa = converter.merge_qa_collections(single_qa, pair_qa)

    # Validate and save
    validation_results = converter.validate_qa_collection(merged_qa)
    converter.save_qa_collection(merged_qa, output_path)

    return merged_qa

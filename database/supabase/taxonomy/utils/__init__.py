"""
Supabase Taxonomy Utilities
============================

Utilities for loading Travel Insurance Taxonomy data into Supabase
with dual vector embeddings (normalized + original text) optimized
for AI Agentic vector search.

Also includes legacy Neo4j utilities.
"""

# ============================================================================
# SUPABASE TAXONOMY LOADER (NEW)
# ============================================================================

from .config import (
    TaxonomyLoaderConfig,
    load_config,
    validate_environment,
)

from .models import (
    # JSON Models
    TravelInsuranceTaxonomy,
    GeneralCondition,
    Benefit,
    BenefitCondition,
    ProductConditionData,
    ProductBenefitData,
    TaxonomyMetadata,
    # Database Models
    ProductDB,
    GeneralConditionDB,
    BenefitDB,
    BenefitConditionDB,
    # Helpers
    format_parameters_for_embedding,
    format_coverage_limit,
)

from .embedding_service import (
    EmbeddingService,
)

from .loader import (
    TaxonomyLoader,
    main as run_loader,
)

# ============================================================================
# LEGACY UTILITIES (Neo4j, file operations, etc.)
# ============================================================================

from .api_client import (
    AnalysisResult,
    APIClient,
)
from .response_validator import (
    ResponseValidator,
)
from .file_utils import (
    load_json,
    save_json,
    load_json_directory,
    load_pickle,
    save_pickle,
    load_text_file,
    save_text_file,
    ensure_directory,
    list_files,
    get_file_size_mb,
    merge_json_files,
)
from .embedding_utils import (
    load_embedding_model,
    compute_similarity_matrix,
    deduplicate_concepts_by_similarity,
    find_most_similar,
    is_similar_to_any,
)

__version__ = "2.0.0"

__all__ = [
    # Supabase Taxonomy Loader (NEW)
    "TaxonomyLoaderConfig",
    "load_config",
    "validate_environment",
    "TravelInsuranceTaxonomy",
    "GeneralCondition",
    "Benefit",
    "BenefitCondition",
    "ProductConditionData",
    "ProductBenefitData",
    "TaxonomyMetadata",
    "ProductDB",
    "GeneralConditionDB",
    "BenefitDB",
    "BenefitConditionDB",
    "EmbeddingService",
    "TaxonomyLoader",
    "run_loader",
    "format_parameters_for_embedding",
    "format_coverage_limit",
    # Legacy - API client
    "AnalysisResult",
    "APIClient",
    # Legacy - Response validation
    "ResponseValidator",
    # Legacy - File operations
    "load_json",
    "save_json",
    "load_json_directory",
    "load_pickle",
    "save_pickle",
    "load_text_file",
    "save_text_file",
    "ensure_directory",
    "list_files",
    "get_file_size_mb",
    "merge_json_files",
    # Legacy - Embedding operations
    "load_embedding_model",
    "compute_similarity_matrix",
    "deduplicate_concepts_by_similarity",
    "find_most_similar",
    "is_similar_to_any"
]

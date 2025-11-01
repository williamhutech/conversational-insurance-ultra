"""Neo4j Knowledge Graph Utilities - Helper functions and tools."""

from database.neo4j.policies.utils.api_client import (
    AnalysisResult,
    APIClient,
)
from database.neo4j.policies.utils.response_validator import (
    ResponseValidator,
)
from database.neo4j.policies.utils.file_utils import (
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
from database.neo4j.policies.utils.embedding_utils import (
    load_embedding_model,
    generate_embeddings_batch,
    compute_similarity_matrix,
    deduplicate_concepts_by_similarity,
    find_most_similar,
    is_similar_to_any,
)
from database.neo4j.policies.utils.neo4j_utils import (
    test_connection,
    execute_query,
    execute_write_query,
    clear_database,
    get_node_count,
    get_relationship_count,
    get_database_stats,
    print_database_stats,
    batch_execute,
)

__all__ = [
    # API client
    "AnalysisResult",
    "APIClient",
    # Response validation
    "ResponseValidator",
    # File operations
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
    # Embedding operations
    "load_embedding_model",
    "generate_embeddings_batch",
    "compute_similarity_matrix",
    "deduplicate_concepts_by_similarity",
    "find_most_similar",
    "is_similar_to_any",
    # Neo4j operations
    "test_connection",
    "execute_query",
    "execute_write_query",
    "clear_database",
    "get_node_count",
    "get_relationship_count",
    "get_database_stats",
    "print_database_stats",
    "batch_execute",
]

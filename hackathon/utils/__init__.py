"""
GraphRAG Hackathon Utilities

Common utility functions and modules for the GraphRAG hackathon project.
"""

from .tigergraph_connection import (
    TigerGraphConnectionManager,
    get_connection_manager,
    get_connection,
    test_connection,
    get_graph_stats
)

from .document_loader import (
    load_documents_jsonl,
    load_documents_json,
    validate_document,
    filter_valid_documents,
    get_document_stats,
    merge_document_collections,
    chunk_document_by_tokens
)

from .graph_operations import (
    batch_upsert_vertices,
    batch_upsert_edges,
    create_document_to_chunk_edges,
    create_entity_relationship_edges,
    get_graph_summary,
    print_graph_summary
)

__all__ = [
    # Connection management
    'TigerGraphConnectionManager',
    'get_connection_manager',
    'get_connection',
    'test_connection',
    'get_graph_stats',
    # Document loading
    'load_documents_jsonl',
    'load_documents_json',
    'validate_document',
    'filter_valid_documents',
    'get_document_stats',
    'merge_document_collections',
    'chunk_document_by_tokens',
    # Graph operations
    'batch_upsert_vertices',
    'batch_upsert_edges',
    'create_document_to_chunk_edges',
    'create_entity_relationship_edges',
    'get_graph_summary',
    'print_graph_summary'
]
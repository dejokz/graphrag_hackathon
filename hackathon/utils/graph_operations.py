"""
Graph Operations Utilities

Provides batch operations and helper functions for TigerGraph graph manipulation.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


def batch_upsert_vertices(conn_manager, vertex_data: List[Dict[str, Any]],
                          batch_size: int = 100,
                          show_progress: bool = False) -> tuple[int, int]:
    """
    Batch upsert vertices into the graph

    Args:
        conn_manager: TigerGraphConnectionManager instance
        vertex_data: List of dictionaries with keys:
                    - vertex_type: Type of vertex
                    - vertex_id: Unique vertex ID
                    - attributes: Dictionary of vertex attributes
        batch_size: Number of vertices to upsert in each batch
        show_progress: Whether to show progress updates

    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    start_time = datetime.now()

    for i, vertex_info in enumerate(vertex_data):
        try:
            vertex_type = vertex_info['vertex_type']
            vertex_id = vertex_info['vertex_id']
            attributes = vertex_info['attributes']

            conn_manager.upsert_vertex(vertex_type, vertex_id, attributes)
            success_count += 1

            # Progress update
            if show_progress and (i + 1) % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (i + 1) / elapsed
                print(f"  Progress: {i+1}/{len(vertex_data)} ({rate:.1f} vertices/sec)")

        except Exception as e:
            failure_count += 1
            if failure_count <= 5:  # Only show first 5 failures
                vertex_id = vertex_info.get('vertex_id', 'unknown')
                print(f"  Failed to upsert vertex {vertex_id}: {e}")

    return success_count, failure_count


def batch_upsert_edges(conn_manager, edge_data: List[Dict[str, Any]],
                       batch_size: int = 100,
                       show_progress: bool = False) -> tuple[int, int]:
    """
    Batch upsert edges into the graph

    Args:
        conn_manager: TigerGraphConnectionManager instance
        edge_data: List of dictionaries with keys:
                  - edge_type: Type of edge
                  - source_type: Type of source vertex
                  - source_id: ID of source vertex
                  - target_type: Type of target vertex
                  - target_id: ID of target vertex
                  - attributes: Dictionary of edge attributes (optional)
        batch_size: Number of edges to upsert in each batch
        show_progress: Whether to show progress updates

    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    start_time = datetime.now()

    for i, edge_info in enumerate(edge_data):
        try:
            edge_type = edge_info['edge_type']
            source_type = edge_info['source_type']
            source_id = edge_info['source_id']
            target_type = edge_info['target_type']
            target_id = edge_info['target_id']
            attributes = edge_info.get('attributes', {})

            conn_manager.upsert_edge(
                edge_type, source_type, source_id,
                target_type, target_id, attributes
            )
            success_count += 1

            # Progress update
            if show_progress and (i + 1) % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = (i + 1) / elapsed
                print(f"  Progress: {i+1}/{len(edge_data)} ({rate:.1f} edges/sec)")

        except Exception as e:
            failure_count += 1
            if failure_count <= 5:  # Only show first 5 failures
                source_id = edge_info.get('source_id', 'unknown')
                target_id = edge_info.get('target_id', 'unknown')
                print(f"  Failed to upsert edge {source_id} -> {target_id}: {e}")

    return success_count, failure_count


def create_document_to_chunk_edges(documents: List[Dict[str, Any]],
                                    conn_manager,
                                    show_progress: bool = False) -> tuple[int, int]:
    """
    Create DOC_HAS_CHUNK edges between documents and their chunks

    Args:
        documents: List of chunked documents (each with original_doc_id)
        conn_manager: TigerGraphConnectionManager instance
        show_progress: Whether to show progress updates

    Returns:
        Tuple of (success_count, failure_count)
    """
    edge_data = []

    for chunk_doc in documents:
        original_doc_id = chunk_doc.get('original_doc_id')
        chunk_doc_id = chunk_doc.get('doc_id')

        if original_doc_id and chunk_doc_id:
            edge_data.append({
                'edge_type': 'DOC_HAS_CHUNK',
                'source_type': 'DrugDoc',
                'source_id': original_doc_id,
                'target_type': 'DrugChunk',
                'target_id': chunk_doc_id,
                'attributes': {
                    'chunk_number': chunk_doc.get('chunk_number', 0),
                    'total_chunks': chunk_doc.get('total_chunks', 1)
                }
            })

    return batch_upsert_edges(conn_manager, edge_data, show_progress=show_progress)


def create_entity_relationship_edges(entities: List[Dict[str, Any]],
                                      relationships: List[Dict[str, Any]],
                                      conn_manager,
                                      show_progress: bool = False) -> tuple[int, int]:
    """
    Create ENTITY_RELATED_TO edges based on extracted relationships

    Args:
        entities: List of extracted entities
        relationships: List of extracted relationships
        conn_manager: TigerGraphConnectionManager instance
        show_progress: Whether to show progress updates

    Returns:
        Tuple of (success_count, failure_count)
    """
    edge_data = []

    # Create entity lookup for fast access
    entity_lookup = {entity['entity_id']: entity for entity in entities}

    for rel in relationships:
        source_entity_id = rel.get('source_entity_id')
        target_entity_id = rel.get('target_entity_id')
        relation_type = rel.get('relation_type')
        confidence = rel.get('confidence', 0.0)

        if source_entity_id in entity_lookup and target_entity_id in entity_lookup:
            source_entity = entity_lookup[source_entity_id]
            target_entity = entity_lookup[target_entity_id]

            edge_data.append({
                'edge_type': 'ENTITY_RELATED_TO',
                'source_type': 'DrugEntity',
                'source_id': source_entity_id,
                'target_type': 'DrugEntity',
                'target_id': target_entity_id,
                'attributes': {
                    'relation_type': relation_type,
                    'confidence': confidence,
                    'source_entity_type': source_entity.get('entity_type'),
                    'target_entity_type': target_entity.get('entity_type')
                }
            })

    return batch_upsert_edges(conn_manager, edge_data, show_progress=show_progress)


def get_graph_summary(conn_manager) -> Dict[str, Any]:
    """
    Get a comprehensive summary of the current graph state

    Args:
        conn_manager: TigerGraphConnectionManager instance

    Returns:
        Dictionary with graph summary information
    """
    stats = conn_manager.get_graph_statistics()

    return {
        'total_vertices': stats['total_vertices'],
        'total_edges': stats['total_edges'],
        'vertex_types': stats['vertices'],
        'edge_types': stats['edges'],
        'vertex_type_count': len(stats['vertices']),
        'edge_type_count': len(stats['edges'])
    }


def print_graph_summary(summary: Dict[str, Any]):
    """
    Pretty print graph summary

    Args:
        summary: Graph summary dictionary from get_graph_summary
    """
    print("=== Graph Summary ===")
    print(f"Total Vertices: {summary['total_vertices']:,}")
    print(f"Total Edges: {summary['total_edges']:,}")
    print(f"Vertex Types: {summary['vertex_type_count']}")
    print(f"Edge Types: {summary['edge_type_count']}")

    if summary['vertex_types']:
        print("\nVertex Types:")
        for vtype, count in sorted(summary['vertex_types'].items()):
            print(f"  {vtype}: {count:,}")

    if summary['edge_types']:
        print("\nEdge Types:")
        for etype, count in sorted(summary['edge_types'].items()):
            print(f"  {etype}: {count:,}")
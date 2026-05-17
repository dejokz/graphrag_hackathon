"""
Check current graph state
Refactored to use environment variables and modular connection management
"""
import sys
import os
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent.parent
hackathon_root = Path(__file__).parent.parent

# Add project root and hackathon root to path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(hackathon_root))

# Change to hackathon directory to ensure .env is found
os.chdir(str(hackathon_root))

from utils.tigergraph_connection import get_connection_manager
from utils.graph_operations import print_graph_summary


def check_graph_state() -> dict:
    """
    Check current graph state and provide comprehensive analysis

    Returns:
        Dictionary with graph state information
    """
    print("=== Current Graph State ===\n")

    # Initialize connection manager
    conn_manager = get_connection_manager()

    # Test connection
    if not conn_manager.test_connection():
        print("X Failed to connect to TigerGraph")
        return {'success': False, 'error': 'Connection failed'}

    print(f"\nGraph: {conn_manager.graph_name}\n")

    # Get detailed graph statistics
    print("Graph Statistics:")
    print("-" * 40)

    stats = conn_manager.get_graph_statistics()

    print(f"Total Vertices: {stats['total_vertices']:,}")
    print(f"Total Edges: {stats['total_edges']:,}")

    # Vertex type breakdown
    if stats['vertices']:
        print(f"\nVertex Types ({len(stats['vertices'])}):")
        for vtype, count in sorted(stats['vertices'].items()):
            if count > 0:
                print(f"  {vtype:20s}: {count:,}")
            else:
                print(f"  {vtype:20s}: 0")

    # Edge type breakdown
    if stats['edges']:
        print(f"\nEdge Types ({len(stats['edges'])}):")
        for etype, count in sorted(stats['edges'].items()):
            if count > 0:
                print(f"  {etype:30s}: {count:,}")
            else:
                print(f"  {etype:30s}: 0")

    # Check for data completeness
    print(f"\nData Completeness:")
    print("-" * 40)

    doc_count = stats['vertices'].get('DrugDoc', 0)
    chunk_count = stats['vertices'].get('DrugChunk', 0)
    entity_count = stats['vertices'].get('DrugEntity', 0)
    relation_count = stats['vertices'].get('DrugRelation', 0)

    print(f"Documents (DrugDoc): {doc_count:,}")
    print(f"Chunks (DrugChunk): {chunk_count:,}")
    print(f"Entities (DrugEntity): {entity_count:,}")
    print(f"Relations (DrugRelation): {relation_count:,}")

    # Calculate ratios and averages
    avg_chunks_per_doc = chunk_count / doc_count if doc_count > 0 else 0
    avg_entities_per_chunk = (stats['edges'].get('CHUNK_HAS_ENTITY', 0)) / chunk_count if chunk_count > 0 else 0
    avg_relationships_per_entity = (stats['edges'].get('ENTITY_RELATED_TO', 0)) / entity_count if entity_count > 0 else 0

    print(f"\nGraph Quality Metrics:")
    print("-" * 40)
    print(f"Average chunks per document: {avg_chunks_per_doc:.1f}")
    print(f"Average entities per chunk: {avg_entities_per_chunk:.1f}")
    print(f"Average relationships per entity: {avg_relationships_per_entity:.1f}")

    # Check expected pipeline stages
    print(f"\nPipeline Stage Status:")
    print("-" * 40)

    if doc_count > 0:
        print(f"[COMPLETE] Document Loading")
        print(f"          Expected: ~1,000+ documents")
        print(f"          Actual: {doc_count} documents")
    else:
        print(f"[PENDING] Document Loading")

    if chunk_count > 0:
        print(f"[COMPLETE] Semantic Chunking")
        print(f"          Expected: ~3,000+ chunks")
        print(f"          Actual: {chunk_count} chunks")
        print(f"          Quality: {avg_chunks_per_doc:.1f} chunks/doc")
    else:
        print(f"[PENDING] Semantic Chunking")

    if entity_count > 0:
        print(f"[COMPLETE] Entity Extraction")
        print(f"          Expected: ~5,000+ entities")
        print(f"          Actual: {entity_count} entities")
        print(f"          Quality: {avg_entities_per_chunk:.1f} entities/chunk")
    else:
        print(f"[PENDING] Entity Extraction")

    if relation_count > 0:
        print(f"[COMPLETE] Relationship Extraction")
        print(f"          Expected: ~10,000+ relationships")
        print(f"          Actual: {relation_count} relationships")
        print(f"          Quality: {avg_relationships_per_entity:.1f} relationships/entity")
    else:
        print(f"[PENDING] Relationship Extraction")

    # Check for required vertex/edge types
    print(f"\nSchema Validation:")
    print("-" * 40)

    required_vertices = ['DrugDoc', 'DrugChunk', 'DrugEntity']
    required_edges = ['DOC_HAS_CHUNK', 'CHUNK_HAS_ENTITY', 'ENTITY_RELATED_TO']

    missing_vertices = [v for v in required_vertices if v not in stats['vertices'] or stats['vertices'][v] == 0]
    missing_edges = [e for e in required_edges if e not in stats['edges'] or stats['edges'][e] == 0]

    if not missing_vertices:
        print(f"[VALID] All required vertex types present")
    else:
        print(f"[INVALID] Missing or empty vertex types: {', '.join(missing_vertices)}")

    if not missing_edges:
        print(f"[VALID] All required edge types present")
    else:
        print(f"[INVALID] Missing or empty edge types: {', '.join(missing_edges)}")

    # Next steps recommendation
    print(f"\nRecommended Next Steps:")
    print("-" * 40)

    if chunk_count == 0 and doc_count > 0:
        print("1. Run: from graph_construction import create_semantic_chunks")
        print("2. Run: from graph_construction import extract_medical_entities")
        print("3. Run: from graph_construction import extract_medical_relationships")
        print("4. Create vector embeddings")
        print("5. Test GraphRAG queries")

    elif entity_count == 0 and chunk_count > 0:
        print("1. Run: from graph_construction import extract_medical_entities")
        print("2. Run: from graph_construction import extract_medical_relationships")
        print("3. Create vector embeddings")
        print("4. Test GraphRAG queries")

    elif relation_count == 0 and entity_count > 0:
        print("1. Run: from graph_construction import extract_medical_relationships")
        print("2. Create vector embeddings")
        print("3. Test GraphRAG queries")

    else:
        print("Graph construction appears complete!")
        print("1. Test GraphRAG queries")
        print("2. Build evaluation pipelines")
        print("3. Create comparison dashboard")

    return {
        'success': True,
        'graph_name': conn_manager.graph_name,
        'total_vertices': stats['total_vertices'],
        'total_edges': stats['total_edges'],
        'vertices': stats['vertices'],
        'edges': stats['edges'],
        'doc_count': doc_count,
        'chunk_count': chunk_count,
        'entity_count': entity_count,
        'relation_count': relation_count,
        'avg_chunks_per_doc': avg_chunks_per_doc,
        'avg_entities_per_chunk': avg_entities_per_chunk,
        'avg_relationships_per_entity': avg_relationships_per_entity,
        'pipeline_complete': all([
            doc_count > 0,
            chunk_count > 0,
            entity_count > 0,
            relation_count > 0
        ])
    }


def main():
    """Main function to check graph state"""
    result = check_graph_state()
    return result


if __name__ == "__main__":
    main()
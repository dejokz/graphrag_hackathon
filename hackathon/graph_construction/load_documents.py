"""
Load all FDA documents into graphRAG_hackathon DrugDoc vertices
Refactored to use environment variables and modular connection management
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Get the project root directory
project_root = Path(__file__).parent.parent.parent
hackathon_root = Path(__file__).parent.parent

# Add project root and hackathon root to path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(hackathon_root))

# Change to hackathon directory to ensure .env is found
os.chdir(str(hackathon_root))

from utils.tigergraph_connection import get_connection_manager
from utils.document_loader import load_documents_jsonl, validate_document
from utils.graph_operations import batch_upsert_vertices


def load_documents_to_graph(dataset_path: str = None, batch_size: int = 100) -> dict:
    """
    Load documents from a JSONL file into the graph

    Args:
        dataset_path: Path to the JSONL file (defaults to processed_medical_dataset.jsonl)
        batch_size: Number of documents to process in each batch

    Returns:
        Dictionary with loading statistics
    """
    if dataset_path is None:
        dataset_path = "hackathon/data/processed_medical_dataset.jsonl"

    print("=== Loading FDA Documents into GraphRAG Hackathon ===\n")

    # Initialize connection manager
    conn_manager = get_connection_manager()

    # Test connection
    if not conn_manager.test_connection():
        print("X Failed to connect to TigerGraph")
        return {'success': False, 'error': 'Connection failed'}

    # Verify DrugDoc vertex type exists
    print(f"\nVerifying DrugDoc vertex type...")
    try:
        count = conn_manager.get_vertex_count('DrugDoc')
        print(f"Current DrugDoc vertices: {count}")
    except Exception as e:
        print(f"DrugDoc exists but has no vertices yet: {e}")

    # Load all documents using utility function
    print(f"\nLoading FDA documents from file...")
    dataset_file = Path(dataset_path)

    if not dataset_file.exists():
        print(f"X Dataset file not found: {dataset_file}")
        print(f"Please ensure the expanded medical dataset has been created.")
        return {'success': False, 'error': f'Dataset file not found: {dataset_file}'}

    documents = load_documents_jsonl(dataset_file)
    print(f"Loaded {len(documents)} documents from file")

    # Validate documents
    print(f"\nValidating documents...")
    valid_documents = []
    invalid_count = 0

    for doc in documents:
        is_valid, errors = validate_document(doc)
        if is_valid:
            valid_documents.append(doc)
        else:
            invalid_count += 1
            if invalid_count <= 5:
                doc_id = doc.get('doc_id', 'unknown')
                print(f"  Invalid document {doc_id}: {', '.join(errors)}")

    print(f"Valid documents: {len(valid_documents)}")
    print(f"Invalid documents: {invalid_count}")

    # Create DrugDoc vertices using batch operations
    print(f"\nCreating DrugDoc vertices...")

    vertex_data = []
    for doc in valid_documents:
        doc_id = doc['doc_id']
        content = doc.get('content', '')

        vertex_data.append({
            'vertex_type': 'DrugDoc',
            'vertex_id': doc_id,
            'attributes': {'content': content}
        })

    # Batch upsert vertices
    start_time = datetime.now()
    created_count, failed_count = batch_upsert_vertices(
        conn_manager,
        vertex_data,
        batch_size=batch_size,
        show_progress=True
    )

    # Final verification
    print(f"\n=== Verification ===")
    try:
        final_count = conn_manager.get_vertex_count('DrugDoc')
        print(f"DrugDoc vertices in graph: {final_count}")
    except Exception as e:
        print(f"Verification failed: {e}")

    elapsed_total = (datetime.now() - start_time).total_seconds()

    result = {
        'success': True,
        'documents_loaded': created_count,
        'documents_failed': failed_count,
        'total_documents_in_file': len(documents),
        'valid_documents': len(valid_documents),
        'invalid_documents': invalid_count,
        'time_seconds': elapsed_total,
        'rate_docs_per_sec': created_count / elapsed_total if elapsed_total > 0 else 0,
        'final_vertex_count': final_count if 'final_count' in locals() else 0
    }

    print(f"\n=== LOADING COMPLETE ===")
    print(f"Documents loaded: {created_count}")
    print(f"Failed: {failed_count}")
    print(f"Time: {elapsed_total:.1f} seconds")
    print(f"Rate: {result['rate_docs_per_sec']:.1f} docs/sec")
    print(f"\nVertex types: DrugDoc, DrugChunk, DrugEntity, DrugRelation")
    print(f"Edge types: DOC_HAS_CHUNK, CHUNK_HAS_ENTITY, CHUNK_MENTIONS_RELATION, DOC_HAS_ENTITY, ENTITY_RELATED_TO")
    print(f"\nNext steps:")
    print(f"1. Semantic chunking (2048 tokens, 256 overlap)")
    print(f"2. Entity extraction (drug, disease, protein, pathway, etc.)")
    print(f"3. Relationship extraction (TREATS, INHIBITS, etc.)")
    print(f"4. Vector embeddings (768-dim)")
    print(f"5. GraphRAG validation with 5 drug mechanism questions")

    return result


def main():
    """Main function to load documents into the graph"""
    result = load_documents_to_graph()
    return result


if __name__ == "__main__":
    main()
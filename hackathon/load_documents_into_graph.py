"""
Load all FDA documents into graphRAG_hackathon DrugDoc vertices
Refactored to use environment variables and modular connection management
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tigergraph_connection import get_connection_manager
from utils.document_loader import load_documents_jsonl
from utils.graph_operations import batch_upsert_vertices

import json
from datetime import datetime


def main():
    """Main function to load documents into the graph"""

    print("=== Loading FDA Documents into GraphRAG Hackathon ===\n")

    # Initialize connection manager
    conn_manager = get_connection_manager()

    # Test connection
    if not conn_manager.test_connection():
        print("X Failed to connect to TigerGraph")
        return

    # Verify DrugDoc vertex type exists
    print(f"\nVerifying DrugDoc vertex type...")
    try:
        count = conn_manager.get_vertex_count('DrugDoc')
        print(f"Current DrugDoc vertices: {count}")
    except Exception as e:
        print(f"DrugDoc exists but has no vertices yet: {e}")

    # Load all documents using utility function
    print(f"\nLoading FDA documents from file...")
    dataset_path = Path("hackathon/data/processed_medical_dataset.jsonl")

    if not dataset_path.exists():
        print(f"X Dataset file not found: {dataset_path}")
        print(f"Please ensure the expanded medical dataset has been created.")
        return

    documents = load_documents_jsonl(dataset_path)
    print(f"Loaded {len(documents)} documents from file")

    # Create DrugDoc vertices using batch operations
    print(f"\nCreating DrugDoc vertices...")

    vertex_data = []
    for doc in documents:
        doc_id = doc['doc_id']
        content = doc.get('content', '')

        if not content or len(content.strip()) < 10:
            print(f"Skipping empty document: {doc_id}")
            continue

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
        batch_size=100,
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
    print(f"\n=== LOADING COMPLETE ===")
    print(f"Documents loaded: {created_count}")
    print(f"Failed: {failed_count}")
    print(f"Time: {elapsed_total:.1f} seconds")
    print(f"Rate: {created_count/elapsed_total:.1f} docs/sec")
    print(f"\nVertex types: DrugDoc, DrugChunk, DrugEntity, DrugRelation")
    print(f"Edge types: DOC_HAS_CHUNK, CHUNK_HAS_ENTITY, CHUNK_MENTIONS_RELATION, DOC_HAS_ENTITY, ENTITY_RELATED_TO")
    print(f"\nNext steps:")
    print(f"1. Semantic chunking (2048 tokens, 256 overlap)")
    print(f"2. Entity extraction (drug, disease, protein, pathway, etc.)")
    print(f"3. Relationship extraction (TREATS, INHIBITS, etc.)")
    print(f"4. Vector embeddings (768-dim)")
    print(f"5. GraphRAG validation with 5 drug mechanism questions")


if __name__ == "__main__":
    main()
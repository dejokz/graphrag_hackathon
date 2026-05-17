"""
Semantic Chunking for DrugDoc vertices
Chunks documents into configurable token sizes with overlap
Creates DrugChunk vertices and DOC_HAS_CHUNK edges
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
from utils.graph_operations import batch_upsert_vertices, batch_upsert_edges
import tiktoken


def create_semantic_chunks(chunk_size: int = 2048, chunk_overlap: int = 256,
                          batch_size: int = 100) -> dict:
    """
    Create semantic chunks from DrugDoc vertices

    Args:
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks in tokens
        batch_size: Number of chunks to process in each batch

    Returns:
        Dictionary with chunking statistics
    """
    print("=== Semantic Chunking ===\n")
    print(f"CHUNK_SIZE: {chunk_size} tokens")
    print(f"CHUNK_OVERLAP: {chunk_overlap} tokens\n")

    # Initialize connection manager
    conn_manager = get_connection_manager()

    # Test connection
    if not conn_manager.test_connection():
        print("X Failed to connect to TigerGraph")
        return {'success': False, 'error': 'Connection failed'}

    # Get token encoding
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception as e:
        print(f"X Failed to get tokenizer: {e}")
        return {'success': False, 'error': f'Tokenizer error: {e}'}

    # Get all DrugDoc vertices
    print(f"Fetching DrugDoc vertices...")
    try:
        conn = conn_manager.get_connection()
        result = conn.getVertices("DrugDoc", limit=10000)
        documents = result if isinstance(result, list) else result.get("DrugDoc", [])
        print(f"Found {len(documents)} DrugDoc vertices")
    except Exception as e:
        print(f"X Error fetching documents: {e}")
        return {'success': False, 'error': f'Document fetch error: {e}'}

    # Process documents and create chunks
    total_chunks = 0
    total_documents_processed = 0
    failed_documents = 0
    start_time = datetime.now()

    chunk_vertices = []
    chunk_edges = []

    print(f"\nChunking documents...")

    for i, doc in enumerate(documents):
        try:
            doc_id = doc.get("v_id") or doc.get("doc_id")
            attributes = doc.get("attributes", {})

            if not doc_id:
                continue

            content = attributes.get("content", "")

            if not content or len(content.strip()) < 50:
                continue

            # Tokenize content
            tokens = encoding.encode(content)
            num_tokens = len(tokens)

            # Create chunks
            if num_tokens <= chunk_size:
                # Single chunk for short documents
                chunk_vertices.append({
                    'vertex_type': 'DrugChunk',
                    'vertex_id': f"{doc_id}_chunk_0",
                    'attributes': {
                        'document_id': doc_id,
                        'text': content,
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                })

                chunk_edges.append({
                    'edge_type': 'DOC_HAS_CHUNK',
                    'source_type': 'DrugDoc',
                    'source_id': doc_id,
                    'target_type': 'DrugChunk',
                    'target_id': f"{doc_id}_chunk_0",
                    'attributes': {
                        'chunk_index': 0,
                        'total_chunks': 1
                    }
                })

                total_chunks += 1
            else:
                # Multiple chunks with overlap for long documents
                chunk_idx = 0
                start = 0
                total_chunks_for_doc = 0

                while start < num_tokens:
                    end = min(start + chunk_size, num_tokens)
                    chunk_tokens = tokens[start:end]
                    chunk_text = encoding.decode(chunk_tokens)

                    chunk_id = f"{doc_id}_chunk_{chunk_idx}"

                    chunk_vertices.append({
                        'vertex_type': 'DrugChunk',
                        'vertex_id': chunk_id,
                        'attributes': {
                            'document_id': doc_id,
                            'text': chunk_text,
                            'chunk_index': chunk_idx,
                            'total_chunks': 0  # Will be updated after counting
                        }
                    })

                    chunk_edges.append({
                        'edge_type': 'DOC_HAS_CHUNK',
                        'source_type': 'DrugDoc',
                        'source_id': doc_id,
                        'target_type': 'DrugChunk',
                        'target_id': chunk_id,
                        'attributes': {
                            'chunk_index': chunk_idx,
                            'total_chunks': 0  # Will be updated after counting
                        }
                    })

                    total_chunks += 1
                    total_chunks_for_doc += 1
                    chunk_idx += 1

                    # Move to next chunk with overlap
                    start = end - chunk_overlap if end < num_tokens else end

                # Update total_chunks in attributes
                for chunk_data in chunk_vertices[-total_chunks_for_doc:]:
                    chunk_data['attributes']['total_chunks'] = total_chunks_for_doc

                for edge_data in chunk_edges[-total_chunks_for_doc:]:
                    edge_data['attributes']['total_chunks'] = total_chunks_for_doc

            total_documents_processed += 1

            # Progress update and batch processing
            if (i + 1) % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_documents_processed / elapsed

                # Process current batch
                if chunk_vertices:
                    vertex_success, vertex_failed = batch_upsert_vertices(
                        conn_manager, chunk_vertices, batch_size=50, show_progress=False
                    )
                    edge_success, edge_failed = batch_upsert_edges(
                        conn_manager, chunk_edges, batch_size=50, show_progress=False
                    )

                    failed_documents += vertex_failed + edge_failed
                    chunk_vertices.clear()
                    chunk_edges.clear()

                print(f"  Progress: {i+1}/{len(documents)} documents, {total_chunks} chunks ({rate:.1f} docs/sec)")

        except Exception as e:
            failed_documents += 1
            if failed_documents <= 5:
                doc_id = doc.get("v_id", doc.get("doc_id", "unknown"))
                print(f"  Failed to process document {doc_id}: {e}")

    # Process remaining chunks in final batch
    if chunk_vertices:
        vertex_success, vertex_failed = batch_upsert_vertices(
            conn_manager, chunk_vertices, batch_size=50, show_progress=False
        )
        edge_success, edge_failed = batch_upsert_edges(
            conn_manager, chunk_edges, batch_size=50, show_progress=False
        )
        failed_documents += vertex_failed + edge_failed

    # Verification
    print(f"\n=== Verification ===")
    try:
        doc_count = conn_manager.get_vertex_count('DrugDoc')
        chunk_count = conn_manager.get_vertex_count('DrugChunk')
        edge_count = conn_manager.get_edge_count('DOC_HAS_CHUNK')

        print(f"DrugDoc vertices: {doc_count}")
        print(f"DrugChunk vertices: {chunk_count}")
        print(f"DOC_HAS_CHUNK edges: {edge_count}")

        avg_chunks_per_doc = total_chunks / total_documents_processed if total_documents_processed > 0 else 0
        print(f"Average chunks per document: {avg_chunks_per_doc:.1f}")

    except Exception as e:
        print(f"Verification failed: {e}")

    elapsed_total = (datetime.now() - start_time).total_seconds()

    result = {
        'success': True,
        'documents_processed': total_documents_processed,
        'chunks_created': total_chunks,
        'failed_documents': failed_documents,
        'time_seconds': elapsed_total,
        'rate_docs_per_sec': total_documents_processed / elapsed_total if elapsed_total > 0 else 0,
        'avg_chunks_per_doc': total_chunks / total_documents_processed if total_documents_processed > 0 else 0
    }

    print(f"\n=== CHUNKING COMPLETE ===")
    print(f"Documents processed: {total_documents_processed}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Failed documents: {failed_documents}")
    print(f"Time: {elapsed_total:.1f} seconds")
    print(f"Rate: {result['rate_docs_per_sec']:.1f} docs/sec")
    print(f"\nNext step: Entity extraction (drug, disease, protein, pathway, etc.)")

    return result


def main():
    """Main function to run semantic chunking"""
    result = create_semantic_chunks()
    return result


if __name__ == "__main__":
    main()
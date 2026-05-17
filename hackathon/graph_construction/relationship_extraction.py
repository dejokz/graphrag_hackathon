"""
Relationship Extraction from DrugChunk vertices
Extracts relationships: TREATS, INHIBITS, ACTIVATES, TARGETS, METABOLIZED_BY, ASSOCIATED_WITH, CONTRAINDICATED_FOR, REGULATES, DIAGNOSED_BY, AFFECTS, CAUSES
Creates DrugRelation vertices and ENTITY_RELATED_TO edges
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, List, Tuple

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


# Relationship patterns with comprehensive coverage
RELATIONSHIP_PATTERNS = {
    'TREATS': [
        r'treats?', r'effective for', r'indicated for', r'management of',
        r'therapy for', r'treatment of', r'used to treat', r'helps treat'
    ],
    'INHIBITS': [
        r'inhibits?', r'blocks?', r'prevents?', r'suppresses?', r'reduces?',
        r'decreases?', r'lowers?', r'antagonizes?', r'counteracts?'
    ],
    'ACTIVATES': [
        r'activates?', r'stimulates?', r'enhances?', r'increases?', r'boosts?',
        r'promotes?', r'induces?', r'upregulates?', r'potentiates?'
    ],
    'TARGETS': [
        r'targets?', r'binds to', r'receptor for', r'acts on', r'interacts with',
        r'affinity for', r'selective for', r'specific for'
    ],
    'METABOLIZED_BY': [
        r'metabolized by', r'cleared by', r'processed by', r'eliminated by',
        r'excreted by', r'broken down by', r'degraded by'
    ],
    'ASSOCIATED_WITH': [
        r'associated with', r'linked to', r'correlated with', r'related to',
        r'connected to', r'accompanied by', r'seen with'
    ],
    'CONTRAINDICATED_FOR': [
        r'contraindicated', r'not recommended', r'avoid in', r'should not be used',
        r'use caution', r'caution in', r'relative contraindication'
    ],
    'REGULATES': [
        r'regulates?', r'modulates?', r'controls?', r'influences?', r'affects?',
        r'impacts?', r'mediates?', r'coordinates?'
    ],
    'DIAGNOSED_BY': [
        r'diagnosed by', r'detected using', r'identified by', r'confirmed by',
        r'diagnosed via', r'assessed using', r'evaluated with'
    ],
    'AFFECTS': [
        r'affects?', r'impacts?', r'influences?', r'changes?', r'alters?',
        r'modifies?', r'transforms?'
    ],
    'CAUSES': [
        r'causes?', r'leads to', r'results in', r'produces?', r'induces?',
        r'triggers?', r'precipitates?', r'brings about'
    ],
    'PREVENTS': [
        r'prevents?', r'protects against', r'reduces risk of', r'decreases risk of',
        r'lowers risk of', r'avoids?', r'ward off'
    ],
    'INTERACTS_WITH': [
        r'interacts with', r'interaction with', r'interacts?', r'may interact',
        r'potential interaction', r'drug interaction'
    ]
}


# Key medical entities for relationship extraction
KEY_ENTITIES = {
    # Drugs
    'lisinopril': 'drug', 'losartan': 'drug', 'valsartan': 'drug', 'candesartan': 'drug',
    'metformin': 'drug', 'statin': 'drug', 'atorvastatin': 'drug', 'simvastatin': 'drug',
    'canagliflozin': 'drug', 'empagliflozin': 'drug', 'dapagliflozin': 'drug',
    'sitagliptin': 'drug', 'glipizide': 'drug', 'glyburide': 'drug',
    'insulin': 'drug', 'metoprolol': 'drug', 'propranolol': 'drug',
    'amlodipine': 'drug', 'diltiazem': 'drug', 'hydrochlorothiazide': 'drug',
    'aspirin': 'drug', 'clopidogrel': 'drug', 'warfarin': 'drug',

    # Proteins
    'ACE': 'protein', 'angiotensin-converting enzyme': 'protein',
    'SGLT2': 'protein', 'sodium-glucose cotransporter-2': 'protein',
    'SGLT1': 'protein', 'sodium-glucose cotransporter-1': 'protein',
    'GLP-1': 'protein', 'glucagon-like peptide-1': 'protein',
    'DPP-4': 'protein', 'dipeptidyl peptidase-4': 'protein',
    'HMG-CoA reductase': 'protein',
    'AMPK': 'protein', 'mTOR': 'protein', 'PI3K': 'protein',

    # Diseases
    'hypertension': 'disease', 'high blood pressure': 'disease',
    'diabetes': 'disease', 'diabetes mellitus': 'disease', 'type 2 diabetes': 'disease',
    'heart failure': 'disease', 'myocardial infarction': 'disease', 'stroke': 'disease',
    'chronic kidney disease': 'disease', 'renal impairment': 'disease',

    # Organs
    'kidney': 'organ', 'renal': 'organ', 'liver': 'organ', 'heart': 'organ',
    'pancreas': 'organ', 'brain': 'organ', 'lung': 'organ'
}


def extract_medical_relationships(batch_size: int = 100, show_progress: bool = True) -> dict:
    """
    Extract medical relationships from DrugChunk vertices

    Args:
        batch_size: Number of chunks to process in each batch
        show_progress: Whether to show progress updates

    Returns:
        Dictionary with extraction statistics
    """
    print("=== Relationship Extraction ===\n")

    # Initialize connection manager
    conn_manager = get_connection_manager()

    # Test connection
    if not conn_manager.test_connection():
        print("X Failed to connect to TigerGraph")
        return {'success': False, 'error': 'Connection failed'}

    # Get all DrugChunk vertices
    print(f"Fetching DrugChunk vertices...")
    try:
        conn = conn_manager.get_connection()
        result = conn.getVertices("DrugChunk", limit=10000)
        chunks = result if isinstance(result, list) else result.get("DrugChunk", [])
        print(f"Found {len(chunks)} DrugChunk vertices")
    except Exception as e:
        print(f"X Error fetching chunks: {e}")
        return {'success': False, 'error': f'Chunk fetch error: {e}'}

    # Extract relationships from chunks
    total_relationships_found = 0
    total_chunks_processed = 0
    failed_chunks = 0
    unique_relationships = {}  # (relation_type, source, target) -> relationship_data
    relationship_edges = []  # ENTITY_RELATED_TO edges
    start_time = datetime.now()

    print(f"\nExtracting relationships from chunks...")

    for i, chunk in enumerate(chunks):
        try:
            chunk_id = chunk.get("v_id") or chunk.get("chunk_id")
            attributes = chunk.get("attributes", {})

            if not chunk_id:
                continue

            text = attributes.get("text", "")
            document_id = attributes.get("document_id", "")

            if not text or len(text.strip()) < 10:
                continue

            text_lower = text.lower()

            # Extract relationships for each pattern type
            for relation_type, patterns in RELATIONSHIP_PATTERNS.items():
                for pattern in patterns:
                    # Look for pattern in text
                    matches = re.finditer(pattern, text_lower, re.IGNORECASE)

                    for match in matches:
                        # Find entities around the match
                        match_start = max(0, match.start() - 150)
                        match_end = min(len(text), match.end() + 150)
                        context = text[match_start:match_end]

                        # Find entities in context
                        entities_in_context = []
                        for entity_name, entity_type in KEY_ENTITIES.items():
                            if entity_name.lower() in context.lower():
                                entities_in_context.append((entity_name, entity_type))

                        # Create relationships between found entities
                        if len(entities_in_context) >= 2:
                            for j in range(len(entities_in_context)):
                                for k in range(j + 1, len(entities_in_context)):
                                    source_entity, source_type = entities_in_context[j]
                                    target_entity, target_type = entities_in_context[k]

                                    # Create relationship key
                                    rel_key = (relation_type, source_entity, target_entity)

                                    # Store unique relationship
                                    if rel_key not in unique_relationships:
                                        rel_id = f"rel_{relation_type.lower()}_{source_entity.lower().replace(' ', '_')}_{target_entity.lower().replace(' ', '_')}"

                                        unique_relationships[rel_key] = {
                                            'relation_id': rel_id,
                                            'relation_type': relation_type,
                                            'source_entity': source_entity,
                                            'target_entity': target_entity,
                                            'source_type': source_type,
                                            'target_type': target_type,
                                            'description': f'{source_entity} {relation_type.lower()} {target_entity}'
                                        }

                                    # Create ENTITY_RELATED_TO edge
                                    source_entity_id = f"entity_{source_entity.lower().replace(' ', '_').replace('-', '_')}"
                                    target_entity_id = f"entity_{target_entity.lower().replace(' ', '_').replace('-', '_')}"

                                    relationship_edges.append({
                                        'edge_type': 'ENTITY_RELATED_TO',
                                        'source_type': 'DrugEntity',
                                        'source_id': source_entity_id,
                                        'target_type': 'DrugEntity',
                                        'target_id': target_entity_id,
                                        'attributes': {
                                            'relation_type': relation_type,
                                            'confidence': 0.7,
                                            'document_id': document_id,
                                            'chunk_id': chunk_id
                                        }
                                    })

                                    total_relationships_found += 1

            total_chunks_processed += 1

            # Progress update and batch processing
            if show_progress and (i + 1) % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_chunks_processed / elapsed

                # Process current batch of edges
                if relationship_edges:
                    edge_success, edge_failed = batch_upsert_edges(
                        conn_manager, relationship_edges, batch_size=50, show_progress=False
                    )
                    failed_chunks += edge_failed
                    relationship_edges.clear()

                print(f"  Progress: {i+1}/{len(chunks)} chunks, {len(unique_relationships)} unique relationships ({rate:.1f} chunks/sec)")

        except Exception as e:
            failed_chunks += 1
            if failed_chunks <= 5:
                chunk_id = chunk.get("v_id", chunk.get("chunk_id", "unknown"))
                print(f"  Failed to process chunk {chunk_id}: {e}")

    # Process remaining edges in final batch
    if relationship_edges:
        edge_success, edge_failed = batch_upsert_edges(
            conn_manager, relationship_edges, batch_size=50, show_progress=False
        )
        failed_chunks += edge_failed

    # Create unique DrugRelation vertices
    print(f"\nCreating {len(unique_relationships)} unique DrugRelation vertices...")
    relation_vertices = [
        {
            'vertex_type': 'DrugRelation',
            'vertex_id': rel_data['relation_id'],
            'attributes': {
                'relation_type': rel_data['relation_type'],
                'source_entity': rel_data['source_entity'],
                'target_entity': rel_data['target_entity'],
                'source_type': rel_data['source_type'],
                'target_type': rel_data['target_type'],
                'description': rel_data['description']
            }
        }
        for rel_data in unique_relationships.values()
    ]

    vertex_success, vertex_failed = batch_upsert_vertices(
        conn_manager, relation_vertices, batch_size=50, show_progress=True
    )

    # Verification
    print(f"\n=== Verification ===")
    try:
        relation_count = conn_manager.get_vertex_count('DrugRelation')
        entity_relation_count = conn_manager.get_edge_count('ENTITY_RELATED_TO')
        entity_count = conn_manager.get_vertex_count('DrugEntity')

        print(f"DrugEntity vertices: {entity_count}")
        print(f"DrugRelation vertices: {relation_count}")
        print(f"ENTITY_RELATED_TO edges: {entity_relation_count}")
        print(f"Unique relationships: {len(unique_relationships)}")

        # Show relationship type distribution
        relation_type_counts = {}
        for rel_data in unique_relationships.values():
            rtype = rel_data['relation_type']
            relation_type_counts[rtype] = relation_type_counts.get(rtype, 0) + 1

        print(f"\nRelationship type distribution:")
        for rtype, count in sorted(relation_type_counts.items()):
            print(f"  {rtype}: {count} relationships")

    except Exception as e:
        print(f"Verification failed: {e}")

    elapsed_total = (datetime.now() - start_time).total_seconds()

    result = {
        'success': True,
        'chunks_processed': total_chunks_processed,
        'unique_relationships': len(unique_relationships),
        'total_relationship_mentions': total_relationships_found,
        'failed_chunks': failed_chunks,
        'time_seconds': elapsed_total,
        'rate_chunks_per_sec': total_chunks_processed / elapsed_total if elapsed_total > 0 else 0,
        'avg_relationships_per_chunk': total_relationships_found / total_chunks_processed if total_chunks_processed > 0 else 0,
        'relationship_type_distribution': relation_type_counts
    }

    print(f"\n=== RELATIONSHIP EXTRACTION COMPLETE ===")
    print(f"Chunks processed: {total_chunks_processed}")
    print(f"Unique relationships: {len(unique_relationships)}")
    print(f"Total relationship mentions: {total_relationships_found}")
    print(f"Failed chunks: {failed_chunks}")
    print(f"Time: {elapsed_total:.1f} seconds")
    print(f"Rate: {result['rate_chunks_per_sec']:.1f} chunks/sec")
    print(f"Avg relationships per chunk: {result['avg_relationships_per_chunk']:.1f}")
    print(f"\nKnowledge graph ready for GraphRAG validation!")

    return result


def main():
    """Main function to run relationship extraction"""
    result = extract_medical_relationships()
    return result


if __name__ == "__main__":
    main()
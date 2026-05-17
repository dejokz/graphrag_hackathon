"""
Entity Extraction from DrugChunk vertices
Extracts medical entities: drug, disease, protein, pathway, side_effect, population, procedure, organ, gene
Creates DrugEntity vertices and CHUNK_HAS_ENTITY edges
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, List, Set

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


# Medical entity types with comprehensive coverage
ENTITY_TYPES = {
    'drug': [
        # Diabetes medications
        'metformin', 'sitagliptin', 'saxagliptin', 'linagliptin', 'alogliptin',
        'canagliflozin', 'empagliflozin', 'dapagliflozin', 'ertugliflozin',
        'semaglutide', 'liraglutide', 'exenatide', 'dulaglutide', 'lixisenatide',
        'insulin glargine', 'insulin detemir', 'insulin degludec', 'insulin lispro',
        'glipizide', 'glyburide', 'glimepiride', 'repaglinide', 'nateglinide',
        'pioglitazone', 'rosiglitazone', 'acarbose', 'miglitol', 'colesevelam',

        # Cardiovascular medications
        'lisinopril', 'losartan', 'valsartan', 'candesartan', 'irbesartan',
        'atorvastatin', 'simvastatin', 'rosuvastatin', 'pravastatin', 'fluvastatin',
        'metoprolol', 'propranolol', 'carvedilol', 'bisoprolol', 'atenolol',
        'amlodipine', 'diltiazem', 'verapamil', 'nifedipine', 'felodipine',
        'furosemide', 'hydrochlorothiazide', 'spironolactone', 'triamterene', 'amiloride',
        'clopidogrel', 'warfarin', 'dabigatran', 'rivaroxaban', 'apixaban',
        'digoxin', 'amiodarone', 'sotalol', 'flecainide', 'propafenone',

        # General medications
        'aspirin', 'ibuprofen', 'naproxen', 'acetaminophen',
        'amoxicillin', 'azithromycin', 'doxycycline', 'ciprofloxacin', 'levofloxacin',
        'omeprazole', 'famotidine', 'ondansetron', 'albuterol', 'fluticasone',
        'sertraline', 'fluoxetine', 'gabapentin', 'pregabalin', 'duloxetine'
    ],

    'disease': [
        'hypertension', 'high blood pressure', 'diabetes', 'diabetes mellitus', 'type 2 diabetes',
        'type 1 diabetes', 'hyperglycemia', 'hypoglycemia', 'cardiovascular disease',
        'heart failure', 'myocardial infarction', 'heart attack', 'stroke', 'ischemic stroke',
        'chronic kidney disease', 'renal impairment', 'nephropathy', 'kidney failure',
        'retinopathy', 'neuropathy', 'hyperlipidemia', 'dyslipidemia', 'hypercholesterolemia',
        'atherosclerosis', 'coronary artery disease', 'angina', 'arrhythmia',
        'depression', 'anxiety', 'asthma', 'copd', 'arthritis', 'osteoporosis'
    ],

    'protein': [
        'ACE', 'angiotensin-converting enzyme', 'SGLT2', 'sodium-glucose cotransporter-2',
        'SGLT1', 'sodium-glucose cotransporter-1', 'GLP-1', 'glucagon-like peptide-1',
        'DPP-4', 'dipeptidyl peptidase-4', 'HMG-CoA reductase', 'beta-2 adrenergic receptor',
        'L-type calcium channel', 'AMPK', 'mTOR', 'MAPK', 'PI3K', 'NF-kappaB', 'NF-κB',
        'JAK', 'STAT', 'Wnt', 'TGF-beta', 'TGF-β', 'insulin receptor', 'GLUT4',
        'ATP-sensitive potassium channel', 'voltage-gated sodium channel'
    ],

    'pathway': [
        'RAAS', 'renin-angiotensin-aldosterone system', 'AMPK signaling', 'mTOR pathway',
        'MAPK pathway', 'PI3K pathway', 'NF-kappaB pathway', 'JAK-STAT pathway', 'Wnt pathway',
        'TGF-beta pathway', 'gluconeogenesis', 'glycolysis', 'lipogenesis', 'cholesterol synthesis',
        'insulin signaling pathway', 'apoptosis pathway', 'inflammatory pathway',
        'coagulation cascade', 'complement system', 'renin-angiotensin system'
    ],

    'side_effect': [
        'hypotension', 'dizziness', 'headache', 'nausea', 'vomiting', 'diarrhea',
        'constipation', 'dry cough', 'angioedema', 'rash', 'hyperkalemia',
        'hypoglycemia', 'weight gain', 'edema', 'fatigue', 'muscle pain', 'myopathy',
        'elevated liver enzymes', 'hepatotoxicity', 'renal impairment', 'renal failure',
        'gastrointestinal bleeding', 'ulcer', 'bradycardia', 'tachycardia', 'palpitations'
    ],

    'population': [
        'elderly', 'geriatric', 'pediatric', 'children', 'adolescents',
        'pregnant', 'pregnancy', 'nursing', 'breastfeeding', 'postpartum',
        'patients with renal impairment', 'patients with hepatic impairment', 'patients with heart failure',
        'diabetics', 'hypertensive patients', 'cardiovascular patients', 'obese patients'
    ],

    'procedure': [
        'dialysis', 'hemodialysis', 'peritoneal dialysis', 'kidney transplantation',
        'coronary artery bypass grafting', 'CABG', 'angioplasty', 'stenting',
        'pacemaker implantation', 'defibrillator implantation', 'cardioversion',
        'endoscopy', 'colonoscopy', 'biopsy', 'imaging', 'CT scan', 'MRI'
    ],

    'organ': [
        'kidney', 'renal', 'liver', 'hepatic', 'heart', 'cardiac', 'brain', 'cerebral',
        'pancreas', 'stomach', 'intestine', 'gastrointestinal', 'lung', 'pulmonary',
        'spleen', 'gallbladder', 'bladder', 'prostate', 'thyroid', 'adrenal gland'
    ]
}


def extract_medical_entities(batch_size: int = 100, show_progress: bool = True) -> dict:
    """
    Extract medical entities from DrugChunk vertices

    Args:
        batch_size: Number of chunks to process in each batch
        show_progress: Whether to show progress updates

    Returns:
        Dictionary with extraction statistics
    """
    print("=== Entity Extraction ===\n")

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

    # Extract entities from chunks
    total_entities_found = 0
    total_chunks_processed = 0
    failed_chunks = 0
    unique_entities = {}  # entity_name -> entity_data
    chunk_entity_edges = []  # CHUNK_HAS_ENTITY edges
    start_time = datetime.now()

    print(f"\nExtracting entities from chunks...")

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
            entities_in_chunk = []

            # Extract entities for each type
            for entity_type, entity_list in ENTITY_TYPES.items():
                for entity_name in entity_list:
                    entity_name_lower = entity_name.lower()

                    if entity_name_lower in text_lower:
                        # Create entity ID if not exists
                        entity_id = f"entity_{entity_name_lower.replace(' ', '_').replace('-', '_')}"

                        if entity_id not in unique_entities:
                            unique_entities[entity_id] = {
                                'entity_id': entity_id,
                                'entity_name': entity_name,
                                'entity_type': entity_type
                            }

                        entities_in_chunk.append({
                            'entity_id': entity_id,
                            'entity_type': entity_type,
                            'entity_name': entity_name
                        })
                        total_entities_found += 1

            # Create CHUNK_HAS_ENTITY edges
            for entity_data in entities_in_chunk:
                chunk_entity_edges.append({
                    'edge_type': 'CHUNK_HAS_ENTITY',
                    'source_type': 'DrugChunk',
                    'source_id': chunk_id,
                    'target_type': 'DrugEntity',
                    'target_id': entity_data['entity_id'],
                    'attributes': {
                        'entity_type': entity_data['entity_type'],
                        'entity_name': entity_data['entity_name'],
                        'document_id': document_id,
                        'confidence': 0.9  # High confidence for exact matches
                    }
                })

            total_chunks_processed += 1

            # Progress update and batch processing
            if show_progress and (i + 1) % batch_size == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                rate = total_chunks_processed / elapsed

                # Process current batch of edges
                if chunk_entity_edges:
                    edge_success, edge_failed = batch_upsert_edges(
                        conn_manager, chunk_entity_edges, batch_size=50, show_progress=False
                    )
                    failed_chunks += edge_failed
                    chunk_entity_edges.clear()

                print(f"  Progress: {i+1}/{len(chunks)} chunks, {len(unique_entities)} unique entities ({rate:.1f} chunks/sec)")

        except Exception as e:
            failed_chunks += 1
            if failed_chunks <= 5:
                chunk_id = chunk.get("v_id", chunk.get("chunk_id", "unknown"))
                print(f"  Failed to process chunk {chunk_id}: {e}")

    # Process remaining edges in final batch
    if chunk_entity_edges:
        edge_success, edge_failed = batch_upsert_edges(
            conn_manager, chunk_entity_edges, batch_size=50, show_progress=False
        )
        failed_chunks += edge_failed

    # Create unique DrugEntity vertices
    print(f"\nCreating {len(unique_entities)} unique DrugEntity vertices...")
    entity_vertices = [
        {
            'vertex_type': 'DrugEntity',
            'vertex_id': entity_data['entity_id'],
            'attributes': {
                'entity_name': entity_data['entity_name'],
                'entity_type': entity_data['entity_type']
            }
        }
        for entity_data in unique_entities.values()
    ]

    vertex_success, vertex_failed = batch_upsert_vertices(
        conn_manager, entity_vertices, batch_size=50, show_progress=True
    )

    # Verification
    print(f"\n=== Verification ===")
    try:
        chunk_count = conn_manager.get_vertex_count('DrugChunk')
        entity_count = conn_manager.get_vertex_count('DrugEntity')
        edge_count = conn_manager.get_edge_count('CHUNK_HAS_ENTITY')

        print(f"DrugChunk vertices: {chunk_count}")
        print(f"DrugEntity vertices: {entity_count}")
        print(f"CHUNK_HAS_ENTITY edges: {edge_count}")

        # Show entity type distribution
        entity_type_counts = {}
        for entity_data in unique_entities.values():
            etype = entity_data['entity_type']
            entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1

        print(f"\nEntity type distribution:")
        for etype, count in sorted(entity_type_counts.items()):
            print(f"  {etype}: {count} entities")

    except Exception as e:
        print(f"Verification failed: {e}")

    elapsed_total = (datetime.now() - start_time).total_seconds()

    result = {
        'success': True,
        'chunks_processed': total_chunks_processed,
        'unique_entities': len(unique_entities),
        'total_entity_mentions': total_entities_found,
        'failed_chunks': failed_chunks,
        'time_seconds': elapsed_total,
        'rate_chunks_per_sec': total_chunks_processed / elapsed_total if elapsed_total > 0 else 0,
        'avg_entities_per_chunk': total_entities_found / total_chunks_processed if total_chunks_processed > 0 else 0,
        'entity_type_distribution': entity_type_counts
    }

    print(f"\n=== ENTITY EXTRACTION COMPLETE ===")
    print(f"Chunks processed: {total_chunks_processed}")
    print(f"Unique entities: {len(unique_entities)}")
    print(f"Total entity mentions: {total_entities_found}")
    print(f"Failed chunks: {failed_chunks}")
    print(f"Time: {elapsed_total:.1f} seconds")
    print(f"Rate: {result['rate_chunks_per_sec']:.1f} chunks/sec")
    print(f"Avg entities per chunk: {result['avg_entities_per_chunk']:.1f}")
    print(f"\nNext step: Relationship extraction (TREATS, INHIBITS, etc.)")

    return result


def main():
    """Main function to run entity extraction"""
    result = extract_medical_entities()
    return result


if __name__ == "__main__":
    main()
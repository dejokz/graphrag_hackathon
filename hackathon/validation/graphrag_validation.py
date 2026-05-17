"""
GraphRAG Validation for Drug Mechanism Questions
Implements semantic retrieval + graph traversal to answer questions
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Get the project root directory
project_root = Path(__file__).parent.parent.parent
hackathon_root = Path(__file__).parent.parent

# Add project root and hackathon root to path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(hackathon_root))

# Change to hackathon directory to ensure .env is found
os.chdir(str(hackathon_root))

from utils.tigergraph_connection import get_connection_manager


# The 5 drug mechanism validation questions
VALIDATION_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the primary mechanism of action of metformin in diabetes treatment?",
        "keywords": ["metformin", "mechanism", "diabetes", "AMPK", "glucose", "liver"]
    },
    {
        "id": 2,
        "question": "How do SGLT2 inhibitors like canagliflozin and empagliflozin work to lower blood glucose?",
        "keywords": ["SGLT2", "canagliflozin", "empagliflozin", "kidney", "glucose", "reabsorption"]
    },
    {
        "id": 3,
        "question": "What is the role of the renin-angiotensin-aldosterone system (RAAS) in lisinopril's mechanism?",
        "keywords": ["lisinopril", "RAAS", "renin", "angiotensin", "ACE", "blood pressure"]
    },
    {
        "id": 4,
        "question": "Compare the mechanisms of statins and ACE inhibitors in cardiovascular protection.",
        "keywords": ["statin", "ACE inhibitor", "cholesterol", "cardiovascular", "mechanism"]
    },
    {
        "id": 5,
        "question": "What are the differences in mechanism between canagliflozin and empagliflozin in kidney function?",
        "keywords": ["canagliflozin", "empagliflozin", "kidney", "function", "difference", "mechanism"]
    }
]


def validate_graphrag_queries(questions: List[Dict[str, Any]] = None) -> dict:
    """
    Validate GraphRAG implementation with drug mechanism questions

    Args:
        questions: List of question dictionaries (defaults to VALIDATION_QUESTIONS)

    Returns:
        Dictionary with validation results
    """
    if questions is None:
        questions = VALIDATION_QUESTIONS

    print("=== GraphRAG Drug Mechanism Validation ===\n")

    # Initialize connection manager
    conn_manager = get_connection_manager()

    # Test connection
    if not conn_manager.test_connection():
        print("X Failed to connect to TigerGraph")
        return {'success': False, 'error': 'Connection failed'}

    print(f"Connected to {conn_manager.graph_name}\n")

    validation_results = []
    start_time = datetime.now()

    # Simple keyword matching for retrieval (simulating semantic search)
    def find_relevant_chunks(question_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find chunks containing relevant keywords"""
        relevant_chunks = []

        # Get all chunks
        try:
            conn = conn_manager.get_connection()
            result = conn.getVertices("DrugChunk", limit=5000)
            chunks = result if isinstance(result, list) else result.get("DrugChunk", [])
        except:
            chunks = []

        # Score chunks based on keyword matches
        for chunk in chunks:
            chunk_id = chunk.get("v_id") or chunk.get("chunk_id")
            attributes = chunk.get("attributes", {})
            text = attributes.get("text", "").lower()
            document_id = attributes.get("document_id", "")

            score = 0
            matched_keywords = []

            for keyword in question_data["keywords"]:
                if keyword.lower() in text:
                    score += 1
                    matched_keywords.append(keyword)

            if score > 0:
                relevant_chunks.append({
                    'chunk_id': chunk_id,
                    'document_id': document_id,
                    'text': attributes.get("text", "")[:300] + "...",
                    'score': score,
                    'matched_keywords': matched_keywords
                })

        # Sort by score and return top 3
        relevant_chunks.sort(key=lambda x: x['score'], reverse=True)
        return relevant_chunks[:3]

    # Find related entities for a chunk
    def find_related_entities(chunk_id: str) -> List[Dict[str, Any]]:
        """Find entities connected to a chunk"""
        related_entities = []

        try:
            conn = conn_manager.get_connection()
            # Get neighbors (entities)
            result = conn.getNeighbors(
                vertexType="DrugChunk",
                vertexId=chunk_id,
                edgeType="CHUNK_HAS_ENTITY",
                targetVertexType="DrugEntity"
            )

            entities = result if isinstance(result, list) else []
            for entity in entities:
                attributes = entity.get("attributes", {})
                related_entities.append({
                    'entity_id': entity.get("v_id"),
                    'entity_type': attributes.get("entity_type", ""),
                    'name': attributes.get("entity_name", "")
                })

        except Exception as e:
            pass

        return related_entities

    # Find relationships between entities
    def find_entity_relationships(entity_name: str) -> List[Dict[str, Any]]:
        """Find relationships involving an entity"""
        relationships = []

        try:
            conn = conn_manager.get_connection()
            # Get entity ID
            entity_id = f"entity_{entity_name.lower().replace(' ', '_').replace('-', '_')}"

            # Get neighbors (related entities)
            result = conn.getNeighbors(
                vertexType="DrugEntity",
                vertexId=entity_id,
                edgeType="ENTITY_RELATED_TO",
                targetVertexType="DrugEntity"
            )

            related = result if isinstance(result, list) else []
            for rel in related:
                attributes = rel.get("attributes", {})
                relationships.append({
                    'relation_type': attributes.get("relation_type", ""),
                    'confidence': attributes.get("confidence", 0)
                })

        except Exception as e:
            pass

        return relationships

    # Process each question
    print(f"Processing {len(questions)} drug mechanism questions...\n")

    for question_data in questions:
        print(f"Question {question_data['id']}: {question_data['question']}")
        print(f"Keywords: {', '.join(question_data['keywords'])}")

        # Find relevant chunks
        relevant_chunks = find_relevant_chunks(question_data)

        question_result = {
            'question_id': question_data['id'],
            'question': question_data['question'],
            'relevant_chunks_found': len(relevant_chunks),
            'entities_found': [],
            'relationships_found': []
        }

        if not relevant_chunks:
            print(f"No relevant chunks found\n")
            print("-" * 80 + "\n")
            validation_results.append(question_result)
            continue

        print(f"\nTop {len(relevant_chunks)} relevant chunks:")

        all_entities = []
        all_relationships = []

        for i, chunk in enumerate(relevant_chunks, 1):
            print(f"\n{i}. Chunk: {chunk['chunk_id']}")
            print(f"   Document: {chunk['document_id']}")
            print(f"   Score: {chunk['score']} (matched: {', '.join(chunk['matched_keywords'])})")
            print(f"   Preview: {chunk['text']}")

            # Find related entities
            entities = find_related_entities(chunk['chunk_id'])
            if entities:
                entity_names = [e['name'] for e in entities]
                print(f"   Related entities: {', '.join(entity_names)}")
                all_entities.extend(entities)

                # Find relationships for each entity
                for entity in entities:
                    relationships = find_entity_relationships(entity['name'])
                    if relationships:
                        for rel in relationships:
                            all_relationships.append({
                                'entity': entity['name'],
                                'relation': rel['relation_type'],
                                'confidence': rel['confidence']
                            })

        # Summary
        if all_entities:
            unique_entities = list(set([e['name'] for e in all_entities]))
            print(f"\nUnique entities found: {', '.join(unique_entities)}")
            question_result['entities_found'] = unique_entities

        if all_relationships:
            print(f"Relationships detected:")
            for rel in all_relationships[:5]:  # Show top 5
                print(f"  - {rel['entity']} -> {rel['relation']} (confidence: {rel['confidence']:.1f})")
            question_result['relationships_found'] = all_relationships

        print(f"\n{'-' * 80}\n")
        validation_results.append(question_result)

    elapsed_total = (datetime.now() - start_time).total_seconds()

    # Get current graph stats
    stats = conn_manager.get_graph_statistics()

    result = {
        'success': True,
        'questions_processed': len(questions),
        'validation_time_seconds': elapsed_total,
        'graph_statistics': stats,
        'question_results': validation_results,
        'avg_relevant_chunks_per_question': sum(r['relevant_chunks_found'] for r in validation_results) / len(validation_results) if validation_results else 0,
        'avg_entities_per_question': sum(len(r['entities_found']) for r in validation_results) / len(validation_results) if validation_results else 0,
        'avg_relationships_per_question': sum(len(r['relationships_found']) for r in validation_results) / len(validation_results) if validation_results else 0
    }

    print("=== VALIDATION COMPLETE ===")
    print(f"GraphRAG implementation tested on {len(questions)} drug mechanism questions")
    print(f"Graph contains: {stats['vertices'].get('DrugDoc', 0)} documents, "
          f"{stats['vertices'].get('DrugChunk', 0)} chunks, "
          f"{stats['vertices'].get('DrugEntity', 0)} entities, "
          f"{stats['edges'].get('ENTITY_RELATED_TO', 0)} relationships")
    print(f"Validation time: {elapsed_total:.1f} seconds")
    print(f"Knowledge graph structure: DrugDoc → DrugChunk → DrugEntity → DrugEntity")

    return result


def main():
    """Main function to run GraphRAG validation"""
    result = validate_graphrag_queries()
    return result


if __name__ == "__main__":
    main()
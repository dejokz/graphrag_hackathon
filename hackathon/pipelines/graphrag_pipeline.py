"""Pipeline 3: GraphRAG. TigerGraph knowledge graph + hybrid retrieval + LLM."""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Add hackathon root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tigergraph_connection import get_connection_manager
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.callbacks import get_openai_callback


@dataclass
class PipelineResult:
    response: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0
    cost_usd: float = 0.0
    pipeline_name: str = "GraphRAG"


GEMINI_FLASH_INPUT_PRICE = 0.0
GEMINI_FLASH_OUTPUT_PRICE = 0.0

# Prompt template for GraphRAG synthesis
GRAPHRAG_PROMPT = """Answer the following question based on the retrieved graph context.
Use the relationships and entities mentioned to provide a comprehensive answer.

Context:
{context}

Question: {question}

Answer:"""


def run(
    question: str,
    graphrag_base_url: str = None,
    graphname: str = None,
    auth: tuple = None,
    method: str = "hybrid",
    top_k: int = 3,
    num_hops: int = 2,
    num_seen_min: int = 1,
    similarity_threshold: float = 0.85,
    chunk_only: bool = True,
    doc_only: bool = False,
    combine: bool = True,
    community_level: int = 2,
) -> PipelineResult:
    """Run a question through GraphRAG with tuned retrieval parameters."""
    # Get configuration from environment
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("API key must be provided via GEMINI_API_KEY environment variable")

    start = time.perf_counter()

    # Step 1: Retrieve relevant context using TigerGraph with text matching
    try:
        conn_mgr = get_connection_manager()
        conn = conn_mgr.get_connection()

        # Extract key terms from the question using the graph structure
        # Query DrugEntity vertices to find relevant entities mentioned in the question
        question_lower = question.lower()

        # Get all entities from the graph
        entities_data = conn.getVertices('DrugEntity', limit=100)

        # Find entities mentioned in the question
        search_terms = []
        entity_matches = {}

        for entity in entities_data:
            attrs = entity.get('attributes', {})
            if isinstance(attrs, dict):
                # Check both name and text fields for drug names
                entity_name = attrs.get('name', '').lower()
                entity_text = attrs.get('text', '').lower()
                entity_id = entity.get('v_id', 'unknown')

                # Check if entity name is mentioned in question
                if entity_name and entity_name in question_lower:
                    search_terms.append(entity_name)
                    entity_matches[entity_name] = entity_id

                # Check if entity text contains terms from question
                if entity_text:
                    # Extract potential drug names from entity text
                    for word in question_lower.split():
                        if len(word) > 3 and word in entity_text:  # Only substantial words
                            if word not in search_terms:
                                search_terms.append(word)
                                entity_matches[word] = entity_id

        # Fallback: extract key words from question if no entities found
        if not search_terms:
            medical_keywords = ['drug', 'medication', 'treatment', 'therapy', 'medicine',
                             'side', 'effect', 'adverse', 'reaction', 'mechanism', 'action',
                             'cardiovascular', 'heart', 'blood', 'pressure', 'sugar', 'diabetes']

            for keyword in medical_keywords:
                if keyword in question_lower and keyword not in search_terms:
                    search_terms.append(keyword)

        print(f"GraphRAG extracted search terms: {search_terms}")

        # Get data based on method
        if method == "hybrid":
            # Get both chunks and entities for hybrid retrieval
            chunks_data = conn.getVertices('DrugChunk', limit=50)
            entities_data = conn.getVertices('DrugEntity', limit=50)

            # Score chunks
            scored_chunks = []
            for chunk in chunks_data:
                attrs = chunk.get('attributes', {})
                if isinstance(attrs, dict) and 'text' in attrs:
                    text = attrs['text'].lower()
                    chunk_id = chunk.get('v_id', 'unknown')
                    score = 0
                    matched_terms = []
                    for term in search_terms:
                        if term in text:
                            count = text.count(term)
                            score += count * 10
                            matched_terms.append(term)
                    if score > 0:
                        scored_chunks.append({
                            'text': attrs['text'],
                            'chunk_id': chunk_id,
                            'score': score,
                            'matched_terms': matched_terms,
                            'type': 'chunk'
                        })

            # Score entities
            scored_entities = []
            for entity in entities_data:
                attrs = entity.get('attributes', {})
                if isinstance(attrs, dict) and 'text' in attrs:
                    text = attrs['text'].lower()
                    entity_id = entity.get('v_id', 'unknown')
                    score = 0
                    matched_terms = []
                    for term in search_terms:
                        if term in text:
                            count = text.count(term)
                            score += count * 5  # Entities get lower weight than chunks
                            matched_terms.append(term)
                    if score > 0:
                        scored_entities.append({
                            'text': attrs['text'],
                            'entity_id': entity_id,
                            'score': score,
                            'matched_terms': matched_terms,
                            'type': 'entity'
                        })

            # Combine and sort by score
            all_items = scored_chunks + scored_entities
            all_items.sort(key=lambda x: x['score'], reverse=True)
            retrieved_items = all_items[:top_k]

        elif method == "community":
            # For community search, focus on chunks
            chunks_data = conn.getVertices('DrugChunk', limit=50)

            scored_chunks = []
            for chunk in chunks_data:
                attrs = chunk.get('attributes', {})
                if isinstance(attrs, dict) and 'text' in attrs:
                    text = attrs['text'].lower()
                    chunk_id = chunk.get('v_id', 'unknown')
                    score = 0
                    matched_terms = []
                    for term in search_terms:
                        if term in text:
                            count = text.count(term)
                            score += count * 10
                            matched_terms.append(term)
                    if score > 0:
                        scored_chunks.append({
                            'text': attrs['text'],
                            'chunk_id': chunk_id,
                            'score': score,
                            'matched_terms': matched_terms,
                            'type': 'chunk'
                        })

            scored_chunks.sort(key=lambda x: x['score'], reverse=True)
            retrieved_items = scored_chunks[:top_k]
        else:
            raise ValueError(f"Unsupported method: {method}")

        print(f"Found {len(retrieved_items)} relevant items for GraphRAG ({method} method)")

        # Extract context from retrieved items
        context_parts = []
        for i, item in enumerate(retrieved_items):
            if isinstance(item, dict) and 'text' in item:
                text = item['text']
                item_type = item.get('type', 'unknown')
                item_id = item.get('chunk_id', item.get('entity_id', 'unknown'))
                if text and text.strip():
                    context_parts.append(f"[{i+1}] {item_type.upper()} ({item_id}): {text}")

        if not context_parts:
            context = "No relevant context found in the knowledge graph."
        else:
            context = "\n\n".join(context_parts)

    except Exception as e:
        print(f"Error retrieving context from TigerGraph: {e}")
        context = "Error retrieving graph context for this question."

    # Step 2: Generate answer using LLM with retrieved graph context
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("DEFAULT_MODEL", "gemini-2.5-flash"),
        google_api_key=api_key,
        temperature=0,
    )

    prompt = GRAPHRAG_PROMPT.format(context=context, question=question)

    with get_openai_callback() as cb:
        answer = llm.invoke(prompt)

    latency = time.perf_counter() - start

    cost = (cb.prompt_tokens / 1_000_000 * GEMINI_FLASH_INPUT_PRICE +
            cb.completion_tokens / 1_000_000 * GEMINI_FLASH_OUTPUT_PRICE)

    return PipelineResult(
        response=answer.content,
        prompt_tokens=cb.prompt_tokens,
        completion_tokens=cb.completion_tokens,
        total_tokens=cb.total_tokens,
        latency_seconds=round(latency, 3),
        cost_usd=round(cost, 6),
        pipeline_name="GraphRAG",
    )
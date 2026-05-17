"""Pipeline 2: Basic RAG. Vector-only retrieval + LLM, no graph traversal."""

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
    pipeline_name: str = "Basic RAG"


GEMINI_FLASH_INPUT_PRICE = 0.0
GEMINI_FLASH_OUTPUT_PRICE = 0.0

# Prompt template for Basic RAG synthesis
BASIC_RAG_PROMPT = """Answer the following question based ONLY on the provided context.
If the context does not contain enough information to answer the question, say so.

Context:
{context}

Question: {question}

Answer:"""


def run(
    question: str,
    api_key: str = None,
    graphrag_base_url: str = None,
    graphname: str = None,
    auth: tuple = None,
    model: str = "gemini-2.5-flash",
    top_k: int = 5,
) -> PipelineResult:
    """Run a question through Basic RAG (vector similarity only, no graph traversal)."""
    # Get configuration from environment
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("API key must be provided via GEMINI_API_KEY environment variable")

    start = time.perf_counter()

    # Step 1: Retrieve relevant chunks via TigerGraph with text matching
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

        print(f"Extracted search terms: {search_terms}")

        # Get all chunks and score them by relevance
        all_chunks = conn.getVertices('DrugChunk', limit=50)  # Get more chunks to filter

        # Score chunks based on term relevance
        scored_chunks = []
        for chunk in all_chunks:
            attrs = chunk.get('attributes', {})
            if isinstance(attrs, dict) and 'text' in attrs:
                text = attrs['text'].lower()
                chunk_id = chunk.get('v_id', 'unknown')

                # Simple relevance scoring
                score = 0
                matched_terms = []
                for term in search_terms:
                    if term in text:
                        # Count occurrences for better scoring
                        count = text.count(term)
                        score += count * 10
                        matched_terms.append(term)

                if score > 0:
                    scored_chunks.append({
                        'text': attrs['text'],
                        'chunk_id': chunk_id,
                        'score': score,
                        'matched_terms': matched_terms
                    })

        # Sort by score and take top_k
        scored_chunks.sort(key=lambda x: x['score'], reverse=True)
        chunks = scored_chunks[:top_k]

        print(f"Found {len(scored_chunks)} relevant chunks for terms: {search_terms}")
        if chunks:
            for i, chunk in enumerate(chunks):
                print(f"  Chunk {i+1}: {chunk['chunk_id']} (score: {chunk['score']})")

    except Exception as e:
        print(f"Error retrieving chunks from TigerGraph: {e}")
        chunks = []

    # Step 2: Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            # Extract text from chunk structure
            text = chunk.get("text", "")
            if text and text.strip():
                context_parts.append(f"[{i+1}] {text}")

    if not context_parts:
        context = "No relevant context found in the knowledge graph."
    else:
        context = "\n\n".join(context_parts)

    # Step 3: Generate answer using LLM with retrieved context
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0,
    )

    prompt = BASIC_RAG_PROMPT.format(context=context, question=question)

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
        pipeline_name="Basic RAG",
    )
"""
Convenience script: Run a single question through all 3 evaluation pipelines
Usage: python hackathon/run_pipelines.py
"""
import sys
import os
from pathlib import Path

# Add hackathon root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pipelines import llm_only, basic_rag, graphrag_pipeline


def run_single_question(question: str = None):
    """Run a single question through all 3 pipelines."""
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file")
        return

    # Get GraphRAG configuration
    graphrag_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:8000")
    graphname = os.getenv("TIGERGRAPH_GRAPH_NAME", "graphRAG_hackathon")

    # Get auth credentials
    username = os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
    password = os.getenv("TIGERGRAPH_PASSWORD", "")
    auth = (username, password) if password else None

    # Default question if none provided
    if question is None:
        question = "What is the mechanism of action of metformin in diabetes treatment?"

    print("=== Running Single Question Through All Pipelines ===\n")
    print(f"Question: {question}\n")

    # Pipeline 1: LLM-Only
    p1 = None
    print("Pipeline 1: LLM-Only")
    try:
        p1 = llm_only.run(question, api_key)
        print(f"  Response: {p1.response}")
        print(f"  Tokens: {p1.total_tokens} (prompt: {p1.prompt_tokens}, completion: {p1.completion_tokens})")
        print(f"  Latency: {p1.latency_seconds}s")
        print(f"  Cost: ${p1.cost_usd}\n")
    except Exception as e:
        print(f"  Error: {e}\n")

    # Pipeline 2: Basic RAG
    p2 = None
    print("Pipeline 2: Basic RAG")
    try:
        p2 = basic_rag.run(question, api_key, graphrag_url, graphname, auth)
        print(f"  Response: {p2.response}")
        print(f"  Tokens: {p2.total_tokens} (prompt: {p2.prompt_tokens}, completion: {p2.completion_tokens})")
        print(f"  Latency: {p2.latency_seconds}s")
        print(f"  Cost: ${p2.cost_usd}\n")
    except Exception as e:
        print(f"  Error: {e}\n")

    # Pipeline 3: GraphRAG
    p3 = None
    print("Pipeline 3: GraphRAG")
    try:
        p3 = graphrag_pipeline.run(question, graphrag_url, graphname, auth)
        print(f"  Response: {p3.response}")
        print(f"  Tokens: {p3.total_tokens} (prompt: {p3.prompt_tokens}, completion: {p3.completion_tokens})")
        print(f"  Latency: {p3.latency_seconds}s")
        print(f"  Cost: ${p3.cost_usd}\n")
    except Exception as e:
        print(f"  Error: {e}\n")

    # Summary
    print("=== Summary ===")
    if p1 and p3 and p1.total_tokens > 0 and p3.total_tokens > 0:
        token_reduction_llm = (p1.total_tokens - p3.total_tokens) / p1.total_tokens * 100
        print(f"Token reduction vs LLM-Only: {token_reduction_llm:.1f}%")

    if p2 and p3 and p2.total_tokens > 0 and p3.total_tokens > 0:
        token_reduction_rag = (p2.total_tokens - p3.total_tokens) / p2.total_tokens * 100
        print(f"Token reduction vs Basic RAG: {token_reduction_rag:.1f}%")

    if p1:
        print(f"\nLLM-Only:   {p1.total_tokens} tokens, {p1.latency_seconds}s latency")
    if p2:
        print(f"Basic RAG:  {p2.total_tokens} tokens, {p2.latency_seconds}s latency")
    if p3:
        print(f"GraphRAG:   {p3.total_tokens} tokens, {p3.latency_seconds}s latency")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a question through all 3 evaluation pipelines")
    parser.add_argument("--question", type=str, help="The question to run", default=None)

    args = parser.parse_args()
    run_single_question(args.question)
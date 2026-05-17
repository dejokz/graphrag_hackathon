"""
Convenience script: Run full evaluation on all 20 evaluation questions
Usage: python hackathon/run_evaluation.py
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add hackathon root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pipelines import llm_only, basic_rag, graphrag_pipeline
from benchmark_service import BenchmarkResult
from evaluation import judge, bertscore_eval


def run_full_evaluation():
    """Run comprehensive evaluation on all questions."""
    # Check for required configuration
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file")
        return False

    # Load evaluation questions
    eval_path = Path("hackathon/eval_questions.json")
    if not eval_path.exists():
        print(f"Error: Evaluation questions file not found at {eval_path}")
        return False

    with open(eval_path, 'r') as f:
        eval_questions = json.load(f)

    print(f"=== Full Evaluation on {len(eval_questions)} Questions ===\n")

    # Get GraphRAG configuration
    graphrag_url = os.getenv("GRAPHRAG_BASE_URL", "http://localhost:8000")
    graphname = os.getenv("TIGERGRAPH_GRAPH_NAME", "graphRAG_hackathon")

    # Get auth credentials
    username = os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
    password = os.getenv("TIGERGRAPH_PASSWORD", "")
    auth = (username, password) if password else None

    # Run all questions through all pipelines
    results = []
    start_time = datetime.now()

    for i, eq in enumerate(eval_questions):
        print(f"[{i+1}/{len(eval_questions)}] {eq['question'][:60]}...")
        print(f"  Category: {eq['category']}")

        try:
            # Run through all 3 pipelines
            p1 = llm_only.run(eq['question'], api_key)
            p2 = basic_rag.run(eq['question'], api_key, graphrag_url, graphname, auth)
            p3 = graphrag_pipeline.run(eq['question'], graphrag_url, graphname, auth)

            result = BenchmarkResult(
                question=eq['question'],
                llm_only=p1.__dict__,
                basic_rag=p2.__dict__,
                graphrag=p3.__dict__,
            )
            results.append(result)

            print(f"  LLM-Only: {p1.total_tokens} tokens, {p1.latency_seconds}s")
            print(f"  Basic RAG: {p2.total_tokens} tokens, {p2.latency_seconds}s")
            print(f"  GraphRAG: {p3.total_tokens} tokens, {p3.latency_seconds}s")

            # Calculate token reduction
            if p2.total_tokens > 0 and p3.total_tokens > 0:
                reduction = (p2.total_tokens - p3.total_tokens) / p2.total_tokens * 100
                print(f"  Token reduction: {reduction:.1f}% vs Basic RAG")

            print()

        except Exception as e:
            print(f"  Error: {e}")
            print()

    elapsed = (datetime.now() - start_time).total_seconds()

    # Compute summary statistics
    summary = {}
    for pipeline in ["llm_only", "basic_rag", "graphrag"]:
        pipeline_results = [getattr(r, pipeline) for r in results if hasattr(r, pipeline)]
        if pipeline_results:
            summary[pipeline] = {
                "avg_tokens": sum(p['total_tokens'] for p in pipeline_results) / len(pipeline_results),
                "avg_latency": sum(p['latency_seconds'] for p in pipeline_results) / len(pipeline_results),
                "total_tokens": sum(p['total_tokens'] for p in pipeline_results),
            }

    # Calculate token reduction
    if summary.get('basic_rag') and summary.get('graphrag'):
        rag_tokens = summary['basic_rag']['avg_tokens']
        gr_tokens = summary['graphrag']['avg_tokens']
        if rag_tokens > 0:
            summary['token_reduction_vs_rag'] = (rag_tokens - gr_tokens) / rag_tokens * 100

    # Save results
    output_path = Path("hackathon/results/evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    results_data = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(eval_questions),
        "evaluation_time_seconds": elapsed,
        "summary": summary,
        "results": [
            {
                "id": r.question,
                "llm_only": r.llm_only,
                "basic_rag": r.basic_rag,
                "graphrag": r.graphrag,
            }
            for r in results
        ]
    }

    with open(output_path, 'w') as f:
        json.dump(results_data, f, indent=2)

    # Run accuracy evaluation
    print("=== Running Accuracy Evaluation ===\n")

    # Prepare answers for each pipeline
    for pipeline_name in ["llm_only", "basic_rag", "graphrag"]:
        print(f"Evaluating {pipeline_name}...")

        answers = [
            {"question_id": r.question, "answer": getattr(r, pipeline_name).response}
            for r in results
        ]

        try:
            # LLM-as-a-Judge
            judge_results = judge.evaluate_batch(eval_questions, answers, api_key, pipeline_name)
            pass_rate = judge.compute_pass_rate(judge_results)

            # BERTScore
            bert_results = bertscore_eval.evaluate_batch(eval_questions, answers, pipeline_name)
            bert_avg = bertscore_eval.compute_avg_f1(bert_results)

            print(f"  LLM-as-a-Judge Pass Rate: {pass_rate:.1f}%")
            print(f"  BERTScore F1 (raw): {bert_avg['avg_f1_raw']:.4f}")
            print(f"  BERTScore F1 (rescaled): {bert_avg['avg_f1_rescaled']:.4f}")
            print()

        except Exception as e:
            print(f"  Error in accuracy evaluation: {e}")
            print()

    # Print final summary
    print("=== Evaluation Complete ===")
    print(f"Questions processed: {len(results)}")
    print(f"Total time: {elapsed:.1f} seconds")
    print(f"Average time per question: {elapsed/len(results):.1f} seconds")
    print(f"\nResults saved to: {output_path}")

    if summary.get('token_reduction_vs_rag'):
        print(f"\n🎯 Token Reduction: {summary['token_reduction_vs_rag']:.1f}% vs Basic RAG")

    if summary.get('graphrag'):
        print(f"\n📊 GraphRAG Average Metrics:")
        print(f"  Tokens: {summary['graphrag']['avg_tokens']:.0f}")
        print(f"  Latency: {summary['graphrag']['avg_latency']:.3f}s")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run full evaluation on all evaluation questions")
    args = parser.parse_args()

    success = run_full_evaluation()
    sys.exit(0 if success else 1)
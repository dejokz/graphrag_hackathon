"""GraphRAG Inference Hackathon - Comparison Dashboard.

Run with: streamlit run hackathon/dashboard/app.py
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add hackathon root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipelines import llm_only, basic_rag, graphrag_pipeline
from benchmark_service import (
    BenchmarkResult,
    compute_summary,
    save_results,
)
from evaluation import judge, bertscore_eval

# Load environment variables
load_dotenv()

# ── Page Config ──
st.set_page_config(
    page_title="GraphRAG Benchmark Dashboard",
    page_icon="🐯",
    layout="wide",
)

# ── Sidebar: Configuration ──
with st.sidebar:
    st.header("Configuration")

    api_key = st.text_input("Google API Key", type="password",
                            value=os.getenv("GEMINI_API_KEY", "") or "your-api-key-here")
    graphrag_url = st.text_input("GraphRAG Service URL",
                                  value=os.getenv("GRAPHRAG_BASE_URL", "http://localhost:8000"))
    graphname = st.text_input("Graph Name", value=os.getenv("TIGERGRAPH_GRAPH_NAME", "graphRAG_hackathon"))
    username = st.text_input("TigerGraph Username", value=os.getenv("TIGERGRAPH_USERNAME", "tigergraph"))
    password = st.text_input("TigerGraph Password", type="password",
                              value=os.getenv("TIGERGRAPH_PASSWORD", "") or "your-password-here")
    model = st.selectbox("LLM Model", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"])

    st.divider()

    st.subheader("GraphRAG Tuning (Path B)")
    gr_method = st.selectbox("Retriever Method", ["hybrid", "community"])
    gr_top_k = st.slider("top_k", 1, 10, 3)
    gr_num_hops = st.slider("num_hops", 1, 4, 2)
    gr_num_seen_min = st.slider("num_seen_min", 1, 5, 1)
    gr_sim_threshold = st.slider("similarity_threshold", 0.5, 1.0, 0.85, 0.05)
    gr_chunk_only = st.checkbox("chunk_only", value=True)
    gr_combine = st.checkbox("combine", value=True)
    gr_community_level = st.slider("community_level", 1, 5, 2)

    st.divider()

    st.subheader("Basic RAG Settings")
    rag_top_k = st.slider("Basic RAG top_k", 1, 20, 5)

# ── Helper: Build auth tuple ──
def get_auth():
    if username and password:
        return (username, password)
    return None

# ── Helper: Run single query ──
def run_benchmark(question: str) -> dict:
    auth = get_auth()
    p1 = llm_only.run(question, api_key, model)
    p2 = basic_rag.run(question, api_key, graphrag_url, graphname, auth, model, rag_top_k)
    p3 = graphrag_pipeline.run(
        question, graphrag_url, graphname, auth,
        method=gr_method,
        top_k=gr_top_k,
        num_hops=gr_num_hops,
        num_seen_min=gr_num_seen_min,
        similarity_threshold=gr_sim_threshold,
        chunk_only=gr_chunk_only,
        combine=gr_combine,
        community_level=gr_community_level,
    )
    return {
        "llm_only": p1,
        "basic_rag": p2,
        "graphrag": p3,
    }

# ── Main Tabs ──
tab1, tab2, tab3, tab4 = st.tabs([
    "Single Query Benchmark",
    "Batch Evaluation",
    "Accuracy Results",
    "Results History",
])

# ════════════════════════════════════════
# Tab 1: Single Query Benchmark
# ════════════════════════════════════════
with tab1:
    st.header("Single Query Benchmark")
    question = st.text_input("Enter your question:", placeholder="e.g., What is the mechanism of action of metformin?")

    if st.button("Run All Pipelines", type="primary", disabled=not (api_key and question)):
        with st.spinner("Running all 3 pipelines..."):
            results = run_benchmark(question)

        # Metrics comparison
        st.subheader("Metrics Comparison")
        col1, col2, col3 = st.columns(3)

        pipelines = [
            ("LLM-Only", results["llm_only"]),
            ("Basic RAG", results["basic_rag"]),
            ("GraphRAG", results["graphrag"]),
        ]

        for col, (name, result) in zip([col1, col2, col3], pipelines):
            with col:
                st.markdown(f"### {name}")
                st.metric("Tokens", f"{result.total_tokens:,}")
                st.metric("Prompt Tokens", f"{result.prompt_tokens:,}")
                st.metric("Completion Tokens", f"{result.completion_tokens:,}")
                st.metric("Latency", f"{result.latency_seconds:.3f}s")
                st.metric("Cost", f"${result.cost_usd:.6f}")

        # Token reduction highlight
        rag_tokens = results["basic_rag"].total_tokens
        gr_tokens = results["graphrag"].total_tokens
        if rag_tokens > 0:
            reduction = (rag_tokens - gr_tokens) / rag_tokens * 100
            st.subheader("Token Reduction")
            if reduction > 0:
                st.success(f"GraphRAG uses **{reduction:.1f}% fewer tokens** than Basic RAG for this query!")
            else:
                st.warning(f"GraphRAG uses **{abs(reduction):.1f}% more tokens** than Basic RAG for this query.")

        # Side-by-side responses
        st.subheader("Responses")
        col1, col2, col3 = st.columns(3)
        for col, (name, result) in zip([col1, col2, col3], pipelines):
            with col:
                st.markdown(f"**{name}**")
                st.markdown(result.response)

        # Token bar chart
        st.subheader("Token Usage Comparison")
        fig = go.Figure(data=[
            go.Bar(name="Prompt Tokens", x=["LLM-Only", "Basic RAG", "GraphRAG"],
                   y=[results["llm_only"].prompt_tokens, results["basic_rag"].prompt_tokens, results["graphrag"].prompt_tokens]),
            go.Bar(name="Completion Tokens", x=["LLM-Only", "Basic RAG", "GraphRAG"],
                   y=[results["llm_only"].completion_tokens, results["basic_rag"].completion_tokens, results["graphrag"].completion_tokens]),
        ])
        fig.update_layout(barmode="stack", title="Token Usage by Pipeline")
        st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════
# Tab 2: Batch Evaluation
# ════════════════════════════════════════
with tab2:
    st.header("Batch Evaluation")
    st.markdown("Run all evaluation questions through all pipelines and collect metrics.")

    # Load eval questions
    eval_path = os.path.join(os.path.dirname(__file__), "eval_questions.json")
    if os.path.exists(eval_path):
        eval_questions = json.loads(open(eval_path).read())
        st.info(f"Loaded {len(eval_questions)} evaluation questions from `eval_questions.json`")

        if st.button("Run Batch Benchmark", type="primary", disabled=not api_key):
            progress = st.progress(0)
            all_results = []

            for i, eq in enumerate(eval_questions):
                with st.spinner(f"[{i+1}/{len(eval_questions)}] {eq['question'][:60]}..."):
                    result = run_benchmark(eq["question"])
                    all_results.append({
                        "id": eq["id"],
                        "question": eq["question"],
                        "category": eq["category"],
                        "reference_answer": eq["reference_answer"],
                        "results": result,
                    })
                progress.progress((i + 1) / len(eval_questions))

            st.session_state["batch_results"] = all_results
            st.success(f"Completed batch evaluation of {len(eval_questions)} questions!")

            # Show summary
            summary = compute_summary_from_batch(all_results)
            st.json(summary)

            # Save results
            output_path = os.path.join(os.path.dirname(__file__), "..", "docs", "batch_results.json")
            save_batch_results(all_results, output_path)
            st.info(f"Results saved to {output_path}")
    else:
        st.warning("No eval_questions.json found. Create one in the hackathon/ directory.")

# ════════════════════════════════════════
# Tab 3: Accuracy Results
# ════════════════════════════════════════
with tab3:
    st.header("Accuracy Evaluation")
    st.markdown("Run LLM-as-a-Judge and BERTScore evaluation on batch results.")

    if "batch_results" not in st.session_state:
        st.warning("Run the batch evaluation first (Tab 2).")
    else:
        batch = st.session_state["batch_results"]

        if st.button("Run Accuracy Evaluation", type="primary", disabled=not api_key):
            # LLM-as-a-Judge
            st.subheader("LLM-as-a-Judge")
            judge_progress = st.progress(0)

            judge_results = {}
            for pipeline_name in ["llm_only", "basic_rag", "graphrag"]:
                st.markdown(f"**Evaluating {pipeline_name}...**")
                answers = [
                    {"question_id": r["id"], "answer": r["results"][pipeline_name].response}
                    for r in batch
                ]
                results = judge.evaluate_batch(eval_questions, answers, api_key, pipeline_name)
                pass_rate = judge.compute_pass_rate(results)
                judge_results[pipeline_name] = {
                    "results": results,
                    "pass_rate": pass_rate,
                }
                st.metric(f"{pipeline_name} Pass Rate", f"{pass_rate}%")
                judge_progress.progress(len(judge_results) / 3)

            st.session_state["judge_results"] = judge_results

            # BERTScore
            st.subheader("BERTScore")
            for pipeline_name in ["llm_only", "basic_rag", "graphrag"]:
                answers = [
                    {"question_id": r["id"], "answer": r["results"][pipeline_name].response}
                    for r in batch
                ]
                bert_results = bertscore_eval.evaluate_batch(
                    eval_questions, answers, pipeline_name
                )
                avg = bertscore_eval.compute_avg_f1(bert_results)
                st.metric(f"{pipeline_name} BERTScore F1 (raw)", f"{avg['avg_f1_raw']:.4f}")
                st.metric(f"{pipeline_name} BERTScore F1 (rescaled)", f"{avg['avg_f1_rescaled']:.4f}")

# ════════════════════════════════════════
# Tab 4: Results History
# ════════════════════════════════════════
with tab4:
    st.header("Results History")

    results_file = st.file_uploader("Load previous results (JSON)", type=["json"])
    if results_file:
        data = json.loads(results_file.read())
        st.json(data)


# ── Helper functions ──
def compute_summary_from_batch(batch_results: list) -> dict:
    """Compute summary metrics from batch results."""
    pipelines = ["llm_only", "basic_rag", "graphrag"]
    summary = {}

    for p in pipelines:
        tokens = [r["results"][p].total_tokens for r in batch_results]
        latencies = [r["results"][p].latency_seconds for r in batch_results]
        summary[p] = {
            "avg_tokens": round(sum(tokens) / len(tokens)) if tokens else 0,
            "avg_latency": round(sum(latencies) / len(latencies), 3) if latencies else 0,
        }

    rag_tokens = summary["basic_rag"]["avg_tokens"]
    gr_tokens = summary["graphrag"]["avg_tokens"]
    if rag_tokens > 0:
        summary["token_reduction_pct"] = round((rag_tokens - gr_tokens) / rag_tokens * 100, 1)

    return summary


def save_batch_results(batch_results: list, path: str):
    """Save batch results to JSON."""
    serializable = []
    for r in batch_results:
        entry = {
            "id": r["id"],
            "question": r["question"],
            "category": r["category"],
            "reference_answer": r["reference_answer"],
        }
        for p in ["llm_only", "basic_rag", "graphrag"]:
            entry[p] = {
                "response": r["results"][p].response,
                "prompt_tokens": r["results"][p].prompt_tokens,
                "completion_tokens": r["results"][p].completion_tokens,
                "total_tokens": r["results"][p].total_tokens,
                "latency_seconds": r["results"][p].latency_seconds,
                "cost_usd": r["results"][p].cost_usd,
            }
        serializable.append(entry)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(serializable, f, indent=2)
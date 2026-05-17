"""Pipeline 1: LLM-Only baseline. No retrieval, just prompt -> response."""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Add hackathon root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    pipeline_name: str = "LLM-Only"


# Gemini 2.0 Flash pricing (free tier, but tracking for display)
GEMINI_FLASH_INPUT_PRICE = 0.0  # free tier
GEMINI_FLASH_OUTPUT_PRICE = 0.0  # free tier


def run(question: str, api_key: str = None, model: str = "gemini-2.5-flash") -> PipelineResult:
    """Run a question through the LLM with no retrieval context."""
    # Get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("API key must be provided either as parameter or via GEMINI_API_KEY environment variable")

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0,
    )

    start = time.perf_counter()
    with get_openai_callback() as cb:
        answer = llm.invoke(question)
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
        pipeline_name="LLM-Only",
    )
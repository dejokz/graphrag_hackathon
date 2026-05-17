"""LLM-as-a-Judge evaluation. Grades answers as PASS/FAIL."""

import json
import time
from dataclasses import dataclass

import httpx


JUDGE_PROMPT = """You are an expert answer evaluator. Your job is to grade whether a candidate answer is factually correct and sufficiently complete compared to a reference answer.

Question: {question}

Reference Answer: {reference_answer}

Candidate Answer: {candidate_answer}

Grade the candidate answer as PASS or FAIL:
- PASS: The candidate answer is factually correct and covers the key information in the reference answer. Minor wording differences are acceptable.
- FAIL: The candidate answer is factually incorrect, contains hallucinations, or misses critical information from the reference answer.

Respond with ONLY a JSON object in this exact format:
{{"grade": "PASS" or "FAIL", "reasoning": "brief explanation"}}"""


@dataclass
class JudgeResult:
    question_id: str
    grade: str  # PASS or FAIL
    reasoning: str
    pipeline_name: str
    latency_seconds: float = 0.0


def evaluate_answer(
    question: str,
    reference_answer: str,
    candidate_answer: str,
    api_key: str,
    question_id: str = "",
    pipeline_name: str = "",
    model: str = "gemini-2.0-flash",
) -> JudgeResult:
    """Use an LLM to grade a candidate answer against a reference."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0,
    )

    prompt = JUDGE_PROMPT.format(
        question=question,
        reference_answer=reference_answer,
        candidate_answer=candidate_answer,
    )

    start = time.perf_counter()
    response = llm.invoke(prompt)
    latency = time.perf_counter() - start

    # Parse JSON from response
    content = response.content.strip()
    # Handle markdown code blocks
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
        grade = parsed.get("grade", "FAIL").upper()
        reasoning = parsed.get("reasoning", "")
    except json.JSONDecodeError:
        # Fallback: check for PASS/FAIL in text
        if "PASS" in content.upper():
            grade = "PASS"
            reasoning = content
        else:
            grade = "FAIL"
            reasoning = content

    return JudgeResult(
        question_id=question_id,
        grade=grade,
        reasoning=reasoning,
        pipeline_name=pipeline_name,
        latency_seconds=round(latency, 3),
    )


def evaluate_batch(
    eval_questions: list[dict],
    answers: list[dict],
    api_key: str,
    pipeline_name: str = "",
    model: str = "gemini-2.0-flash",
) -> list[JudgeResult]:
    """Evaluate a batch of answers against reference answers."""
    results = []

    # Build lookup from question ID to answer
    answer_map = {a["question_id"]: a["answer"] for a in answers}

    for q in eval_questions:
        qid = q.get("id", "")
        candidate = answer_map.get(qid)
        if candidate is None:
            continue

        result = evaluate_answer(
            question=q["question"],
            reference_answer=q["reference_answer"],
            candidate_answer=candidate,
            api_key=api_key,
            question_id=qid,
            pipeline_name=pipeline_name,
            model=model,
        )
        results.append(result)
        print(f"  [{pipeline_name}] {qid}: {result.grade}")

    return results


def compute_pass_rate(results: list[JudgeResult]) -> float:
    """Compute the PASS rate for a set of judge results."""
    if not results:
        return 0.0
    passes = sum(1 for r in results if r.grade == "PASS")
    return round(passes / len(results) * 100, 1)
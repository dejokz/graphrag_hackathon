"""BERTScore evaluation for semantic similarity."""

import json
from dataclasses import dataclass
from pathlib import Path

from bert_score import score as bert_score_fn


@dataclass
class BertScoreResult:
    question_id: str
    pipeline_name: str
    precision: float
    recall: float
    f1: float


def evaluate(
    candidates: list[str],
    references: list[str],
    question_ids: list[str],
    pipeline_name: str = "",
    model_type: str = "microsoft/deberta-xlarge-mnli",
    lang: str = "en",
) -> list[BertScoreResult]:
    """Compute BERTScore for a list of candidate answers against references."""
    P, R, F1 = bert_score_fn(
        candidates,
        references,
        lang=lang,
        model_type=model_type,
        verbose=True,
    )

    results = []
    for i in range(len(candidates)):
        results.append(BertScoreResult(
            question_id=question_ids[i] if i < len(question_ids) else str(i),
            pipeline_name=pipeline_name,
            precision=round(P[i].item(), 4),
            recall=round(R[i].item(), 4),
            f1=round(F1[i].item(), 4),
        ))

    return results


def evaluate_batch(
    eval_questions: list[dict],
    answers: list[dict],
    pipeline_name: str = "",
    model_type: str = "microsoft/deberta-xlarge-mnli",
) -> list[BertScoreResult]:
    """Evaluate a batch of answers using BERTScore."""
    # Build lookup from question ID to answer and reference
    answer_map = {a["question_id"]: a["answer"] for a in answers}

    candidates = []
    references = []
    ids = []

    for q in eval_questions:
        qid = q.get("id", "")
        candidate = answer_map.get(qid)
        if candidate is None:
            continue
        candidates.append(candidate)
        references.append(q["reference_answer"])
        ids.append(qid)

    if not candidates:
        return []

    return evaluate(candidates, references, ids, pipeline_name, model_type)


def compute_avg_f1(results: list[BertScoreResult]) -> dict:
    """Compute average F1 score (raw and rescaled)."""
    if not results:
        return {"avg_f1_raw": 0.0, "avg_f1_rescaled": 0.0}

    f1s = [r.f1 for r in results]
    avg_raw = sum(f1s) / len(f1s)

    # Rescaled BERTScore: map from [0,1] range typical of BERTScore
    # The rescaling formula from the hackathon guide: rescaled = (raw - 0.5) / 0.5
    rescaled = [(f - 0.5) / 0.5 for f in f1s]
    avg_rescaled = sum(rescaled) / len(rescaled)

    return {
        "avg_f1_raw": round(avg_raw, 4),
        "avg_f1_rescaled": round(avg_rescaled, 4),
        "count": len(results),
    }
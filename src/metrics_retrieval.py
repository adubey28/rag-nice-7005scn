"""
Retrieval metrics: precision@k, recall@k, and mean reciprocal rank.

WHY THESE ARE COMPUTED LOCALLY AND NOT BY AN LLM JUDGE
------------------------------------------------------
RAGAS offers LLM-judged context precision and context recall. This module
deliberately does not use them, for three reasons:

1. **Determinism.** These metrics are pure arithmetic over character spans. Run
   them a thousand times and you get the same number. An LLM judge does not
   guarantee that, and a headline claim about H2 resting on a stochastic judge
   is weaker than one resting on arithmetic.

2. **Cost.** They consume no API quota. Given free-tier token limits, spending
   the entire judge budget on faithfulness (the H1 metric that genuinely
   requires semantic judgement) rather than on relevance decisions we can
   compute exactly is the correct allocation.

3. **Construct validity.** The evaluation dataset already records exactly which
   passages support each reference answer. Asking a model to re-decide
   relevance would discard that ground truth and substitute an opinion for it.

RELEVANCE IS DEFINED BY SPAN OVERLAP
------------------------------------
A retrieved chunk counts as relevant if it overlaps a gold passage by at least
`min_overlap_chars` characters. This is the design decision that makes the four
experimental conditions comparable at all: fixed-size and semantic chunking
produce different boundaries, so a gold list of chunk IDs would be meaningless
across conditions. Character spans are chunking-agnostic, so the same ground
truth scores every condition identically.

DEFINITIONS USED
----------------
  precision@k  proportion of the k retrieved chunks that are relevant
  recall@k     proportion of the question's DISTINCT GOLD PASSAGES that were
               covered by at least one retrieved chunk
  RR           1 / rank of the first relevant chunk, else 0
  MRR          mean of RR across questions

Note the recall definition. It is passage-level, not chunk-level. A multi-step
question with two gold passages scores 0.5 if only one is found, regardless of
how many chunks touched it. Chunk-level recall would be uninterpretable, because
the number of chunks overlapping a passage is an artefact of chunk size — which
is precisely one of the variables under test.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spans import is_relevant, overlap  # noqa: E402

DEFAULT_MIN_OVERLAP = 50


# --------------------------------------------------------------------------
# Per-question metrics
# --------------------------------------------------------------------------

def relevance_flags(retrieved: list[dict], gold_spans: list[dict],
                    min_overlap_chars: int = DEFAULT_MIN_OVERLAP) -> list[bool]:
    """Relevance of each retrieved chunk, in rank order."""
    return [is_relevant(c, gold_spans, min_overlap_chars) for c in retrieved]


def precision_at_k(retrieved: list[dict], gold_spans: list[dict], k: int,
                   min_overlap_chars: int = DEFAULT_MIN_OVERLAP) -> float:
    """Proportion of the top-k retrieved chunks that are relevant.

    The denominator is k, not len(retrieved). If the retriever returns fewer
    than k chunks, the shortfall counts against it — otherwise a retriever that
    returns one lucky chunk would score 1.0 and beat one that returns five with
    four hits.
    """
    if k <= 0:
        return 0.0
    flags = relevance_flags(retrieved[:k], gold_spans, min_overlap_chars)
    return sum(flags) / k


def recall_at_k(retrieved: list[dict], gold_spans: list[dict], k: int,
                min_overlap_chars: int = DEFAULT_MIN_OVERLAP) -> float:
    """Proportion of distinct gold passages covered by the top-k chunks."""
    if not gold_spans:
        return 0.0
    covered: set[int] = set()
    for chunk in retrieved[:k]:
        for i, g in enumerate(gold_spans):
            if chunk.get("doc_id") != g.get("doc_id"):
                continue
            if overlap(chunk["start_char"], chunk["end_char"],
                       g["start_char"], g["end_char"]) >= min_overlap_chars:
                covered.add(i)
    return len(covered) / len(gold_spans)


def reciprocal_rank(retrieved: list[dict], gold_spans: list[dict],
                    min_overlap_chars: int = DEFAULT_MIN_OVERLAP) -> float:
    """1 / rank of the first relevant chunk; 0.0 if none is relevant."""
    for rank, chunk in enumerate(retrieved, start=1):
        if is_relevant(chunk, gold_spans, min_overlap_chars):
            return 1.0 / rank
    return 0.0


def evaluate_question(retrieved: list[dict], gold_spans: list[dict], k: int,
                      min_overlap_chars: int = DEFAULT_MIN_OVERLAP) -> dict:
    """All retrieval metrics for a single question."""
    return {
        f"precision@{k}": precision_at_k(retrieved, gold_spans, k, min_overlap_chars),
        f"recall@{k}": recall_at_k(retrieved, gold_spans, k, min_overlap_chars),
        "reciprocal_rank": reciprocal_rank(retrieved, gold_spans, min_overlap_chars),
        "n_gold_passages": len(gold_spans),
        "n_retrieved": len(retrieved),
        "hit": any(relevance_flags(retrieved[:k], gold_spans, min_overlap_chars)),
    }


# --------------------------------------------------------------------------
# Aggregation across a run
# --------------------------------------------------------------------------

def aggregate(per_question: list[dict], k: int) -> dict:
    """Mean metrics across questions, plus the dispersion needed for reporting.

    Standard deviation and n are included because a mean without them cannot
    support a significance claim, and the analysis uses paired tests across
    conditions on exactly these per-question values.
    """
    if not per_question:
        return {}

    def col(name: str) -> list[float]:
        return [float(r[name]) for r in per_question if name in r]

    out: dict[str, float] = {"n_questions": len(per_question)}
    for name in (f"precision@{k}", f"recall@{k}", "reciprocal_rank"):
        vals = col(name)
        if not vals:
            continue
        label = "mrr" if name == "reciprocal_rank" else name
        out[label] = statistics.mean(vals)
        out[f"{label}_sd"] = statistics.stdev(vals) if len(vals) > 1 else 0.0
    out["hit_rate"] = sum(1 for r in per_question if r.get("hit")) / len(per_question)
    return out


def by_question_type(per_question: list[dict], question_types: list[str],
                     k: int) -> dict[str, dict]:
    """Break the aggregate down by factual / comparative / multi_step.

    Worth reporting separately: multi-step questions require more than one
    passage, so recall@k is where hybrid retrieval should show an advantage if
    H2 holds. A single pooled mean can hide that entirely.
    """
    buckets: dict[str, list[dict]] = {}
    for row, qtype in zip(per_question, question_types):
        buckets.setdefault(qtype, []).append(row)
    return {qtype: aggregate(rows, k) for qtype, rows in sorted(buckets.items())}

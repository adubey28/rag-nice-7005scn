"""
Stage 4a - The experiment runner: conditions, generation, retrieval metrics.

WHAT THIS DOES
--------------
Runs every evaluation question through every experimental condition, caches each
generated answer to disk, and computes the retrieval metrics that need no LLM at
all. RAGAS scoring is a separate step (evaluate_ragas.py) because it is the only
part that consumes a rate-limited external quota.

THE FIVE CONDITIONS
-------------------
    fixed_dense_k5       fixed-size chunking, dense retrieval
    fixed_hybrid_k5      fixed-size chunking, hybrid retrieval
    semantic_dense_k5    semantic chunking (p85), dense retrieval
    semantic_hybrid_k5   semantic chunking (p85), hybrid retrieval
    baseline_noretrieval same generator, no context at all

Plus a top-k sensitivity check on the best configuration only.

WHY CACHING IS NOT AN OPTIMISATION HERE
---------------------------------------
It is a correctness requirement. Gemini 3.x deprecated `temperature`, so
generation is not bit-reproducible: re-running a question can produce a
different answer. If scoring re-generated answers on the fly, the faithfulness
score and the answer it supposedly describes could diverge, and a crash halfway
through would leave the run internally inconsistent.

Caching every answer keyed by (condition, question, model) means all downstream
scoring reads ONE frozen set of outputs. The experiment becomes auditable even
though the generator is not deterministic, and a rate-limit crash at question 47
costs 47 questions rather than the whole run.

RETRIEVAL METRICS ARE COMPUTED HERE, NOT BY RAGAS
-------------------------------------------------
precision@k, recall@k and MRR are derived from character-span overlap between
retrieved chunks and the dataset's gold passages. That is deterministic, free,
and identical across conditions by construction - which matters because chunk
boundaries differ between the fixed and semantic arms, so any chunk-ID-based
relevance judgement would not be comparable across exactly the comparison H1
is about.

It also removes the metrics with the largest LLM cost from the quota budget.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import dataset as ds  # noqa: E402
from metrics_retrieval import (  # noqa: E402
    precision_at_k, recall_at_k, reciprocal_rank,
)

CACHE_DIR = config.OUTPUTS / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR = config.OUTPUTS / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Conditions
# --------------------------------------------------------------------------

def core_conditions(top_k: int = 5) -> list[config.RunConfig]:
    """The four core cells of the 2x2 design, plus the non-retrieval baseline."""
    docs = tuple(config.CORPUS_DOCS)
    cells = [
        config.RunConfig(chunking=c, retrieval=r, top_k=top_k, doc_ids=docs)
        for c in ("fixed", "semantic")
        for r in ("dense", "hybrid")
    ]
    baseline = config.RunConfig(chunking="none", retrieval="none",
                                top_k=0, doc_ids=docs)
    return cells + [baseline]


def topk_sweep(best: config.RunConfig, ks: tuple[int, ...] = (3, 5, 10)) -> list:
    """Sensitivity check on retrieval depth, best configuration only."""
    return [config.RunConfig(chunking=best.chunking, retrieval=best.retrieval,
                             top_k=k, doc_ids=best.doc_ids) for k in ks]


# --------------------------------------------------------------------------
# Caching
# --------------------------------------------------------------------------

def cache_key(condition: str, question: str, model: str) -> str:
    h = hashlib.sha256(f"{condition}|{question}|{model}".encode()).hexdigest()[:20]
    return f"{condition}__{h}"


def load_cached(key: str) -> dict | None:
    p = CACHE_DIR / f"{key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None          # corrupt part-write; regenerate
    return None


def save_cached(key: str, payload: dict) -> None:
    tmp = CACHE_DIR / f"{key}.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(CACHE_DIR / f"{key}.json")   # atomic: no half-written cache files


# --------------------------------------------------------------------------
# Running one condition
# --------------------------------------------------------------------------

@dataclass
class QuestionResult:
    question_id: str
    question_type: str
    condition: str
    answer: str
    contexts: list[str]
    retrieved: list[dict]
    context_chars: int
    precision_at_k: float | None
    recall_at_k: float | None
    reciprocal_rank: float | None
    latency_seconds: float
    from_cache: bool

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def run_condition(cfg: config.RunConfig, rows: list[dict],
                  min_overlap_chars: int = 40, sleep: float = 0.0,
                  progress: bool = True) -> list[QuestionResult]:
    from generate import generate_answer

    baseline = cfg.retrieval == "none"
    retriever = None
    if not baseline:
        from retrieve import get_retriever
        retriever = get_retriever(cfg.index_name(), cfg.retrieval,
                                  cfg.embedding_model)

    results: list[QuestionResult] = []
    for i, row in enumerate(rows, start=1):
        q = row["question"]
        key = cache_key(cfg.name(), q, cfg.gen_model)
        cached = load_cached(key)

        if cached is not None:
            payload, from_cache = cached, True
        else:
            if baseline:
                hits = []
                gen = generate_answer(q, no_retrieval=True, model=cfg.gen_model,
                                      temperature=cfg.gen_temperature)
            else:
                hits = retriever.search(q, cfg.top_k)
                gen = generate_answer(q, chunks=hits, model=cfg.gen_model,
                                      temperature=cfg.gen_temperature)
            payload = {
                "question_id": row["question_id"],
                "question": q,
                "condition": cfg.name(),
                "answer": gen["answer"],
                "contexts": gen["contexts"],
                "context_chars": gen.get("context_chars", 0),
                "gen_config_variant": gen.get("gen_config_variant"),
                "temperature_applied": gen.get("temperature_applied"),
                "latency_seconds": gen["latency_seconds"],
                "retrieved": [
                    {"chunk_id": h["chunk_id"], "doc_id": h["doc_id"],
                     "start_char": h["start_char"], "end_char": h["end_char"],
                     "rank": h["rank"], "score": h["score"]}
                    for h in hits
                ],
            }
            save_cached(key, payload)
            from_cache = False
            if sleep:
                time.sleep(sleep)

        gold = ds.gold_spans_for(row)
        retrieved = payload["retrieved"]
        if baseline or not retrieved:
            p = r = rr = None
        else:
            p = precision_at_k(retrieved, gold, cfg.top_k, min_overlap_chars)
            r = recall_at_k(retrieved, gold, cfg.top_k, min_overlap_chars)
            rr = reciprocal_rank(retrieved, gold, min_overlap_chars)

        results.append(QuestionResult(
            question_id=row["question_id"], question_type=row["question_type"],
            condition=cfg.name(), answer=payload["answer"],
            contexts=payload["contexts"], retrieved=retrieved,
            context_chars=payload.get("context_chars", 0),
            precision_at_k=p, recall_at_k=r, reciprocal_rank=rr,
            latency_seconds=payload["latency_seconds"], from_cache=from_cache))

        if progress and i % 10 == 0:
            n_new = sum(1 for x in results if not x.from_cache)
            print(f"    {i}/{len(rows)} ({n_new} generated, "
                  f"{i - n_new} from cache)")

    return results


def summarise(results: list[QuestionResult]) -> dict:
    """Aggregate retrieval metrics overall and by question type."""
    def agg(rs: list[QuestionResult]) -> dict:
        ps = [r.precision_at_k for r in rs if r.precision_at_k is not None]
        rc = [r.recall_at_k for r in rs if r.recall_at_k is not None]
        rr = [r.reciprocal_rank for r in rs if r.reciprocal_rank is not None]
        cc = [r.context_chars for r in rs if r.context_chars]
        return {
            "n": len(rs),
            "precision_at_k": sum(ps) / len(ps) if ps else None,
            "recall_at_k": sum(rc) / len(rc) if rc else None,
            "mrr": sum(rr) / len(rr) if rr else None,
            "mean_context_chars": sum(cc) / len(cc) if cc else 0,
        }

    out = {"overall": agg(results)}
    for qt in ds.QUESTION_TYPES:
        subset = [r for r in results if r.question_type == qt]
        if subset:
            out[qt] = agg(subset)
    return out

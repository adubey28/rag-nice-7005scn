"""
Stage 1d/2 — Retrieval: question -> top-k chunks.

Independent variable 2. Two methods behind one `search()` signature:

  dense   exact cosine similarity over embeddings (FAISS IndexFlatIP)
  hybrid  dense + BM25 lexical, fused by reciprocal rank fusion


WHY THE TOKENISER MATTERS FOR H2
--------------------------------
H2 predicts that hybrid beats dense on this corpus. The literature's synthesis
is that sparse retrieval earns its place where a corpus carries exact
identifiers, codes and specialised terminology that general-purpose embeddings
handle poorly — and NICE guidelines are full of exactly that: drug names,
numeric thresholds ("48 mmol/mol"), doses ("10 mg"), and numbered
recommendation identifiers ("1.6.10").

A naive tokeniser that strips punctuation would shred "1.6.10" into "1", "6",
"10" and "HbA1c" into "hba" and "1c", destroying precisely the lexical signal
the hypothesis depends on. The tokeniser below preserves decimal/dotted numbers
and alphanumeric compounds. If H2 is refuted, that must be because hybrid
retrieval genuinely does not help here — not because the tokeniser threw the
evidence away. Report the tokenisation rule in the methodology.


WHY RECIPROCAL RANK FUSION
--------------------------
Dense scores are cosine similarities in [-1, 1]; BM25 scores are unbounded and
corpus-dependent. They are not on a common scale, so a weighted sum of raw
scores would need arbitrary normalisation and an arbitrary weight — a free
parameter that would have to be tuned, and tuning it on the test set would
invalidate the comparison. RRF discards the scores and fuses ranks only:

    score(d) = SUM over rankers of  1 / (k + rank_r(d))

with k = 60 (Cormack, Clarke & Buettcher, 2009). It has no tunable weight, which
is exactly what a controlled comparison needs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()
import embed_index  # noqa: E402

# NOTE: imported as a MODULE, not `from embed_index import encode_query`.
# A from-import binds the real encoder at import time, which makes the encoder
# impossible to substitute afterwards — offline tests would silently fall
# through to the real sentence-transformer and fail on a missing model. Calling
# through the module keeps the seam open for the test stub.


# --------------------------------------------------------------------------
# Tokenisation for the sparse ranker
# --------------------------------------------------------------------------
# Keeps: words, alphanumeric compounds (hba1c), dotted/decimal numbers (1.6.10,
# 48.5), and hyphenated terms (sglt-2). Lowercased for case-insensitive match.
_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


# --------------------------------------------------------------------------
# Retrievers
# --------------------------------------------------------------------------

class DenseRetriever:
    """Exact cosine-similarity search over the chunk index."""

    method = "dense"

    def __init__(self, index_name: str, embedding_model: str = config.EMBEDDING_MODEL):
        import faiss

        index_path = config.INDEX / f"{index_name}.faiss"
        store_path = config.INDEX / f"{index_name}.chunks.json"
        if not index_path.exists():
            raise FileNotFoundError(
                f"No index at {index_path}. Run `python src/embed_index.py` first."
            )
        self.index_name = index_name
        self.index = faiss.read_index(str(index_path))
        self.chunks: list[dict] = json.loads(store_path.read_text(encoding="utf-8"))
        self.embedding_model = embedding_model

    def rank(self, question: str, n: int) -> list[tuple[int, float]]:
        """Return [(chunk_index, score)] best-first."""
        qvec = embed_index.encode_query(question, self.embedding_model)
        scores, idxs = self.index.search(qvec, min(n, len(self.chunks)))
        return [(int(i), float(s)) for s, i in zip(scores[0], idxs[0]) if i >= 0]

    def search(self, question: str, top_k: int = 5) -> list[dict]:
        out = []
        for rank, (idx, score) in enumerate(self.rank(question, top_k), start=1):
            c = dict(self.chunks[idx])
            c.update(rank=rank, score=score, retriever="dense")
            out.append(c)
        return out


class BM25Ranker:
    """Sparse lexical ranker. Built in memory from the same chunk store, so the
    dense and sparse halves are guaranteed to see an identical chunk set."""

    def __init__(self, chunks: list[dict]):
        from rank_bm25 import BM25Okapi

        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])

    def rank(self, question: str, n: int) -> list[tuple[int, float]]:
        import numpy as np

        scores = self.bm25.get_scores(tokenize(question))
        order = np.argsort(scores)[::-1][:n]
        return [(int(i), float(scores[i])) for i in order]


def reciprocal_rank_fusion(rankings: list[list[tuple[int, float]]],
                           k: int = 60) -> list[tuple[int, float]]:
    """Fuse ranked candidate lists. Input is [(chunk_index, score)] per ranker,
    best-first; score is ignored — only position counts."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for position, (idx, _score) in enumerate(ranking, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + position)
    return sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))


class HybridRetriever:
    """Dense + BM25, fused by RRF."""

    method = "hybrid"

    def __init__(self, index_name: str, embedding_model: str = config.EMBEDDING_MODEL,
                 rrf_k: int = 60, fusion_pool: int = 30):
        self.dense = DenseRetriever(index_name, embedding_model)
        self.chunks = self.dense.chunks
        self.sparse = BM25Ranker(self.chunks)
        self.rrf_k = rrf_k
        self.fusion_pool = fusion_pool
        self.index_name = index_name

    def search(self, question: str, top_k: int = 5) -> list[dict]:
        pool = max(self.fusion_pool, top_k)
        dense_rank = self.dense.rank(question, pool)
        sparse_rank = self.sparse.rank(question, pool)

        dense_pos = {idx: p for p, (idx, _) in enumerate(dense_rank, start=1)}
        sparse_pos = {idx: p for p, (idx, _) in enumerate(sparse_rank, start=1)}

        fused = reciprocal_rank_fusion([dense_rank, sparse_rank], k=self.rrf_k)

        out = []
        for rank, (idx, score) in enumerate(fused[:top_k], start=1):
            c = dict(self.chunks[idx])
            c.update(
                rank=rank,
                score=float(score),
                retriever="hybrid",
                dense_rank=dense_pos.get(idx),      # None = dense missed it
                sparse_rank=sparse_pos.get(idx),    # None = BM25 missed it
            )
            out.append(c)
        return out


@lru_cache(maxsize=8)
def get_retriever(index_name: str, method: str = "dense",
                  embedding_model: str = config.EMBEDDING_MODEL,
                  rrf_k: int = 60, fusion_pool: int = 30):
    """Factory. Cached so a batch run loads each index and model only once."""
    if method == "dense":
        return DenseRetriever(index_name, embedding_model)
    if method == "hybrid":
        return HybridRetriever(index_name, embedding_model, rrf_k, fusion_pool)
    raise ValueError(f"Unknown retrieval method: {method}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Retrieve chunks for a question.")
    ap.add_argument("question")
    ap.add_argument("--top-k", type=int, default=config.STAGE1.top_k)
    ap.add_argument("--chunking", default="fixed", choices=["fixed", "semantic"])
    ap.add_argument("--retrieval", default="dense", choices=["dense", "hybrid"])
    ap.add_argument("--docs", nargs="+", default=config.CORPUS_DOCS)
    ap.add_argument("--compare", action="store_true",
                    help="Run dense and hybrid side by side on the same question.")
    args = ap.parse_args()

    cfg = config.RunConfig(chunking=args.chunking, retrieval=args.retrieval,
                           top_k=args.top_k, doc_ids=tuple(args.docs))

    methods = ["dense", "hybrid"] if args.compare else [args.retrieval]
    for method in methods:
        r = get_retriever(cfg.index_name(), method, cfg.embedding_model,
                          cfg.rrf_k, cfg.fusion_pool)
        hits = r.search(args.question, args.top_k)
        print(f"\n{'=' * 78}\n{method.upper()}  |  {args.question}\n{'=' * 78}")
        for h in hits:
            extra = ""
            if method == "hybrid":
                extra = (f" | dense#{h.get('dense_rank') or '-'}"
                         f" sparse#{h.get('sparse_rank') or '-'}")
            print(f"--- rank {h['rank']} | score {h['score']:.4f} | "
                  f"{h['chunk_id']}{extra}")
            print(h["text"][:300].replace("\n", " ") + "...\n")


if __name__ == "__main__":
    main()

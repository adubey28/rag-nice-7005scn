"""
Stage 1b/2 — Chunking: cleaned document text -> list of chunk records.

Independent variable 1. Two strategies:

  fixed     RecursiveCharacterTextSplitter, fixed size with overlap (baseline)
  semantic  percentile-breakpoint semantic chunking (H1's challenger)


WHY `start_char` IS RECORDED ON EVERY CHUNK
-------------------------------------------
Relevance judgements in the evaluation dataset are anchored to *passages* of the
guideline (e.g. NG28 recommendation 1.6.10). Chunk boundaries differ between the
fixed and semantic conditions, so a fixed list of gold chunk IDs would be
meaningless in the other condition — precision@k and recall@k would not be
comparable across exactly the comparison H1 is about.

So gold evidence is recorded once, as character spans in the source document,
and a retrieved chunk counts as relevant if its [start_char, end_char) span
overlaps a gold span. Relevance is then defined identically for every condition.


WHY SEMANTIC CHUNKING IS REIMPLEMENTED RATHER THAN IMPORTED
-----------------------------------------------------------
`langchain_experimental.SemanticChunker` is the usual off-the-shelf choice, but
it returns chunk *text* with no character offsets, and it rejoins sentences with
its own separator so the output cannot be reliably located in the source. That
breaks the span-overlap scheme above, which is load-bearing for H2's retrieval
metrics.

The function below is a faithful implementation of the same published algorithm
(Kamradt's percentile-breakpoint method, as implemented in SemanticChunker):

  1. split the text into sentences, keeping each sentence's character span;
  2. form a context window around each sentence (`buffer` neighbours either
     side) so that a single short sentence is not embedded in isolation;
  3. embed every window with the SAME model used for retrieval;
  4. compute cosine DISTANCE between consecutive windows;
  5. set the breakpoint threshold at the Nth percentile of those distances;
  6. cut wherever distance exceeds the threshold;
  7. group the sentences between cuts into chunks.

Two deliberate deviations, both of which must be stated in the methodology:

  (a) Character spans are preserved throughout (the reason for reimplementing).
  (b) A hard cap (`max_chars`) splits oversized chunks. Uncapped semantic chunks
      can run to many thousands of characters; at a fixed top-k that would hand
      the semantic condition far more context than the fixed condition, so any
      faithfulness difference would be confounded by context volume rather than
      caused by segmentation quality. The cap keeps the comparison honest.

Using the same embedding model for chunking and for retrieval is required by the
design (the embedding model is held constant), and is also why the semantic
condition carries a real computational cost — reported as a secondary outcome.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

import config  # noqa: E402
from console import safe_stdout  # noqa: E402

safe_stdout()


# --------------------------------------------------------------------------
# Strategy 1: fixed-size with overlap (baseline)
# --------------------------------------------------------------------------

def chunk_fixed(text: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
    """Fixed-size chunking with overlap.

    RecursiveCharacterTextSplitter tries progressively finer separators
    (paragraph -> line -> sentence -> word), falling back to a hard character
    cut only when a span exceeds chunk_size with no separator available. The
    overlap carries context across boundaries so an idea cut in half is still
    recoverable from at least one chunk.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        add_start_index=True,
    )
    docs = splitter.create_documents([text])
    return [
        {
            "text": d.page_content,
            "start_char": int(d.metadata.get("start_index", -1)),
            "n_chars": len(d.page_content),
        }
        for d in docs
    ]


# --------------------------------------------------------------------------
# Strategy 2: semantic (percentile breakpoint)
# --------------------------------------------------------------------------

# Sentence terminator followed by whitespace. Guideline text is formal prose, so
# this is adequate; abbreviations such as "e.g." will over-split occasionally.
# That is a known, reportable limitation rather than a silent one.
_SENT_END = re.compile(r"(?<=[.!?])\s+")


def split_sentences_with_spans(text: str) -> list[tuple[int, int]]:
    """Return [(start, end)] character spans for each sentence.

    Paragraph breaks always terminate a sentence: in reflowed guideline text a
    blank line separates recommendations, and a recommendation boundary is a
    genuine semantic boundary that should never be crossed.
    """
    spans: list[tuple[int, int]] = []
    para_start = 0
    for para in text.split("\n\n"):
        if para.strip():
            offset = 0
            pieces = _SENT_END.split(para)
            for piece in pieces:
                if not piece.strip():
                    offset += len(piece)
                    continue
                idx = para.index(piece, offset)
                s = para_start + idx
                e = s + len(piece)
                spans.append((s, e))
                offset = idx + len(piece)
        para_start += len(para) + 2       # +2 for the "\n\n" separator
    return spans


def _context_windows(text: str, spans: list[tuple[int, int]],
                     buffer: int) -> list[str]:
    """Sentence i joined with its `buffer` neighbours either side."""
    out = []
    for i in range(len(spans)):
        lo = max(0, i - buffer)
        hi = min(len(spans), i + buffer + 1)
        out.append(" ".join(text[spans[j][0]:spans[j][1]] for j in range(lo, hi)))
    return out


def _split_oversized(text: str, start: int, end: int,
                     max_chars: int) -> list[tuple[int, int]]:
    """Recursively halve a span at the nearest whitespace until it fits."""
    if end - start <= max_chars:
        return [(start, end)]
    mid = (start + end) // 2
    window = text[max(start, mid - 200):min(end, mid + 200)]
    rel = window.rfind(" ")
    cut = (max(start, mid - 200) + rel) if rel > 0 else mid
    if cut <= start or cut >= end:
        cut = mid
    return (_split_oversized(text, start, cut, max_chars)
            + _split_oversized(text, cut, end, max_chars))


def semantic_prepare(text: str, encode_fn, buffer: int = 1):
    """Do the expensive half of semantic chunking once: sentence spans and the
    adjacent-sentence distance profile.

    Separated out because calibrating the breakpoint percentile requires trying
    many thresholds against the SAME distances. Embedding is ~99% of the cost,
    and the distances do not depend on the percentile, so a sweep that re-embeds
    per candidate wastes minutes per document for no reason.
    """
    spans = split_sentences_with_spans(text)
    if len(spans) <= 1:
        return spans, np.zeros(0, dtype="float32")

    windows = _context_windows(text, spans, buffer)
    vecs = np.asarray(encode_fn(windows), dtype="float32")
    # Vectors are unit-normalised, so cosine distance = 1 - dot product.
    distances = 1.0 - np.sum(vecs[:-1] * vecs[1:], axis=1)
    return spans, distances


def chunk_semantic(text: str, encode_fn, percentile: float = 95.0,
                   buffer: int = 1, max_chars: int = 2000,
                   _prepared=None) -> list[dict]:
    """Percentile-breakpoint semantic chunking with preserved character spans.

    `encode_fn` takes list[str] and returns an (n, d) array of L2-normalised
    vectors — injected rather than imported so the same function can be driven
    by the real sentence-transformer or by a deterministic stub in tests.

    `_prepared` optionally supplies a precomputed (spans, distances) pair from
    `semantic_prepare()`, so a percentile sweep embeds only once.
    """
    spans, distances = _prepared if _prepared is not None else \
        semantic_prepare(text, encode_fn, buffer)

    if len(spans) <= 1:
        return [{"text": text, "start_char": 0, "n_chars": len(text)}]

    threshold = float(np.percentile(distances, percentile))
    breakpoints = [i for i, d in enumerate(distances) if d > threshold]

    # Group sentences between breakpoints. A breakpoint at index i means the
    # cut falls AFTER sentence i.
    groups: list[tuple[int, int]] = []
    start_idx = 0
    for bp in breakpoints:
        groups.append((start_idx, bp))
        start_idx = bp + 1
    groups.append((start_idx, len(spans) - 1))

    chunks: list[dict] = []
    for first, last in groups:
        if first > last:
            continue
        s, e = spans[first][0], spans[last][1]
        for cs, ce in _split_oversized(text, s, e, max_chars):
            piece = text[cs:ce].strip()
            if not piece:
                continue
            lead = len(text[cs:ce]) - len(text[cs:ce].lstrip())
            chunks.append({
                "text": piece,
                "start_char": cs + lead,
                "n_chars": len(piece),
            })
    return chunks



def merge_undersized(text: str, chunks: list[dict], min_chars: int) -> list[dict]:
    """Merge chunks shorter than `min_chars` into their neighbour.

    WHY, AND WHY FOR BOTH STRATEGIES
    --------------------------------
    Segmentation produces occasional degenerate fragments - a stray heading, a
    lone page-break artefact. A 5-character chunk cannot support an answer, but
    it still consumes one of the k retrieval slots, so it silently reduces the
    effective context a condition receives.

    The merge is applied to fixed-size and semantic chunking alike. Applying a
    cleanup to only the challenger strategy would be exactly the kind of
    asymmetry that makes an H1 result unpublishable - the two arms must be
    treated identically in every respect except the segmentation rule itself.

    Merging extends the span to cover both pieces and re-slices from source, so
    the [start_char, end_char) invariant is preserved by construction.
    """
    if not chunks:
        return chunks

    merged: list[dict] = []
    for c in chunks:
        if merged and c["n_chars"] < min_chars:
            prev = merged[-1]
            start = prev["start_char"]
            end = max(prev["start_char"] + prev["n_chars"],
                      c["start_char"] + c["n_chars"])
            merged[-1] = {"text": text[start:end], "start_char": start,
                          "n_chars": end - start}
        else:
            merged.append(dict(c))

    # A leading undersized chunk has no predecessor; fold it into its successor.
    if len(merged) > 1 and merged[0]["n_chars"] < min_chars:
        a, b = merged[0], merged[1]
        start = a["start_char"]
        end = b["start_char"] + b["n_chars"]
        merged[:2] = [{"text": text[start:end], "start_char": start,
                       "n_chars": end - start}]
    return merged


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def build_chunks(cfg: config.RunConfig, overwrite: bool = False,
                 encode_fn=None) -> list[dict]:
    out_path = config.INTERIM / f"chunks__{cfg.index_name()}.json"
    if out_path.exists() and not overwrite:
        chunks = json.loads(out_path.read_text(encoding="utf-8"))
        print(f"[chunk] loaded {len(chunks)} existing chunks from {out_path.name}")
        return chunks

    if cfg.chunking == "semantic" and encode_fn is None:
        from embed_index import encode_passages
        encode_fn = lambda ts: encode_passages(ts, cfg.embedding_model)  # noqa: E731

    all_chunks: list[dict] = []
    t0 = time.time()
    for doc_id in cfg.doc_ids:
        doc_path = config.INTERIM / f"{doc_id}.json"
        if not doc_path.exists():
            raise FileNotFoundError(
                f"{doc_path} not found. Run `python src/ingest.py --docs {doc_id}` first."
            )
        doc = json.loads(doc_path.read_text(encoding="utf-8"))

        if cfg.chunking == "fixed":
            pieces = chunk_fixed(doc["text"], cfg.chunk_size, cfg.chunk_overlap)
        elif cfg.chunking == "semantic":
            pieces = chunk_semantic(
                doc["text"], encode_fn,
                percentile=cfg.semantic_percentile,
                buffer=cfg.semantic_buffer,
                max_chars=cfg.semantic_max_chars,
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {cfg.chunking}")

        # Symmetric cleanup: identical policy for both strategies.
        pieces = merge_undersized(doc["text"], pieces, cfg.min_chunk_chars)

        for i, p in enumerate(pieces):
            all_chunks.append({
                "chunk_id": f"{doc_id}:{cfg.chunking}:{i:05d}",
                "doc_id": doc_id,
                "doc_title": doc["title"],
                "ordinal": i,
                "start_char": p["start_char"],
                "end_char": p["start_char"] + p["n_chars"],
                "n_chars": p["n_chars"],
                "text": p["text"],
            })
    elapsed = time.time() - t0

    out_path.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    lengths = sorted(c["n_chars"] for c in all_chunks)
    median = lengths[len(lengths) // 2] if lengths else 0
    print(f"[chunk] strategy={cfg.chunking} docs={list(cfg.doc_ids)}")
    print(f"[chunk] {len(all_chunks)} chunks | "
          f"min {lengths[0]} / median {median} / max {lengths[-1]} chars | "
          f"mean {sum(lengths)/len(lengths):.0f}")
    print(f"[chunk] wall-clock {elapsed:.1f}s  "
          f"(record this — chunking cost is a reportable secondary outcome)")
    print(f"[chunk] wrote {out_path.name}")
    return all_chunks


def main() -> None:
    ap = argparse.ArgumentParser(description="Chunk ingested documents.")
    ap.add_argument("--chunking", default="fixed", choices=["fixed", "semantic"])
    ap.add_argument("--chunk-size", type=int, default=config.STAGE1.chunk_size)
    ap.add_argument("--chunk-overlap", type=int, default=config.STAGE1.chunk_overlap)
    ap.add_argument("--percentile", type=float, default=95.0)
    ap.add_argument("--docs", nargs="+", default=config.CORPUS_DOCS)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    cfg = config.RunConfig(
        chunking=args.chunking,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        semantic_percentile=args.percentile,
        doc_ids=tuple(args.docs),
    )
    chunks = build_chunks(cfg, overwrite=args.overwrite)

    print("\n[chunk] --- sample chunk (inspect this) ---")
    if chunks:
        sample = chunks[len(chunks) // 2]
        print(f"id={sample['chunk_id']} chars={sample['n_chars']} "
              f"span=[{sample['start_char']}, {sample['end_char']})")
        print(sample["text"][:600] + ("..." if sample["n_chars"] > 600 else ""))


if __name__ == "__main__":
    main()

"""
Span-overlap relevance: the bridge between the evaluation dataset and the
retrieval metrics.

The evaluation dataset records gold evidence as character spans in the source
document, because chunk boundaries differ between conditions (see the note at
the top of chunking.py). This module turns those spans into the binary
relevance labels that precision@k, recall@k and MRR consume.

A retrieved chunk counts as relevant to a gold span if the two overlap by at
least `min_overlap_chars`. The minimum guards against a one-character brush at a
boundary counting as a hit — an artefact of chunk edges rather than genuine
retrieval of the evidence.
"""

from __future__ import annotations


def overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Number of characters shared by two half-open spans."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def is_relevant(chunk: dict, gold_spans: list[dict],
                min_overlap_chars: int = 50) -> bool:
    """True if the chunk overlaps any gold span for the same document."""
    for g in gold_spans:
        if g["doc_id"] != chunk["doc_id"]:
            continue
        if overlap(chunk["start_char"], chunk["end_char"],
                   g["start_char"], g["end_char"]) >= min_overlap_chars:
            return True
    return False


def covered_gold_spans(chunks: list[dict], gold_spans: list[dict],
                       min_overlap_chars: int = 50) -> set[int]:
    """Indices of the gold spans hit by at least one retrieved chunk.

    Used for recall@k: the denominator is the number of gold spans required to
    answer the question, not the number of retrieved chunks. A question whose
    answer needs two passages is only fully recalled when both are retrieved —
    which is exactly what the multi-step question type is designed to stress.
    """
    hit: set[int] = set()
    for i, g in enumerate(gold_spans):
        for c in chunks:
            if c["doc_id"] != g["doc_id"]:
                continue
            if overlap(c["start_char"], c["end_char"],
                       g["start_char"], g["end_char"]) >= min_overlap_chars:
                hit.add(i)
                break
    return hit


def locate_span(doc_text: str, passage: str, hint: int | None = None) -> tuple[int, int]:
    """Find a verbatim passage in the source document and return its span.

    Used by the dataset validator: every gold passage you record must be found
    verbatim in the ingested text. If it is not, either the passage was
    mistyped or PDF extraction mangled that region — both are things you need to
    know BEFORE running the experiment, not after.

    Raises ValueError if the passage cannot be located.
    """
    needle = " ".join(passage.split())
    haystack = " ".join(doc_text.split())
    if needle not in haystack:
        raise ValueError(
            "Passage not found verbatim in the ingested document text. "
            "Check for typos, or inspect that region of data/interim/<DOC>.txt "
            "for an extraction failure."
        )
    # Map back to raw offsets by walking the original text.
    start = doc_text.find(passage)
    if start >= 0:
        return start, start + len(passage)

    # Whitespace differs; locate by matching the normalised form progressively.
    words = passage.split()
    first, last = words[0], words[-1]
    search_from = hint or 0
    s = doc_text.find(first, search_from)
    while s != -1:
        e = doc_text.find(last, s)
        if e != -1:
            e += len(last)
            if " ".join(doc_text[s:e].split()) == needle:
                return s, e
        s = doc_text.find(first, s + 1)
    raise ValueError("Passage matched after normalisation but span could not be resolved.")

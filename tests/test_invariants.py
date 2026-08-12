"""
Adversarial invariant tests.

test_components.py checks that the components behave. This file checks the single
property the entire measurement rests on:

    doc_text[chunk.start_char : chunk.end_char] == chunk.text

If that ever fails, span-overlap relevance silently mislabels chunks, and
precision@k / recall@k / MRR become meaningless for BOTH hypotheses — while
still producing plausible-looking numbers. That is the worst class of bug in a
dissertation artefact, so it is tested against deliberately awkward text.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from chunking import (  # noqa: E402
    chunk_fixed, chunk_semantic, split_sentences_with_spans,
)
from spans import covered_gold_spans, is_relevant, locate_span, overlap  # noqa: E402


# --------------------------------------------------------------------------
# Awkward but realistic guideline text: decimal recommendation numbers,
# thresholds with decimal points, units containing slashes, abbreviations,
# a very long recommendation, and irregular paragraph spacing.
# --------------------------------------------------------------------------
DOC = (
    "1.6.10 Offer standard-release metformin to adults with type 2 diabetes. "
    "Review the dose if the eGFR falls below 45 ml/min/1.73 m2.\n\n"
    "1.6.11 Consider an SGLT2 inhibitor in addition to metformin, e.g. "
    "empagliflozin, for adults with chronic heart failure. Do not offer this "
    "if the patient has type 1 diabetes.\n\n"
    "1.7.1 Agree an individualised HbA1c target with the adult. For adults "
    "managed by diet alone the target is 48 mmol/mol (6.5%). For adults on a "
    "drug associated with hypoglycaemia the target is 53 mmol/mol (7.0%).\n\n"
    "1.8.1 Measure blood pressure at every review. " + ("Monitor closely. " * 90) +
    "Record the result in the notes.\n\n"
    "2.1.1 Offer a statin for primary prevention of cardiovascular disease."
)


def _fake_encoder(dim: int = 8):
    """Deterministic topic-clustered vectors: sentences sharing a marker term
    get near-identical vectors, so breakpoints land on genuine topic changes and
    the test has a known expected answer rather than an arbitrary one."""
    topics = {
        "metformin": 0, "SGLT2": 1, "HbA1c": 2, "blood pressure": 3,
        "statin": 4, "Monitor": 3,
    }

    def encode(texts: list[str]) -> np.ndarray:
        vecs = np.zeros((len(texts), dim), dtype="float32")
        for i, t in enumerate(texts):
            hit = next((idx for term, idx in topics.items() if term in t), 7)
            vecs[i, hit] = 1.0
            vecs[i, 6] = 0.15                      # shared background component
            vecs[i] /= np.linalg.norm(vecs[i])
        return vecs

    return encode


# --------------------------------------------------------------------------

def test_fixed_offsets_slice_back_exactly():
    for size, ov in [(300, 50), (1000, 150), (150, 0), (5000, 500)]:
        chunks = chunk_fixed(DOC, size, ov)
        assert chunks, f"no chunks at size={size}"
        for c in chunks:
            s, e = c["start_char"], c["start_char"] + c["n_chars"]
            assert s >= 0, f"negative start_char at size={size}"
            assert DOC[s:e] == c["text"], (
                f"OFFSET MISMATCH (fixed, size={size}, overlap={ov})\n"
                f"  expected: {c['text'][:80]!r}\n"
                f"  sliced  : {DOC[s:e][:80]!r}"
            )


def test_semantic_offsets_slice_back_exactly():
    enc = _fake_encoder()
    for pct in [50.0, 80.0, 95.0]:
        for cap in [400, 2000, 100_000]:
            chunks = chunk_semantic(DOC, enc, percentile=pct, max_chars=cap)
            assert chunks, f"no chunks at pct={pct}, cap={cap}"
            for c in chunks:
                s, e = c["start_char"], c["start_char"] + c["n_chars"]
                assert DOC[s:e] == c["text"], (
                    f"OFFSET MISMATCH (semantic, pct={pct}, cap={cap})\n"
                    f"  expected: {c['text'][:80]!r}\n"
                    f"  sliced  : {DOC[s:e][:80]!r}"
                )


def test_semantic_covers_document_without_gaps_or_overlap():
    """Semantic chunks must partition the document: no text silently dropped
    (which would make some gold passages unretrievable by construction) and no
    duplication (which would double-count relevance)."""
    chunks = sorted(chunk_semantic(DOC, _fake_encoder(), percentile=80.0),
                    key=lambda c: c["start_char"])
    for a, b in zip(chunks, chunks[1:]):
        a_end = a["start_char"] + a["n_chars"]
        assert a_end <= b["start_char"], (
            f"chunks overlap: {a['chunk_id'] if 'chunk_id' in a else a_end} "
            f"ends at {a_end}, next starts at {b['start_char']}"
        )
        gap = DOC[a_end:b["start_char"]]
        assert gap.strip() == "", f"non-whitespace text dropped between chunks: {gap!r}"


def test_max_chars_cap_is_enforced():
    """The long 1.8.1 recommendation must be split, or the semantic condition
    would receive far more context per retrieved chunk than the fixed condition
    and confound H1."""
    cap = 500
    chunks = chunk_semantic(DOC, _fake_encoder(), percentile=95.0, max_chars=cap)
    oversized = [c["n_chars"] for c in chunks if c["n_chars"] > cap]
    assert not oversized, f"chunks exceed max_chars={cap}: {oversized}"


def test_sentence_splitter_preserves_decimals_and_units():
    spans = split_sentences_with_spans(DOC)
    texts = [DOC[s:e] for s, e in spans]
    joined = " ".join(texts)
    for token in ["1.6.10", "45 ml/min/1.73", "48 mmol/mol", "(6.5%)", "2.1.1"]:
        assert token in joined, f"{token!r} was destroyed by sentence splitting"
    # A recommendation number must not be orphaned as its own "sentence".
    assert not any(t.strip() in {"1.6.10", "1.7.1", "2.1.1"} for t in texts), \
        "recommendation number split off from its recommendation text"


def test_span_relevance_semantics():
    gold = [{"doc_id": "NG28", "start_char": 100, "end_char": 300}]
    hit = {"doc_id": "NG28", "start_char": 90, "end_char": 200}
    graze = {"doc_id": "NG28", "start_char": 290, "end_char": 400}   # 10 chars
    other_doc = {"doc_id": "NG136", "start_char": 100, "end_char": 300}

    assert is_relevant(hit, gold, min_overlap_chars=50)
    assert not is_relevant(graze, gold, min_overlap_chars=50), \
        "a boundary graze must not count as retrieving the evidence"
    assert not is_relevant(other_doc, gold), \
        "relevance must not leak across documents"
    assert overlap(0, 10, 10, 20) == 0, "half-open spans must not touch-count"


def test_recall_denominator_is_gold_spans_not_chunks():
    """A two-passage (multi-step) question is only fully recalled when both
    passages are hit — the property the multi-step question type exists to test."""
    gold = [
        {"doc_id": "NG28", "start_char": 0, "end_char": 200},
        {"doc_id": "NG28", "start_char": 500, "end_char": 700},
    ]
    one = [{"doc_id": "NG28", "start_char": 0, "end_char": 200}]
    both = one + [{"doc_id": "NG28", "start_char": 480, "end_char": 720}]

    assert covered_gold_spans(one, gold) == {0}
    assert len(covered_gold_spans(one, gold)) / len(gold) == 0.5
    assert covered_gold_spans(both, gold) == {0, 1}


def test_locate_span_finds_passages_and_rejects_fabrications():
    passage = "Agree an individualised HbA1c target with the adult."
    s, e = locate_span(DOC, passage)
    assert DOC[s:e] == passage

    # Whitespace-normalised match (as a passage copied from a PDF would be).
    s2, e2 = locate_span(DOC, "Offer  standard-release   metformin")
    assert " ".join(DOC[s2:e2].split()) == "Offer standard-release metformin"

    try:
        locate_span(DOC, "Offer insulin glargine to all adults immediately.")
    except ValueError:
        pass
    else:
        raise AssertionError(
            "validator accepted a passage absent from the source — it would let "
            "an unverifiable gold answer into the evaluation dataset"
        )


if __name__ == "__main__":
    import traceback

    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception:
                failures += 1
                print(f"FAIL  {name}")
                traceback.print_exc()
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)

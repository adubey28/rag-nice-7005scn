"""
Logic tests for Stage 2. No network, no API keys, no model download: the
embedder is stubbed with a deterministic hash-based function so that chunking
behaviour is reproducible and testable in isolation.

    python -m pytest tests/ -v        (or: python tests/test_components.py)
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from chunking import chunk_semantic, split_sentences_with_spans, chunk_fixed  # noqa: E402
from retrieve import tokenize, reciprocal_rank_fusion  # noqa: E402
from spans import overlap, is_relevant, covered_gold_spans  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def stub_encode(texts):
    """Deterministic pseudo-embedder: topic word -> direction. Sentences sharing
    a topic get similar vectors, so semantic boundaries are predictable."""
    topics = ["diabetes", "hypertension", "heart", "lipid"]
    vecs = []
    for t in texts:
        v = np.zeros(8, dtype="float32")
        low = t.lower()
        for i, topic in enumerate(topics):
            v[i] = low.count(topic)
        v[4] = len(t) / 1000.0
        if not v.any():
            v[5] = 1.0
        vecs.append(v / (np.linalg.norm(v) + 1e-9))
    return np.vstack(vecs)


DOC = (
    "1.1.1 Offer metformin to adults with diabetes. Diabetes management should "
    "be reviewed annually. Diabetes education is recommended.\n\n"
    "1.2.1 Measure blood pressure in adults with hypertension. Hypertension "
    "should be confirmed with ambulatory monitoring. Hypertension treatment "
    "begins with lifestyle advice.\n\n"
    "1.3.1 Assess lipid levels before starting a statin. Lipid modification "
    "reduces cardiovascular risk. Lipid targets should be discussed."
)


def test_sentence_spans():
    spans = split_sentences_with_spans(DOC)
    ok = all(DOC[s:e].strip() and DOC[s:e] == DOC[s:e].strip() for s, e in spans)
    check("sentence spans round-trip to source text", ok)
    check("spans are strictly ordered",
          all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)))
    check("paragraph breaks terminate sentences", len(spans) >= 9,
          f"got {len(spans)}")


def test_semantic_spans():
    chunks = chunk_semantic(DOC, stub_encode, percentile=60.0, buffer=1,
                            max_chars=2000)
    ok = all(DOC[c["start_char"]:c["start_char"] + c["n_chars"]] == c["text"] for c in chunks)
    check("semantic chunk spans round-trip EXACTLY to source text", ok,
          "" if ok else "span/text mismatch -> retrieval metrics would be wrong")
    check("more than one semantic chunk produced", len(chunks) > 1,
          f"got {len(chunks)}")
    check("no empty chunks", all(c["n_chars"] > 0 for c in chunks))
    check("chunk text is stripped (no leading/trailing whitespace)",
          all(c["text"] == c["text"].strip() for c in chunks))


def test_max_chars_cap():
    long_doc = " ".join(f"Sentence number {i} about diabetes care." for i in range(300))
    chunks = chunk_semantic(long_doc, stub_encode, percentile=99.9, buffer=1,
                            max_chars=500)
    biggest = max(c["n_chars"] for c in chunks)
    check("max_chars cap enforced", biggest <= 500, f"largest chunk {biggest}")
    ok = all(long_doc[c["start_char"]:c["start_char"] + c["n_chars"]] == c["text"] for c in chunks)
    check("capped chunks still round-trip to source", ok)


def test_fixed_chunking():
    chunks = chunk_fixed(DOC, 120, 20)
    check("fixed chunking produces chunks", len(chunks) > 1, f"got {len(chunks)}")
    ok = all(c["start_char"] >= 0 for c in chunks)
    check("fixed chunks carry start_char", ok)


def test_tokenizer():
    toks = tokenize("Offer 10 mg atorvastatin; see recommendation 1.6.10 and HbA1c 48.5 with SGLT-2.")
    check("recommendation id '1.6.10' preserved", "1.6.10" in toks, toks)
    check("decimal '48.5' preserved", "48.5" in toks, toks)
    check("'hba1c' preserved as one token", "hba1c" in toks, toks)
    check("hyphenated 'sglt-2' preserved", "sglt-2" in toks, toks)
    check("punctuation stripped", ";" not in "".join(toks))


def test_rrf():
    dense = [(10, 0.9), (11, 0.8), (12, 0.7)]
    sparse = [(12, 5.0), (13, 4.0), (10, 3.0)]
    fused = reciprocal_rank_fusion([dense, sparse], k=60)
    ids = [i for i, _ in fused]
    check("RRF returns union of both rankings", set(ids) == {10, 11, 12, 13}, ids)
    check("doc in both lists outranks doc in one", ids[0] in (10, 12), ids)
    expected = 1 / 61 + 1 / 63          # chunk 10: dense#1, sparse#3
    got = dict(fused)[10]
    check("RRF score formula 1/(k+rank) correct", abs(got - expected) < 1e-9,
          f"{got} vs {expected}")
    check("scores sorted descending",
          all(fused[i][1] >= fused[i + 1][1] for i in range(len(fused) - 1)))


def test_span_relevance():
    check("overlap: disjoint = 0", overlap(0, 100, 200, 300) == 0)
    check("overlap: partial", overlap(0, 100, 50, 150) == 50)
    check("overlap: contained", overlap(0, 100, 10, 20) == 10)

    gold = [{"doc_id": "NG28", "start_char": 1000, "end_char": 1300},
            {"doc_id": "NG136", "start_char": 500, "end_char": 800}]
    hit = {"doc_id": "NG28", "start_char": 900, "end_char": 1200}
    brush = {"doc_id": "NG28", "start_char": 980, "end_char": 1010}
    wrong_doc = {"doc_id": "NG136", "start_char": 1000, "end_char": 1300}

    check("overlapping chunk is relevant", is_relevant(hit, gold))
    check("30-char brush below threshold is NOT relevant",
          not is_relevant(brush, gold, min_overlap_chars=50))
    check("same span in a different document is NOT relevant",
          not is_relevant(wrong_doc, gold))

    covered = covered_gold_spans([hit], gold)
    check("multi-passage recall: 1 of 2 gold spans covered", covered == {0}, covered)
    both = covered_gold_spans([hit, {"doc_id": "NG136", "start_char": 600,
                                     "end_char": 900}], gold)
    check("multi-passage recall: 2 of 2 when both retrieved", both == {0, 1}, both)


if __name__ == "__main__":
    print("\nSTAGE 2 LOGIC TESTS (stubbed embedder — no network, no API calls)\n")
    for fn in [test_sentence_spans, test_semantic_spans, test_max_chars_cap,
               test_fixed_chunking, test_tokenizer, test_rrf, test_span_relevance]:
        print(f"{fn.__name__}:")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    print("ALL TESTS PASSED")

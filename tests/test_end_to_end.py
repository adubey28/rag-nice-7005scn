"""
End-to-end smoke test: synthetic PDF -> ingest -> chunk -> index -> retrieve.

WHY THIS EXISTS
---------------
The unit tests in test_invariants.py check individual functions. This test
exercises the whole chain against a purpose-built PDF whose correct output is
known in advance, using a deterministic stub embedder in place of the real
sentence-transformer. It therefore runs offline, in under a second, with no API
key and no model download — and it catches integration bugs (wrong argument
order, stale index, chunk store out of sync with the FAISS index) that unit
tests structurally cannot see.

The synthetic guideline deliberately contains every hazard the real NICE PDFs
contain: a running header, a copyright footer, page numbers, a word broken
across a line by hyphenation, numbered recommendations, decimal thresholds and
drug names.

Run:  python -m pytest tests/test_end_to_end.py -v
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import config  # noqa: E402


# --------------------------------------------------------------------------
# Synthetic corpus
# --------------------------------------------------------------------------

HEADER = "Synthetic cardiometabolic guideline (NG99)"
FOOTER = "© NICE 2026. All rights reserved. Subject to Notice of rights."

# One topic per page, so we know which page a query should retrieve.
PAGES = [
    ["1.1.1 Offer standard-release metformin to adults with type 2 diabetes as "
     "initial drug treatment. Review the dose if the estimated glomerular "
     "filtration rate falls below 45 ml/min/1.73 m2.",
     "1.1.2 Agree an individualised HbA1c target of 48 mmol/mol (6.5%) for "
     "adults managed by diet and lifestyle alone."],

    ["1.2.1 Offer antihypertensive drug treatment to adults with persistent "
     "stage 1 hypertension who are under 80 years and have an estimated 10 "
     "year cardiovascular risk of 10% or more.",
     "1.2.2 For adults aged over 55 years without type 2 diabetes, offer a "
     "calcium channel blocker such as amlodipine as step 1 treatment."],

    ["1.3.1 Offer atorvastatin 20 mg daily for the primary prevention of "
     "cardiovascular disease in adults with a 10 year QRISK3 score of 10% or "
     "more.",
     "1.3.2 Measure the full lipid profile before starting lipid lowering "
     "treatment. A fasting sample is not required."],

    ["1.4.1 Offer an angiotensin converting enzyme inhibitor and a beta "
     "blocker as first line treatment for adults with chronic heart failure "
     "with reduced ejection fraction.",
     "1.4.2 Measure N terminal pro B type natriuretic peptide in adults with "
     "suspected heart failure. Refer urgently if the level is above 2000 "
     "ng/litre."],
]


def build_synthetic_pdf(path: Path) -> None:
    """Render PAGES to a PDF with realistic furniture and a hyphen break."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    for page_no, paragraphs in enumerate(PAGES, start=1):
        c.setFont("Helvetica", 9)
        c.drawString(60, height - 45, HEADER)          # running header
        c.setFont("Helvetica", 11)

        y = height - 90
        for para in paragraphs:
            words = para.split()
            line = ""
            for w in words:
                if len(line) + len(w) + 1 > 78:
                    c.drawString(60, y, line)
                    y -= 16
                    line = w
                else:
                    line = f"{line} {w}".strip()
            if line:
                c.drawString(60, y, line)
                y -= 26

        # Page 1 gets a deliberate hyphenation break to test de-hyphenation.
        if page_no == 1:
            c.drawString(60, y, "Metformin is contra-")
            y -= 16
            c.drawString(60, y, "indicated in severe renal impairment.")
            y -= 26

        c.setFont("Helvetica", 8)
        c.drawString(60, 50, FOOTER)                   # running footer
        c.drawString(width - 80, 50, str(page_no))     # page number
        c.showPage()

    c.save()


# --------------------------------------------------------------------------
# Deterministic stub embedder
# --------------------------------------------------------------------------

DIM = 64

# Fine chunking for the fixture: the synthetic guideline is short, and ranking
# behaviour is only observable when there are more candidates than top_k.
TEST_CHUNK_SIZE = 250
TEST_OVERLAP = 40


def fixture_cfg(strategy: str) -> "config.RunConfig":
    return config.RunConfig(chunking=strategy, chunk_size=TEST_CHUNK_SIZE,
                            chunk_overlap=TEST_OVERLAP, doc_ids=("NG99",))


def _stable_hash(token: str) -> int:
    """Deterministic token hash.

    Python's built-in hash() is salted with a per-process random seed unless
    PYTHONHASHSEED is pinned, so using it here made the stub embedder produce
    DIFFERENT vectors on every run. Retrieval assertions built on it passed or
    failed depending on the seed - a genuinely non-deterministic test suite that
    looked green only because the seed happened to be pinned during development.

    crc32 is stable across processes, machines and Python versions. A test that
    can fail intermittently is worse than no test: it trains you to ignore red.
    """
    return zlib.crc32(token.encode("utf-8"))


def _stub_vectors(texts: list[str]) -> np.ndarray:
    """Hashed bag-of-words, L2-normalised.

    Not a language model, but not random either: texts sharing vocabulary score
    higher together than texts that do not. That is enough to drive semantic
    chunking and dense retrieval through their real code paths and to make the
    assertions below meaningful rather than tautological.
    """
    out = np.zeros((len(texts), DIM), dtype="float32")
    for i, t in enumerate(texts):
        for tok in re.findall(r"[a-z0-9]+", t.lower()):
            out[i, _stable_hash(tok) % DIM] += 1.0
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    out /= np.where(norms == 0, 1.0, norms)
    return out


# --------------------------------------------------------------------------
# Fixture: temp workspace with the synthetic doc ingested
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def workspace():
    tmp = Path(tempfile.mkdtemp(prefix="ragnice_e2e_"))

    # Redirect all pipeline paths into the temp workspace.
    orig = (config.RAW, config.INTERIM, config.INDEX, config.OUTPUTS)
    config.RAW = tmp / "raw"
    config.INTERIM = tmp / "interim"
    config.INDEX = tmp / "index"
    config.OUTPUTS = tmp / "outputs"
    for p in (config.RAW, config.INTERIM, config.INDEX, config.OUTPUTS):
        p.mkdir(parents=True, exist_ok=True)

    config.CORPUS["NG99"] = {
        "title": "Synthetic cardiometabolic guideline",
        "filename": "ng99.pdf",
        "url": "https://example.invalid/ng99",
    }

    build_synthetic_pdf(config.RAW / "ng99.pdf")

    # Patch the embedder BEFORE importing retrieve, which binds encode_query
    # at import time.
    import embed_index
    # Patch the module attributes; retrieve.py calls through the module, so this
    # takes effect regardless of whether retrieve was already imported by
    # another test file during collection.
    embed_index.encode_passages = lambda texts, model_name=None, batch_size=32: _stub_vectors(texts)
    embed_index.encode_query = lambda q, model_name=None: _stub_vectors([config.QUERY_PREFIX + q])
    config.EMBEDDING_DIM = DIM

    import ingest
    record = ingest.ingest("NG99", overwrite=True)

    yield {"tmp": tmp, "record": record}

    config.RAW, config.INTERIM, config.INDEX, config.OUTPUTS = orig
    shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# 1. Ingestion
# --------------------------------------------------------------------------

def test_running_header_and_footer_are_removed(workspace):
    text = workspace["record"]["text"]
    assert HEADER not in text, "running header survived ingestion"
    assert "All rights reserved" not in text, "copyright footer survived ingestion"


def test_hyphen_break_is_rejoined(workspace):
    text = workspace["record"]["text"]
    assert "contraindicated" in text, "hyphenated word was not rejoined"
    assert "contra-\nindicated" not in text


def test_clinical_content_survives(workspace):
    """Cleaning must not be so aggressive that it eats the guideline itself."""
    text = workspace["record"]["text"].lower()
    for token in ["metformin", "amlodipine", "atorvastatin", "48 mmol/mol",
                  "qrisk3", "2000 ng/litre"]:
        assert token.lower() in text, f"lost clinical content: {token}"


def test_recommendation_numbers_preserved(workspace):
    text = workspace["record"]["text"]
    for rec in ["1.1.1", "1.2.2", "1.3.1", "1.4.2"]:
        assert rec in text, f"lost recommendation identifier {rec}"


# --------------------------------------------------------------------------
# 2. Chunking (both strategies) — offsets must be exact
# --------------------------------------------------------------------------

@pytest.mark.parametrize("strategy", ["fixed", "semantic"])
def test_chunk_offsets_slice_back_to_source(workspace, strategy):
    """The single most important invariant in the pipeline.

    Every retrieval metric depends on [start_char, end_char) locating the chunk
    in the source document. If offsets drift, precision@k and recall@k silently
    measure nothing, while still producing plausible numbers.
    """
    from chunking import build_chunks

    cfg = fixture_cfg(strategy)
    chunks = build_chunks(cfg, overwrite=True)
    source = workspace["record"]["text"]

    assert chunks, f"{strategy} chunking produced nothing"
    for c in chunks:
        assert source[c["start_char"]:c["end_char"]] == c["text"], (
            f"{strategy}: offsets do not slice back to source at {c['chunk_id']}"
        )


def test_semantic_and_fixed_produce_different_boundaries(workspace):
    """If the two strategies segment identically, H1 has nothing to test."""
    from chunking import build_chunks

    fixed = build_chunks(fixture_cfg("fixed"), overwrite=True)
    semantic = build_chunks(fixture_cfg("semantic"), overwrite=True)
    fixed_bounds = {(c["start_char"], c["end_char"]) for c in fixed}
    semantic_bounds = {(c["start_char"], c["end_char"]) for c in semantic}
    assert fixed_bounds != semantic_bounds, "strategies segmented identically"


# --------------------------------------------------------------------------
# 3. Indexing and retrieval
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def indexes(workspace):
    from embed_index import build_index

    built = {}
    for strategy in ("fixed", "semantic"):
        name, n = build_index(fixture_cfg(strategy), overwrite=True)
        built[strategy] = (name, n)
    return built


def test_index_and_chunk_store_stay_in_sync(workspace, indexes):
    """A FAISS index holding a different number of vectors than the chunk store
    holds records means every retrieved chunk_id is wrong. Silent and fatal."""
    import json

    import faiss

    for strategy, (name, n) in indexes.items():
        index = faiss.read_index(str(config.INDEX / f"{name}.faiss"))
        chunks = json.loads((config.INDEX / f"{name}.chunks.json").read_text())
        assert index.ntotal == len(chunks) == n, f"{strategy}: index/store mismatch"


@pytest.mark.parametrize("question,expect", [
    ("Which drug is offered as initial treatment for type 2 diabetes?", "metformin"),
    ("Which calcium channel blocker is offered as step 1 treatment?", "amlodipine"),
    ("What statin dose is offered for primary prevention?", "atorvastatin"),
])
def test_dense_retrieval_finds_the_right_passage(workspace, indexes, question, expect):
    from retrieve import get_retriever

    name = indexes["fixed"][0]
    hits = get_retriever.__wrapped__(name, "dense")
    top3 = hits.search(question, 3)
    joined = " ".join(h["text"].lower() for h in top3)
    assert expect in joined, f"dense retrieval missed '{expect}' in top-3"


def test_hybrid_returns_fusion_provenance(workspace, indexes):
    """Every hybrid hit must record where it came from, so the validation gate
    can confirm fusion actually happened rather than dense passing through."""
    from retrieve import get_retriever

    name = indexes["fixed"][0]
    hybrid = get_retriever.__wrapped__(name, "hybrid")
    hits = hybrid.search("amlodipine calcium channel blocker", 5)

    assert hits, "hybrid returned nothing"
    for h in hits:
        assert h["retriever"] == "hybrid"
        assert "dense_rank" in h and "sparse_rank" in h
    assert any(h["sparse_rank"] is not None for h in hits), "BM25 contributed nothing"


def test_hybrid_differs_from_dense_on_an_exact_term(workspace, indexes):
    """H2's premise: lexical matching should change the ranking for rare exact
    terms (drug names, thresholds). If hybrid == dense on every query, the
    hypothesis cannot be tested and the fusion is misconfigured."""
    from retrieve import get_retriever

    name = indexes["fixed"][0]
    dense = get_retriever.__wrapped__(name, "dense")
    hybrid = get_retriever.__wrapped__(name, "hybrid")

    differed = False
    for q in ["2000 ng/litre", "QRISK3 10%", "45 ml/min/1.73 m2", "amlodipine"]:
        d = [h["chunk_id"] for h in dense.search(q, 3)]
        hy = [h["chunk_id"] for h in hybrid.search(q, 3)]
        if d != hy:
            differed = True
            break
    assert differed, "hybrid ranking never differed from dense across exact-term queries"


# --------------------------------------------------------------------------
# 4. Span-overlap relevance (the bridge to the retrieval metrics)
# --------------------------------------------------------------------------

def test_gold_span_located_and_scored(workspace, indexes):
    """Simulates one evaluation-dataset row end to end: locate a verbatim
    passage in the source, retrieve for a question, and confirm the retrieved
    chunk is judged relevant by span overlap."""
    from retrieve import get_retriever
    from spans import covered_gold_spans, is_relevant, locate_span

    source = workspace["record"]["text"]
    passage = "Offer standard-release metformin to adults with type 2 diabetes"
    start, end = locate_span(source, passage)
    assert start >= 0, "gold passage not found in source text"
    assert source[start:end] == passage

    gold = [{"doc_id": "NG99", "start_char": start, "end_char": end}]

    name = indexes["fixed"][0]
    hits = get_retriever.__wrapped__(name, "dense").search(
        "Which drug is offered as initial treatment for type 2 diabetes?", 5)

    assert any(is_relevant(h, gold, min_overlap_chars=20) for h in hits), \
        "no retrieved chunk overlapped the gold span"
    assert covered_gold_spans(hits, gold, min_overlap_chars=20) == {0}
